"""Read or drive the disposable live MKB test session through the debugger."""
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


def start_session(out: Path, slot: int, source: Path) -> dict:
    if native.game_pids():
        raise RuntimeError("Existing game session; leave it untouched")
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = source.resolve()
    selected = sorted(source.glob(f"*slot{slot:02}.*"))
    if sorted(p.suffix for p in selected) != [".pst", ".thumb"]:
        raise RuntimeError("Expected a normal-build fixture and thumbnail")
    fixtures = sorted(p for p in source.glob("state_*_slot??.*")
                      if p.suffix in (".pst", ".thumb"))
    target = out / "saves/openbios"
    target.mkdir(parents=True)
    hashes = {str(p): native.digest(p) for p in fixtures}
    for path in fixtures:
        shutil.copyfile(path, target / path.name)
    exe = ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    env = shared.clean_environment(os.environ)
    env.update(SDL_AUDIODRIVER="dummy", PSX_DEV_INPUT="0", PSX_LOAD_SLOT="-1")
    with (out / "stdout.log").open("w") as so, (out / "stderr.log").open("w") as se:
        proc = subprocess.Popen([
            str(exe), "--no-launcher", "--game", str(ROOT / "game.toml"),
            "--disc", str(ROOT / "Medal of Honor - Underground/Medal of Honor - Underground (USA).cue"),
            "--memcard-dir", str(out / "saves"), "--debug-port", "4372"],
            cwd=out, env=env, stdout=so, stderr=se,
            creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        shared.wait_for_ping(proc)
        native.require_debugger_owner(proc.pid)
        loaded = native.load(slot)
        native.command("clear_input")
        result = {"pid": proc.pid, "binary_sha256": native.digest(exe),
                  "source_hashes": hashes, "load": loaded,
                  "preferences": shared.hash_existing(shared.preference_paths())}
        (out / "session.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    except Exception:
        proc.terminate()
        proc.wait(timeout=10)
        raise


def snapshot() -> dict:
    player = int.from_bytes(native.read(0x800AA17C, 4), "little")
    if not 0x800B0000 <= player <= 0x801FC000 or player & 3:
        raise RuntimeError(f"Invalid player pointer {player:#x}")
    actor = native.read(player, 0x500)
    if struct.unpack_from("<I", actor, 8)[0] != 1:
        raise RuntimeError("Player root is not a campaign actor")
    player_input = struct.unpack_from("<I", actor, 0x39C)[0]
    if player_input != player + 0x3FC:
        raise RuntimeError("Unexpected campaign input layout")
    control = native.read(player_input, 0x100)
    return {
        "frame": native.command("frame"),
        "pause": int.from_bytes(native.read(0x800A70F0, 4), "little"),
        "player": f"0x{player:08x}",
        "player_input": f"0x{player_input:08x}",
        "position": list(struct.unpack_from("<3i", actor, 0x220)),
        "rotation_q16": list(struct.unpack_from("<3i", actor, 0x23C)),
        "input_flags": f"0x{struct.unpack_from('<I', control, 0)[0]:08x}",
        "weapon_slot": control[92],
        "weapon_id": control[93],
        "weapon": native.SP_WEAPONS.get(control[93], "Unknown"),
        "clip": struct.unpack_from("<h", control, 0x6E + 2 * control[92])[0] if control[92] < 8 else None,
        "aim_pitch_q16": struct.unpack("<i", native.read(player_input + 0x184, 4))[0],
        "aim_yaw_q16": struct.unpack("<i", native.read(player_input + 0x190, 4))[0],
        "pad": native.command("pad_status"),
        "counters": native.command("mod_counters"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "ping", "load", "save", "snapshot",
                                           "screenshot", "quit"])
    parser.add_argument("--slot", type=int, default=0)
    parser.add_argument("--path", type=Path)
    parser.add_argument("--fixtures", type=Path,
                        default=ROOT / "saves/openbios")
    args = parser.parse_args()

    if args.action == "start":
        if not args.path:
            raise SystemExit("--path is required for a disposable session directory")
        result = start_session(args.path, args.slot, args.fixtures)
    elif args.action == "ping":
        result = native.command("ping")
    elif args.action == "load":
        result = native.load(args.slot)
        native.command("clear_input")
        result["host_input_released"] = True
    elif args.action == "save":
        native.command("savestate", op="save", slot=args.slot)
        native.frames(15)
        result = native.command("savestate_status")
        if result["pending"] or not result["last_ok"]:
            raise RuntimeError("Owned-session checkpoint failed")
    elif args.action == "snapshot":
        result = snapshot()
        if args.path:
            args.path.write_text(json.dumps(result, indent=2) + "\n")
    elif args.action == "screenshot":
        if not args.path:
            raise SystemExit("--path is required for screenshot")
        result = native.command("screenshot_hires", path=str(args.path.resolve()))
    else:
        result = native.command("quit")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
