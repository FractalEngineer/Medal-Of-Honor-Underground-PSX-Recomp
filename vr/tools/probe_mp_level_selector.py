"""Capture the live multiplayer level-selector path without changing rendering."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import time

import inspect_weapon_sets as native


SCENE_ENTRY = 0x8006E9D8
SCENE_SIZE = 0x180
SCENE_CALLBACK = 0x8006C61C
SCENE_CALLBACK_SIZE = 0x290
VISIBILITY_SELECTOR = 0x80096EF4
VISIBILITY_SELECTOR_SIZE = 0x90
VISIBILITY_HELPER = 0x80096AC8
VISIBILITY_HELPER_SIZE = 0x428
FRAME_CALLER = 0x80054BC4
FRAME_CALLER_SIZE = 0x200
MP_CONTEXT = 0x800A0B08
MP_CAMERA_ROOT = 0x800A35B0
MP_CURRENT_PLAYER = 0x800A35C4
MP_SCENE_ROOT = 0x800A35CC
MP_P1_ROOT = 0x800A3604


def command(name, **values):
    deadline = time.monotonic() + 15.0
    while True:
        try:
            return native.command(name, **values)
        except (OSError, RuntimeError) as error:
            if "busy or frozen" not in str(error) or time.monotonic() > deadline:
                raise
            time.sleep(0.05)


def guest_valid(address):
    return 0x80000000 <= address < 0x80200000 and not (address & 3)


def read(address, size):
    return native.read(address, size)


def read_word(address):
    return struct.unpack("<I", read(address, 4))[0]


def fnv1a(data):
    value = 0x811C9DC5
    for byte in data:
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value


def capture_disasm(address, count):
    if not guest_valid(address):
        return None
    result = command("disasm", addr=hex(address), count=count)
    return result["lines"]


def capture_code(address, size):
    data = read(address, size)
    lines = []
    remaining = size // 4
    current = address
    while remaining:
        count = min(remaining, 256)
        lines.extend(capture_disasm(current, count))
        current += count * 4
        remaining -= count
    return {
        "address": f"0x{address:08X}",
        "size": size,
        "fnv32": f"0x{fnv1a(data):08X}",
        "sha256": native.hashlib.sha256(data).hexdigest(),
        "disasm": lines,
    }


def capture_scene_pc_counts():
    callers = (0x80054CD4, 0x80054D54)
    pcs = (SCENE_ENTRY, *callers)
    command("pc_probe_clear")
    command(
        "pc_probe_arm",
        pcs=",".join(hex(address) for address in pcs),
        n=32,
    )
    deadline = time.monotonic() + 10.0
    probe = None
    while time.monotonic() < deadline:
        native.frames(2)
        probe = command("pc_probe_dump")
        counts = {
            int(row["pc"], 0): row["count"]
            for row in probe["slots"]
        }
        if counts.get(SCENE_ENTRY, 0) and all(
            counts.get(address, 0) for address in callers
        ):
            break
    command("pc_probe_clear")
    if not probe:
        raise RuntimeError("Native MP PC probe returned no state")
    counts = {
        int(row["pc"], 0): row["count"]
        for row in probe["slots"]
    }
    return probe


def collect_scene_list(head):
    nodes = []
    seen = set()
    current = head
    while current and current not in seen and len(nodes) < 64:
        if not guest_valid(current):
            raise RuntimeError(f"Unrecognized scene-list node {current:#010x}")
        seen.add(current)
        data = read(current, 0x388)
        words = struct.unpack_from("<24I", data, 0)
        callback = struct.unpack_from("<I", data, 0x384)[0]
        next_node = struct.unpack_from("<I", data, 4)[0]
        row = {
            "address": f"0x{current:08X}",
            "head_words": [f"0x{value:08X}" for value in words],
            "next": f"0x{next_node:08X}",
            "callback_0x384": f"0x{callback:08X}",
            "visibility_mask_0x0c": (
                f"0x{struct.unpack_from('<I', data, 0x0C)[0]:08X}"
            ),
            "render_flags_0x10": (
                f"0x{struct.unpack_from('<I', data, 0x10)[0]:08X}"
            ),
            "aux_flags_0x14": (
                f"0x{struct.unpack_from('<I', data, 0x14)[0]:08X}"
            ),
            "field_0x114": f"0x{struct.unpack_from('<I', data, 0x114)[0]:08X}",
            "field_0x2a4": f"0x{struct.unpack_from('<I', data, 0x2a4)[0]:08X}",
            "field_0x2ac": f"0x{struct.unpack_from('<I', data, 0x2ac)[0]:08X}",
        }
        if guest_valid(callback):
            code = read(callback, 0x1000)
            row["callback_code"] = {
                "address": f"0x{callback:08X}",
                "requested_bytes": 4096,
                "sha256": native.hashlib.sha256(code).hexdigest(),
                "fnv32": f"0x{fnv1a(code):08X}",
                "disasm": capture_disasm(callback, 256),
            }
        nodes.append(row)
        current = next_node
    return nodes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic port 4372 is occupied")

    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    copies = out / "saves/openbios"
    copies.mkdir(parents=True)
    sources = []
    for suffix in ("pst", "thumb"):
        source = (
            native.ROOT
            / f"saves/openbios/state_8001F844_slot01.{suffix}"
        )
        sources.append(source)
        shutil.copyfile(source, copies / source.name)
    source_hashes = {str(path): native.digest(path) for path in sources}
    preferences = [
        native.ROOT / "build-release/settings.toml",
        native.ROOT / "build-release/keybinds.ini",
        Path("C:/Program Files (x86)/Steam/config/steamvr.vrsettings"),
    ]
    preference_hashes = {
        str(path): native.digest(path) for path in preferences if path.is_file()
    }
    exe = native.ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PSX_", "MOHU_VR_"))
    }
    env.update(
        PSX_DEV_INPUT="0",
        PSX_VSYNC="0",
        PSX_OPENXR_ENABLE="0",
        PSX_STEREO_SHED="0",
        MOHU_VR_MP_CONTROL="0",
        MOHU_VR_STEREO_PROOF="0",
    )
    receipt = {
        "schema": 1,
        "fixture": "copied root MP slot 1, zero switches, no fire",
        "fixture_slot": 1,
        "executable_sha256": native.digest(exe),
        "source_saves": source_hashes,
        "preferences": preference_hashes,
        "complete": False,
    }
    with (out / "stdout.log").open("w") as stdout, (
        out / "stderr.log"
    ).open("w") as stderr:
        process = subprocess.Popen(
            [
                str(exe),
                "--headless-opengl",
                "--no-launcher",
                "--game",
                str(native.ROOT / "analysis/vr-baseline/game-interp.toml"),
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
            deadline = time.monotonic() + 40.0
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Diagnostic game exited during startup")
                try:
                    command("ping")
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.1)
            receipt["load"] = native.load(1)
            command("set_input", buttons="0xffff")
            command("set_input", port=2, buttons="0xffff")
            receipt["players_before"] = native.players()

            scene_code = read(SCENE_ENTRY, SCENE_SIZE)
            receipt["scene_contract"] = {
                "address": f"0x{SCENE_ENTRY:08X}",
                "size": SCENE_SIZE,
                "fnv32": f"0x{fnv1a(scene_code):08X}",
                "sha256": native.hashlib.sha256(scene_code).hexdigest(),
                "disasm": capture_disasm(SCENE_ENTRY, SCENE_SIZE // 4),
            }
            receipt["mp_roots"] = {
                "context": f"0x{MP_CONTEXT:08X}",
                "camera": f"0x{read_word(MP_CAMERA_ROOT):08X}",
                "current_player": f"0x{read_word(MP_CURRENT_PLAYER):08X}",
                "scene": f"0x{read_word(MP_SCENE_ROOT):08X}",
                "player": f"0x{read_word(MP_P1_ROOT):08X}",
            }
            receipt["code_contracts"] = {
                "frame_caller": capture_code(FRAME_CALLER, FRAME_CALLER_SIZE),
                "scene_dispatch": capture_code(SCENE_ENTRY, SCENE_SIZE),
                "scene_node_callback": capture_code(
                    SCENE_CALLBACK, SCENE_CALLBACK_SIZE
                ),
                "visibility_selector": capture_code(
                    VISIBILITY_SELECTOR, VISIBILITY_SELECTOR_SIZE
                ),
                "visibility_helper": capture_code(
                    VISIBILITY_HELPER, VISIBILITY_HELPER_SIZE
                ),
            }
            selector_callers = (0x8006C664, 0x8006C688)
            helper_callers = (0x80096F70,)
            for address in selector_callers:
                word = read_word(address)
                if word != 0x0C025BBD:
                    raise RuntimeError(
                        f"Unexpected visibility-selector call at {address:#010x}"
                    )
            for address in helper_callers:
                word = read_word(address)
                if word != 0x0C025AB2:
                    raise RuntimeError(
                        f"Unexpected visibility-helper call at {address:#010x}"
                    )
            receipt["selector_calls"] = {
                "node_callback_to_selector": [
                    {
                        "call_site": f"0x{address:08X}",
                        "word": f"0x{read_word(address):08X}",
                        "return_address": f"0x{address + 8:08X}",
                    }
                    for address in selector_callers
                ],
                "selector_to_helper": [
                    {
                        "call_site": f"0x{address:08X}",
                        "word": f"0x{read_word(address):08X}",
                        "return_address": f"0x{address + 8:08X}",
                    }
                    for address in helper_callers
                ],
            }

            receipt["scene_invocation"] = {
                "mode": "natural MP frame window",
                "pc_probe": capture_scene_pc_counts(),
            }
            receipt["scene_callers"] = []
            for address in (0x80054CD4, 0x80054D54):
                word = read_word(address)
                if word != 0x0C01BA76:
                    raise RuntimeError(
                        f"Unexpected scene call word {word:#010x} at {address:#010x}"
                    )
                receipt["scene_callers"].append(
                    {
                        "call_site": f"0x{address:08X}",
                        "word": f"0x{word:08X}",
                        "return_address": f"0x{address + 8:08X}",
                        "disasm": capture_disasm(address, 4),
                    }
                )

            scene_head = read_word(MP_SCENE_ROOT)
            receipt["scene_head"] = f"0x{scene_head:08X}"
            receipt["scene_list"] = collect_scene_list(scene_head)
            if not receipt["scene_list"]:
                raise RuntimeError("Scene callback list was empty")
            level_nodes = [
                node
                for node in receipt["scene_list"]
                if node["callback_0x384"] == f"0x{SCENE_CALLBACK:08X}"
            ]
            if not level_nodes:
                raise RuntimeError("Scene list contained no level-selector nodes")
            receipt["mp_level_selection"] = {
                "shape": "flat_native_scene_list",
                "scene_root": f"0x{scene_head:08X}",
                "scene_node_count": len(receipt["scene_list"]),
                "level_node_count": len(level_nodes),
                "visibility_selector": f"0x{VISIBILITY_SELECTOR:08X}",
                "visibility_helper": f"0x{VISIBILITY_HELPER:08X}",
                "visibility_gate_field": "+0x0C",
                "queue": [node["address"] for node in level_nodes],
                "masks": [
                    {
                        "node": node["address"],
                        "visibility_mask": node["visibility_mask_0x0c"],
                        "render_flags": node["render_flags_0x10"],
                        "aux_flags": node["aux_flags_0x14"],
                    }
                    for node in level_nodes
                ],
                "pvs_queue": (
                    "No separate PVS leaf queue is written by the complete "
                    "8006C61C callback; level nodes are traversed in this list "
                    "order and 80096EF4 gates each object."
                ),
            }

            receipt["players_after"] = native.players()
            if any(
                before["actor"] != after["actor"]
                or before["weapon_id"] != after["weapon_id"]
                or before["clip"] != after["clip"]
                or before["health_raw"] != after["health_raw"]
                or before["position"] != after["position"]
                or before["rotation"] != after["rotation"]
                for before, after in zip(
                    receipt["players_before"], receipt["players_after"]
                )
            ):
                raise RuntimeError("Selector probe changed player state")
            receipt["complete"] = True
            native.save(out / "receipt.json", receipt)
        except BaseException as error:
            receipt["error"] = str(error)
            native.save(out / "receipt.json", receipt)
            raise
        finally:
            try:
                command("pc_probe_clear")
                command("render_pass_refuse", on=1)
                native.frames(4)
                command("quit")
            except (OSError, RuntimeError):
                pass
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=8)
                receipt["forced_cleanup"] = True
            receipt["exit_code"] = process.returncode
            receipt["source_saves_unchanged"] = all(
                native.digest(Path(path)) == digest
                for path, digest in source_hashes.items()
            )
            receipt["preferences_unchanged"] = all(
                native.digest(Path(path)) == digest
                for path, digest in preference_hashes.items()
            )
            receipt["remaining_game_pids"] = native.game_pids()
            native.save(out / "receipt.json", receipt)
    if not (
        receipt.get("complete")
        and receipt["source_saves_unchanged"]
        and receipt["preferences_unchanged"]
        and not receipt["remaining_game_pids"]
        and receipt["exit_code"] == 0
    ):
        raise RuntimeError("MP selector probe cleanup failed")
    if args.proof:
        revision = subprocess.run(
            ["git", "-C", str(native.ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
        proof = {
            "schema": 1,
            "date": "2026-10-26",
            "source_revision": revision,
            "fixture": receipt["fixture"],
            "executable_sha256": receipt["executable_sha256"],
            "source_hashes": {
                "vr/tools/probe_mp_level_selector.py": native.digest(Path(__file__)),
                "vr/underground/mp_view.h": native.digest(
                    native.ROOT / "vr/underground/mp_view.h"
                ),
                "vr/underground/vr_diagnostic.c": native.digest(
                    native.ROOT / "vr/underground/vr_diagnostic.c"
                ),
            },
            "code_contracts": {
                name: {
                    key: value
                    for key, value in contract.items()
                    if key != "disasm"
                }
                for name, contract in receipt["code_contracts"].items()
            },
            "scene_callers": receipt["scene_callers"],
            "selector_calls": receipt["selector_calls"],
            "scene_invocation": {
                "mode": receipt["scene_invocation"]["mode"],
                "pc_counts": {
                    row["pc"]: row["count"]
                    for row in receipt["scene_invocation"]["pc_probe"]["slots"]
                },
            },
            "mp_level_selection": receipt["mp_level_selection"],
            "source_saves_unchanged": receipt["source_saves_unchanged"],
            "preferences_unchanged": receipt["preferences_unchanged"],
            "remaining_game_pids": receipt["remaining_game_pids"],
            "exit_code": receipt["exit_code"],
            "raw_receipt": str(
                out.relative_to(native.ROOT) / "receipt.json"
                if out.is_relative_to(native.ROOT)
                else out / "receipt.json"
            ),
            "raw_receipt_sha256": native.digest(out / "receipt.json"),
            "limits": [
                "No MP frustum/render override was added in W2.1.",
                "No weapon switch or firing occurred in this fixture.",
                "The measured MP path is a flat native scene list; W2.2 must not assume the SP PVS leaf queue.",
            ],
        }
        native.save(args.proof.resolve(), proof)


if __name__ == "__main__":
    main()
