"""Capture complete native viewmodel topology and animated vertices for all IDs.

Runs one isolated headless process over copied multiplayer slots 1-4. It does
not fire, damage a fixture, edit guest code or open a headset. Every node is
captured through the existing W1 animated-model seam at one fixed synthetic
hand pose.
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
import check_p38_mesh as mesh
import check_weapon_meshes as topology
import check_weapon_pose_spaces as pose
import inspect_weapon_sets as native
import probe_native_shot as shot
import probe_weapon_calibration as calibration


ROOT = native.ROOT
CYCLES = {
    1: (0, 1, 17, 10),
    2: (8, 16, 4, 15),
    3: (9, 14, 5, 10),
    4: (12, 17, 13, 15),
}


def command(cmd, **values):
    return eye.command(cmd, **values)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def set_profile_hand():
    return pose.set_hand_pair(
        grip=(0.0, 0.0, -0.7),
        aim_q=pose.quat_axis(1, -70),
    )


def capture_node_space(node, attempts=12):
    command("mod_cmd", name="mohu.vr.weapon.space", args=f"node={node}")
    for _ in range(attempts):
        set_profile_hand()
        native.frames(4)
        result = command(
            "mod_cmd", name="mohu.vr.weapon.space", args=""
        )
        value = json.loads(result["reply"])
        if value.get("valid") and value.get("node") == node:
            return value
    raise RuntimeError(f"weapon node {node} did not refresh")


def capture_nodes(model, out, weapon_id, slot):
    counts = {index: row["vertices"]
              for index, row in enumerate(model["nodes"])}
    nodes = {}
    for node, count in counts.items():
        if not count:
            continue
        calibration.CALIBRATION_NODE = node
        try:
            space = capture_node_space(node)
        except RuntimeError as error:
            raise RuntimeError(
                f"ID {weapon_id} node {node} capture was not refreshed"
            ) from error
        local, animated, local_sha, animated_sha, local_bytes, animated_bytes = (
            calibration.read_captured_vertices(count)
        )
        if int(space["local_addr"], 16) != int(model["nodes"][node]["address"], 16):
            raise RuntimeError(
                f"ID {weapon_id} node {node} source address changed during capture"
            )
        nodes[str(node)] = {
            "count": count,
            "local_address": model["nodes"][node]["address"],
            "local_sha256": local_sha,
            "animated_sha256": animated_sha,
            "local": local,
            "animated": animated,
        }
        (out / f"node-{node:02}.bin").write_bytes(local_bytes)
        (out / f"node-{node:02}-animated.bin").write_bytes(animated_bytes)
    return nodes


def capture_faces(model, out, weapon_id, slot):
    counts = {index: row["vertices"]
              for index, row in enumerate(model["nodes"])}
    address = int(model["faces"], 16)
    data = native.read(address, model["face_count"] * 28)
    triangles, consumed = mesh.decode_triangles(
        data, model["face_count"], counts
    )
    stream = data[:consumed]
    (out / "faces.bin").write_bytes(stream)
    return {
        "address": model["faces"],
        "bytes": consumed,
        "sha256": hashlib.sha256(stream).hexdigest(),
        "triangles": len(triangles),
    }


def validate_topology(profile, model, face_bytes, nodes):
    counts = [row["vertices"] for row in model["nodes"]]
    triangles, consumed = mesh.decode_triangles(
        face_bytes,
        model["face_count"],
        {node: count for node, count in enumerate(counts)},
    )
    if consumed != len(face_bytes):
        raise RuntimeError("Captured face stream length mismatch")
    vertices = {
        (int(node), index)
        for node, row in nodes.items()
        for index in range(row["count"])
    }
    kept = [
        triangle for triangle in triangles
        if all(topology.selected(profile, *vertex) for vertex in triangle)
    ]
    mixed = [
        triangle for triangle in triangles
        if any(topology.selected(profile, *vertex) for vertex in triangle)
        and not all(topology.selected(profile, *vertex) for vertex in triangle)
    ]
    selected_vertices = {
        vertex for vertex in vertices
        if topology.selected(profile, *vertex)
    }
    if mixed:
        raise RuntimeError(f"ID {profile['id']} has mixed arm/gun triangles")
    if len(kept) != profile["faces"]:
        raise RuntimeError(
            f"ID {profile['id']} retained {len(kept)} faces"
        )
    expected_vertices = sum(
        1 for node in range(len(counts))
        for vertex in range(counts[node])
        if topology.selected(profile, node, vertex)
    )
    if len(selected_vertices) != expected_vertices:
        raise RuntimeError("Captured node vertex accounting failed")
    return {
        "faces": len(kept),
        "vertices": len(selected_vertices),
        "masked_vertices": len(vertices) - len(selected_vertices),
        "mixed_triangles": 0,
        "components": topology.triangle_components(kept, selected_vertices),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--ids", type=int, nargs="+")
    args = parser.parse_args()

    selected_ids = set(args.ids or topology.PROFILES)
    unknown = selected_ids - set(topology.PROFILES)
    if unknown:
        parser.error(f"Unknown weapon IDs: {sorted(unknown)}")
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
    for slot in CYCLES:
        for suffix in ("pst", "thumb"):
            source = ROOT / (
                f"saves/openbios/state_8001F844_slot{slot:02}.{suffix}"
            )
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
        for path in preferences if path.is_file()
    }
    executable = (
        ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    )
    env = {
        key: value for key, value in os.environ.items()
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
        MOHU_VR_WEAPON_GUN_ONLY="1",
    )
    receipt = {
        "schema": 1,
        "kind": "W3.4 complete viewmodel topology and animated profile capture",
        "complete": False,
        "headset_used": False,
        "fixture": "copied root MP slots 1-4, native cycles, no fire",
        "executable_sha256": native.digest(executable),
        "source_hashes": {
            name: native.digest(ROOT / name)
            for name in (
                "vr/underground/vr_diagnostic.c",
                "vr/underground/weapon.c",
                "vr/underground/weapon.h",
                "vr/tools/check_weapon_meshes.py",
                "vr/tools/probe_weapon_profiles.py",
            )
        },
        "source_saves": source_hashes,
        "preferences": preference_hashes,
        "weapons": [],
    }
    process = None
    with (out / "stdout.log").open("w") as stdout, \
            (out / "stderr.log").open("w") as stderr:
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

            for slot, expected_cycle in CYCLES.items():
                native.load(slot)
                shot.comparison.release_load_override()
                pose.set_head()
                for switches, expected_id in enumerate(expected_cycle):
                    players = native.players()
                    weapon_id = players[0]["weapon_id"]
                    if weapon_id != expected_id:
                        raise RuntimeError(
                            f"Slot {slot} switch {switches} selected "
                            f"{weapon_id}, expected {expected_id}"
                        )
                    set_profile_hand()
                    native.frames(4)
                    model = native.first_person_model()
                    if weapon_id not in selected_ids:
                        if switches + 1 < len(expected_cycle):
                            native.switch()
                            shot.comparison.release_load_override()
                        continue
                    profile = topology.PROFILES[weapon_id]
                    case_dir = out / f"slot-{slot:02}-id-{weapon_id:02}"
                    case_dir.mkdir()
                    faces = capture_faces(model, case_dir, weapon_id, slot)
                    captured = capture_nodes(model, case_dir, weapon_id, slot)
                    face_bytes = (case_dir / "faces.bin").read_bytes()
                    profile_with_id = dict(profile, id=weapon_id)
                    topology_result = validate_topology(
                        profile_with_id, model, face_bytes, captured
                    )
                    _, images = pose.capture_eyes(case_dir / "pair")
                    row = {
                        "id": weapon_id,
                        "name": profile["name"],
                        "slot": slot,
                        "switches": switches,
                        "players": players,
                        "model": model,
                        "face_stream": faces,
                        "nodes": captured,
                        "topology": topology_result,
                        "images": images,
                        "stereo": command("stereo_stats"),
                        "render_pass": command("render_pass_stats"),
                    }
                    if row["render_pass"]["verify_mismatch"]:
                        raise RuntimeError("Stereo rollback verification failed")
                    receipt["weapons"].append(row)
                    save(out / "captures.json", receipt)
                    print(
                        f"captured slot {slot} switch {switches} "
                        f"id {weapon_id} {profile['name']}",
                        flush=True,
                    )
                    if switches + 1 < len(expected_cycle):
                        native.switch()
                        shot.comparison.release_load_override()
            ids = {row["id"] for row in receipt["weapons"]}
            if ids != selected_ids:
                raise RuntimeError(f"Captured IDs differ: {sorted(ids)}")
            receipt["complete"] = True
        except BaseException as error:
            receipt["error"] = str(error)
            try:
                receipt["failure_state"] = {
                    "players": native.players(),
                    "counters": command("mod_counters"),
                    "stereo": command("stereo_stats"),
                    "render_pass": command("render_pass_stats"),
                }
            except (OSError, RuntimeError):
                pass
            save(out / "captures.json", receipt)
            raise
        finally:
            try:
                command("openxr_hands_override", clear=1)
                command("mod_cmd", name="mohu.vr.stereo.pose", args="reset")
                command("mod_cmd", name="mohu.vr.weapon.pose", args="reset")
            except (OSError, RuntimeError, TypeError):
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
            save(out / "captures.json", receipt)

    if not (
        receipt["complete"]
        and receipt["source_saves_unchanged"]
        and receipt["preferences_unchanged"]
        and not receipt["remaining_game_pids"]
        and receipt["exit_code"] == 0
    ):
        raise RuntimeError("W3.4 profile capture did not close cleanly")
    if args.proof:
        compact = dict(receipt)
        compact["weapons"] = [
            {
                key: row[key] for key in (
                    "id", "name", "slot", "switches", "model",
                    "face_stream", "topology", "images", "stereo",
                    "render_pass",
                )
            }
            | {
                "node_capture": {
                    node: {
                        key: value[key] for key in (
                            "count", "local_address", "local_sha256",
                            "animated_sha256",
                        )
                    }
                    for node, value in row["nodes"].items()
                },
            }
            for row in receipt["weapons"]
        ]
        save(args.proof, compact)
    print(
        f"PASS: captured {len(receipt['weapons'])} complete-gun topologies "
        "and animated node sets"
    )


if __name__ == "__main__":
    main()
