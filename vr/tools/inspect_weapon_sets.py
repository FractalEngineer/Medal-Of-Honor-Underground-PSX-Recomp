"""Inventory operator-owned Underground saves in an isolated flat process.

Uses the reference game's copied-save/native-input procedure. No save, ammo,
controller setting, game config, or guest code is edited.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "psxrecomp/tools"))
from debug_client import connect, send_cmd

WEAPONS = {0: "P38 pistol", 1: "MP40", 4: "Shotgun", 5: "Scoped rifle",
           8: "Colt .45", 9: "Silenced pistol", 10: "Stick grenade",
           12: "M1 Garand", 13: "Panzerfaust", 14: "Crossbow",
           15: "Petrol bomb", 16: "Sten", 17: "StG44"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def game_pids():
    result = subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-Process Medal_of_Honor_Underground_Recompiled -ErrorAction SilentlyContinue | ForEach-Object { $_.Id }"],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return [int(value) for value in result.stdout.split()]


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def command(name, **values):
    with connect(port=4372, timeout=25) as sock:
        result = send_cmd(sock, {"cmd": name, **values})
    if not result.get("ok"):
        raise RuntimeError(result)
    return result


def frames(count):
    start = command("frame")["frame"]
    deadline = time.monotonic() + 35
    while command("frame")["frame"] - start < count:
        if time.monotonic() > deadline:
            raise TimeoutError("Guest frames stopped advancing")
        time.sleep(.02)


def load(slot):
    before = command("savestate_status")
    command("savestate", op="load", slot=slot)
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        state = command("savestate_status")
        if state["generation"] > before["generation"] and not state["pending"]:
            if not state["last_ok"] or state["last_slot"] != slot:
                raise RuntimeError("Invalid fixture: ask the operator for a fresh PGXP slot")
            command("set_input", buttons="0xffff")
            command("set_input", port=2, buttons="0xffff")
            frames(30)
            return state
        time.sleep(.05)
    raise TimeoutError("Save load did not complete")


def read(address, size):
    return bytes.fromhex(command("read_ram", addr=hex(address), len=size)["hex"])


def players():
    result = []
    for port, glob in ((1, 0x800A3604), (2, 0x800A3608)):
        actor = int.from_bytes(read(glob, 4), "little")
        if not 0x800B0000 <= actor < 0x801FC000:
            raise RuntimeError("Unrecognized multiplayer player root")
        data = read(actor, 0x400)
        inp = struct.unpack_from("<I", data, 0x39C)[0]
        if struct.unpack_from("<I", data, 8)[0] != 1 or inp != actor + 0x400:
            raise RuntimeError("Unrecognized multiplayer actor/input layout")
        control = read(inp, 128)
        if control[92] > 3:
            raise RuntimeError("Unrecognized loadout slot")
        result.append({"port": port, "actor": hex(actor), "input": hex(inp),
            "weapon_slot": control[92], "weapon_id": control[93],
            "weapon": WEAPONS.get(control[93], "Unknown"),
            "reserve": struct.unpack_from("<h", control, 94 + control[92] * 2)[0],
            "clip": struct.unpack_from("<h", control, 110 + control[92] * 2)[0],
            "input_fields": control[60:128].hex(),
            "health_raw": struct.unpack_from("<i", data, 0x108)[0],
            "health": struct.unpack_from("<i", data, 0x108)[0] / 65536,
            "position": struct.unpack_from("<3i", data, 0x220),
            "rotation": struct.unpack_from("<3h", data, 0x23C)})
    return result


def switch():
    command("press", buttons=65535 ^ 0x2000, frames=12)
    frames(90)
    command("set_input", buttons="0xffff")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--slots", type=int, nargs="+", default=[1, 2, 3, 4])
    parser.add_argument("--cycle", action="store_true")
    parser.add_argument("--damage", action="store_true")
    parser.add_argument("--discover-damage", action="store_true")
    parser.add_argument("--only-damage-ids", type=int, nargs="+")
    parser.add_argument("--fire-frames", type=int, default=24)
    parser.add_argument("--release-frames", type=int, default=240)
    parser.add_argument("--scoped-zoom", action="store_true")
    parser.add_argument("--control", choices=("fire", "idle", "turn-away"), default="fire")
    parser.add_argument("--approach-frames", type=int, default=0)
    args = parser.parse_args()
    if any(not 0 <= slot <= 99 for slot in args.slots):
        parser.error("Slots must be in 0..99")
    if not 1 <= args.fire_frames <= 600 or not 1 <= args.release_frames <= 1800 or not 0 <= args.approach_frames <= 600:
        parser.error("Frame window exceeds the bounded control limits")
    if args.damage and not args.cycle:
        parser.error("--damage requires --cycle")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic TCP port occupied")
    if game_pids():
        raise RuntimeError("Close the existing game before starting this owned test")
    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    copies = out / "saves/openbios"
    copies.mkdir(parents=True)
    sources = []
    for slot in args.slots:
        for suffix in ("pst", "thumb"):
            path = ROOT / f"saves/openbios/state_8001F844_slot{slot:02}.{suffix}"
            if not path.is_file():
                raise FileNotFoundError(path)
            sources.append(path)
            shutil.copyfile(path, copies / path.name)
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in sources}
    preferences = [ROOT / "build-release/settings.toml", ROOT / "build-release/keybinds.ini",
                   Path("C:/Program Files (x86)/Steam/config/steamvr.vrsettings")]
    preference_hashes = {str(p): digest(p) for p in preferences if p.is_file()}
    exe = ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PSX_", "MOHU_VR_"))}
    env.update(PSX_DEV_INPUT="0", PSX_VSYNC="0", PSX_OPENXR_ENABLE="0")
    receipt = {"executable_sha256": digest(exe), "source_saves": hashes,
               "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "diagnostic_game_config_sha256": digest(ROOT / "analysis/vr-baseline/game-interp.toml"),
               "preference_hashes": preference_hashes,
               "controls": {"case": args.control, "fire_frames": args.fire_frames,
                            "release_frames": args.release_frames, "scoped_zoom": args.scoped_zoom,
                            "approach_frames": args.approach_frames},
               "slots": [], "complete": False}
    with (out / "stdout.log").open("w") as stdout, (out / "stderr.log").open("w") as stderr:
        process = subprocess.Popen([str(exe), "--headless-opengl", "--no-launcher",
            "--game", str(ROOT / "analysis/vr-baseline/game-interp.toml"),
            "--memcard-dir", str(out / "saves"), "--debug-port", "4372"],
            cwd=out, env=env, stdout=stdout, stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 40
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f"Diagnostic startup exited: {process.returncode}")
                try:
                    command("ping")
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(.1)
            for slot in args.slots:
                state = load(slot)
                damage_code = read(0x8004EAB4, 532)
                if hashlib.sha256(damage_code).hexdigest() != "5ee9683eb0646d46a39e0b552f214fe90be010d2d41cebbe45fadc2db2a1b9e5":
                    raise RuntimeError("Unrecognized native damage function")
                directory = out / f"slot-{slot:02}"
                directory.mkdir()
                (directory / "ram.bin").write_bytes(read(0x80000000, 0x200000))
                command("screenshot_file", path=str(directory / "flat.png"))
                row = {"slot": slot, "load": state, "captures": []}
                receipt["slots"].append(row)
                seen = set()
                for index in range(13 if args.cycle else 1):
                    current = players()
                    row["captures"].append({"switches": index, "players": current})
                    save(out / "inventory.json", receipt)
                    key = (current[0]["weapon_slot"], current[0]["weapon_id"])
                    print(slot, index, key, flush=True)
                    if key in seen:
                        row["cycle_closed"] = True
                        break
                    seen.add(key)
                    if args.discover_damage:
                        before = read(0x80000000, 0x200000)
                        (directory / "before-fire.bin").write_bytes(before)
                        target = int(current[1]["actor"], 16)
                        command("wtrace_range", lo=hex(target), hi=hex(target + 0x500))
                        command("wtrace_clear")
                        command("press", buttons=65535 ^ 0x4000, frames=24)
                        frames(100)
                        (directory / "after-fire.bin").write_bytes(read(0x80000000, 0x200000))
                        save(directory / "actor-writes.json", command("wtrace_dump", count=2048))
                        command("screenshot_file", path=str(directory / "after-fire.png"))
                        command("wtrace_range", lo="0", hi="0")
                        break
                    if args.cycle:
                        command("screenshot_file", path=str(directory / f"weapon-{index:02}.png"))
                        if args.damage and (not args.only_damage_ids or key[1] in args.only_damage_ids):
                            load(slot)
                            for unused in range(index):
                                switch()
                            before = players()
                            if (before[0]["weapon_slot"], before[0]["weapon_id"]) != key:
                                raise RuntimeError("Fresh-load weapon preparation disagrees")
                            if args.approach_frames:
                                command("press", buttons=65535 ^ 0x10, frames=args.approach_frames)
                                frames(args.approach_frames + 12)
                                row["captures"][-1]["approach"] = players()
                                command("screenshot_file", path=str(directory / f"approach-{index:02}.png"))
                                before = players()
                            for player in before:
                                address = int(player["actor"], 16) + 0x108
                                command("wtrace_range" if player["port"] == 1 else "wtrace_add",
                                        lo=hex(address), hi=hex(address + 4))
                            command("wtrace_clear")
                            if args.control == "turn-away":
                                command("press", buttons=65535 ^ 0x20, frames=180)
                                frames(190)
                                row["captures"][-1]["turned"] = players()
                                command("screenshot_file", path=str(directory / f"turned-{index:02}.png"))
                            if args.scoped_zoom and key[1] == 5:
                                command("set_input", buttons="0xfdff")
                                frames(60)
                            start_frame = command("frame")["frame"]
                            if args.control != "idle":
                                command("press", buttons=65535 ^ (0x4200 if args.scoped_zoom and key[1] == 5 else 0x4000), frames=args.fire_frames)
                            frames(args.fire_frames + args.release_frames)
                            command("set_input", buttons="0xffff")
                            after = players()
                            trace = command("wtrace_dump", count=2048)
                            if trace["total"] != trace["available"] or trace["emitted"] != trace["total"]:
                                raise RuntimeError("Health write trace incomplete")
                            command("wtrace_range", lo="0", hi="0")
                            row["captures"][-1]["fire"] = {"before": before, "after": after, "health_trace": trace,
                                "frame_window": [start_frame, command("frame")["frame"]]}
                            save(out / "inventory.json", receipt)
                            print("damage", before[1]["health"], after[1]["health"], trace["emitted"], flush=True)
                            load(slot)
                            for unused in range(index):
                                switch()
                        switch()
                save(out / "inventory.json", receipt)
                if args.cycle and not row.get("cycle_closed"):
                    raise RuntimeError("Weapon cycle did not close within 12 switches")
                print(f"Slot {slot} loaded", flush=True)
            receipt["complete"] = True
        finally:
            if process.poll() is None:
                try:
                    command("clear_input")
                    command("clear_input", port=2)
                    command("quit")
                except (OSError, RuntimeError):
                    pass
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=8)
            receipt["exit_code"] = process.returncode
            receipt["source_saves_unchanged"] = all(digest(ROOT / p) == value for p, value in hashes.items())
            receipt["preferences_unchanged"] = all(digest(Path(p)) == value for p, value in preference_hashes.items())
            receipt["remaining_game_pids"] = game_pids()
            save(out / "inventory.json", receipt)
    assert receipt["source_saves_unchanged"] and receipt["preferences_unchanged"] and not receipt["remaining_game_pids"]


if __name__ == "__main__":
    main()
