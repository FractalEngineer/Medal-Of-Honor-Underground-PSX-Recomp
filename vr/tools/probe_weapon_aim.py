"""Exercise the hand-fixed native shot candidate on desktop.

Every pose is solved through the current authored weapon defaults. Native
construction, spread, ammunition, motion and damage remain active.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import socket
import subprocess
import time

import numpy as np

import check_weapon_pose_spaces as poses
import inspect_weapon_sets as native
import probe_native_shot as shot
import probe_p38_headset as comparison
import probe_shot_families as families
from weapon_defaults import calibrations

ROOT = native.ROOT
PSX_SIGNS = np.array([1.0, -1.0, -1.0])
NON_SHOTGUN_AXIS_COSINE = 0.9995
THROWN_AXIS_COSINE = 0.9945


def mod_command(name, args):
    result = native.command("mod_cmd", name=name, args=args)
    if result["result"] != 1:
        raise RuntimeError(f"{name} {args!r}: {result}")
    return json.loads(result["reply"])


def shot_command(args):
    return mod_command("mohu.vr.shot", args)


def marker_command(args):
    return mod_command("mohu.vr.marker", args)


def quat_from_matrix(matrix):
    m = np.asarray(matrix, dtype=np.float64)
    trace = float(np.trace(m))
    if trace > 0:
        scale = math.sqrt(trace + 1.0) * 2.0
        q = np.array([
            (m[2, 1] - m[1, 2]) / scale,
            (m[0, 2] - m[2, 0]) / scale,
            (m[1, 0] - m[0, 1]) / scale,
            0.25 * scale,
        ])
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        scale = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2.0
        q = np.array([
            0.25 * scale,
            (m[0, 1] + m[1, 0]) / scale,
            (m[0, 2] + m[2, 0]) / scale,
            (m[2, 1] - m[1, 2]) / scale,
        ])
    elif m[1, 1] > m[2, 2]:
        scale = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2.0
        q = np.array([
            (m[0, 1] + m[1, 0]) / scale,
            0.25 * scale,
            (m[1, 2] + m[2, 1]) / scale,
            (m[0, 2] - m[2, 0]) / scale,
        ])
    else:
        scale = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2.0
        q = np.array([
            (m[0, 2] + m[2, 0]) / scale,
            (m[1, 2] + m[2, 1]) / scale,
            0.25 * scale,
            (m[1, 0] - m[0, 1]) / scale,
        ])
    return q / np.linalg.norm(q)


def rotation_between(source, target):
    source = np.asarray(source, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    source /= np.linalg.norm(source)
    target /= np.linalg.norm(target)
    cross = np.cross(source, target)
    dot = float(np.clip(np.dot(source, target), -1.0, 1.0))
    if np.linalg.norm(cross) < 1e-9:
        if dot > 0:
            return np.eye(3)
        axis = np.cross(source, np.array([1.0, 0.0, 0.0]))
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(source, np.array([0.0, 1.0, 0.0]))
        axis /= np.linalg.norm(axis)
        return -np.eye(3) + 2.0 * np.outer(axis, axis)
    skew = np.array([
        [0.0, -cross[2], cross[1]],
        [cross[2], 0.0, -cross[0]],
        [-cross[1], cross[0], 0.0],
    ])
    return np.eye(3) + skew + skew @ skew / (1.0 + dot)


def model_basis_vector(calibration, vector):
    return np.array([
        np.dot(calibration["right"], vector),
        -np.dot(calibration["up"], vector),
        np.dot(calibration["forward"], vector),
    ])


def psx_hand_quaternion(matrix):
    # vr_pose_to_transform produces diag(1,-1,-1) * Q * diag(1,-1,-1).
    source = np.diag(PSX_SIGNS) @ matrix @ np.diag(PSX_SIGNS)
    return quat_from_matrix(source)


def marker_aim(before, calibration, marker):
    camera = shot_command("camera")
    if not camera["valid"]:
        raise RuntimeError("No canonical camera for marker-axis aim")
    rt, tr = poses.decode_control(
        [f"{word:08X}" for word in camera["control"]]
    )
    rt = rt / 4096.0
    target_world = np.asarray(before[1]["position"], dtype=float) / 65536.0
    target_world[1] -= 150.0
    target_camera = rt @ target_world + tr
    grip = np.array([0.15, 0.0, -0.5])
    hand_origin = grip * PSX_SIGNS * poses.HAND_UNITS_PER_METRE
    grip_pivot = np.asarray(calibration["grip_pivot"], dtype=float)
    tip = np.asarray(calibration["muzzle"], dtype=float)
    axis = np.asarray(calibration["forward"], dtype=float)
    basis_axis = model_basis_vector(calibration, axis)
    basis_tip = model_basis_vector(calibration, tip - grip_pivot)
    scale = poses.HAND_UNITS_PER_METRE / calibration["model_units_per_metre"]

    rotation = np.eye(3)
    for _ in range(4):
        tip_camera = hand_origin + scale * rotation @ basis_tip
        direction = target_camera - tip_camera
        direction /= np.linalg.norm(direction)
        rotation = rotation_between(basis_axis, direction)
    quaternion = psx_hand_quaternion(rotation)
    if quaternion[3] < 0:
        quaternion = -quaternion
    poses.set_hand_pair(grip=grip.tolist(), aim_q=quaternion.tolist(),
                        grip_q=quaternion.tolist())
    solved_direction = rotation @ basis_axis
    solved_direction /= np.linalg.norm(solved_direction)
    cosine = float(np.dot(solved_direction, direction))
    if cosine < 0.9999:
        raise RuntimeError(f"Marker-axis pose solve failed: cosine={cosine}")
    return {
        "camera": camera,
        "target_world": target_world.tolist(),
        "hand_camera": hand_origin.tolist(),
        "marker_axis": axis.tolist(),
        "marker_direction_camera": solved_direction.tolist(),
        "quaternion_xyzw": quaternion.tolist(),
        "axis_cosine": cosine,
    }


def affine_point(control, point):
    values = np.array(control, dtype=np.uint32)
    rt = np.array([
        [np.int16(values[0] & 0xffff), np.int16(values[0] >> 16),
         np.int16(values[1] & 0xffff)],
        [np.int16(values[1] >> 16), np.int16(values[2] & 0xffff),
         np.int16(values[2] >> 16)],
        [np.int16(values[3] & 0xffff), np.int16(values[3] >> 16),
         np.int16(values[4] & 0xffff)],
    ], dtype=float) / 4096.0
    tr = np.array([np.int32(word) for word in values[5:8]], dtype=float)
    return rt @ np.asarray(point, dtype=float) + tr


def camera_point_to_world(camera, point):
    rt, tr = poses.decode_control([f"{word:08X}" for word in camera])
    inverse = np.linalg.inv(rt / 4096.0)
    return inverse @ (np.asarray(point, dtype=float) - tr)


def verify_marker_conversion(sample, marker, camera):
    if not marker["valid"] or marker["id"] != sample["weapon"]:
        raise RuntimeError(f"ID {sample['weapon']}: invalid per-shot marker")
    if sample.get("hand_fixed"):
        calibration = calibrations()[sample["weapon"]]
        tip = calibration["muzzle"]
        axis = np.asarray(calibration["forward"])
    else:
        # Historical animated-origin receipts retain their declared policy.
        tip = marker["tip"]
        axis = np.asarray(marker["tip"]) - np.asarray(marker["axis_base"])
    camera_tip = affine_point(sample["weapon_control"], tip)
    camera_axis = (
        affine_point(sample["weapon_control"], np.asarray(tip) + axis)
        - camera_tip
    )
    world_tip = camera_point_to_world(camera["control"], camera_tip)
    expected = np.asarray(sample["aimed_position"], dtype=float) / 65536.0
    error = float(np.max(np.abs(world_tip - expected)))
    if error > 1.0 / 65536.0:
        raise RuntimeError(
            f"ID {sample['weapon']}: marker/aim origin error={error}"
        )
    world_axis = (
        camera_point_to_world(camera["control"], camera_tip + camera_axis)
        - world_tip
    )
    world_axis /= np.linalg.norm(world_axis)
    return {
        "origin_error_world_units": error,
        "world_axis": world_axis.tolist(),
    }


def origin_rows(shot_address):
    rows = []
    for index in range(marker_command("origins")["count"]):
        row = marker_command(f"origin={index}")
        if row["event_shot"] == shot_address:
            rows.append((index, row))
    return rows


def run_fallback_control(name, out, *, marker_mode=None, invalid_hand=False,
                         port=1, recover=False):
    families.prepare_weapon(1, 0)
    native.frames(8)
    shot_command("stop")
    shot_command("start")
    native.frames(12)
    before = native.players()
    request = None
    if port == 1 and marker_mode is None:
        request = marker_aim(before, calibrations()[0], marker_command("status"))
        if invalid_hand:
            poses.set_hand_pair(
                grip=(0.15, 0.0, -0.5),
                aim_q=request["quaternion_xyzw"],
                grip_q=request["quaternion_xyzw"],
                focused=0,
            )
        native.frames(8)
    if marker_mode == "missing":
        marker_command("stop")
    elif marker_mode == "stale":
        marker_command("freeze")
        native.frames(40)

    marker_before = marker_command("status")
    native.command("wtrace_range", lo="0x800B0000", hi="0x801FF000")
    native.command("wtrace_clear")
    collector = shot.TraceCollector({
        **shot.FILTERS,
        "motion_context": (0x8006EB8C, 0x8006F7D0),
        "shot_update": (0x80047720, 0x80047C80),
        "rng": families.RNG_FILTER,
    })
    if port == 1:
        native.command("openxr_input_override", right_trigger=1000)
    else:
        native.command("set_input", port=2, buttons=65535 ^ 0x4000)
    collector.wait(8)
    release_before = native.command("frame")["frame"]
    native.command("openxr_input_override", clear=1)
    native.command("set_input", port=2, buttons=65535)
    release_after = native.command("frame")["frame"]
    collector.wait(180)
    native.command("wtrace_range", lo="0", hi="0")
    collector.collect()
    shot_command("stop")

    status = shot_command("status")
    if status["overflow"]:
        raise RuntimeError(f"{name}: shot sample overflow")
    shots = [
        shot_command(f"read={index}") for index in range(status["count"])
    ]
    owner = int(before[port - 1]["actor"], 16)
    owned = [row for row in shots if row["owner"] == owner]
    after = native.players()
    if not owned or after[port - 1]["clip"] >= before[port - 1]["clip"]:
        raise RuntimeError(f"{name}: missing native shot/ammo consumption")
    if (not recover and any(row["aimed"] for row in owned)) or \
            (recover and any(not row["aimed"] for row in owned)):
        raise RuntimeError(f"{name}: invalid control was overridden")
    if not recover and any(any(row["aimed_position"]) for row in owned):
        raise RuntimeError(f"{name}: invalid control reused an aimed position")
    if any(not row["code_valid"] for row in owned):
        raise RuntimeError(f"{name}: missing native code guard")
    if recover and any(not row["family_eligible"] for row in owned):
        raise RuntimeError(f"{name}: valid control was not family-eligible")
    if port == 2 and any(row["family_eligible"] for row in owned):
        raise RuntimeError(f"{name}: P2 shot passed the P1 family guard")

    lifetimes = families.trace_lifecycle(shots, collector)
    for lifetime in lifetimes:
        born = lifetime["birth_frame"]
        lifetime["trigger_phase"] = (
            "held" if born < release_before else
            "released" if born > release_after else "release-boundary"
        )
    damage = [
        row for row in collector.entries("damage")
        if (int(row["addr"], 0) & 0x1FFFFFFF) ==
           native.p2_health_address(before[port - 1])
        and int(row["old"], 0) > int(row["new"], 0)
    ]
    row = {
        "name": name,
        "port": port,
        "invalid_hand": invalid_hand,
        "marker_mode": marker_mode or "valid",
        "recovered": recover,
        "before": before,
        "after": after,
        "marker_before": marker_before,
        "request": request,
        "shots": shots,
        "owned_shots": owned,
        "lifetimes": lifetimes,
        "native_damage": damage,
        "trace_counts": {
            key: len(value) for key, value in collector.rows.items()
        },
    }
    comparison.save_json(out / f"control-{name}.json", row)
    print(
        f"CONTROL {name}: shots={len(owned)} aimed=0 "
        f"valid={marker_before['valid']}",
        flush=True,
    )
    return row


def run_fallback_controls(out):
    controls = []
    marker_command("start")
    controls.append(run_fallback_control("missing-marker", out,
                                         marker_mode="missing"))
    marker_command("start")
    controls.append(run_fallback_control("stale-marker", out,
                                         marker_mode="stale"))
    marker_command("start")
    controls.append(run_fallback_control("unfocused-hand", out,
                                         invalid_hand=True))
    marker_command("start")
    controls.append(run_fallback_control("p2-fire", out, port=2))
    marker_command("start")
    controls.append(run_fallback_control("recovered", out, recover=True))
    return controls


def spread_summary(motions):
    directions = [row["direction"] for row in motions]
    angles = [
        math.degrees(math.acos(float(np.clip(np.dot(left, right), -1, 1))))
        for index, left in enumerate(directions)
        for right in directions[index + 1:]
    ]
    speeds = [
        math.sqrt(sum(value * value for value in row["delta_world"]))
        for row in motions
    ]
    return {
        "pellets": len(motions),
        "maximum_pair_angle_degrees": max(angles),
        "minimum_pair_angle_degrees": min(angles),
        "speeds_world_units_per_frame": speeds,
        "speed_range": max(speeds) - min(speeds),
    }


def target_ray_miss(origin, direction, target):
    origin = np.asarray(origin, dtype=float)
    direction = np.asarray(direction, dtype=float)
    target = np.asarray(target, dtype=float)
    direction /= np.linalg.norm(direction)
    projected = float(np.dot(target - origin, direction))
    closest = origin + projected * direction
    return float(np.linalg.norm(target - closest))


def run_weapon(slot, switches, weapon_id, calibration, out):
    families.prepare_weapon(slot, switches)
    native.frames(8)
    shot_command("stop")
    shot_command("start-p1")
    native.frames(12)
    before = native.players()
    if before[0]["weapon_id"] != weapon_id:
        raise RuntimeError(
            f"Wrong fixture: slot {slot} switch {switches} selected "
            f"{before[0]['weapon_id']}, expected {weapon_id}"
        )
    marker_before = marker_command("status")
    if not marker_before["valid"] or marker_before["id"] != weapon_id:
        raise RuntimeError(f"ID {weapon_id}: canonical marker unavailable")
    request = marker_aim(before, calibration, marker_before)
    native.frames(8)

    control = families.fire_control(weapon_id)
    if control["approach_frames"]:
        native.command("openxr_input_override", ly=1000)
        native.frames(control["approach_frames"])
        native.command("openxr_input_override", clear=1)
        native.frames(4)
        before = native.players()
        request = marker_aim(before, calibration, marker_command("status"))
        native.frames(8)

    native.command("wtrace_range", lo="0x800B0000", hi="0x801FF000")
    native.command("wtrace_clear")
    collector = shot.TraceCollector({
        **shot.FILTERS,
        "motion_context": (0x8006EB8C, 0x8006F7D0),
        "shot_update": (0x80047720, 0x80047C80),
        "rng": families.RNG_FILTER,
    })
    native.command("openxr_input_override", right_trigger=1000)
    collector.wait(min(control["hold_frames"], 8))
    release_before = native.command("frame")["frame"]
    native.command("openxr_input_override", clear=1)
    release_after = native.command("frame")["frame"]
    collector.wait(control["release_frames"])
    native.command("wtrace_range", lo="0", hi="0")
    collector.collect()
    shot_command("stop")

    status = shot_command("status")
    if status["overflow"]:
        raise RuntimeError(f"ID {weapon_id}: shot sample overflow")
    shots = [
        shot_command(f"read={index}") for index in range(status["count"])
    ]
    after = native.players()
    if not shots or after[0]["clip"] == before[0]["clip"] and \
            after[0]["reserve"] == before[0]["reserve"]:
        raise RuntimeError(f"ID {weapon_id}: missing native ammunition change")

    motions = []
    converted = []
    impacts = []
    stage_events = []
    for index, sample in enumerate(shots):
        if sample["weapon"] != weapon_id or not sample["family_eligible"]:
            raise RuntimeError(f"ID {weapon_id}: family guard rejected shot")
        marker = marker_command(f"shot={index}")
        impact_position = sample["aimed_position"]
        events = origin_rows(sample["shot"])
        if sample["type"] == 0x13F3 or sample["type"] == 0x13F1:
            if sample["aimed"] or not events or not all(
                    row["aimed"] and row["code_valid"] for _, row in events):
                raise RuntimeError(
                    f"ID {weapon_id}: deferred origin did not convert"
                )
            origin_index, event = events[-1]
            stage_events.extend(row for _, row in events)
            event_sample = {
                **sample,
                "weapon_control": event["weapon_control"],
                "aimed_position": event["aimed_position"],
            }
            impact_position = event["aimed_position"]
            event_marker = marker_command(f"origin={origin_index}")
            converted.append(verify_marker_conversion(
                event_sample, event_marker, request["camera"]
            ))
        else:
            if not sample["aimed"]:
                raise RuntimeError(f"ID {weapon_id}: shot fell back to native")
            converted.append(verify_marker_conversion(
                sample, marker, request["camera"]
            ))
        motions.append(shot.first_motion(
            collector.entries("motion"), sample["shot"]
        ))
        axis_cosine = float(np.dot(
            converted[-1]["world_axis"], motions[-1]["direction"]
        ))
        minimum_axis_cosine = (
            THROWN_AXIS_COSINE if weapon_id in (10, 15) else
            NON_SHOTGUN_AXIS_COSINE
        )
        if weapon_id != 4 and axis_cosine < minimum_axis_cosine:
            raise RuntimeError(
                f"ID {weapon_id}: native motion disagrees with marker axis"
            )
        impacts.append({
            "axis_cosine": axis_cosine,
            "target_ray_miss_world_units": target_ray_miss(
                np.asarray(impact_position, dtype=float) / 65536.0,
                converted[-1]["world_axis"], request["target_world"],
            ),
        })

    damage_rows = [
        row for row in collector.entries("damage")
        if (int(row["addr"], 0) & 0x1FFFFFFF) ==
           native.p2_health_address(before[1])
        and int(row["old"], 0) > int(row["new"], 0)
    ]
    if weapon_id not in (10, 15) and not damage_rows:
        raise RuntimeError(f"ID {weapon_id}: synthetic aim did not damage P2")

    if weapon_id == 4:
        spread = spread_summary(motions)
        if spread["pellets"] != 6 or \
                spread["maximum_pair_angle_degrees"] <= 0.01 or \
                spread["speed_range"] <= 1.0:
            raise RuntimeError(f"Shotgun native spread/speed changed: {spread}")
    else:
        spread = None

    lifetimes = families.trace_lifecycle(shots, collector)
    for lifetime in lifetimes:
        born = lifetime["birth_frame"]
        lifetime["trigger_phase"] = (
            "held" if born < release_before else
            "released" if born > release_after else "release-boundary"
        )
    rng = [
        row for row in collector.entries("rng")
        if int(row["pc"], 0) == families.RNG_STORE_PC
    ]
    if not rng:
        raise RuntimeError(f"ID {weapon_id}: missing native RNG updates")

    row = {
        "id": weapon_id,
        "name": native.WEAPONS[weapon_id],
        "slot": slot,
        "switches": switches,
        "before": before,
        "after": after,
        "request": request,
        "camera": request["camera"],
        "marker_before": marker_before,
        "shots": shots,
        "motions": motions,
        "converted": converted,
        "impacts": impacts,
        "lifetimes": lifetimes,
        "origins": stage_events,
        "spread": spread,
        "trigger_window": {
            "release_before": release_before,
            "release_after": release_after,
            "requested_hold_frames": min(control["hold_frames"], 8),
        },
        "rng": {
            "calls": len(rng),
            "store_pc": f"0x{families.RNG_STORE_PC:08X}",
            "events": [
                {"seq": row["seq"], "old": row["old"], "new": row["new"]}
                for row in rng
            ],
            "states_before": [row["old"] for row in rng],
            "states_after": [row["new"] for row in rng],
        },
        "native_damage": damage_rows,
        "trace_counts": {
            key: len(value) for key, value in collector.rows.items()
        },
    }
    comparison.save_json(out / f"id-{weapon_id:02}.json", row)
    print(
        f"ID {weapon_id:02} {row['name']}: shots={len(shots)} "
        f"damage={bool(damage_rows)} spread="
        f"{spread['maximum_pair_angle_degrees'] if spread else 'n/a'}",
        flush=True,
    )
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--ids", type=int, nargs="+")
    args = parser.parse_args()
    selected = set(args.ids or native.WEAPONS)
    unknown = selected - set(native.WEAPONS)
    if unknown:
        parser.error(f"Unknown weapon IDs: {sorted(unknown)}")
    if args.proof and selected != set(native.WEAPONS):
        parser.error("--proof requires all 13 weapon IDs")
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic TCP port 4372 is occupied")

    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    saves = out / "saves/openbios"
    saves.mkdir(parents=True)
    source_hashes = {}
    for slot in families.CYCLES:
        for suffix in ("pst", "thumb"):
            source = ROOT / (
                f"saves/openbios/state_8001F844_slot{slot:02}.{suffix}"
            )
            shutil.copyfile(source, saves / source.name)
            source_hashes[str(source.relative_to(ROOT))] = native.digest(source)
    preferences = comparison.hash_existing(comparison.preference_paths())
    executable = ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    receipt = {
        "schema": 1,
        "kind": "W5.3d all-family animated-marker desktop candidate",
        "complete": False,
        "headset_used": False,
        "fixture": "copied root MP slots 1-4; first occurrence of every weapon ID",
        "executable_sha256": native.digest(executable),
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "build": comparison.build_configuration(
            ROOT / "build-release/CMakeCache.txt"
        ),
        "sources": {
            name: native.digest(ROOT / name)
            for name in (
                "vr/underground/vr_diagnostic.c",
                "vr/underground/shot.h",
                "vr/underground/weapon.c",
                "vr/underground/weapon.h",
                "vr/underground/weapon_markers.h",
                "vr/underground/weapon_marker_groups.inc",
                "vr/tools/probe_weapon_aim.py",
            )
        },
        "source_saves": source_hashes,
        "preferences": preferences,
        "weapons": [],
        "controls": [],
        "limits": [
            "Synthetic desktop controls; physical grip/scale and headset acceptance remain open.",
            "Provisional non-P38 marker axes are not newly measured physical bores.",
            "This candidate does not close matched tracked impact preservation.",
        ],
    }
    env = comparison.environment("native", True)
    env.update(
        PSX_INTERNAL_RESOLUTION="native",
        PSX_VR_WEAPON_POSE="1",
        MOHU_VR_WEAPON_CALIBRATED="1",
        MOHU_VR_WEAPON_AIM="1",
    )
    process = None
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
            table = calibrations()
            for slot, switches, weapon_id in families.first_occurrences():
                if weapon_id not in selected:
                    continue
                receipt["weapons"].append(
                    run_weapon(
                        slot, switches, weapon_id, table[weapon_id], out
                    )
                )
                comparison.save_json(out / "receipt.json", receipt)
            counters = native.command("mod_counters")
            lookup = {row["name"]: row["count"] for row in counters["counters"]}
            if lookup.get("mohu.vr.shot.weapon.tracking_fallback", 0):
                raise RuntimeError("A candidate shot fell back to native")
            render = shot_command("render")
            if not render["weapon_aim"]:
                raise RuntimeError("Candidate flag did not reach the runtime")
            if selected == set(native.WEAPONS):
                receipt["controls"] = run_fallback_controls(out)
                marker_status = marker_command("status")
                if marker_status["replay_rejected"] <= 0:
                    raise RuntimeError("No marker replay-rejection evidence")
                receipt["control_marker_status"] = marker_status
            receipt["render"] = render
            receipt["counters"] = counters
            receipt["render_pass"] = native.command("render_pass_stats")
            receipt["stereo"] = native.command("stereo_stats")
            published = receipt["stereo"]["published"]
            recovered = (
                published["valid"] and
                receipt["stereo"]["last_pair_id"] >
                receipt["stereo"]["last_failed_attempt"]
            )
            if receipt["render_pass"]["verify_mismatch"] or \
                    receipt["render_pass"]["vram_leaks"] or \
                    receipt["stereo"]["refused"] or not recovered:
                raise RuntimeError("Stereo/render rollback did not recover")
            if receipt["stereo"]["failed"]:
                receipt["stereo_recovery"] = {
                    "discarded": receipt["stereo"]["failed"],
                    "last_failed_attempt":
                        receipt["stereo"]["last_failed_attempt"],
                    "last_published_pair":
                        receipt["stereo"]["last_pair_id"],
                    "recovered": True,
                }
            receipt["complete"] = True
        except BaseException as error:
            receipt["error"] = str(error)
            raise
        finally:
            try:
                native.command("openxr_hands_override", clear=1)
                native.command("openxr_input_override", clear=1)
                native.command("wtrace_range", lo="0", hi="0")
                shot_command("stop")
                native.command("quit")
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
                for path, value in preferences.items()
            )
            receipt["remaining_game_pids"] = native.game_pids()
            comparison.save_json(out / "receipt.json", receipt)

    if not (
        receipt["complete"]
        and {row["id"] for row in receipt["weapons"]} == selected
        and receipt["exit_code"] == 0
        and receipt["source_saves_unchanged"]
        and receipt["preferences_unchanged"]
        and not receipt["remaining_game_pids"]
    ):
        raise RuntimeError("Weapon-aim probe did not close cleanly")
    if args.proof:
        receipt["raw_receipt"] = str(
            (out / "receipt.json").relative_to(ROOT)
        )
        receipt = families.seal_receipt(out / "receipt.json", receipt)
        comparison.save_json(args.proof, receipt)
    print(f"PASS: {len(selected)} animated-marker weapon controls", flush=True)


if __name__ == "__main__":
    main()
