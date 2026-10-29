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
MODEL_OBJECT_OFFSET = 0x4AC
MODEL_MAGIC = 0x00160024


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def game_pids():
    result = subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-Process Medal_of_Honor*Recompiled* -ErrorAction SilentlyContinue | ForEach-Object { $_.Id }"],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return [int(value) for value in result.stdout.split()]


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def command(cmd, **values):
    with connect(port=4372, timeout=25) as sock:
        result = send_cmd(sock, {"cmd": cmd, **values})
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


def p2_health_address(player):
    return (int(player["actor"], 16) + 0x108) & 0x1FFFFFFF


def p2_damage_in_trace(trace, player):
    address = p2_health_address(player)
    for entry in trace.get("entries", []):
        if (int(entry["addr"], 0) & 0x1FFFFFFF) != address:
            continue
        if int(entry["old"], 0) > int(entry["new"], 0):
            return True
    return False


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


def weapon_model():
    actor = int.from_bytes(read(0x800A3604, 4), "little")
    if not 0x800B0000 <= actor < 0x801FC000:
        raise RuntimeError("Unrecognized player-one root")
    inp = int.from_bytes(read(actor + 0x39C, 4), "little")
    obj = actor + MODEL_OBJECT_OFFSET
    header = int.from_bytes(read(obj + 0x80, 4), "little")
    if not 0x800B0000 <= header < 0x801FFFF8:
        raise RuntimeError("Unrecognized weapon node header")
    nodes = int.from_bytes(read(header, 4), "little")
    count = int.from_bytes(read(header + 4, 4), "little")
    if not 0x800B0000 <= nodes < 0x801FFFC0 or not 1 <= count <= 64:
        raise RuntimeError("Unrecognized weapon node table")
    table = read(nodes, count * 8)
    state = read(obj, 0x200)
    return {
        "actor": hex(actor),
        "input": hex(inp),
        "object": hex(obj),
        "magic": hex(int.from_bytes(state[0x70:0x74], "little")),
        "node_header": hex(header),
        "nodes": hex(nodes),
        "node_count": count,
        "node_counts": [struct.unpack_from("<H", table, i * 8 + 4)[0]
                        for i in range(count)],
        "node_table_sha256": hashlib.sha256(table).hexdigest(),
        "state_words": [state[i:i + 4].hex() for i in range(0x48, 0x94, 4)],
        "state_sha256": hashlib.sha256(state).hexdigest(),
    }


def switch():
    command("press", buttons=65535 ^ 0x2000, frames=12)
    frames(90)
    command("set_input", buttons="0xffff")


def first_person_model():
    """Read the native MP viewmodel pointer, independently of the body object."""
    actor = int(players()[0]["actor"], 16)
    inp = int.from_bytes(read(actor + 0x39C, 4), "little")
    obj = int.from_bytes(read(actor + 0x114, 4), "little")
    if obj != inp + 0x9F0:
        raise RuntimeError("Unrecognized first-person object contract")
    state = read(obj, 0xC0)
    header = struct.unpack_from("<I", state, 0x80)[0]
    if not 0x80000000 <= header <= 0x801FFFF8:
        raise RuntimeError("Invalid first-person node header")
    nodes, count = struct.unpack("<II", read(header, 8))
    if not 1 <= count <= 64 or not 0x80000000 <= nodes <= 0x80200000 - count * 8:
        raise RuntimeError("Invalid first-person node table")
    table = read(nodes, count * 8)
    geometry = []
    geometry_hash = 2166136261
    for index in range(count):
        address, vertices = struct.unpack_from("<II", table, index * 8)
        if vertices > 2048 or (vertices and not 0x80000000 <= address <= 0x80200000 - vertices * 8):
            raise RuntimeError("Invalid first-person vertex range")
        data = read(address, vertices * 8) if vertices else b""
        for value in struct.pack("<I", vertices) + data:
            geometry_hash = ((geometry_hash ^ value) * 16777619) & 0xFFFFFFFF
        geometry.append({"node": index, "address": hex(address),
                         "vertices": vertices, "sha256": hashlib.sha256(data).hexdigest()})
    fnv = 1469598103934665603  # Existing title helper's historical seed.
    for value in table:
        fnv = ((fnv ^ value) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return {"actor": hex(actor), "input": hex(inp), "object": hex(obj),
            "magic": hex(struct.unpack_from("<I", state, 0x70)[0]),
            "node_count": count, "nodes": geometry,
            "node_table_sha256": hashlib.sha256(table).hexdigest(),
            "node_table_fnv64": hex(fnv),
            "geometry_fnv32": hex(geometry_hash),
            "face_count": struct.unpack_from("<H", state, 0xB6)[0],
            "faces": hex(struct.unpack_from("<I", state, 0xB8)[0])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--slots", type=int, nargs="+", default=[1, 2, 3, 4])
    parser.add_argument("--cycle", action="store_true")
    parser.add_argument("--damage", action="store_true")
    parser.add_argument("--models", action="store_true")
    parser.add_argument("--first-person-models", action="store_true")
    parser.add_argument("--pose-controls", action="store_true",
                        help="Capture native/translated/yawed/lost/restored top-view controls")
    parser.add_argument("--discover-damage", action="store_true")
    parser.add_argument("--only-damage-ids", type=int, nargs="+")
    parser.add_argument("--fire-frames", type=int, default=24)
    parser.add_argument("--release-frames", type=int, default=240)
    parser.add_argument("--scoped-zoom", action="store_true")
    parser.add_argument("--control", choices=("fire", "idle", "turn-away"), default="fire")
    parser.add_argument("--approach-frames", type=int, default=0)
    parser.add_argument("--weapon-pose-x", type=int)
    parser.add_argument("--weapon-pose-yaw-mdeg", type=int)
    parser.add_argument("--force-weapon-tracking-loss", action="store_true")
    parser.add_argument("--require-p2-damage", action="store_true")
    parser.add_argument("--auto-special-controls", action="store_true")
    parser.add_argument("--damage-retries", type=int, default=3)
    args = parser.parse_args()
    if any(not 0 <= slot <= 99 for slot in args.slots):
        parser.error("Slots must be in 0..99")
    if not 1 <= args.fire_frames <= 600 or not 1 <= args.release_frames <= 1800 or not 0 <= args.approach_frames <= 600:
        parser.error("Frame window exceeds the bounded control limits")
    if args.weapon_pose_x is not None and not -2048 <= args.weapon_pose_x <= 2048:
        parser.error("Weapon pose X must be in -2048..2048")
    if (args.weapon_pose_yaw_mdeg is not None and
            not -180000 <= args.weapon_pose_yaw_mdeg <= 180000):
        parser.error("Weapon pose yaw must be in -180000..180000 millidegrees")
    if (args.damage or args.models) and not args.cycle:
        parser.error("--damage and --models require --cycle")
    if (args.require_p2_damage and
            (not args.damage or args.control != "fire")):
        parser.error("--require-p2-damage requires --damage --control fire")
    if not 1 <= args.damage_retries <= 5:
        parser.error("Damage retries must be in 1..5")
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
            path = ROOT / f"analysis/fixtures/mp/openbios/state_8001F844_slot{slot:02}.{suffix}"
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
    weapon_pose = args.weapon_pose_x is not None or args.weapon_pose_yaw_mdeg is not None
    weapon_pose = weapon_pose or args.pose_controls
    if weapon_pose:
        env.update(
            PSX_VR_WEAPON_POSE="1",
            MOHU_VR_WEAPON_POSE="1",
            MOHU_VR_WEAPON_FLAT_PROBE="1",
            MOHU_VR_WEAPON_SYNTHETIC_X=str(args.weapon_pose_x or 0),
            MOHU_VR_WEAPON_SYNTHETIC_YAW_MDEG=str(args.weapon_pose_yaw_mdeg or 0),
        )
    if args.force_weapon_tracking_loss:
        env["MOHU_VR_WEAPON_FORCE_TRACKING_LOSS"] = "1"
    receipt = {"executable_sha256": digest(exe), "source_saves": hashes,
               "vr_sources": {name: digest(ROOT / name) for name in (
                   "vr/underground/vr_diagnostic.c", "vr/underground/weapon.c",
                   "vr/underground/weapon.h", "vr/tools/inspect_weapon_sets.py")},
               "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "diagnostic_game_config_sha256": digest(ROOT / "analysis/vr-baseline/game-interp.toml"),
               "preference_hashes": preference_hashes,
               "controls": {"case": args.control, "fire_frames": args.fire_frames,
                            "release_frames": args.release_frames, "scoped_zoom": args.scoped_zoom,
                            "approach_frames": args.approach_frames,
                            "auto_special_controls": args.auto_special_controls,
                            "force_weapon_tracking_loss": args.force_weapon_tracking_loss,
                            "models": args.models, "weapon_pose": weapon_pose,
                            "first_person_models": args.first_person_models,
                            "pose_controls": args.pose_controls,
                            "weapon_pose_x": args.weapon_pose_x or 0,
                            "weapon_pose_yaw_mdeg": args.weapon_pose_yaw_mdeg or 0},
               "p2_damaged_ids": [], "slots": [], "complete": False}
    damaged_ids = set()
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
                    capture = {"switches": index, "players": current}
                    if args.models:
                        capture["weapon_model"] = weapon_model()
                        if int(capture["weapon_model"]["magic"], 16) != MODEL_MAGIC:
                            raise RuntimeError("Unrecognized weapon object")
                    if args.first_person_models:
                        capture["first_person_model"] = first_person_model()
                        capture["mod_counters"] = command("mod_counters")
                    row["captures"].append(capture)
                    save(out / "inventory.json", receipt)
                    key = (current[0]["weapon_slot"], current[0]["weapon_id"])
                    print(slot, index, key, flush=True)
                    if key in seen:
                        row["cycle_closed"] = True
                        break
                    seen.add(key)
                    if args.pose_controls:
                        controls = []
                        capture["pose_controls"] = controls
                        for label, x, yaw, lost in (
                                ("native", 0, 0, 0), ("translated", 24, 0, 0),
                                ("yawed", 0, 12000, 0), ("lost", 24, 0, 1),
                                ("restored", 0, 0, 0)):
                            command("mod_cmd", name="mohu.vr.weapon.pose",
                                    args=f"x={x} yaw={yaw} lost={lost}")
                            frames(6)  # The diagnostic command latches at VBlank.
                            before_counters = command("mod_counters")
                            frames(12)
                            image = directory / f"pose-{index:02}-{label}.png"
                            command("screenshot_file", path=str(image))
                            counters = command("mod_counters")
                            before_counts = {c["name"]: c["count"] for c in before_counters["counters"]}
                            counts = {c["name"]: c["count"] for c in counters["counters"]}
                            delta = {name: value - before_counts.get(name, 0)
                                     for name, value in counts.items() if "mohu.vr.weapon." in name}
                            prefix = "mohu.vr.weapon."
                            if lost:
                                if delta.get(prefix + "viewmodel_apply", 0) or not delta.get(prefix + "tracking_fallback", 0):
                                    raise RuntimeError("Tracking-loss fallback failed")
                            elif not delta.get(prefix + "viewmodel_apply", 0):
                                raise RuntimeError(f"Viewmodel did not apply for ID {key[1]} {label}")
                            # Counters are sampled from a running guest. One
                            # active call may be between apply and restore;
                            # loss intervals must drain to exact equality.
                            skew = counts.get(prefix + "viewmodel_apply", 0) - counts.get(prefix + "viewmodel_restore", 0)
                            if abs(skew) > (0 if lost else 1):
                                raise RuntimeError("Viewmodel control scope leaked")
                            controls.append({"case": label, "x": x, "yaw_mdeg": yaw,
                                             "lost": lost, "sha256": digest(image),
                                             "image": str(image.relative_to(out)),
                                             "counter_delta": delta})
                        command("mod_cmd", name="mohu.vr.weapon.pose", args="lost=1")
                        frames(12)
                        drained = {c["name"]: c["count"] for c in command("mod_counters")["counters"]}
                        if drained.get(prefix + "viewmodel_apply", 0) != drained.get(prefix + "viewmodel_restore", 0):
                            raise RuntimeError("Viewmodel restore did not drain after tracking loss")
                        capture["pose_scope_drained"] = True
                        command("mod_cmd", name="mohu.vr.weapon.pose", args="reset")
                        save(out / "inventory.json", receipt)
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
                            special = args.auto_special_controls
                            scoped_zoom = args.scoped_zoom or (special and key[1] == 5)
                            approach_frames = (
                                max(args.approach_frames, 180)
                                if special and key[1] == 15
                                else args.approach_frames)
                            fire_frames = (
                                max(args.fire_frames,
                                    60 if key[1] in (5, 15) else 36)
                                if special and key[1] in (5, 10, 15)
                                else args.fire_frames)
                            release_frames = (
                                max(args.release_frames, 720)
                                if special and key[1] in (5, 10, 15)
                                else args.release_frames)
                            attempts = []
                            p2_damaged = False
                            for attempt in range(args.damage_retries):
                                load(slot)
                                for unused in range(index):
                                    switch()
                                before = players()
                                if (before[0]["weapon_slot"], before[0]["weapon_id"]) != key:
                                    raise RuntimeError("Fresh-load weapon preparation disagrees")
                                if approach_frames:
                                    command("press", buttons="0xffff", ly=0,
                                            frames=approach_frames)
                                    frames(approach_frames + 12)
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
                                if scoped_zoom and key[1] == 5:
                                    command("set_input", buttons="0xfdff")
                                    frames(60)
                                start_frame = command("frame")["frame"]
                                if args.control != "idle":
                                    command("press", buttons=65535 ^ (0x4200 if scoped_zoom and key[1] == 5 else 0x4000), frames=fire_frames)
                                frames(fire_frames + release_frames)
                                command("set_input", buttons="0xffff")
                                after = players()
                                trace = command("wtrace_dump", count=2048)
                                if trace["total"] != trace["available"] or trace["emitted"] != trace["total"]:
                                    raise RuntimeError("Health write trace incomplete")
                                command("wtrace_range", lo="0", hi="0")
                                hit = trace["emitted"] > 0 and p2_damage_in_trace(
                                    trace, before[1])
                                attempts.append({
                                    "attempt": attempt + 1,
                                    "before": before,
                                    "after": after,
                                    "health_trace": trace,
                                    "p2_damaged": hit,
                                    "frame_window": [start_frame, command("frame")["frame"]],
                                })
                                p2_damaged = p2_damaged or hit
                                if hit:
                                    break
                            if args.require_p2_damage and not p2_damaged:
                                raise RuntimeError(
                                    f"P2 did not take native damage for weapon {key[1]}")
                            if p2_damaged:
                                damaged_ids.add(key[1])
                                receipt["p2_damaged_ids"] = sorted(damaged_ids)
                            row["captures"][-1]["fire"] = {
                                "attempts": attempts, "p2_damaged": p2_damaged}
                            save(out / "inventory.json", receipt)
                            last = attempts[-1]
                            print("damage", last["before"][1]["health"],
                                  last["after"][1]["health"],
                                  last["health_trace"]["emitted"],
                                  f"attempts={len(attempts)}", flush=True)
                            load(slot)
                            for unused in range(index):
                                switch()
                        switch()
                save(out / "inventory.json", receipt)
                if args.cycle and not row.get("cycle_closed"):
                    raise RuntimeError("Weapon cycle did not close within 12 switches")
                print(f"Slot {slot} loaded", flush=True)
            if args.require_p2_damage and damaged_ids != set(WEAPONS):
                missing = sorted(set(WEAPONS) - damaged_ids)
                raise RuntimeError(f"Missing P2 damage for weapon IDs: {missing}")
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
