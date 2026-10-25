"""Validate the P38 absolute hand/head coordinate contract in copied MP slot 1."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageChops, ImageDraw

import check_mp_view as eye
import inspect_weapon_sets as native


ROOT = native.ROOT
HAND_UNITS_PER_METRE = 48.0 / 0.067
HEAD_UNITS_PER_METRE = 1000.0
PIVOT = np.array([98.0, 296.0, 193.0], dtype=np.float64)
WEAPON_ROI = (250, 90, 512, 120)
WORLD_ROI = (110, 30, 190, 65)
RT_TOLERANCE = 1
TR_TOLERANCE = 1


def command(cmd, **values):
    return eye.command(cmd, **values)


def quat_axis(axis, degrees):
    angle = math.radians(degrees) * 0.5
    q = np.array([0.0, 0.0, 0.0, math.cos(angle)])
    q[axis] = math.sin(angle)
    return q


def quat_multiply(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array(
        [
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz,
        ]
    )


def quat_matrix(q):
    q = np.asarray(q, dtype=np.float64)
    q = q / np.linalg.norm(q)
    x, y, z, w = q
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def psx_rotation(q):
    signs = np.array([1.0, -1.0, -1.0])
    return signs[:, None] * quat_matrix(q) * signs[None, :]


def hand_transform(hands):
    grip = hands["pose"][1][0]
    aim = hands["pose"][1][1]
    origin_q = hands["origin_orientation_xyzw"]
    origin_p = np.asarray(hands["origin_position_m"], dtype=np.float64)
    grip_p = np.asarray(grip["position_m"], dtype=np.float64)
    o = quat_matrix(origin_q)
    e = quat_matrix(aim["orientation_xyzw"])
    signs = np.array([1.0, -1.0, -1.0])
    rotation = signs[:, None] * (o.T @ e) * signs[None, :]
    translation = signs * (o.T @ (grip_p - origin_p)) * HAND_UNITS_PER_METRE
    return rotation, translation


def expected_view(head):
    yaw = math.radians(head["yaw_mdeg"] * 0.001)
    pitch = math.radians(head["pitch_mdeg"] * 0.001)
    qyaw = np.array([0.0, math.sin(yaw * 0.5), 0.0, math.cos(yaw * 0.5)])
    qpitch = np.array([math.sin(pitch * 0.5), 0.0, 0.0, math.cos(pitch * 0.5)])
    q = quat_multiply(qyaw, qpitch)
    elevation = quat_matrix(q)
    signs = np.array([1.0, -1.0, -1.0])
    rotation = signs[:, None] * elevation.T * signs[None, :]
    position_m = np.array(
        [
            head["x_milli"] / (1000.0 * HEAD_UNITS_PER_METRE),
            head["y_milli"] / (1000.0 * HEAD_UNITS_PER_METRE),
            -head["z_milli"] / (1000.0 * HEAD_UNITS_PER_METRE),
        ]
    )
    translation = signs * (elevation.T @ (-position_m)) * HEAD_UNITS_PER_METRE
    return rotation, translation


def decode_control(words):
    raw = [int(value, 16) for value in words]
    rotation = []
    for index in range(9):
        half = raw[index // 2] >> ((index & 1) * 16)
        rotation.append(struct.unpack("<h", struct.pack("<H", half & 0xFFFF))[0])
    translation = [
        struct.unpack("<i", struct.pack("<I", raw[index] & 0xFFFFFFFF))[0]
        for index in range(5, 8)
    ]
    return np.asarray(rotation, dtype=np.int32).reshape(3, 3), np.asarray(
        translation, dtype=np.int32
    )


def compose_expected(native_words, hands):
    native_rotation, native_translation = decode_control(native_words)
    hand_rotation, hand_translation = hand_transform(hands)
    rotation = np.rint(hand_rotation @ native_rotation).astype(np.int32)
    translation = np.rint(
        PIVOT
        + hand_translation
        + hand_rotation @ (native_translation - PIVOT)
    ).astype(np.int32)
    return rotation, translation, hand_rotation, hand_translation


def transform_point(rotation, translation, point):
    return rotation.astype(np.float64) @ np.asarray(point) / 4096.0 + translation


def observed_control(capture):
    return decode_control(capture["tracked_gte"])


def affine_from_control(words):
    rotation, translation = decode_control(words)
    result = np.eye(4)
    result[:3, :3] = rotation.astype(np.float64) / 4096.0
    result[:3, 3] = translation
    return result


def recover_hand_affine(capture):
    native_affine = affine_from_control(capture["native_gte"])
    tracked_affine = affine_from_control(capture["tracked_gte"])
    return tracked_affine @ np.linalg.inv(native_affine)


def expected_hand_affine(hand_rotation, hand_translation):
    result = np.eye(4)
    result[:3, :3] = hand_rotation
    result[:3, 3] = PIVOT + hand_translation - hand_rotation @ PIVOT
    return result


def assert_control(capture, expected_rotation, expected_translation):
    observed_rotation, observed_translation = observed_control(capture)
    rotation_error = int(np.max(np.abs(observed_rotation - expected_rotation)))
    translation_error = int(
        np.max(np.abs(observed_translation - expected_translation))
    )
    if rotation_error > RT_TOLERANCE or translation_error > TR_TOLERANCE:
        raise RuntimeError(
            f"GTE composition mismatch: RT={rotation_error}, TR={translation_error}"
        )
    return {
        "rt_max_abs_error": rotation_error,
        "tr_max_abs_error": translation_error,
    }


def assert_view(capture, head):
    rotation, translation = expected_view(head)
    observed_rotation = (
        np.asarray(capture["view_rt12"], dtype=np.float64) / 4096.0
    ).reshape(3, 3)
    observed_translation = np.asarray(
        capture["view_t_precise"], dtype=np.float64
    )
    rotation_error = float(np.max(np.abs(observed_rotation - rotation)))
    translation_error = float(np.max(np.abs(observed_translation - translation)))
    if rotation_error > 1.0 / 4096.0 + 1e-12 or translation_error > 1e-6:
        raise RuntimeError(
            f"eye-view mismatch: R={rotation_error}, t={translation_error}"
        )
    return {
        "rotation_max_abs_error": rotation_error,
        "translation_max_abs_error": translation_error,
        "observed_eye_from_origin": {
            "rotation": observed_rotation.tolist(),
            "translation": observed_translation.tolist(),
        },
    }


def set_hand_pair(
    grip=(0.0, 0.0, 0.0),
    aim=(0.0, 0.0, 0.0),
    grip_q=(0.0, 0.0, 0.0, 1.0),
    aim_q=(0.0, 0.0, 0.0, 1.0),
    origin=(0.0, 0.0, 0.0),
    origin_q=(0.0, 0.0, 0.0, 1.0),
    *,
    focused=1,
    active=1,
    flags=15,
    age_ms=0,
):
    origin_args = {
        "origin_valid": 1,
        "ox_mm": round(origin[0] * 1000),
        "oy_mm": round(origin[1] * 1000),
        "oz_mm": round(origin[2] * 1000),
        "oqx": round(origin_q[0] * 1_000_000),
        "oqy": round(origin_q[1] * 1_000_000),
        "oqz": round(origin_q[2] * 1_000_000),
        "oqw": round(origin_q[3] * 1_000_000),
    }
    common = {
        "hand": "right",
        "focused": focused,
        "active": active,
        "flags": flags,
        "age_ms": age_ms,
        **origin_args,
    }
    command(
        "openxr_hands_override",
        pose="grip",
        px_mm=round(grip[0] * 1000),
        py_mm=round(grip[1] * 1000),
        pz_mm=round(grip[2] * 1000),
        qx=round(grip_q[0] * 1_000_000),
        qy=round(grip_q[1] * 1_000_000),
        qz=round(grip_q[2] * 1_000_000),
        qw=round(grip_q[3] * 1_000_000),
        **common,
    )
    command(
        "openxr_hands_override",
        pose="aim",
        px_mm=round(aim[0] * 1000),
        py_mm=round(aim[1] * 1000),
        pz_mm=round(aim[2] * 1000),
        qx=round(aim_q[0] * 1_000_000),
        qy=round(aim_q[1] * 1_000_000),
        qz=round(aim_q[2] * 1_000_000),
        qw=round(aim_q[3] * 1_000_000),
        **common,
    )
    return command("openxr_hands")


def set_head(yaw_mdeg=0, pitch_mdeg=0, x_milli=0, y_milli=0, z_milli=0):
    result = command(
        "mod_cmd",
        name="mohu.vr.stereo.pose",
        args=(
            f"yaw={yaw_mdeg} pitch={pitch_mdeg} "
            f"x={x_milli} y={y_milli} z={z_milli}"
        ),
    )
    if result["result"] != 1:
        raise RuntimeError(f"head pose rejected: {result}")
    return {
        "yaw_mdeg": yaw_mdeg,
        "pitch_mdeg": pitch_mdeg,
        "x_milli": x_milli,
        "y_milli": y_milli,
        "z_milli": z_milli,
        "requested_physical_mm": [
            x_milli / HEAD_UNITS_PER_METRE,
            y_milli / HEAD_UNITS_PER_METRE,
            z_milli / HEAD_UNITS_PER_METRE,
        ],
    }


def capture_space(attempts=3):
    for _ in range(attempts):
        result = command(
            "mod_cmd", name="mohu.vr.weapon.space", args="node=11"
        )
        value = json.loads(result["reply"])
        if value.get("valid"):
            return value
        native.frames(2)
    raise RuntimeError("weapon space capture was not refreshed")


def image_difference_pixels(first, second, box):
    difference = ImageChops.difference(
        first.crop(box).convert("RGB"), second.crop(box).convert("RGB")
    )
    return sum(pixel != (0, 0, 0) for pixel in difference.getdata())


def write_control_sheet(out, rows, proof_path):
    selected = (
        ("hand base", "hand-base"),
        ("hand +X", "hand-x-+1"),
        ("hand +Y", "hand-y-+1"),
        ("hand +Z", "hand-z-+1"),
        ("head +X 100 mm", "head-x-+100mm"),
        ("head yaw +15", "head-yaw-+15deg"),
        ("head pitch -15", "head-pitch--15deg"),
        ("combined", "combined-head-hand"),
    )
    by_case = {row["case"]: row for row in rows}
    images = []
    for label, case in selected:
        by_case[case]
        image_dir = out / (
            ("head-phase/" if case.startswith(("head-", "combined-")) else "")
            + "pair-"
            + case
        )
        image_path = next(image_dir.glob("*_sbs.png"))
        source = Image.open(image_path).convert("RGB")
        image = Image.new("RGB", (source.width, source.height + 16), (0, 0, 0))
        image.paste(source, (0, 16))
        ImageDraw.Draw(image).text((5, 2), label, fill=(255, 255, 255))
        images.append(image)
    sheet = Image.new(
        "RGB", (images[0].width, sum(image.height for image in images)),
        (0, 0, 0)
    )
    y = 0
    for image in images:
        sheet.paste(image, (0, y))
        y += image.height
    sheet.save(proof_path)
    return native.digest(proof_path)


def assert_render_clean():
    stats = command("stereo_stats")
    deadline = time.monotonic() + 3
    while (
        stats["eye_hashes"][0] != stats["eye_hashes"][1]
        or stats["eye_cycles"][0] != stats["eye_cycles"][1]
    ):
        if time.monotonic() > deadline:
            raise RuntimeError("stereo eye state did not settle")
        time.sleep(0.02)
        stats = command("stereo_stats")
    checks = command("render_pass_stats")
    if (
        stats["failed"]
        or stats["eye_cycles"][0] != stats["eye_cycles"][1]
        or checks["verify_mismatch"]
        or checks["vram_leaks"]
        or checks["watchdog"]
        or checks["nesting_repairs"]
    ):
        raise RuntimeError("stereo/rollback invariant failed")
    return stats, checks


def capture_eyes(directory):
    for attempt in range(2):
        target = directory if attempt == 0 else directory.with_name(
            directory.name + "-retry"
        )
        target.mkdir()
        command("stereo_dump", path=target.as_posix(), count=1)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            left_files = list(target.glob("*_left.png"))
            right_files = list(target.glob("*_right.png"))
            if len(left_files) == len(right_files) == 1:
                try:
                    images = [
                        Image.open(left_files[0]).convert("RGB"),
                        Image.open(right_files[0]).convert("RGB"),
                    ]
                    visible = all(
                        image.size == (512, 120)
                        and sum(
                            pixel != (0, 0, 0) for pixel in image.getdata()
                        )
                        >= 64
                        and len(set(image.getdata())) >= 20
                        for image in images
                    )
                    if visible:
                        return images, {
                            path.name: native.digest(path)
                            for path in (left_files[0], right_files[0])
                        }
                except OSError:
                    pass
            time.sleep(0.05)
        native.frames(3)
    raise RuntimeError("No fresh visibly populated eye pair")


def counters():
    return {
        row["name"]: row["count"]
        for row in command("mod_counters")["counters"]
    }


def counter_delta(before, after):
    return {
        key: value - before.get(key, 0)
        for key, value in after.items()
        if key.startswith("mohu.vr.weapon.")
    }


def run_case(out, name, hands, head, baseline):
    native.frames(10)
    images, files = capture_eyes(out / f"pair-{name}")
    capture = capture_space()
    stats, checks = assert_render_clean()
    if ImageChops.difference(images[0], images[1]).getbbox():
        raise RuntimeError("zero-IPD eyes differ")
    rotation, translation, hand_rotation, hand_translation = compose_expected(
        capture["native_gte"], hands
    )
    control_error = assert_control(capture, rotation, translation)
    hand_affine_observed = recover_hand_affine(capture)
    hand_affine_expected = expected_hand_affine(
        hand_rotation, hand_translation
    )
    affine_rotation_error = float(
        np.max(
            np.abs(
                hand_affine_observed[:3, :3]
                - hand_affine_expected[:3, :3]
            )
        )
    )
    affine_translation_error = float(
        np.max(
            np.abs(
                hand_affine_observed[:3, 3]
                - hand_affine_expected[:3, 3]
            )
        )
    )
    if affine_rotation_error > 1e-4 or affine_translation_error > 1.0:
        raise RuntimeError(
            "recovered absolute hand transform mismatch: "
            f"R={affine_rotation_error}, t={affine_translation_error}"
        )
    view_error = assert_view(capture, head)
    point_origin = transform_point(
        *observed_control(capture), capture["animated"][:3]
    )
    analytic_model_point = np.array([0.0, 0.0, 100.0])
    point_origin_fixed = transform_point(
        *observed_control(capture), analytic_model_point
    )
    eye_rotation = np.asarray(view_error["observed_eye_from_origin"]["rotation"])
    eye_translation = np.asarray(
        view_error["observed_eye_from_origin"]["translation"]
    )
    point_eye = eye_rotation @ point_origin + eye_translation
    point_eye_fixed = eye_rotation @ point_origin_fixed + eye_translation
    full_changed = weapon_changed = world_changed = None
    if baseline is not None:
        full_changed = image_difference_pixels(
            baseline["images"][0], images[0], (0, 0, 512, 120)
        )
        weapon_changed = image_difference_pixels(
            baseline["images"][0], images[0], WEAPON_ROI
        )
        world_changed = image_difference_pixels(
            baseline["images"][0], images[0], WORLD_ROI
        )
    return {
        "case": name,
        "hands": hands,
        "head": head,
        "capture": capture,
        "expected": {
            "hand_rotation": hand_rotation.tolist(),
            "hand_translation": hand_translation.tolist(),
            "gte_rotation": rotation.tolist(),
            "gte_translation": translation.tolist(),
            "point_origin": point_origin.tolist(),
            "point_eye": point_eye.tolist(),
            "analytic_model_point": analytic_model_point.tolist(),
            "point_origin_fixed": point_origin_fixed.tolist(),
            "point_eye_fixed": point_eye_fixed.tolist(),
            "hand_affine": hand_affine_observed.tolist(),
        },
        "numerical": {
            **control_error,
            **view_error,
            "hand_rotation_max_abs_error": affine_rotation_error,
            "hand_translation_max_abs_error": affine_translation_error,
        },
        "images": files,
        "pixel_difference": {
            "weapon_roi": weapon_changed,
            "world_roi": world_changed,
            "full": full_changed,
        },
        "stereo": {
            "pairs": stats["pairs"],
            "failed": stats["failed"],
            "eye_cycles": stats["eye_cycles"],
            "eye_hashes": stats["eye_hashes"],
            "verify_checks": checks["verify_checks"],
            "verify_mismatch": checks["verify_mismatch"],
        },
    }


def run_head_suite(out, receipt):
    native.frames(4)
    command("set_input", buttons=65535, ly=1000)
    native.frames(30)
    command("set_input", buttons=65535, ly=0)
    native.frames(4)
    receipt["head_test_positioning"] = {
        "action": "native forward analog ly=1000 for 30 guest frames",
        "guest_frames": 30,
        "fire": False,
        "weapon_switches": 0,
    }
    fixed_hands = set_hand_pair()
    receipt["head_test_positioning"]["players"] = native.players()
    head_rows = []
    for name, head_args in (
        ("head-x--100mm", {"x_milli": -100000}),
        ("head-x-+100mm", {"x_milli": 100000}),
        ("head-y--100mm", {"y_milli": -100000}),
        ("head-y-+100mm", {"y_milli": 100000}),
        ("head-z--100mm", {"z_milli": -100000}),
        ("head-z-+100mm", {"z_milli": 100000}),
        ("head-yaw--15deg", {"yaw_mdeg": -15000}),
        ("head-yaw-+15deg", {"yaw_mdeg": 15000}),
        ("head-pitch--15deg", {"pitch_mdeg": -15000}),
        ("head-pitch-+15deg", {"pitch_mdeg": 15000}),
    ):
        head = set_head(**head_args)
        fixed_hands = command("openxr_hands")
        row = run_case(out, name, fixed_hands, head, None)
        head_rows.append(row)
        receipt["cases"].append(row)
    receipt["head_only"] = head_rows
    anchor = np.asarray(head_rows[0]["expected"]["hand_affine"])
    for row in head_rows[1:]:
        current = np.asarray(row["expected"]["hand_affine"])
        if (
            np.max(np.abs(current[:3, :3] - anchor[:3, :3])) > 1e-4
            or np.max(np.abs(current[:3, 3] - anchor[:3, 3])) > 1.0
        ):
            raise RuntimeError("head-only motion changed the origin-space hand anchor")

    combined_q = quat_axis(1, 15)
    combined_hands = set_hand_pair(
        grip=(0.08, 0.04, -0.02),
        aim=(0.08, 0.04, -0.02),
        grip_q=combined_q,
        aim_q=combined_q,
    )
    combined = run_case(
        out,
        "combined-head-hand",
        combined_hands,
        set_head(yaw_mdeg=15000, pitch_mdeg=-10000, x_milli=50000),
        None,
    )
    receipt["combined"] = combined
    receipt["cases"].append(combined)
    return combined


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    if native.game_pids():
        raise RuntimeError("close the existing game before this owned control")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("diagnostic port 4372 occupied")
    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    copies = out / "saves/openbios"
    copies.mkdir(parents=True)
    sources = []
    for suffix in ("pst", "thumb"):
        source = ROOT / f"saves/openbios/state_8001F844_slot01.{suffix}"
        sources.append(source)
        shutil.copyfile(source, copies / source.name)
    preferences = [
        ROOT / "build-release/settings.toml",
        ROOT / "build-release/keybinds.ini",
        Path("C:/Program Files (x86)/Steam/config/steamvr.vrsettings"),
    ]
    source_hashes = {str(p): native.digest(p) for p in sources}
    preference_hashes = {str(p): native.digest(p) for p in preferences if p.is_file()}
    exe = ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
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
        "date": "2026-10-25",
        "fixture": "copied root MP slot 1, P38 ID 0, zero switches, no fire",
        "executable_sha256": native.digest(exe),
        "source_hashes": {
            name: native.digest(ROOT / name)
            for name in (
                "vr/underground/vr_diagnostic.c",
                "vr/underground/weapon.c",
                "vr/underground/weapon.h",
                "vr/tools/check_weapon_pose_spaces.py",
                "vr/tools/weapon_pose_head_worker.py",
                "psxrecomp/runtime/src/debug_server.c",
                "psxrecomp/runtime/src/psx_openxr.c",
            )
        },
        "input_contract": {
            "hand_units_per_metre": HAND_UNITS_PER_METRE,
            "head_diagnostic_units_per_metre": HEAD_UNITS_PER_METRE,
            "pivot_native_camera": PIVOT.tolist(),
            "direct_weapon_x_or_yaw": False,
            "stereo_eye_offset": 0,
            "rt_tolerance": RT_TOLERANCE,
            "tr_tolerance": TR_TOLERANCE,
            "visible_pixels_minimum": 64,
            "visible_colors_minimum": 20,
        },
        "source_saves": source_hashes,
        "preferences": preference_hashes,
        "cases": [],
        "complete": False,
    }
    head_directory = out / "head-phase"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "vr/tools/weapon_pose_head_worker.py"),
            str(head_directory),
        ],
        cwd=ROOT,
        check=True,
    )
    head_result = json.loads(
        (head_directory / "head-result.json").read_text(encoding="utf-8")
    )
    if not head_result.get("complete") or head_result.get("remaining_game_pids"):
        raise RuntimeError("head phase did not complete cleanly")
    receipt["head_worker"] = {
        "directory": str(head_directory.relative_to(out)),
        "owned_pid": head_result.get("owned_pid"),
        "exit_code": head_result.get("exit_code"),
        "executable_sha256": head_result.get("executable_sha256"),
    }
    receipt["head_test_positioning"] = head_result["head_test_positioning"]
    receipt["head_only"] = head_result["head_only"]
    receipt["combined"] = head_result["combined"]
    receipt["cases"].extend(head_result["cases"])
    owned_pid = None
    with (out / "stdout.log").open("w") as stdout, (
        out / "stderr.log"
    ).open("w") as stderr:
        process = subprocess.Popen(
            [
                str(exe),
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
        owned_pid = process.pid
        receipt["owned_pid"] = owned_pid
        try:
            deadline = time.monotonic() + 40
            while True:
                if process.poll() is not None:
                    raise RuntimeError("diagnostic game exited during startup")
                try:
                    command("ping")
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.1)
            receipt["load"] = native.load(1)
            players = native.players()
            if (players[0]["weapon_slot"], players[0]["weapon_id"]) != (0, 0):
                raise RuntimeError("fixture is not P38 in slot 1")
            receipt["players_before"] = players

            receipt["load"] = native.load(1)
            command("openxr_hands_override", clear=1)
            set_head()
            native.frames(6)
            baseline_images, baseline_files = capture_eyes(out / "pair-native")
            baseline = {"images": baseline_images, "files": baseline_files}
            receipt["native"] = {
                "images": baseline_files,
                "stereo": assert_render_clean()[0],
            }

            # Fresh-load absolute starts.
            for name, grip in (
                ("absolute-start-a", (0.05, 0.03, -0.025)),
                ("absolute-start-b", (-0.06, -0.02, 0.025)),
            ):
                receipt["load"] = native.load(1)
                hands = set_hand_pair(grip=grip, aim=grip)
                receipt["cases"].append(run_case(out, name, hands, set_head(), baseline))

            start_a = receipt["cases"][-2]["capture"]
            start_b = receipt["cases"][-1]["capture"]
            if start_a["tracked_gte"] == start_b["tracked_gte"]:
                raise RuntimeError("different first hand poses produced the same GTE")

            # Hand-only translation and orientation.
            command("openxr_hands_override", clear=1)
            receipt["load"] = native.load(1)
            base_hands = set_hand_pair()
            receipt["base_hand_case"] = run_case(
                out, "hand-base", base_hands, set_head(), baseline
            )
            receipt["cases"].append(receipt["base_hand_case"])
            hand_cases = []
            for axis, index in (("x", 0), ("y", 1), ("z", 2)):
                for sign in (-1, 1):
                    grip = [0.0, 0.0, 0.0]
                    grip[index] = sign * 0.1
                    hand_cases.append((f"hand-{axis}-{sign:+d}", tuple(grip), None))
            for name, axis, sign in (
                ("hand-yaw", 1, -1), ("hand-yaw", 1, 1),
                ("hand-pitch", 0, -1), ("hand-pitch", 0, 1),
                ("hand-roll", 2, -1), ("hand-roll", 2, 1),
            ):
                q = quat_axis(axis, sign * 15)
                hand_cases.append((f"{name}-{sign:+d}", (0.0, 0.0, 0.0), q))
            hand_rows = []
            for name, grip, q in hand_cases:
                q = tuple(q if q is not None else (0.0, 0.0, 0.0, 1.0))
                hands = set_hand_pair(grip=grip, aim=grip, grip_q=q, aim_q=q)
                row = run_case(out, name, hands, set_head(), baseline)
                if row["pixel_difference"]["weapon_roi"] < 20:
                    raise RuntimeError(f"{name} did not visibly move the weapon")
                if row["pixel_difference"]["world_roi"] != 0:
                    raise RuntimeError(f"{name} moved the sampled world")
                hand_rows.append(row)
                receipt["cases"].append(row)
            receipt["hand_only"] = hand_rows

            # Move origin and hand consistently. The pure transform must remain
            # unchanged when the pose is expressed in the new origin.
            q_origin = quat_axis(1, 15)
            p_origin = np.array([0.12, 0.2, -0.3])
            q_relative = quat_axis(2, 10)
            p_relative = np.array([0.03, -0.02, 0.04])
            p_new = p_origin + quat_matrix(q_origin) @ p_relative
            q_new = quat_multiply(q_origin, q_relative)
            base_origin_hands = set_hand_pair(
                grip=tuple(p_relative),
                aim=tuple(p_relative),
                grip_q=tuple(q_relative),
                aim_q=tuple(q_relative),
            )
            origin_base = run_case(
                out, "origin-identity", base_origin_hands, set_head(),
                baseline
            )
            moved_origin_hands = set_hand_pair(
                grip=tuple(p_new),
                aim=tuple(p_new),
                grip_q=tuple(q_new),
                aim_q=tuple(q_new),
                origin=tuple(p_origin),
                origin_q=tuple(q_origin),
            )
            origin_moved = run_case(
                out, "origin-moved", moved_origin_hands, set_head(),
                baseline
            )
            origin_error = float(
                np.max(
                    np.abs(
                        np.asarray(origin_base["expected"]["hand_affine"])
                        - np.asarray(origin_moved["expected"]["hand_affine"])
                    )
                )
            )
            if origin_error > 1.0:
                raise RuntimeError(f"origin-space anchor changed by {origin_error}")
            receipt["origin_recenter"] = {
                "base": origin_base,
                "moved": origin_moved,
                "origin_position_m": p_origin.tolist(),
                "origin_orientation_xyzw": q_origin.tolist(),
                "anchor_max_abs_error": origin_error,
                "physical_recenter": "not tested; W1 uses explicit synthetic origin",
            }
            receipt["cases"].extend([origin_base, origin_moved])

            # Invalid samples must fall back without writing a pose. The bad
            # quaternion is rejected by the override API before any state change.
            command("openxr_hands_override", clear=1)
            set_head()
            invalid_cases = []
            for name, values, expect_fallback in (
                ("invalid-unfocused", {"focused": 0}, True),
                ("invalid-inactive", {"active": 0}, True),
                ("invalid-missing-validity", {"flags": 1}, True),
                ("invalid-stale-151ms", {"age_ms": 151}, True),
            ):
                before = counters()
                hands = set_hand_pair(**values)
                native.frames(4)
                images, files = capture_eyes(out / f"pair-{name}")
                after = counters()
                stats, _ = assert_render_clean()
                changed = image_difference_pixels(
                    baseline["images"][0], images[0], WEAPON_ROI
                )
                delta = counter_delta(before, after)
                if delta.get("mohu.vr.weapon.viewmodel_apply", 0):
                    raise RuntimeError(f"{name} did not fall back natively")
                if expect_fallback and not delta.get(
                    "mohu.vr.weapon.tracking_fallback", 0
                ):
                    raise RuntimeError(f"{name} did not report fallback")
                invalid_cases.append(
                    {
                        "case": name,
                        "hands": hands,
                        "images": files,
                        "weapon_roi_difference": changed,
                        "counter_delta": delta,
                        "stereo": stats,
                    }
                )
                command("openxr_hands_override", clear=1)

            bad_quaternion = None
            try:
                command(
                    "openxr_hands_override",
                    hand="right",
                    pose="grip",
                    active=1,
                    focused=1,
                    flags=15,
                    px_mm=0,
                    py_mm=0,
                    pz_mm=0,
                    qx=0,
                    qy=0,
                    qz=0,
                    qw=0,
                )
            except RuntimeError as error:
                bad_quaternion = str(error)
            if not bad_quaternion:
                raise RuntimeError("bad quaternion override was not rejected")
            native.frames(3)
            invalid_cases.append({"case": "invalid-bad-quaternion", "error": bad_quaternion})

            before = counters()
            recovery_hands = set_hand_pair(grip=(0.1, 0.0, 0.0), aim=(0.1, 0.0, 0.0))
            recovery = run_case(
                out, "valid-recovery", recovery_hands, set_head(), baseline
            )
            after = counters()
            recovery["counter_delta"] = counter_delta(before, after)
            if not recovery["counter_delta"].get("mohu.vr.weapon.viewmodel_apply", 0):
                raise RuntimeError("valid recovery did not write the pose")
            receipt["invalid_recovery"] = {
                "invalid": invalid_cases,
                "recovery": recovery,
            }
            receipt["cases"].append(recovery)

            receipt["players_after"] = native.players()
            if (
                receipt["players_after"][0]["weapon_id"] != 0
                or receipt["players_after"][0]["clip"] != players[0]["clip"]
                or receipt["players_after"][1]["position"] != players[1]["position"]
                or receipt["players_after"][1]["health_raw"] != players[1]["health_raw"]
            ):
                raise RuntimeError("test changed weapon, clip or P2 health")
            receipt["complete"] = True
            native.save(out / "receipt.json", receipt)
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
        raise RuntimeError("W1 harness did not close cleanly")
    if args.proof:
        proof = {
            key: receipt[key]
            for key in (
                "schema",
                "date",
                "fixture",
                "executable_sha256",
                "source_hashes",
                "input_contract",
                "source_saves",
                "preferences",
                "complete",
                "source_saves_unchanged",
                "preferences_unchanged",
                "remaining_game_pids",
            )
        }
        proof["case_summary"] = [
            {
                "case": row["case"],
                "rt_max_abs_error": row["numerical"]["rt_max_abs_error"],
                "tr_max_abs_error": row["numerical"]["tr_max_abs_error"],
                "view_rotation_error": row["numerical"]["rotation_max_abs_error"],
                "view_translation_error": row["numerical"]["translation_max_abs_error"],
                "hand_rotation_error": row["numerical"]["hand_rotation_max_abs_error"],
                "hand_translation_error": row["numerical"]["hand_translation_max_abs_error"],
                "weapon_pixels": row["pixel_difference"]["weapon_roi"],
                "world_pixels": row["pixel_difference"]["world_roi"],
                "full_pixels": row["pixel_difference"]["full"],
                "images": row["images"],
                "eye_hashes": row["stereo"]["eye_hashes"],
                "verify_checks": row["stereo"]["verify_checks"],
                "image_directory": (
                    "head-phase/"
                    if row["case"].startswith(("head-", "combined-"))
                    else ""
                ) + "pair-" + row["case"],
            }
            for row in receipt["cases"]
        ]
        proof["origin_recenter"] = {
            key: value
            for key, value in receipt["origin_recenter"].items()
            if key not in ("base", "moved")
        }
        proof["origin_recenter"]["anchor_max_abs_error"] = receipt[
            "origin_recenter"
        ]["anchor_max_abs_error"]
        proof["head_test_positioning"] = receipt["head_test_positioning"]
        proof["head_worker"] = receipt["head_worker"]
        proof["invalid_cases"] = [
            {
                "case": row["case"],
                "weapon_roi_difference": row.get("weapon_roi_difference"),
                "counter_delta": row.get("counter_delta"),
                "error": row.get("error"),
            }
            for row in receipt["invalid_recovery"]["invalid"]
        ]
        proof["recovery_counter_delta"] = receipt["invalid_recovery"][
            "recovery"
        ]["counter_delta"]
        proof["limits"] = [
            "Synthetic desktop poses, not physical headset acceptance.",
            "Provisional pivot is not a W3 grip calibration.",
            "No firing, shot redirection, HUD or performance work.",
            "Physical recenter is not tested by the synthetic origin control.",
        ]
        args.proof.parent.mkdir(parents=True, exist_ok=True)
        control_sheet = args.proof.with_name("weapon-pose-space-controls.png")
        control_hash = write_control_sheet(
            out, receipt["cases"], control_sheet
        )
        proof["control_sheet"] = {
            "path": str(control_sheet.resolve().relative_to(ROOT)),
            "sha256": control_hash,
        }
        native.save(args.proof, proof)
    print("PASS: W1 P38 absolute hand/head spatial controls", flush=True)


if __name__ == "__main__":
    main()
