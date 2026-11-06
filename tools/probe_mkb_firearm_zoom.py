"""Replay firearm zoom in build-release; preserve saves and leave slot 0 ready."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vr/tools"))
import inspect_weapon_sets as n
import probe_p38_headset as shared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--sensitivity", type=float, default=5)
    parser.add_argument("--aiming-sensitivity", type=float, default=4)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    exe = ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    hashes = {str(p): n.digest(p) for p in (ROOT / "saves").rglob("*") if p.is_file()}
    if args.pid is None:
        if n.game_pids():
            raise RuntimeError("Preserve the existing game session; explicitly supply its --pid")
        env = shared.clean_environment(os.environ)
        env.update(PSX_DEV_INPUT="0", PSX_LOAD_SLOT="-1")
        with (out / "stdout.log").open("w") as so, (out / "stderr.log").open("w") as se:
            proc = subprocess.Popen([str(exe), "--no-launcher", "--game", str(ROOT / "game.toml"),
                "--disc", str(ROOT / "Medal of Honor - Underground/Medal of Honor - Underground (USA).cue"),
                "--debug-port", "4372"], cwd=ROOT / "build-release", env=env,
                stdout=so, stderr=se, creationflags=subprocess.CREATE_NO_WINDOW)
        shared.wait_for_ping(proc)
        args.pid = proc.pid
    n.require_debugger_owner(args.pid)
    receipt = dict(pid=args.pid, binary_sha256=n.digest(exe), checks={}, cases={})
    old_snapshot = n.command("get_snapshots")["snapshots"][3]

    def command(value):
        n.command("mod_cmd", name="mohu.mkb.test", args=value)

    def reset(slot):
        n.load(slot)
        n.command("clear_input")
        command("motion 0 0")
        n.frames(6)

    def snapshot():
        actor = int.from_bytes(n.read(0x800AA17C, 4), "little")
        inp = actor + 0x3FC
        data = n.read(inp, 0x1DC)
        counters = n.command("mod_counters")["counters"]
        return dict(depth=struct.unpack_from("<I", data, 0xAC)[0],
                    flags=struct.unpack_from("<I", data)[0],
                    mode=struct.unpack_from("<I", data, 0x1D4)[0],
                    clip=struct.unpack_from("<h", data, 0x6E + 2 * data[92])[0],
                    position=list(struct.unpack("<3i", n.read(actor + 0x220, 12))),
                    angles=list(struct.unpack("<3i", n.read(actor + 0x23C, 12))),
                    h=int(n.command("gte_state")["gte_ctrl"][26], 16),
                    counters={r["name"]: r["count"] for r in counters})

    try:
        reset(0)
        before = snapshot()
        n.command("screenshot_hires", path=str(out / "normal.png"))
        actor = int.from_bytes(n.read(0x800AA17C, 4), "little")
        n.command("wtrace_range", lo=hex(actor + 0x4A8), hi=hex(actor + 0x4AC))
        n.command("wtrace_clear")
        command("aim 1")
        n.frames(12)
        aimed = snapshot()
        inward = n.command("wtrace_dump", count=32)["entries"]
        n.command("screenshot_hires", path=str(out / "aimed.png"))
        command("motion 30 0")
        n.frames(5)
        moved_mouse = snapshot()
        n.command("wtrace_clear")
        command("aim 0")
        n.frames(12)
        released = snapshot()
        outward = n.command("wtrace_dump", count=32)["entries"]
        n.command("wtrace_range", lo="0", hi="0")
        n.command("screenshot_hires", path=str(out / "released.png"))
        values_in = [int(r["new"], 16) for r in inward]
        values_out = [int(r["new"], 16) for r in outward]
        checks = receipt["checks"]
        # Live GTE H can belong to the held-weapon pass. Its world focal length
        # is the player's field, consumed by the native world projection.
        checks["projection_125"] = before["depth"] == 400 and aimed["depth"] == 500
        checks["eased_in"] = all(v in values_in for v in (426, 474, 500))
        checks["eased_out"] = all(v in values_out for v in (474, 426, 400))
        checks["no_stationary_aim"] = aimed["mode"] == 7 and not aimed["flags"] & 0x20
        expected = 30 * args.aiming_sensitivity / 10 / 1.25 * 65536
        checks["lower_sensitivity"] = abs(moved_mouse["angles"][1] - aimed["angles"][1] - expected) <= 1
        visible = "mohu.mkb.reticle.visible"
        tight = "mohu.mkb.firearm.reticle.tight"
        checks["reticle_while_aiming"] = aimed["counters"].get(visible, 0) > before["counters"].get(visible, 0)
        checks["tight_native_packets"] = aimed["counters"].get(tight, 0) > before["counters"].get(tight, 0)
        checks["weapon_visible_while_aiming"] = aimed["counters"].get("mohu.mkb.firearm.weapon.visible", 0) > 0
        after_release = snapshot()
        n.frames(12)
        checks["reticle_hidden_on_release"] = snapshot()["counters"].get(visible, 0) == after_release["counters"].get(visible, 0)
        # The visible weapon can leave its own projection in live GTE registers.
        # The player's stored world focal length is the release-state authority.
        checks["restored_focal_length"] = released["depth"] == 400
        receipt["cases"].update(before=before, aimed=aimed, released=released,
                                 zoom_in=inward, zoom_out=outward)
        command("aim 1")
        n.frames(10)
        start = snapshot()
        n.command("set_input", layer="host", buttons="0xffff", pad_type=1, lx=128, ly=0, rx=128, ry=128)
        n.frames(12)
        end = snapshot()
        checks["walking_while_zoomed"] = end["position"] != start["position"] and end["angles"] == start["angles"]
        n.command("clear_input")
        n.frames(6)
        camera = int.from_bytes(n.read(0x800AA160, 4), "little")
        n.command("set_snapshot", slot=3, addr=hex(camera + 0x220))
        n.command("wtrace_range", lo="0x800B0000", hi="0x801FC000")
        n.command("wtrace_clear")
        n.command("set_input", layer="host", buttons="0xbfff", pad_type=1, lx=128, ly=128, rx=128, ry=128)
        n.frames(10)
        n.command("clear_input")
        n.frames(10)
        checks["fire_while_zoomed"] = snapshot()["clip"] < end["clip"]
        types = n.command("wtrace_dump", count=32, pc_lo="0x800484CC", pc_hi="0x800484D0")
        bullets = [r for r in types["entries"] if int(r["new"], 16) == 0x13F6]
        shot = int(bullets[0]["s0"], 16) if bullets else 0
        constructor = n.command("wtrace_dump", count=256, pc_lo="0x8004815C", pc_hi="0x80048400",
                                addr_lo=hex(shot + 0x220), addr_hi=hex(shot + 0x22C))
        # Native construction can use the cached ray or the direct camera path.
        # Both populate this same position triplet before projectile motion.
        rows = constructor["entries"][-3:]
        origin = [int(e["new"], 16) for e in rows]
        origin = [v - 2**32 if v & 0x80000000 else v for v in origin]
        eye = list(struct.unpack("<3i", bytes.fromhex(n.command("read_frame_ram",
            frame=rows[0]["frame"], addr=hex(camera + 0x220), len=12)["hex"]))) if rows else []
        checks["live_zoomed_shot_origin"] = len(origin) == 3 and origin == eye
        receipt["cases"]["projectile_origin"] = dict(origin=origin, eye=eye, trace=constructor)
        n.command("wtrace_range", lo="0", hi="0")
        reset(1)
        n.command("set_input", buttons="0xfdff", pad_type=1, lx=128, ly=128, rx=128, ry=128)
        n.frames(180)
        sniper = snapshot()
        checks["native_sniper_kept"] = sniper["depth"] > 500 and sniper["mode"] == 7
        receipt["cases"]["sniper"] = sniper
        reset(1)
        n.command("mod_cmd", name="mohu.mkb.test", args="select 2")
        n.frames(45)
        crossbow_before = snapshot()
        command("aim 1")
        n.frames(12)
        crossbow = snapshot()
        actor = int.from_bytes(n.read(0x800AA17C, 4), "little")
        checks["crossbow_zoom"] = n.read(actor + 0x459, 1)[0] == 14 and crossbow["depth"] == 500
        checks["crossbow_crosshair"] = crossbow["counters"].get(visible, 0) > crossbow_before["counters"].get(visible, 0)
        checks["crossbow_visible"] = crossbow["counters"].get("mohu.mkb.firearm.weapon.visible", 0) > crossbow_before["counters"].get("mohu.mkb.firearm.weapon.visible", 0)
        receipt["cases"]["crossbow"] = crossbow
        n.command("screenshot_hires", path=str(out / "crossbow-aimed.png"))
    finally:
        n.command("wtrace_range", lo="0", hi="0")
        n.command("set_snapshot", slot=3, addr=old_snapshot["addr"] if old_snapshot["active"] else "0")
        reset(0)
        command("release")
        n.frames(8)
        n.command("clear_input")
        receipt["source_saves_unchanged"] = all(n.digest(Path(p)) == h for p, h in hashes.items())
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    failures = [k for k, v in receipt["checks"].items() if not v]
    print(json.dumps(dict(pid=args.pid, checks=len(receipt["checks"]), failures=failures,
                          source_saves_unchanged=receipt["source_saves_unchanged"]), indent=2))
    if failures or not receipt["source_saves_unchanged"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
