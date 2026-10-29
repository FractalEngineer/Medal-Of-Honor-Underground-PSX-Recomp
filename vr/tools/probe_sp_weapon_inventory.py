"""Inventory naturally reachable SP weapons in copied fixtures.

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

import inspect_weapon_sets as native
import probe_p38_headset as comparison


ROOT = native.ROOT
SP_PLAYER = 0x800AA17C
SP_INPUT_OFFSET = 0x39C
SP_VIEWMODEL_OFFSET = 0x114
SP_INPUT_VIEWMODEL_OFFSET = 0x330


def read_word(address: int) -> int:
    return struct.unpack("<I", native.read(address, 4))[0]


def read_half(address: int) -> int:
    return struct.unpack("<H", native.read(address, 2))[0]


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
    fnv = 2166136261
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
        for value in struct.pack("<I", vertices) + data:
            fnv = ((fnv ^ value) * 16777619) & 0xFFFFFFFF
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
        "geometry_fnv32": f"{fnv:08X}",
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
        "weapon": native.WEAPONS.get(weapon_id, "Unknown"),
        "weapon_slot": native.read(player_input + 92, 1)[0],
        "model": geometry_identity(object_address),
        "render": comparison.shot_command("render"),
        "counters": comparison.counter_values(),
    }


def counter_delta(before: dict, after: dict, name: str) -> int:
    return int(after.get(name, 0)) - int(before.get(name, 0))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--slots", type=int, nargs="+", default=[1, 3, 4, 5])
    parser.add_argument("--switches", type=int, default=4)
    args = parser.parse_args()
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic TCP port 4372 is occupied")
    if any(not 1 <= slot <= 99 for slot in args.slots):
        parser.error("slots must be in 1..99")
    if not 1 <= args.switches <= 8:
        parser.error("switches must be in 1..8")

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    saves = out / "saves/openbios"
    saves.mkdir(parents=True)
    sources = {}
    for slot in args.slots:
        for suffix in ("pst", "thumb"):
            source = ROOT / (
                "analysis/fixtures/sp/openbios/"
                f"state_8001F844_slot{slot:02}.{suffix}"
            )
            if not source.is_file():
                raise FileNotFoundError(source)
            shutil.copyfile(source, saves / source.name)
            sources[str(source.relative_to(ROOT))] = native.digest(source)

    preferences = comparison.hash_existing(comparison.preference_paths())
    executable = (
        ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    )
    env = comparison.environment("tracked", True, hand_fixed=True)
    env.update(
        PSX_INTERNAL_RESOLUTION="native",
        PSX_RENDER_PASS_VERIFY="1",
        MOHU_VR_MP_CONTROL="0",
        MOHU_VR_MP_FRUSTUM="0",
        MOHU_VR_WEAPON_TRACE="0",
    )
    receipt = {
        "schema": 1,
        "kind": "G7a read-only SP natural weapon inventory",
        "complete": False,
        "headset_used": False,
        "slots": args.slots,
        "switches_per_slot": args.switches,
        "fixture_hashes": sources,
        "executable_sha256": native.digest(executable),
        "build": comparison.build_configuration(ROOT / "build-release/CMakeCache.txt"),
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
