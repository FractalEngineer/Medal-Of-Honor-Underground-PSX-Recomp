"""Check scoped-rifle controls in an explicitly owned build-release session.

Loads slot 1 without saving. The output directory holds evidence, never builds.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vr/tools"))
import inspect_weapon_sets as native


def snapshot():
    frame = native.command("frame")["frame"]
    player = int.from_bytes(native.read(0x800AA17C, 4), "little")
    if not 0x800B0000 <= player <= 0x801FC000 or player & 3:
        raise RuntimeError("Not a campaign player")
    actor = native.read(player, 0x800)
    if struct.unpack_from("<I", actor, 8)[0] != 1 or \
            struct.unpack_from("<I", actor, 0x39C)[0] != player + 0x3FC:
        raise RuntimeError("Unexpected campaign actor")
    return dict(frame=frame, position=list(struct.unpack_from("<3i", actor, 0x220)),
                angles=list(struct.unpack_from("<3i", actor, 0x23C)),
                flags=struct.unpack_from("<I", actor, 0x3FC)[0],
                mode=struct.unpack_from("<I", actor, 0x5D0)[0],
                weapon=actor[0x459], clip=struct.unpack_from("<h", actor, 0x46A)[0],
                depth=struct.unpack_from("<I", actor, 0x4A8)[0])


def pad(scope, lx=128, ly=128, rx=128, buttons=0xFFFF):
    native.command("set_input", layer="host", pad_type=1,
                   buttons=buttons & (0xFDFF if scope else 0xFFFF),
                   lx=lx, ly=ly, rx=rx, ry=128)


def reset(scope):
    native.load(1)
    # load() leaves a raw neutral override; host-layer tests must release it.
    native.command("clear_input")
    native.command("mod_cmd", name="mohu.mkb.test", args="motion 0 0")
    native.frames(3)
    pad(scope)
    native.frames(180 if scope else 20)
    state = snapshot()
    if state["weapon"] != 5:
        raise RuntimeError("Slot 1 must contain the scoped rifle in slot 0")
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--sensitivity", type=float, default=50)
    parser.add_argument("--scoped-sensitivity", type=float, default=100)
    args = parser.parse_args()
    native.require_debugger_owner(args.pid)
    args.out.mkdir(parents=True, exist_ok=True)
    exe = ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    sources = sorted((ROOT / "saves").rglob("*"))
    hashes = {str(p): native.digest(p) for p in sources if p.is_file()}
    receipt = dict(pid=args.pid, binary_sha256=native.digest(exe), checks=[], cases={})
    old_snapshots = native.command("get_snapshots")["snapshots"]

    def check(name, passed):
        receipt["checks"].append(dict(name=name, passed=bool(passed)))

    try:
        for scoped in (False, True):
            label = "scoped" if scoped else "unscoped"
            before = reset(scoped)
            check(label + "_walk_mode", before["mode"] == 7)
            check(label + "_native_scope_flag", bool(before["flags"] & 0x20) == scoped)
            native.command("mod_cmd", name="mohu.mkb.test", args="motion 60 25")
            native.frames(8)
            after = snapshot()
            yaw = (after["angles"][1] - before["angles"][1]) % (4096 << 16)
            pitch = after["angles"][0] - before["angles"][0]
            gain = args.sensitivity / 100
            if scoped:
                gain *= args.scoped_sensitivity / 100 * 400 / max(400, before["depth"])
            check(label + "_direct_mouse", abs(yaw - 60 * gain * 65536) <= 1 and
                  abs(pitch + 25 * gain * 65536) <= 1)
            native.frames(20)
            idle = snapshot()
            check(label + "_no_idle_drift", after["angles"] == idle["angles"])
            receipt["cases"][label + "_look"] = dict(before=before, after=after, idle=idle)
            native.command("screenshot_hires", path=str((args.out / (label + ".png")).resolve()))

            for movement, ly, rx in (("forward", 0, 128), ("back", 255, 128),
                                      ("left", 128, 0), ("right", 128, 255),
                                      ("diagonal", 0, 255)):
                start = reset(scoped)
                player = int.from_bytes(native.read(0x800AA17C, 4), "little")
                native.command("set_snapshot", slot=3, addr=hex(player + 0x220))
                native.frames(3)
                first_frame = native.command("frame")["frame"]
                pad(scoped, ly=ly, rx=rx)
                native.frames(24)
                pad(scoped)
                last_frame = native.command("frame")["frame"]
                end = snapshot()
                # Read immutable frame snapshots. Live debugger requests can
                # land on different sides of a native update or input sample.
                trajectory = []
                for f in range(first_frame, last_frame):
                    raw = bytes.fromhex(native.command("read_frame_ram", frame=f,
                        addr=hex(player + 0x220), len=44)["hex"])
                    trajectory.append(dict(frame=f, position=list(struct.unpack_from("<3i", raw)),
                                           angles=list(struct.unpack_from("<3i", raw, 0x1C))))
                steps = [math.hypot(b["position"][0] - a["position"][0],
                                    b["position"][2] - a["position"][2])
                         for a, b in zip(trajectory, trajectory[1:])]
                moving_steps = [d for d in steps if d > 65536]
                delta = [b - a for a, b in zip(start["position"], end["position"])]
                distance = math.hypot(delta[0], delta[2])
                check(label + "_" + movement + "_moves", distance > 65536)
                check(label + "_" + movement + "_sustained", len(moving_steps) >= 4)
                check(label + "_" + movement + "_keeps_angles", end["angles"] == start["angles"])
                receipt["cases"][label + "_" + movement] = dict(
                    before=start, after=end, delta=delta, distance=distance,
                    trajectory=trajectory, moving_steps=moving_steps,
                    native_step=statistics.median(moving_steps[1:8]) if len(moving_steps) > 1 else 0)

        for movement in ("forward", "back", "left", "right", "diagonal"):
            scoped = receipt["cases"]["scoped_" + movement]["native_step"]
            normal = receipt["cases"]["unscoped_" + movement]["native_step"]
            check(movement + "_scope_keeps_speed", 0.8 < scoped / normal < 1.25)

        start = reset(True)
        pad(True, buttons=0xBFFF)
        native.frames(12)
        pad(True)
        native.frames(40)
        fired = snapshot()
        check("scoped_native_fire", fired["clip"] == start["clip"] - 1)
        receipt["cases"]["fire"] = dict(before=start, after=fired)
        pad(False)
        native.frames(20)
        released = snapshot()
        check("scope_release", released["mode"] == 7 and not released["flags"] & 0x20)
        receipt["cases"]["release"] = released
        restored = reset(False)
        check("restore_clears_scope", restored["mode"] == 7 and not restored["flags"] & 0x20)
        receipt["counters"] = native.command("mod_counters")
        receipt["scanlines"] = native.command("scanline")
        check("scanlines_off", receipt["scanlines"]["scanlines"] == 0)
        receipt["dithering"] = native.command("dithering")
        check("dithering_off", receipt["dithering"]["mode"] == 0)
    finally:
        old = old_snapshots[3]
        native.command("set_snapshot", slot=3, addr=old["addr"] if old["active"] else "0x0")
        native.command("clear_input")
        native.command("mod_cmd", name="mohu.mkb.test", args="release")
        receipt["source_saves_unchanged"] = all(native.digest(Path(p)) == h for p, h in hashes.items())
        (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    failures = [c["name"] for c in receipt["checks"] if not c["passed"]]
    print(json.dumps(dict(checks=len(receipt["checks"]), failures=failures,
                          source_saves_unchanged=receipt["source_saves_unchanged"]), indent=2))
    if failures or not receipt["source_saves_unchanged"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
