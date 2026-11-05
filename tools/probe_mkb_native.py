"""Collect Underground native aim evidence in an isolated flat test session.

Only copied saves are loaded. This is a research tool, not a mouse mod or a
production input path. No VR activation, code patches, or source-save writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
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
    parser.add_argument("--slot", type=int, choices=range(12), default=3)
    parser.add_argument("--cold", action="store_true", help="Reach gameplay through native menus instead of loading a save")
    parser.add_argument("--fixtures", type=Path, default=ROOT / "analysis/fixtures/sp/openbios")
    parser.add_argument("--inject", action="store_true", help="Research only: perturb the statically traced native aim targets")
    parser.add_argument("--interpreter", action="store_true", help="Request diagnostic interpreter controls")
    args = parser.parse_args()
    if native.game_pids():
        raise RuntimeError("Existing game session; leave it untouched")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    target = out / "saves/openbios"
    target.mkdir(parents=True)
    source = args.fixtures.resolve()
    fixtures = [] if args.cold else sorted(source.glob(f"*slot{args.slot:02}.*"))
    if not args.cold and sorted(p.suffix for p in fixtures) != [".pst", ".thumb"]:
        raise RuntimeError("Expected one operator fixture and thumbnail")
    hashes = {str(p): native.digest(p) for p in fixtures}
    for path in fixtures:
        shutil.copyfile(path, target / path.name)
    preferences = shared.hash_existing(shared.preference_paths())
    exe = ROOT / "build-probe/Medal_of_Honor_Underground_Recompiled.exe"
    env = shared.clean_environment(os.environ)
    env.update(SDL_AUDIODRIVER="dummy", PSX_DEV_INPUT="0", PSX_LOAD_SLOT="-1")
    config = ROOT / "game.toml"
    if args.interpreter:
        env["PSX_OVERLAY_NATIVE_OFF"] = "1"
        contents = config.read_text(encoding="utf-8")
        contents, changes = re.subn(r"(?m)^overlay_cache\s*=\s*true$", "overlay_cache = false", contents)
        if changes != 1:
            raise RuntimeError("Expected one overlay cache configuration")
        contents = re.sub(r'(?m)^exe = .*$', lambda _: 'exe = ' + json.dumps(str(ROOT / 'disc/SLUS_012.70')), contents)
        config = out / "game-interpreter.toml"
        config.write_text(contents, encoding="utf-8")
    receipt = dict(collection_complete=False, native_mouse_aim_verified=False,
                   call_order_verified=False,
                   binary_sha256=native.digest(exe), source_hashes=hashes,
                   config_sha256=native.digest(config),
                   vr_requested=False, interpreter_diagnostic=args.interpreter, samples=[])

    def snapshot(label):
        player = int.from_bytes(native.read(0x800AA17C, 4), "little")
        if not 0x800B0000 <= player <= 0x801FC000:
            raise RuntimeError(f"Invalid SP player {player:#x}")
        data = native.read(player, 0x500)
        if player & 3 or struct.unpack_from("<I", data, 8)[0] != 1:
            raise RuntimeError("SP root does not own a player actor")
        (out / f"{label}.actor.bin").write_bytes(data)
        inp = struct.unpack_from("<I", data, 0x39C)[0]
        if inp != player + 0x3FC:
            raise RuntimeError("Unrecognized campaign input layout")
        code = native.read(0x800892C8, 0xF20)
        if hashlib.sha256(code).hexdigest() != "6517965996647b2589bf95f282f5c3bd7f1b8c6bf0118b0a3b6495960e16d401":
            raise RuntimeError("Unsupported single-player overlay")
        controls = native.read(inp, 0x300)
        (out / f"{label}.input.bin").write_bytes(controls)
        row = dict(label=label, frame=native.command("frame"), player=hex(player),
                   input=hex(inp), pad=native.command("pad_status"),
                   position=struct.unpack_from("<3i", data, 0x220),
                   rotation_q16=struct.unpack_from("<3i", data, 0x23C),
                   rotation_velocity_q16=struct.unpack_from("<3i", data, 0x248),
                   input_flags=hex(struct.unpack_from("<I", controls)[0]),
                   aim_pitch_q16=struct.unpack_from("<i", controls, 0x184)[0],
                   aim_yaw_q16=struct.unpack_from("<i", controls, 0x190)[0],
                   weapon_id=controls[93],
                   weapon_slot=controls[92],
                   clip=struct.unpack_from("<h", controls, 0x6E + 2 * controls[92])[0] if controls[92] < 8 else None,
                   pause=int.from_bytes(native.read(0x800A70F0, 4), "little"))
        receipt["samples"].append(row)
        print(json.dumps({k: v for k, v in row.items() if k != "pad"}), flush=True)
        return row

    with (out / "stdout.log").open("w") as so, (out / "stderr.log").open("w") as se:
        proc = subprocess.Popen([
            str(exe), "--no-launcher", "--headless-opengl", "--game", str(config),
            "--disc", str(ROOT / "Medal of Honor - Underground/Medal of Honor - Underground (USA).cue"),
            "--memcard-dir", str(out / "saves"), "--debug-port", "4372"],
            cwd=out, env=env, stdout=so, stderr=se, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            shared.wait_for_ping(proc)
            if args.cold:
                native.command("set_input", buttons="0xffff")
                native.frames(1200)
                receipt["menu_inputs"] = []
                for buttons in ["0xfff7"] * 4 + ["0xbfff"] * 12:
                    player = int.from_bytes(native.read(0x800AA17C, 4), "little")
                    if 0x800B0000 <= player <= 0x801FC000 and int.from_bytes(native.read(player + 8, 4), "little") == 1:
                        break
                    receipt["menu_inputs"].append(dict(buttons=buttons, frame=native.command("frame")))
                    native.command("set_input", buttons=buttons)
                    native.frames(5)
                    native.command("set_input", buttons="0xffff")
                    native.frames(150)
                native.frames(120)
            else:
                receipt["load"] = native.load(args.slot)
            native.command("set_input", buttons="0xffff", pad_type=1, lx=128, ly=128, rx=128, ry=128)
            native.frames(90)
            snapshot("neutral")
            if args.inject:
                for label, offset in [("yaw_target", 0x190), ("pitch_target", 0x184)]:
                    native.frames(120)
                    before = snapshot(label + "_before")
                    address = int(before["input"], 16) + offset + 2
                    byte = native.read(address, 1)[0]
                    delta = 32 if byte < 224 else -32
                    receipt.setdefault("injections", []).append(dict(address=hex(address), before=byte, after=byte + delta,
                                                                     native_angle_delta=delta))
                    native.command("write_ram", addr=hex(address), val=hex(byte + delta))
                    native.frames(4)
                    snapshot(label + "_early")
                    native.frames(120)
                    snapshot(label + "_settled")
                # The dispatch ring does not cover internal dirty-RAM calls.
                # Use the function-entry ring, with its physical range filter.
                native.command("fn_filter", lo="0x00076000", hi="0x00090000")
                native.command("fn_clear")
                native.command("set_input", buttons="0xbfff", pad_type=1)
                native.frames(6)
                native.command("set_input", buttons="0xffff", pad_type=1)
                trace = native.command("fn_entry_dump", count=2048)
                native.command("fn_disable")
                (out / "aim_call_order.json").write_text(json.dumps(trace, indent=2) + "\n")
                receipt["function_trace_entries"] = len(trace["entries"])
                if not trace["entries"]:
                    receipt["unresolved"] = "No internal player-update entries reached the trace ring; call ordering and update ownership are unproven"
            for label, axes in [("turn_right", dict(lx=255)), ("turn_left", dict(lx=0)),
                                ("look_up", dict(ry=0)), ("look_down", dict(ry=255))]:
                native.command("set_input", buttons="0xffff", pad_type=1, lx=128, ly=128, rx=128, ry=128)
                before = snapshot(label + "_before")
                player = int(before["player"], 16)
                native.command("wtrace_range", lo=hex(player + 0x220), hi=hex(player + 0x260))
                native.command("wtrace_clear")
                native.command("set_input", buttons="0xffff", pad_type=1, **axes)
                native.frames(12)
                snapshot(label + "_held")
                trace = native.command("wtrace_dump", count=128)
                (out / f"{label}.writes.json").write_text(json.dumps(trace, indent=2) + "\n")
                native.command("set_input", buttons="0xffff", pad_type=1, lx=128, ly=128, rx=128, ry=128)
                native.frames(12)
                snapshot(label + "_after")
            native.command("screenshot_hires", path=str(out / "baseline.png"))
            # Read resident overlay bytes in bounded debugger packets.
            ram = bytearray()
            for offset in range(0, 0x100000, 0x1000):
                ram.extend(native.read(0x80000000 + offset, 0x1000))
            (out / "resident.bin").write_bytes(ram)
            for label, address, count in [("player_update", 0x800892C8, 970),
                                          ("analog_converter", 0x80083C6C, 81),
                                          ("player_movement", 0x8008D800, 2300),
                                          ("actor_dispatch", 0x80078E08, 200)]:
                result = [native.command("disasm", addr=hex(address + offset * 4), count=min(256, count - offset))
                          for offset in range(0, count, 256)]
                (out / f"{label}.disasm.json").write_text(json.dumps(result, indent=2) + "\n")
            native.command("savestate", op="save", slot=0)
            native.frames(15)
            receipt["saved_fixture"] = native.command("savestate_status")
            if receipt["saved_fixture"]["pending"] or not receipt["saved_fixture"]["last_ok"]:
                raise RuntimeError("Probe fixture save did not complete successfully")
            receipt["collection_complete"] = True
        except Exception as error:
            receipt["error"] = f"{type(error).__name__}: {error}"
            raise
        finally:
            try:
                native.command("quit")
            except (OSError, RuntimeError):
                pass
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                receipt["forced_cleanup"] = True
                proc.terminate()
                proc.wait(timeout=8)
            receipt.update(exit_code=proc.returncode,
                           source_saves_unchanged=all(native.digest(Path(k)) == v for k, v in hashes.items()),
                           preferences_unchanged=shared.hash_existing(shared.preference_paths()) == preferences,
                           remaining_game_pids=native.game_pids())
            (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps({k: v for k, v in receipt.items() if k != "samples"}), flush=True)


if __name__ == "__main__":
    main()
