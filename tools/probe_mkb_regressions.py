"""Reproduce the operator's petrol-bomb look and slot-01 wall reports."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vr/tools"))
import inspect_weapon_sets as native
import probe_p38_headset as shared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--fixtures", type=Path, default=ROOT / "analysis/runtime/mkb-direct-play-20261106/saves/openbios")
    args = parser.parse_args()
    if native.game_pids():
        raise RuntimeError("Preserve the existing game session")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    target = out / "saves/openbios"
    target.mkdir(parents=True)
    files = sorted(args.fixtures.resolve().glob("*slot0[01].*"))
    if len(files) != 4:
        raise RuntimeError("Expected slot 00 and slot 01 plus thumbnails")
    hashes = {str(p): native.digest(p) for p in files}
    for p in files:
        shutil.copyfile(p, target / p.name)
    exe = ROOT / "build-mkb-probe/Medal_of_Honor_Underground_Recompiled.exe"
    env = shared.clean_environment(os.environ)
    env.update(SDL_AUDIODRIVER="dummy", PSX_DEV_INPUT="0", PSX_LOAD_SLOT="-1")
    receipt = dict(binary_sha256=native.digest(exe), source_hashes=hashes,
                   preferences=shared.hash_existing(shared.preference_paths()), cases={})
    owns_debugger = False

    def command(args):
        result = native.command("mod_cmd", name="mohu.mkb.test", args=args)
        if result["result"] != 1:
            raise RuntimeError(result)

    def host(*, ly=128):
        native.command("set_input", layer="host", buttons=0xffff, pad_type=1,
                       lx=128, ly=ly, rx=128, ry=128)

    def snapshot(label):
        player = int.from_bytes(native.read(0x800AA17C, 4), "little")
        actor = native.read(player, 0x500)
        inp = struct.unpack_from("<I", actor, 0x39c)[0]
        if inp != player + 0x3fc:
            raise RuntimeError("Unexpected player layout")
        data = native.read(inp, 0x300)
        row = dict(label=label, frame=native.command("frame")["frame"],
                   position=list(struct.unpack_from("<3i", actor, 0x220)),
                   rotation=list(struct.unpack_from("<3i", actor, 0x23c)),
                   angular_velocity=list(struct.unpack_from("<3i", actor, 0x248)),
                   velocity=list(struct.unpack_from("<3i", actor, 0x254)),
                   flags=hex(struct.unpack_from("<I", data)[0]),
                   weapon_slot=data[92], weapon_id=data[93],
                   mode=struct.unpack_from("<I", data, 0x1d4)[0],
                   previous_mode=struct.unpack_from("<I", data, 0x1d8)[0],
                   pitch_target=struct.unpack_from("<i", data, 0x184)[0],
                   yaw_target=struct.unpack_from("<i", data, 0x190)[0],
                   pad=native.command("pad_status")["slot0"])
        (out / f"{label}.actor.bin").write_bytes(actor)
        (out / f"{label}.input.bin").write_bytes(data)
        print(json.dumps({k:v for k,v in row.items() if k != "pad"}), flush=True)
        return row

    def load(slot):
        native.load(slot)
        native.command("clear_input")
        host()
        native.frames(30)

    with (out / "stdout.log").open("w") as so, (out / "stderr.log").open("w") as se:
        proc = subprocess.Popen([str(exe), "--no-launcher", "--headless-opengl",
            "--game", str(ROOT / "game.toml"), "--disc",
            str(ROOT / "Medal of Honor - Underground/Medal of Honor - Underground (USA).cue"),
            "--memcard-dir", str(out / "saves"), "--debug-port", "4372"],
            cwd=out, env=env, stdout=so, stderr=se, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            shared.wait_for_ping(proc)
            native.require_debugger_owner(proc.pid)
            owns_debugger = True
            load(0)
            command("motion 0 0")
            native.frames(8)
            command("select 2")
            native.frames(90)
            before = snapshot("bomb_before")
            command("motion 32 -16")
            native.frames(16)
            after = snapshot("bomb_after")
            receipt["cases"]["bomb"] = [before, after]
            native.command("screenshot_hires", path=str(out / "bomb.png"))
            load(0)
            command("motion 0 0")
            native.frames(8)
            rows = [snapshot("down_start")]
            command("motion 0 500")
            native.frames(8)
            rows.append(snapshot("down_look"))
            for i in range(4):
                native.frames(15)
                rows.append(snapshot(f"down_idle_{i}"))
            receipt["cases"]["down"] = rows
            native.command("screenshot_hires", path=str(out / "down.png"))
            for direct in (False, True):
                name = "direct" if direct else "native"
                load(1)
                if direct:
                    command("motion 0 0")
                    native.frames(8)
                rows = [snapshot(f"wall_{name}_start")]
                host(ly=0)
                for i in range(8):
                    native.frames(15)
                    rows.append(snapshot(f"wall_{name}_{i}"))
                host()
                native.frames(30)
                rows.append(snapshot(f"wall_{name}_released"))
                native.command("screenshot_hires", path=str(out / f"wall_{name}.png"))
                receipt["cases"][f"wall_{name}"] = rows
            receipt["counters"] = native.command("mod_counters")
            wrap = 4096 * 65536
            bomb_before, bomb_after = receipt["cases"]["bomb"]
            wall = receipt["cases"]["wall_direct"]
            down = receipt["cases"]["down"]
            receipt["checks"] = {
                "bomb_yaw": (bomb_after["rotation"][1] - bomb_before["rotation"][1]) % wrap == 32 * 65536,
                "bomb_pitch": bomb_after["rotation"][0] - bomb_before["rotation"][0] == 16 * 65536,
                "wall_no_uncommanded_turn": all(r["rotation"][1] == wall[0]["rotation"][1] for r in wall),
                "wall_no_angular_velocity": all(r["angular_velocity"] == [0, 0, 0] for r in wall[1:]),
                "down_no_uncommanded_turn": all(r["rotation"][1] == down[0]["rotation"][1] for r in down),
                "down_pitch_exact": down[1]["rotation"][0] - down[0]["rotation"][0] == -500 * 65536,
                "down_no_idle_drift": all(r["rotation"] == down[1]["rotation"] for r in down[1:]),
            }
        finally:
            if owns_debugger:
                try:
                    native.command("quit")
                except (OSError, RuntimeError):
                    pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=10)
            receipt["exit_code"] = proc.returncode
            receipt["source_saves_unchanged"] = all(native.digest(Path(p)) == h for p,h in hashes.items())
            receipt["preferences_unchanged"] = shared.hash_existing(shared.preference_paths()) == receipt["preferences"]
            (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if not all(receipt.get("checks", {}).values()) or not receipt.get("checks"):
        raise RuntimeError("Regression checks failed; inspect receipt.json")


if __name__ == "__main__":
    main()
