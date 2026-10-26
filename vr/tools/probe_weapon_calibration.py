"""Capture the native P38 model vertices used for calibration.

The fixture is a fresh copied multiplayer slot 1 with P38 ID 0, zero weapon
switches and no fire. The probe reads source and animated vertex records through
the existing W1 capture seam. It does not apply a new pose contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import time

import check_mp_view as eye
import check_weapon_pose_spaces as pose
import inspect_weapon_sets as native


ROOT = native.ROOT
CALIBRATION_NODE = 13


def command(cmd, **values):
    return eye.command(cmd, **values)


def read_captured_vertices(total):
    local = []
    animated = []
    while len(local) < total:
        result = command(
            "mod_cmd",
            name="mohu.vr.weapon.space",
            args=f"vertices={len(local)}",
        )
        chunk = json.loads(result["reply"])
        if (
            not chunk.get("valid")
            or chunk.get("node") != CALIBRATION_NODE
            or chunk.get("start") != len(local)
            or chunk.get("total") != total
            or not chunk.get("count")
        ):
            raise RuntimeError(f"Invalid captured vertex chunk: {chunk}")
        local.extend(chunk["local"])
        animated.extend(chunk["animated"])
    if len(local) != total or len(animated) != total:
        raise RuntimeError("Captured vertex chunk count mismatch")
    local_bytes = b"".join(
        struct.pack("<hhhh", *vertex) for vertex in local
    )
    animated_bytes = b"".join(
        struct.pack("<hhhh", *vertex) for vertex in animated
    )
    return (
        local,
        animated,
        hashlib.sha256(local_bytes).hexdigest(),
        hashlib.sha256(animated_bytes).hexdigest(),
        local_bytes,
        animated_bytes,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic TCP port 4372 occupied")

    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    copies = out / "saves/openbios"
    copies.mkdir(parents=True)
    sources = []
    for suffix in ("pst", "thumb"):
        source = ROOT / f"saves/openbios/state_8001F844_slot01.{suffix}"
        sources.append(source)
        shutil.copyfile(source, copies / source.name)
    source_hashes = {str(path): native.digest(path) for path in sources}
    preferences = [
        ROOT / "build-release/settings.toml",
        ROOT / "build-release/keybinds.ini",
        Path("C:/Program Files (x86)/Steam/config/steamvr.vrsettings"),
    ]
    preference_hashes = {
        str(path): native.digest(path)
        for path in preferences
        if path.is_file()
    }
    executable = ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
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
        PSX_RENDER_PASS_VERIFY="1",
        PSX_VR_WEAPON_POSE="1",
        MOHU_VR_MP_CONTROL="1",
        MOHU_VR_STEREO_PROOF="1",
        MOHU_VR_EYE_RENDER_VIEW="1",
        MOHU_VR_EYE_GUEST_SUBMIT="1",
        MOHU_VR_EYE_OFFSET="0",
    )
    receipt = {
        "schema": 1,
        "date": "2026-10-26",
        "kind": "W3.1 P38 model-local vertex capture",
        "fixture": "copied root MP slot 1, P38 ID 0, zero switches, no fire",
        "executable_sha256": native.digest(executable),
        "source_hashes": {
            name: native.digest(ROOT / name)
            for name in (
                "vr/underground/vr_diagnostic.c",
                "vr/underground/weapon.c",
                "vr/underground/weapon.h",
                "vr/tools/check_weapon_pose_spaces.py",
                "vr/tools/probe_weapon_calibration.py",
            )
        },
        "source_saves": source_hashes,
        "preferences": preference_hashes,
        "calibration_node": CALIBRATION_NODE,
        "complete": False,
    }
    stdout_path = out / "stdout.log"
    stderr_path = out / "stderr.log"
    process = None
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        process = subprocess.Popen(
            [
                str(executable),
                "--headless-opengl",
                "--no-launcher",
                "--game",
                str(ROOT / "analysis/vr-baseline/game-interp.toml"),
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
            deadline = time.monotonic() + 40
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
            players = native.players()
            if (
                players[0]["weapon_slot"],
                players[0]["weapon_id"],
            ) != (0, 0):
                raise RuntimeError("Fixture is not P38 in multiplayer slot 1")
            receipt["players"] = players

            command("openxr_hands_override", clear=1)
            pose.set_head()
            pose.set_hand_pair()
            native.frames(6)
            images, files = pose.capture_eyes(out / "pair-native")
            receipt["images"] = files
            receipt["stereo"] = command("stereo_stats")
            receipt["render_pass"] = command("render_pass_stats")
            if receipt["render_pass"]["verify_mismatch"] != 0:
                raise RuntimeError("Render verification mismatch")

            capture = pose.capture_space(
                node=CALIBRATION_NODE, refresh=pose.set_hand_pair
            )
            if capture["node"] != CALIBRATION_NODE or capture["id"] != 0:
                raise RuntimeError("P38 calibration capture returned the wrong node")
            node_table = int(capture["node_table"], 16)
            table_address, local_count = struct.unpack(
                "<II", native.read(node_table + CALIBRATION_NODE * 8, 8)
            )
            local_address = int(capture["local_addr"], 16)
            output_address = int(capture["output_addr"], 16)
            if table_address != local_address:
                raise RuntimeError("Node table and captured source range disagree")
            (
                local,
                animated,
                local_sha,
                animated_sha,
                local_bytes,
                animated_bytes,
            ) = read_captured_vertices(
                local_count,
            )
            object_address = int(capture["object"], 16)
            object_state = native.read(object_address, 0xC0)
            face_count, face_address = struct.unpack_from(
                "<HI", object_state, 0xB6
            )
            receipt["capture"] = capture
            receipt["model"] = {
                "object": capture["object"],
                "node_table": capture["node_table"],
                "output_table": capture["output_table"],
                "node": CALIBRATION_NODE,
                "local_address": hex(local_address),
                "output_address": hex(output_address),
                "vertex_count": local_count,
                "local_sha256": local_sha,
                "animated_sha256": animated_sha,
                "local_bytes": len(local_bytes),
                "animated_bytes": len(animated_bytes),
                "source_face_count": face_count,
                "source_face_address": hex(face_address),
                "object_state_sha256": hashlib.sha256(object_state).hexdigest(),
                "local_vertices_xyzw": local,
                "animated_vertices_xyzw": animated,
            }
            receipt["players_after"] = native.players()
            receipt["complete"] = True
        except BaseException as error:
            receipt["error"] = str(error)
            native.save(out / "receipt.json", receipt)
            raise
        finally:
            try:
                command("openxr_hands_override", clear=1)
                command("mod_cmd", name="mohu.vr.stereo.pose", args="reset")
                command("mod_cmd", name="mohu.vr.weapon.pose", args="reset")
            except (OSError, RuntimeError):
                pass
            if process.poll() is None:
                try:
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
            receipt["exit_code"] = process.returncode
            receipt["source_saves_unchanged"] = all(
                native.digest(ROOT / path) == value
                for path, value in source_hashes.items()
            )
            receipt["preferences_unchanged"] = all(
                native.digest(Path(path)) == value
                for path, value in preference_hashes.items()
            )
            receipt["remaining_game_pids"] = native.game_pids()
            native.save(out / "receipt.json", receipt)

    if not (
        receipt["complete"]
        and receipt["source_saves_unchanged"]
        and receipt["preferences_unchanged"]
        and not receipt["remaining_game_pids"]
    ):
        raise RuntimeError("W3.1 calibration probe did not close cleanly")
    if args.proof:
        compact = {
            key: receipt[key]
            for key in (
                "schema",
                "date",
                "kind",
                "fixture",
                "executable_sha256",
                "source_hashes",
                "source_saves",
                "preferences",
                "calibration_node",
                "capture",
                "model",
                "players",
                "players_after",
                "stereo",
                "render_pass",
                "complete",
                "source_saves_unchanged",
                "preferences_unchanged",
                "remaining_game_pids",
            )
        }
        compact["images"] = receipt["images"]
        args.proof.parent.mkdir(parents=True, exist_ok=True)
        native.save(args.proof, compact)
    print(f"PASS: captured {receipt['model']['vertex_count']} P38 vertices")


if __name__ == "__main__":
    main()
