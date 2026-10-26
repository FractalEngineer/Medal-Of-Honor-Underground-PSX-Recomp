"""Measure moving grip/muzzle markers during native weapon animation states.

The probe uses copied root multiplayer slots and native pad input. It captures
one complete animated-model frame per sample, so marker groups are evaluated at
one exact producer output rather than across several guest frames.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time

import numpy as np
from PIL import Image, ImageDraw

import check_mp_view as eye
import check_weapon_meshes as topology
import check_weapon_pose_spaces as pose
import inspect_weapon_sets as native
import probe_native_shot as shot
import probe_weapon_profiles as profiles


ROOT = native.ROOT
CYCLES = profiles.CYCLES
FIRE = 0x4000
RELOAD = 0x8000
SWITCH = 0x2000
R2 = 0x0200
FIREARM_IDS = {0, 1, 4, 8, 9, 12, 14, 16, 17}
RELOAD_IDS = {0, 1, 4, 8, 9, 12, 14, 16, 17}
SPECIAL_IDS = {5, 10, 13, 14, 15}
MARKER_DISTANCE_RATIO = 0.01
MARKER_ANGLE_DEGREES = 2.0


def command(cmd, **values):
    return eye.command(cmd, **values)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def marker_groups():
    complete = json.loads((
        ROOT / "vr/proof/weapon-p38-complete-calibration-receipt.json"
    ).read_text(encoding="utf-8"))
    provisional = json.loads((
        ROOT / "vr/proof/weapon-provisional-calibrations-receipt.json"
    ).read_text(encoding="utf-8"))
    result = {
        0: {
            "grip": [
                [complete["marker_groups"]["grip_node"], vertex]
                for vertex in complete["marker_groups"]["grip_vertex_indices"]
            ],
            "muzzle": [
                [complete["marker_groups"]["muzzle_node"], vertex]
                for vertex in complete["marker_groups"]["muzzle_vertex_indices"]
            ],
        },
    }
    for row in provisional["weapons"]:
        calibration = row["calibration"]
        if "grip_markers" not in calibration:
            continue
        result[row["id"]] = {
            "grip": calibration["grip_markers"],
            "muzzle": calibration["muzzle_markers"],
        }
    if set(result) != set(topology.PROFILES):
        raise RuntimeError("Marker groups do not cover all measured weapon IDs")
    return result


def set_profile_hand():
    return pose.set_hand_pair(
        grip=(0.0, 0.0, -0.7),
        aim_q=pose.quat_axis(1, -70),
    )


def capture_frame(attempts=3):
    for _ in range(attempts):
        set_profile_hand()
        command(
            "mod_cmd", name="mohu.vr.weapon.space", args="frame-capture"
        )
        for _ in range(4):
            native.frames(1)
            result = command(
                "mod_cmd", name="mohu.vr.weapon.space", args="frame"
            )
            frame = json.loads(result["reply"])
            if frame.get("valid"):
                break
        if not frame.get("valid"):
            continue
        local = {}
        animated = {}
        for start in range(0, frame["vertex_count"], 4):
            chunk = json.loads(command(
                "mod_cmd", name="mohu.vr.weapon.space",
                args=f"frame={start}",
            )["reply"])
            if (
                not chunk.get("valid")
                or chunk.get("sequence") != frame["sequence"]
                or chunk.get("start") != start
                or chunk.get("total") != frame["vertex_count"]
            ):
                raise RuntimeError(f"Invalid frame chunk: {chunk}")
            for node, index, before, after in zip(
                chunk["nodes"], chunk["indices"],
                chunk["local"], chunk["animated"],
            ):
                key = (int(node), int(index))
                local[key] = list(before)
                animated[key] = list(after)
        frame["local"] = local
        frame["animated"] = animated
        frame["animated_sha256"] = hashlib.sha256(
            b"".join(
                bytes((node, index & 0xFF, index >> 8))
                + np.asarray(animated[(node, index)], dtype="<i2").tobytes()
                for node, index in sorted(animated)
            )
        ).hexdigest()
        return frame
    return None


def marker_point(frame, vertices):
    try:
        points = np.asarray(
            [frame["animated"][(int(node), int(index))][:3]
             for node, index in vertices],
            dtype=np.float64,
        )
    except KeyError as error:
        raise RuntimeError(f"Marker vertex missing from frame: {error}") from error
    return points.mean(axis=0)


def analyze(frame, baseline, groups):
    grip = marker_point(frame, groups["grip"])
    muzzle = marker_point(frame, groups["muzzle"])
    base_grip = marker_point(baseline, groups["grip"])
    base_muzzle = marker_point(baseline, groups["muzzle"])
    delta = muzzle - grip
    base_delta = base_muzzle - base_grip
    distance = float(np.linalg.norm(delta))
    base_distance = float(np.linalg.norm(base_delta))
    tolerance = max(1.0, base_distance * MARKER_DISTANCE_RATIO)
    if distance <= 1e-9 or base_distance <= 1e-9:
        raise RuntimeError("Degenerate animated grip/muzzle distance")
    cosine = float(np.dot(delta, base_delta) / (distance * base_distance))
    angle = math.degrees(math.acos(max(-1.0, min(1.0, cosine))))
    keys = {
        (int(node), int(index))
        for name in ("grip", "muzzle")
        for node, index in groups[name]
    }
    marker_motion = max(
        float(np.linalg.norm(
            np.asarray(frame["animated"][key][:3], dtype=np.float64)
            - np.asarray(baseline["animated"][key][:3], dtype=np.float64)
        ))
        for key in keys
    )
    all_motion = max(
        float(np.linalg.norm(
            np.asarray(frame["animated"][key][:3], dtype=np.float64)
            - np.asarray(baseline["animated"][key][:3], dtype=np.float64)
        ))
        for key in baseline["animated"]
        if key in frame["animated"]
    )
    control_changed = frame["native_gte"] != baseline["native_gte"]
    rigid = (
        abs(distance - base_distance) <= tolerance
        and angle <= MARKER_ANGLE_DEGREES
    )
    return {
        "frame": frame["frame"],
        "sequence": frame["sequence"],
        "id": frame["id"],
        "grip": grip.tolist(),
        "muzzle": muzzle.tolist(),
        "grip_muzzle_distance": distance,
        "distance_delta": distance - base_distance,
        "axis_angle_degrees": angle,
        "marker_motion": marker_motion,
        "animated_vertex_motion": all_motion,
        "native_control_changed": control_changed,
        "animated": all_motion > 0.0 or control_changed,
        "marker_contract": "rigid" if rigid else "moving-marker-required",
        "native_gte": frame["native_gte"],
        "animated_sha256": frame["animated_sha256"],
    }


def hold(mask):
    command("set_input", buttons=str(65535 ^ mask))


def press(mask, frames=1):
    command("press", buttons=65535 ^ mask, frames=frames)


def release_all():
    command("set_input", buttons="0xffff")


def player_state():
    player = native.players()[0]
    return {
        key: player[key]
        for key in ("weapon_slot", "weapon_id", "clip", "reserve")
    }


def player_effect(before, after):
    return {
        "before": before,
        "after": after,
        "changed": {
            key: [before[key], after[key]]
            for key in before if before[key] != after[key]
        },
    }


def sample_offsets(label, expected_id, offsets, baseline, groups,
                   allow_hidden=False):
    samples = []
    elapsed = 0
    for offset in offsets:
        if offset < elapsed:
            raise ValueError("Animation sample offsets must increase")
        native.frames(offset - elapsed)
        frame = capture_frame()
        if frame is None:
            if not allow_hidden:
                raise RuntimeError("Animated weapon frame did not refresh")
            samples.append({
                "case": label,
                "offset": offset,
                "model_hidden": True,
            })
            break
        if frame["id"] != expected_id:
            samples.append({
                "case": label,
                "offset": offset,
                "frame": frame["frame"],
                "sequence": frame["sequence"],
                "id": frame["id"],
                "transitioned": True,
            })
            break
        samples.append({"case": label, "offset": offset}
                       | analyze(frame, baseline, groups))
        elapsed = offset
    return samples


def capture_visual(directory, label):
    directory.mkdir(parents=True, exist_ok=True)
    images, hashes = eye.pair(directory / label)
    return {
        "sha256": hashes,
        "weapon_center_pixels": [
            len(set(image.crop((250, 90, 512, 120)).getdata()))
            for image in images
        ],
        "eyes_identical": images[0].tobytes() == images[1].tobytes(),
    }


def prepare_weapon(slot, switches):
    native.load(slot)
    shot.comparison.release_load_override()
    for _ in range(switches):
        native.switch()
        shot.comparison.release_load_override()
    pose.set_head()
    set_profile_hand()
    native.frames(5)


def probe_weapon(slot, switches, expected_id, out, groups):
    prepare_weapon(slot, switches)
    before = native.players()
    if before[0]["weapon_id"] != expected_id:
        raise RuntimeError(
            f"Slot {slot} switch {switches} selected "
            f"{before[0]['weapon_id']}, expected {expected_id}"
        )
    baseline = capture_frame()
    if baseline is None:
        raise RuntimeError("Animated baseline did not refresh")
    if baseline["id"] != expected_id:
        raise RuntimeError(
            f"Expected animated baseline ID {expected_id}, got {baseline['id']}"
        )
    baseline_analysis = analyze(baseline, baseline, groups)
    row = {
        "id": expected_id,
        "name": native.WEAPONS[expected_id],
        "slot": slot,
        "switches": switches,
        "players_before": before,
        "baseline": baseline_analysis,
        "states": {},
        "effects": {},
        "visuals": {},
    }
    row["visuals"]["idle"] = capture_visual(
        out / f"slot-{slot:02}-id-{expected_id:02}", "idle"
    )

    if expected_id in FIREARM_IDS:
        before_action = player_state()
        press(FIRE, frames=24)
        state = sample_offsets(
            "recoil", expected_id, (1, 2, 4, 8, 16, 24),
            baseline, groups,
        )
        row["effects"]["recoil"] = player_effect(
            before_action, player_state()
        )
        release_all()
        row["states"]["recoil"] = state
        native.frames(45)
        row["visuals"]["recoil"] = capture_visual(
            out / f"slot-{slot:02}-id-{expected_id:02}", "recoil"
        )
    elif expected_id != 5:
        before_action = player_state()
        press(FIRE, frames=60)
        special_samples = sample_offsets(
            "special", expected_id, (1, 1, 2, 2, 4, 8),
            baseline, groups, allow_hidden=True,
        )
        elapsed = special_samples[-1]["offset"]
        native.frames(max(0, 60 - elapsed))
        release_all()
        native.frames(20)
        post_frame = capture_frame()
        if post_frame is not None:
            if post_frame["id"] == expected_id:
                special_samples.append(
                    {"case": "special", "offset": 60 + 20}
                    | analyze(post_frame, baseline, groups)
                )
            else:
                special_samples.append({
                    "case": "special",
                    "offset": 60 + 20,
                    "frame": post_frame["frame"],
                    "sequence": post_frame["sequence"],
                    "id": post_frame["id"],
                    "transitioned": True,
                })
        row["states"]["special"] = special_samples
        row["effects"]["special"] = player_effect(
            before_action, player_state()
        )
        row["visuals"]["special"] = capture_visual(
            out / f"slot-{slot:02}-id-{expected_id:02}", "special"
        )

    if (expected_id in RELOAD_IDS and
            player_state()["weapon_id"] == expected_id):
        before_action = player_state()
        press(RELOAD, frames=60)
        row["states"]["reload"] = sample_offsets(
            "reload", expected_id, (1, 2, 4, 8, 16, 24),
            baseline, groups,
        )
        row["effects"]["reload"] = player_effect(
            before_action, player_state()
        )
        release_all()
        row["visuals"]["reload"] = capture_visual(
            out / f"slot-{slot:02}-id-{expected_id:02}", "reload"
        )

    if expected_id == 5:
        before_action = player_state()
        command("set_input", buttons=str(0xFFFF ^ R2))
        native.frames(20)
        hold(R2)
        row["states"]["scoped"] = sample_offsets(
            "scoped", expected_id, (1, 2, 4, 8), baseline, groups,
            allow_hidden=True,
        )
        press((0xFFFF ^ R2) ^ FIRE, frames=12)
        row["states"]["scoped-recoil"] = sample_offsets(
            "scoped-recoil", expected_id, (1, 2, 4, 8),
            baseline, groups, allow_hidden=True,
        )
        row["effects"]["scoped-shot"] = player_effect(
            before_action, player_state()
        )
        release_all()
        prepare_weapon(slot, switches)

    release_all()
    prepare_weapon(slot, switches)
    before_action = player_state()
    press(SWITCH, frames=12)
    initial_switch = sample_offsets(
        "switch", expected_id, (1, 2, 4, 8), baseline, groups,
    )
    native.frames(90)
    row["effects"]["switch"] = player_effect(
        before_action, player_state()
    )
    row["states"]["switch"] = initial_switch
    row["visuals"]["switch"] = capture_visual(
        out / f"slot-{slot:02}-id-{expected_id:02}", "switch"
    )
    native.frames(90)
    row["players_after"] = native.players()

    active_states = []
    for name, samples in row["states"].items():
        mode = "idle"
        for sample in samples:
            if sample.get("model_hidden"):
                mode = "model-hidden"
                break
            if sample.get("transitioned"):
                mode = "animated"
                break
            if sample["animated"]:
                mode = "animated"
                break
        contracts = {
            sample["marker_contract"] for sample in samples
            if sample.get("animated") and not sample.get("transitioned")
        }
        effect_name = "scoped-shot" if name == "scoped-recoil" else name
        effect_changed = row["effects"].get(effect_name, {}).get("changed", {})
        if name in ("scoped", "scoped-recoil"):
            confirmed = mode == "model-hidden"
        elif name == "reload":
            confirmed = any(
                key in effect_changed for key in ("clip", "reserve")
            )
        else:
            confirmed = any(key in effect_changed for key in (
                "clip", "reserve", "weapon_slot", "weapon_id"
            ))
        if mode == "idle":
            mode = "not-observed"
        if "moving-marker-required" in contracts:
            contract = "moving-marker-required"
        else:
            contract = "rigid"
        analyzed = [
            sample for sample in samples
            if not sample.get("transitioned") and not sample.get("model_hidden")
        ]
        active_states.append({
            "case": name,
            "mode": mode,
            "evidence": "confirmed" if confirmed else "not-observed",
            "marker_contract": contract,
            "samples": len(samples),
            "max_marker_motion": max(
                (s["marker_motion"] for s in analyzed), default=0.0
            ),
            "max_vertex_motion": max(
                (s["animated_vertex_motion"] for s in analyzed), default=0.0
            ),
            "control_changes": sum(
                s["native_control_changed"] for s in analyzed
            ),
        })
    row["summary"] = active_states
    confirmed_states = [
        state for state in active_states if state["evidence"] == "confirmed"
    ]
    if not confirmed_states:
        raise RuntimeError(f"ID {expected_id} has no confirmed animation state")
    if any(state["marker_contract"] == "moving-marker-required"
           for state in confirmed_states):
        row["muzzle_marker_contract"] = "moving-marker-required"
    else:
        row["muzzle_marker_contract"] = "rigid"
    action_effect = row["effects"].get(
        "recoil", row["effects"].get(
            "special", row["effects"].get("scoped-shot", {})
        )
    )
    changed = action_effect.get("changed", {})
    if expected_id != 5 and not any(
            key in changed for key in ("clip", "reserve", "weapon_slot")):
        raise RuntimeError(f"ID {expected_id} action did not consume or switch")
    switch_changed = row["effects"]["switch"]["changed"]
    if not any(key in switch_changed for key in ("weapon_slot", "weapon_id")):
        raise RuntimeError(f"ID {expected_id} native switch did not change slot")
    return row


def first_occurrences(selected=None):
    result = []
    seen = set()
    for slot, cycle in CYCLES.items():
        for switches, weapon_id in enumerate(cycle):
            if weapon_id in seen or (
                    selected is not None and weapon_id not in selected):
                continue
            seen.add(weapon_id)
            result.append((slot, switches, weapon_id))
    expected = set(topology.PROFILES) if selected is None else set(selected)
    if seen != expected:
        raise RuntimeError("First occurrences do not cover all weapon IDs")
    return result


def write_sheet(out, rows):
    panel_width, panel_height = 262, 30
    scale = 2
    label_width = 170
    cases = ("idle", "recoil", "reload", "switch")
    sheet = Image.new(
        "RGB",
        (label_width + panel_width * scale * len(cases),
         panel_height * scale * len(rows)),
        (20, 20, 20),
    )
    draw = ImageDraw.Draw(sheet)
    for row_index, row in enumerate(rows):
        draw.text(
            (6, row_index * panel_height * scale + 17),
            f"{row['id']:02} {row['name']}",
            fill=(235, 235, 235),
        )
        for column, case in enumerate(cases):
            source_case = case
            if source_case not in row["visuals"]:
                source_case = "special"
            if source_case not in row["visuals"]:
                source_case = "idle"
            directory = out / f"slot-{row['slot']:02}-id-{row['id']:02}"
            if source_case == "idle":
                image_path = next((directory / "idle").glob("*_left.png"))
            else:
                image_path = next((directory / source_case).glob("*_left.png"))
            image = Image.open(image_path).convert("RGB")
            crop = image.crop((250, 90, 512, 120))
            crop = crop.resize(
                (panel_width * scale, panel_height * scale),
                Image.Resampling.NEAREST,
            )
            x = label_width + column * panel_width * scale
            y = row_index * panel_height * scale
            sheet.paste(crop, (x, y))
            draw.rectangle(
                (x, y, x + panel_width * scale - 1,
                 y + panel_height * scale - 1),
                outline=(70, 70, 70),
            )
    proof = ROOT / "vr/proof/weapon-moving-muzzle-controls.png"
    sheet.save(proof, optimize=True)
    return proof


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

    groups = marker_groups()
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
        MOHU_VR_WEAPON_CALIBRATED="1",
    )
    receipt = {
        "schema": 1,
        "kind": "W3.4 moving-muzzle and special-animation desktop controls",
        "complete": False,
        "headset_used": False,
        "fixture": "copied root MP slots 1-4, native pad, fresh load per ID",
        "executable_sha256": native.digest(executable),
        "sources": {
            name: native.digest(ROOT / name)
            for name in (
                "vr/underground/vr_diagnostic.c",
                "vr/underground/weapon.c",
                "vr/underground/weapon.h",
                "vr/tools/probe_weapon_animations.py",
                "vr/tools/probe_weapon_profiles.py",
                "vr/tools/check_weapon_meshes.py",
            )
        },
        "marker_inputs": {
            "P38 complete calibration":
                "vr/proof/weapon-p38-complete-calibration-receipt.json",
            "provisional calibrations":
                "vr/proof/weapon-provisional-calibrations-receipt.json",
        },
        "tolerances": {
            "grip_muzzle_distance_ratio": MARKER_DISTANCE_RATIO,
            "grip_muzzle_axis_degrees": MARKER_ANGLE_DEGREES,
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
            for slot, switches, weapon_id in first_occurrences(selected_ids):
                row = probe_weapon(
                    slot, switches, weapon_id, out, groups[weapon_id]
                )
                receipt["weapons"].append(row)
                save(out / "receipt.json", receipt)
                print(
                    f"animated ID {weapon_id:02} {row['name']}: "
                    f"{row['muzzle_marker_contract']}",
                    flush=True,
                )
            receipt["complete"] = True
            proof_image = write_sheet(out, receipt["weapons"])
            receipt["proof_image"] = str(proof_image.relative_to(ROOT))
            receipt["proof_image_sha256"] = native.digest(proof_image)
        except BaseException as error:
            receipt["error"] = str(error)
            save(out / "receipt.json", receipt)
            raise
        finally:
            try:
                command("openxr_hands_override", clear=1)
                command("mod_cmd", name="mohu.vr.stereo.pose", args="reset")
                command("mod_cmd", name="mohu.vr.weapon.pose", args="reset")
                command("set_input", buttons="0xffff")
                command("set_input", port=2, buttons="0xffff")
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
            save(out / "receipt.json", receipt)

    if not (
        receipt["complete"]
        and receipt["source_saves_unchanged"]
        and receipt["preferences_unchanged"]
        and not receipt["remaining_game_pids"]
        and receipt["exit_code"] == 0
    ):
        raise RuntimeError("W3.4 animation probe did not close cleanly")
    if args.proof:
        compact = dict(receipt)
        compact["weapons"] = [
            {
                key: row[key] for key in (
                    "id", "name", "slot", "switches", "baseline",
                    "states", "effects", "visuals", "summary",
                    "muzzle_marker_contract", "players_after",
                )
            }
            for row in receipt["weapons"]
        ]
        compact["limits"] = [
            "Desktop synthetic render controls, not physical acceptance.",
            "Native input drives recoil, reload, switch and prop animation.",
            "No NPC/SP shot isolation or all-weapon shot override is claimed.",
        ]
        save(args.proof, compact)
    print("PASS: moving-muzzle and special-animation controls completed")


if __name__ == "__main__":
    main()
