"""Inventory naturally reachable SP weapons and exercise the slot-3 camera.

The probe uses ordinary weapon-switch input and the measured SP input/viewmodel
layout. It does not edit inventory, ammunition, health, saves or guest code.
Every game launch is unsandboxed and uses one owned child process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import time

import inspect_weapon_sets as native
import probe_p38_headset as comparison


ROOT = native.ROOT
SP_PLAYER = 0x800AA17C
SP_INPUT_OFFSET = 0x39C
SP_VIEWMODEL_OFFSET = 0x114
SP_INPUT_VIEWMODEL_OFFSET = 0x330
SP_SPECIAL_WEAPONS = {7: "Objective camera"}


def read_word(address: int) -> int:
    return struct.unpack("<I", native.read(address, 4))[0]


def read_half(address: int) -> int:
    return struct.unpack("<H", native.read(address, 2))[0]


def fnv32_bytes(hash_value: int, data: bytes) -> int:
    for value in data:
        hash_value = ((hash_value ^ value) * 16777619) & 0xFFFFFFFF
    return hash_value


def geometry_identity(object_address: int) -> dict:
    header = read_word(object_address + 0x80)
    if not 0x80000000 <= header <= 0x801FFFF8 or header & 3:
        raise RuntimeError(f"Invalid weapon node header {header:#010x}")
    nodes, count = struct.unpack("<II", native.read(header, 8))
    if not 1 <= count <= 32 or (
        nodes and
        not 0x80000000 <= nodes <= 0x80200000 - count * 8 or nodes & 3
    ):
        raise RuntimeError(f"Invalid weapon node table {nodes:#010x}")
    table = native.read(nodes, count * 8)
    raw_fnv = 2166136261
    pose_fnv = 2166136261
    attributes_fnv = 2166136261
    rows = []
    for index in range(count):
        address, vertices = struct.unpack_from("<II", table, index * 8)
        if vertices > 2048 or (
            vertices and
            (not 0x80000000 <= address <= 0x80200000 - vertices * 8 or
             address & 3)
        ):
            raise RuntimeError(f"Invalid weapon node {index} vertex range")
        data = native.read(address, vertices * 8) if vertices else b""
        count_bytes = struct.pack("<I", vertices)
        raw_fnv = fnv32_bytes(raw_fnv, count_bytes)
        pose_fnv = fnv32_bytes(pose_fnv, count_bytes)
        attributes_fnv = fnv32_bytes(attributes_fnv, count_bytes)
        for vertex in range(vertices):
            packet = data[vertex * 8:(vertex + 1) * 8]
            raw_fnv = fnv32_bytes(raw_fnv, packet)
            pose_fnv = fnv32_bytes(pose_fnv, packet[:6])
            attributes_fnv = fnv32_bytes(attributes_fnv, packet[6:])
        rows.append({
            "node": index,
            "address": hex(address),
            "vertices": vertices,
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return {
        "magic": hex(read_word(object_address + 0x70)),
        "face_count": read_half(object_address + 0xB6),
        "node_count": count,
        "geometry_fnv32": f"{raw_fnv:08X}",
        "pose_fnv32": f"{pose_fnv:08X}",
        "attributes_fnv32": f"{attributes_fnv:08X}",
        "nodes": rows,
    }


def snapshot(label: str) -> dict:
    actor = read_word(SP_PLAYER)
    if not 0x800B0000 <= actor <= 0x801FC000:
        raise RuntimeError("Not the measured SP player layout")
    player_input = read_word(actor + SP_INPUT_OFFSET)
    object_address = read_word(actor + SP_VIEWMODEL_OFFSET)
    if player_input != actor + 0x3FC:
        raise RuntimeError("Not the measured SP input layout")
    if object_address != player_input + SP_INPUT_VIEWMODEL_OFFSET:
        raise RuntimeError("Not the measured SP viewmodel layout")
    weapon_id = native.read(player_input + 93, 1)[0]
    return {
        "label": label,
        "actor": hex(actor),
        "input": hex(player_input),
        "object": hex(object_address),
        "weapon_id": weapon_id,
        "weapon": SP_SPECIAL_WEAPONS.get(
            weapon_id, native.WEAPONS.get(weapon_id, "Unknown")
        ),
        "weapon_slot": native.read(player_input + 92, 1)[0],
        "model": geometry_identity(object_address),
        "render": comparison.shot_command("render"),
        "counters": comparison.counter_values(),
    }


def counter_delta(before: dict, after: dict, name: str) -> int:
    return int(after.get(name, 0)) - int(before.get(name, 0))


def capture_stereo(directory: Path) -> tuple[Path, Path]:
    directory.mkdir()
    native.command("stereo_dump", path=directory.as_posix(), count=1)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        left = list(directory.glob("*_left.png"))
        right = list(directory.glob("*_right.png"))
        if len(left) == len(right) == 1:
            return left[0], right[0]
        time.sleep(.05)
    raise RuntimeError("No complete camera stereo pair")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "analysis/fixtures/sp",
        help="directory containing openbios/state_8001F844_slotNN.*",
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=Path("build-release"),
        help="diagnostics-enabled build directory relative to the repository",
    )
    parser.add_argument("--slots", type=int, nargs="+", default=[1, 3, 4, 5])
    parser.add_argument("--switches", type=int, default=4)
    parser.add_argument(
        "--weapon-trace",
        action="store_true",
        help="record the first SP model/tracking rejection in the runtime log",
    )
    parser.add_argument(
        "--dump-ram",
        action="store_true",
        help="save a read-only 2 MiB guest RAM snapshot for mesh analysis",
    )
    parser.add_argument(
        "--camera-objective",
        action="store_true",
        help="exercise slot 3 camera aim plus trigger in an isolated save",
    )
    args = parser.parse_args()
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic TCP port 4372 is occupied")
    if any(not 0 <= slot <= 99 for slot in args.slots):
        parser.error("slots must be in 0..99")
    if not 1 <= args.switches <= 8:
        parser.error("switches must be in 1..8")
    if args.camera_objective and args.slots != [3]:
        parser.error("camera-objective requires --slots 3")

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    saves = out / "saves/openbios"
    saves.mkdir(parents=True)
    source_root = args.source.resolve()
    sources = {}
    for slot in args.slots:
        for suffix in ("pst", "thumb"):
            source = (
                source_root / "openbios" /
                f"state_8001F844_slot{slot:02}.{suffix}"
            )
            if not source.is_file():
                raise FileNotFoundError(source)
            shutil.copyfile(source, saves / source.name)
            sources[str(source)] = native.digest(source)

    preferences = comparison.hash_existing(comparison.preference_paths())
    build_dir = (
        args.build_dir if args.build_dir.is_absolute() else ROOT / args.build_dir
    ).resolve()
    executable = build_dir / "Medal_of_Honor_Underground_Recompiled.exe"
    env = comparison.environment("tracked", True, hand_fixed=True)
    env.update(
        PSX_INTERNAL_RESOLUTION="native",
        PSX_RENDER_PASS_VERIFY="1",
        MOHU_VR_MP_CONTROL="0",
        MOHU_VR_MP_FRUSTUM="0",
        MOHU_VR_WEAPON_TRACE=str(int(args.weapon_trace)),
    )
    if args.camera_objective:
        env["MOHU_VR_EYE_OFFSET"] = "8"
    receipt = {
        "schema": 1,
        "kind": "G7a read-only SP natural weapon inventory",
        "complete": False,
        "headset_used": False,
        "slots": args.slots,
        "switches_per_slot": args.switches,
        "fixture_hashes": sources,
        "executable_sha256": native.digest(executable),
        "build": comparison.build_configuration(build_dir / "CMakeCache.txt"),
        "environment": {
            key: value for key, value in env.items()
            if key.startswith(("PSX_", "MOHU_"))
        },
        "fixed_snapshot": None,
        "inventory": [],
        "limits": [
            "Only naturally reachable weapons are reported.",
            "A visible model does not establish native shot origin or direction.",
            "No inventory, ammo, health, save or guest-code edit is performed.",
        ],
    }
    with (out / "stdout.log").open("w") as stdout, \
            (out / "stderr.log").open("w") as stderr:
        process = subprocess.Popen(
            [
                str(executable),
                "--headless-opengl",
                "--no-launcher",
                "--game",
                str(ROOT / "game.toml"),
                "--memcard-dir",
                str(out / "saves"),
                "--debug-port",
                "4372",
            ],
            cwd=out,
            env=env,
            stdout=stdout,
            stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        receipt["owned_pid"] = process.pid
        try:
            comparison.wait_for_ping(process)
            for slot in args.slots:
                receipt["load"] = native.load(slot)
                if args.dump_ram:
                    slot_dir = out / f"slot-{slot:02}"
                    slot_dir.mkdir()
                    (slot_dir / "ram.bin").write_bytes(
                        native.read(0x80000000, 0x200000)
                    )
                    native.command(
                        "screenshot_file",
                        path=str(slot_dir / "initial.png"),
                    )
                comparison.release_load_override()
                comparison.set_desktop_hands()
                native.frames(10)
                start = comparison.counter_values()
                entries = [snapshot("initial")]
                native.frames(4)
                end = comparison.counter_values()
                entries[0]["render_frames"] = {
                    "project": counter_delta(
                        start, end, "mohu.vr.weapon.sp.project"
                    ),
                    "apply": counter_delta(
                        start, end, "mohu.vr.weapon.sp.apply"
                    ),
                    "model_guard_fail": counter_delta(
                        start, end, "mohu.vr.weapon.sp.model_guard_fail"
                    ),
                }
                if args.camera_objective:
                    idle_left, idle_right = capture_stereo(
                        out / "camera-idle-stereo"
                    )
                    native.command(
                        "openxr_input_override",
                        right_squeeze=0,
                        right_trigger=1000,
                    )
                    native.frames(8)
                    unaimed_path = out / "camera-unaimed.png"
                    native.command(
                        "screenshot_file", path=str(unaimed_path)
                    )
                    native.command("openxr_input_override", clear=1)
                    receipt["camera_unaimed_paper_check"] = {
                        "image": str(unaimed_path),
                        "input": {"right_trigger": 1000},
                        "native_effect": "papers",
                    }
                    receipt["load"] = native.load(3)
                    comparison.release_load_override()
                    comparison.set_desktop_hands()
                    native.frames(10)
                    native.command(
                        "openxr_input_override",
                        right_squeeze=1000,
                        right_trigger=0,
                    )
                    native.frames(8)
                    aim_path = out / "camera-aim.png"
                    native.command("screenshot_file", path=str(aim_path))
                    aim_left, aim_right = capture_stereo(out / "camera-stereo")
                    before_fire = comparison.counter_values()
                    native.command(
                        "openxr_input_override",
                        right_squeeze=1000,
                        right_trigger=1000,
                    )
                    native.frames(8)
                    fire_path = out / "camera-photo.png"
                    native.command("screenshot_file", path=str(fire_path))
                    native.command(
                        "openxr_input_override",
                        right_squeeze=1000,
                        right_trigger=0,
                    )
                    native.frames(8)
                    release_path = out / "camera-after.png"
                    native.command("screenshot_file", path=str(release_path))
                    native.command("openxr_input_override", clear=1)
                    after_fire = comparison.counter_values()
                    entries[0]["camera_objective"] = {
                        "aim_image": str(aim_path),
                        "fire_image": str(fire_path),
                        "release_image": str(release_path),
                        "idle_stereo_images": [
                            str(idle_left), str(idle_right),
                        ],
                        "stereo_images": [
                            str(aim_left), str(aim_right),
                        ],
                        "input": {
                            "right_squeeze": 1000,
                            "right_trigger": 1000,
                        },
                        "counter_delta": {
                            key: counter_delta(before_fire, after_fire, key)
                            for key in after_fire
                            if key.startswith("mohu.vr.")
                        },
                    }
                for index in range(args.switches):
                    native.switch()
                    comparison.release_load_override()
                    comparison.set_desktop_hands()
                    native.frames(8)
                    entries.append(snapshot(f"switch-{index + 1}"))
                receipt["inventory"].append({
                    "slot": slot,
                    "entries": entries,
                    "unique_ids": sorted({
                        row["weapon_id"] for row in entries
                    }),
                    "all_layouts_valid": True,
                })
                comparison.save_json(out / "receipt.json", receipt)
            receipt["complete"] = True
        except BaseException as error:
            receipt["error"] = str(error)
            raise
        finally:
            try:
                native.command("openxr_hands_override", clear=1)
                native.command("openxr_input_override", clear=1)
                native.command("quit")
            except (OSError, RuntimeError):
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                receipt["forced_cleanup"] = True
                process.terminate()
                process.wait(timeout=8)
            receipt["exit_code"] = process.returncode
            receipt["source_saves_unchanged"] = all(
                native.digest(ROOT / path) == digest
                for path, digest in sources.items()
            )
            receipt["preferences_unchanged"] = (
                comparison.hash_existing(comparison.preference_paths()) ==
                preferences
            )
            receipt["remaining_game_pids"] = native.game_pids()
            receipt["complete"] = bool(
                receipt["complete"] and
                receipt["exit_code"] == 0 and
                not receipt.get("forced_cleanup") and
                not receipt["remaining_game_pids"] and
                receipt["source_saves_unchanged"] and
                receipt["preferences_unchanged"]
            )
            comparison.save_json(out / "receipt.json", receipt)
    reachable = sorted({
        weapon_id
        for slot in receipt["inventory"]
        for weapon_id in slot["unique_ids"]
    })
    print(json.dumps({
        "complete": receipt["complete"],
        "reachable_ids": reachable,
        "slots": [
            {"slot": row["slot"], "ids": row["unique_ids"]}
            for row in receipt["inventory"]
        ],
    }))
    if not receipt["complete"]:
        raise RuntimeError("SP weapon inventory probe did not close cleanly")


if __name__ == "__main__":
    main()
