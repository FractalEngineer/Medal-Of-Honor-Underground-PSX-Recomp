"""W6.1 P38 per-eye rendered animated muzzle snapshots; no laser or XR runtime.

Reuses the owned combat runner, measured marker groups, synthetic pose helpers
and eye decoder. NumPy independently evaluates copied vertices/affines and the
W5 helper's same-snapshot world result. Bulk vertex data stays in the raw run.
"""
from __future__ import annotations

import argparse
from functools import partial
from pathlib import Path

import numpy as np

import probe_weapon_combat_states as combat
import check_weapon_pose_spaces as poses
from probe_weapon_animations import marker_groups

ROOT = combat.ROOT
POINT_TOLERANCE = 1e-8
Q16_STEP = 1.0 / 65536.0


def command(args):
    return combat.aim.mod_command("mohu.vr.muzzle", args)


def affine(words):
    rt, tr = poses.decode_control([f"{word:08X}" for word in words])
    return rt / 4096.0, tr.astype(float)


def verify_eye(row, hands, calibration=None):
    if not row["valid"] or not row["restored"] or row["id"] != 0 or \
            row["hash"] != 0x8544F8B9 or \
            row["input"] != row["owner"] + 0x400 or \
            row["object"] != row["input"] + 0x9F0 or row["href"] != 133:
        raise RuntimeError("Rendered muzzle ownership/source/restore guard failed")
    groups = marker_groups()[0]
    refs = groups["grip"] + groups["muzzle"] + [[11, i] for i in range(11, 18)]
    vertices = np.asarray(row["vertices"], dtype=float)
    if vertices.shape != (30, 8) or vertices[:, :2].tolist() != refs:
        raise RuntimeError("Rendered marker selection/count changed")
    xyz = vertices[:, 2:5]
    points = np.array([xyz[:18].mean(axis=0), xyz[18:23].mean(axis=0),
                       xyz[23:].mean(axis=0)])
    rt, tr = affine(row["control"])
    base = points @ rt.T + tr
    view_rt = np.asarray(row["view_rotation"]).reshape(3, 3)
    view_tr = np.asarray(row["view_translation"])
    eye = base @ view_rt.T + view_tr
    base_axis = base[1] - base[2]
    base_axis /= np.linalg.norm(base_axis)
    eye_axis = eye[1] - eye[2]
    eye_axis /= np.linalg.norm(eye_axis)
    errors = {}
    for name, expected in (("model_points", points), ("base_points", base),
                           ("eye_points", eye), ("base_axis", base_axis),
                           ("eye_axis", eye_axis)):
        actual = np.asarray(row[name]).reshape(expected.shape)
        error = float(np.max(np.abs(expected - actual)))
        if not np.isfinite(error) or error > POINT_TOLERANCE:
            raise RuntimeError(f"{name} differs from copied draw data: {error}")
        errors[name] = error
    # Independently predict the applied quantized calibrated affine from the
    # actual SDK-rounded hand sample. This checks attachment before eye pose.
    calibration = calibration or combat.aim.calibrations()[0]
    hand_rt, hand_tr = poses.hand_transform(hands)
    basis = np.array([calibration["right"], -np.array(calibration["up"]),
                      calibration["forward"]])
    expected_rt = np.rint(hand_rt @ basis * poses.HAND_UNITS_PER_METRE /
                          calibration["model_units_per_metre"] * 4096)
    expected_tr = np.rint(hand_tr - expected_rt / 4096.0 @
                          np.asarray(calibration["grip_pivot"]))
    actual_rt, actual_tr = poses.decode_control(
        [f"{word:08X}" for word in row["control"]])
    if np.max(np.abs(actual_rt - expected_rt)) > 1 or \
            np.max(np.abs(actual_tr - expected_tr)) > 1:
        raise RuntimeError("Applied control disagrees with independent hand pose")
    camera_rt, camera_tr = affine(row["camera"])
    inverse = np.linalg.inv(camera_rt)
    ray_origin, ray_axis = base[1], base_axis
    if row.get("hand_fixed"):
        ray_origin = rt @ np.asarray(calibration["muzzle"]) + tr
        ray_axis = rt @ np.asarray(calibration["forward"])
        ray_axis /= np.linalg.norm(ray_axis)
        eye_origin = view_rt @ ray_origin + view_tr
        eye_ray = view_rt @ ray_axis
        eye_ray /= np.linalg.norm(eye_ray)
        for name, expected in (("aim_base", ray_origin), ("aim_axis", ray_axis),
                               ("aim_eye", eye_origin), ("aim_eye_axis", eye_ray)):
            error = float(np.max(np.abs(np.asarray(row[name]) - expected)))
            if not np.isfinite(error) or error > POINT_TOLERANCE:
                raise RuntimeError(f"Hand-fixed {name} disagrees with calibration")
            errors[name] = error
    world_tip = inverse @ (ray_origin - camera_tr)
    world_axis = inverse @ ray_axis
    world_axis /= np.linalg.norm(world_axis)
    error = float(np.max(np.abs(world_tip -
                                np.asarray(row["w5_position"]) / 65536.0)))
    if not np.isfinite(error) or error > Q16_STEP:
        raise RuntimeError("W5 helper differs on the same captured animation")
    angles = np.asarray(row["w5_angles"], dtype=float) / 65536.0
    pitch = np.arctan2(-world_axis[1], np.hypot(world_axis[0], world_axis[2]))
    yaw = np.arctan2(world_axis[0], world_axis[2]) % (2 * np.pi)
    expected_angles = np.array([pitch, yaw, 0]) * 4096 / (2 * np.pi)
    if np.max(np.abs(expected_angles - angles)) > Q16_STEP:
        raise RuntimeError("W5 native angles disagree with the rendered axis")
    if row["canonical_equal"] and not np.array_equal(xyz, vertices[:, 5:8]):
        raise RuntimeError("False canonical/draw epoch equality")
    errors["w5_world_tip"] = error
    row["errors"] = errors
    return row


def capture_pair(refresh):
    refresh()
    before = command("capture")
    for _ in range(24):
        hands = refresh()
        status = command("status")
        if status["valid"] and not status["requested"]:
            break
        combat.native.frames(1)
    else:
        raise RuntimeError(f"No complete restored muzzle pair: {status}")
    eyes = []
    for eye in (0, 1):
        refresh()
        row = command(f"read={eye}")
        if row["sequence"] != status["sequence"] or \
                row["sequence"] <= before["sequence"] or row["eye"] != eye:
            raise RuntimeError("Captured muzzle pair changed identity")
        for part in range(4):
            refresh()
            data = command(f"data={eye}:{part}")
            if data["sequence"] != row["sequence"] or data["eye"] != eye:
                raise RuntimeError("Snapshot changed across data pages")
            row.update(data)
        vertices = []
        for start in range(0, row["vertex_count"], 4):
            refresh()
            page = command(f"vertices={eye}:{start}")
            if page["sequence"] != row["sequence"] or page["start"] != start:
                raise RuntimeError("Snapshot changed across vertex pages")
            vertices += page["vertices"]
        row["vertices"] = vertices
        row["hands"] = hands
        eyes.append(verify_eye(row, hands))
    if eyes[0]["attempt"] != eyes[1]["attempt"] or \
            eyes[0]["generation"] != eyes[1]["generation"] or \
            eyes[0]["vertices"] != eyes[1]["vertices"] or \
            eyes[0]["control"] != eyes[1]["control"]:
        raise RuntimeError("Eyes were captured from different model/pose states")
    return {"sequence": status["sequence"], "eyes": eyes}


def exercise(mode, *, directory, pilot):
    combat.families.prepare_weapon(1, 0)
    combat.marker("start")
    combat.aim.shot_command("start-p1")
    poses.set_head()
    refresh = lambda: poses.set_hand_pair(grip=(0.15, 0.0, -0.5))
    refresh()
    combat.native.frames(12)
    cases = []
    controls = []
    intentional_refusals = 0
    try:
        for name, head, grip, rotation in (
            ("baseline", {}, (0.15, 0.0, -0.5), (0, 0, 0, 1)),
            ("head-yaw", {"yaw_mdeg": 15000}, (0.15, 0.0, -0.5), (0, 0, 0, 1)),
            ("head-translation", {"x_milli": 100000}, (0.15, 0.0, -0.5), (0, 0, 0, 1)),
            ("hand-translation", {}, (0.25, 0.0, -0.5), (0, 0, 0, 1)),
            ("hand-yaw", {}, (0.15, 0.0, -0.5), poses.quat_axis(1, 15)),
        ):
            head_request = poses.set_head(**head)
            refresh = lambda g=grip, q=rotation: poses.set_hand_pair(
                grip=g, grip_q=q, aim_q=q)
            pair = capture_pair(refresh)
            pair.update(name=name, head=head_request)
            for eye in pair["eyes"]:
                request = dict(head_request)
                request["x_milli"] += (-24000 if eye["eye"] == 0 else 24000)
                expected_rt, expected_tr = poses.expected_view(request)
                rotation_error = float(np.max(np.abs(
                    np.asarray(eye["view_rotation"]).reshape(3, 3) - expected_rt)))
                translation_error = float(np.max(np.abs(
                    np.asarray(eye["view_translation"]) - expected_tr)))
                if rotation_error > 1e-6 or translation_error > 1e-6:
                    raise RuntimeError("Captured eye view disagrees with supplied head")
                eye["errors"].update(head_rotation=rotation_error,
                                     head_translation=translation_error)
            cases.append(pair)
            combat.save(directory / f"case-{name}.json", pair)
            print(f"muzzle {name}: pair {pair['eyes'][0]['attempt']}", flush=True)
            if pilot:
                break
        if not pilot:
            for case in cases[1:3]:
                if case["eyes"][0]["control"] != cases[0]["eyes"][0]["control"]:
                    raise RuntimeError("Head-only pose changed model placement")
            poses.set_head()
            refresh = lambda: poses.set_hand_pair(grip=(0.15, 0.0, -0.5))
            refresh()
            before = combat.player_key(combat.native.players())
            combat.native.command("openxr_input_override", right_trigger=1000)
            combat.native.frames(8)
            combat.native.command("openxr_input_override", clear=1)
            recoil = capture_pair(refresh)
            recoil["name"] = "recoil"
            cases.append(recoil)
            after_fire = combat.player_key(combat.native.players())
            if before["clip"] - after_fire["clip"] != 1:
                raise RuntimeError("Recoil capture did not consume a native round")
            combat.save(directory / "case-recoil.json", recoil)
            combat.native.frames(30)
            combat.set_button(combat.RELOAD, frames=8)
            combat.native.frames(8)
            reload = capture_pair(refresh)
            reload["name"] = "reload"
            cases.append(reload)
            combat.save(directory / "case-reload.json", reload)
            combat.native.frames(120)
            after_reload = combat.player_key(combat.native.players())
            if after_reload["clip"] <= after_fire["clip"] or \
                    after_reload["reserve"] >= after_fire["reserve"]:
                raise RuntimeError("Reload capture has no native ammo transfer")
            controls.append({"name": "native-animation-effects", "before": before,
                             "after_fire": after_fire, "after_reload": after_reload})
            baseline_points = np.asarray(cases[0]["eyes"][0]["model_points"])
            if not any(np.max(np.abs(np.asarray(case["eyes"][0]["model_points"]) -
                                     baseline_points)) > 0
                       for case in (recoil, reload)):
                raise RuntimeError("Neither native action changed animated markers")
            for case in (recoil, reload):
                for eye, baseline in zip(case["eyes"], cases[0]["eyes"]):
                    if not eye.get("hand_fixed") or any(
                        np.max(np.abs(np.asarray(eye[key]) - baseline[key])) >
                        POINT_TOLERANCE for key in ("aim_base", "aim_axis")):
                        raise RuntimeError("Native gun animation moved the hand-fixed aim ray")
            poses.set_hand_pair(grip=(0.15, 0.0, -0.5), focused=0)
            combat.native.frames(8)
            invalid = command("status")
            if invalid["valid"]:
                raise RuntimeError("Unfocused hand retained a valid muzzle snapshot")
            controls.append({"name": "unfocused", **invalid})
            recovered = capture_pair(refresh)
            recovered["name"] = "tracking-recovery"
            cases.append(recovered)
            combat.set_button(combat.SWITCH, frames=8)
            combat.native.frames(90)
            changed_weapon = command("status")
            changed_player = combat.native.players()[0]
            if changed_player["weapon_id"] != 1 or changed_weapon["valid"]:
                raise RuntimeError("Weapon change reused the P38 snapshot")
            controls.append({"name": "weapon-change", "player": changed_player,
                             **changed_weapon})
            before_load = command("status")
            combat.native.load(1)
            combat.comparison.release_load_override()
            after_load = command("status")
            if after_load["valid"] or \
                    after_load["generation"] <= before_load["generation"]:
                raise RuntimeError("Load reused a rendered muzzle snapshot")
            controls.append({"name": "load", "before": before_load, "after": after_load})
            refreshed = capture_pair(refresh)
            refreshed["name"] = "load-recovery"
            cases.append(refreshed)
            before_refusal = combat.native.command("stereo_stats")
            before_snapshot = command("status")
            try:
                combat.native.command("render_pass_refuse", on=1)
                refresh()
                combat.native.frames(12)
                refused = combat.native.command("stereo_stats")
                refused_snapshot = command("status")
                if refused_snapshot["stored_valid"] or \
                        refused_snapshot["sequence"] != before_snapshot["sequence"]:
                    raise RuntimeError("Refused eye pair retained/published a muzzle snapshot")
                try:
                    command("read=0")
                except RuntimeError:
                    read_rejected = True
                else:
                    raise RuntimeError("Refused snapshot remained readable")
            finally:
                combat.native.command("render_pass_refuse", on=0)
            intentional_refusals = refused["refused"] - before_refusal["refused"]
            if intentional_refusals <= 0:
                raise RuntimeError("Refusal control exercised no admission refusal")
            recovery = capture_pair(refresh)
            recovery["name"] = "refusal-recovery"
            cases.append(recovery)
            recovered_stats = combat.native.command("stereo_stats")
            if recovered_stats["last_pair_id"] <= refused["last_failed_attempt"] or \
                    recovery["eyes"][0]["attempt"] <= refreshed["eyes"][0]["attempt"]:
                raise RuntimeError("Refusal recovery has no newer complete pair")
            controls.append({"name": "refused-pair", "before": before_snapshot,
                             "refused": refused_snapshot, "read_rejected": read_rejected,
                             "refusals": intentional_refusals,
                             "stereo_refused": refused, "stereo_recovered": recovered_stats})
        stereo = combat.native.command("stereo_stats")
        render = combat.native.command("render_pass_stats")
        if not stereo["pairs"] or not render["verify_checks"] or \
                stereo["failed"] or render["verify_mismatch"] or render["vram_leaks"]:
            raise RuntimeError("Rendered muzzle stereo/rollback gate failed")
        native_shots = combat.shot_rows()
        if not pilot and (len(native_shots) != 1 or not native_shots[0]["aimed"] or
                          not native_shots[0].get("hand_fixed") or
                          native_shots[0]["aimed_position"] != cases[0]["eyes"][0]["w5_position"] or
                          native_shots[0]["aimed_angles"] != cases[0]["eyes"][0]["w5_angles"]):
            raise RuntimeError("Native shot disagrees with the shared hand-fixed ray")
        return {"name": "rendered-muzzle", "shot_count": len(native_shots),
                "intentional_refusals": intentional_refusals,
                "native_shots": native_shots, "linked_damage": [],
                "cases": cases, "controls": controls, "pilot": pilot,
                "stereo": stereo, "render_pass": render}
    finally:
        command("stop")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    if args.pilot and args.proof:
        parser.error("A pilot cannot publish the W6.1 proof")
    out = args.directory.resolve()
    sources = ("vr/underground/rendered_muzzle.h", "vr/underground/rendered_muzzle.inc",
               "vr/tools/probe_rendered_muzzle.py")
    receipt = combat.run_mode(
        "tracked", out, ["rendered-muzzle"], extra_sources=sources,
        case_functions={"rendered-muzzle": partial(exercise, directory=out, pilot=args.pilot)},
        environment_overrides={"MOHU_VR_MP_CONTROL": "1", "MOHU_VR_WEAPON_GUN_ONLY": "1",
                               "MOHU_VR_EYE_OFFSET": "24", "PSX_STEREO_SHED": "0",
                               "PSX_VSYNC": "0"},
    )
    proof = {**receipt, "kind": "W6.1 hand-fixed aim ray and per-eye model diagnostics",
             "raw_receipt": str((out / "receipt.json").relative_to(ROOT)),
             "raw_receipt_sha256": combat.digest(out / "receipt.json"),
             "limits": ["P38 copied MP slot 1; provisional physical calibration.",
                        "Shot and future laser use the same fixed calibration/hand affine; animated markers are diagnostic.",
                        "Canonical natural samples may be a different animation epoch; equality is explicit.",
                        "No laser, triangle hit, headset or physical alignment acceptance."]}
    if args.proof:
        combat.save(args.proof, proof)
    print("PASS: rendered animated muzzle capture" + (" pilot" if args.pilot else ""), flush=True)


if __name__ == "__main__":
    main()
