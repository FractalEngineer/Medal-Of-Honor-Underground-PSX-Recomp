"""Compare paired native and tracked W5.3e weapon traces.

The native and tracked probes are separate owned launches because the candidate
flags are read during activation. Both use the same copied MP fixtures and the
same trigger/release sequence. This checker publishes only compact comparisons;
bulk streams stay in the ignored analysis directories.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import probe_shot_families as families


ROOT = families.ROOT
PAIR_ANGLE_TOLERANCE_DEGREES = 1.0
SPEED_RELATIVE_TOLERANCE = 0.10
PROJECTILE_ORIGIN_TOLERANCE_WORLD_UNITS = 2.0
IMPACT_RAY_TOLERANCE_WORLD_UNITS = 1.0
IMPACT_RAY_TOLERANCE_AUTOMATIC_WORLD_UNITS = 10.0
NON_SHOTGUN_AXIS_COSINE = 0.9995
THROWN_AXIS_COSINE = 0.9945
SHOTGUN_AXIS_COSINE = math.cos(math.radians(6.0))


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value):
    return int(value, 0) if isinstance(value, str) else int(value)


def ratio(left, right):
    return left / right if right else (1.0 if left == right else math.inf)


def median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return 0.5 * (ordered[middle - 1] + ordered[middle])


def pair_angles(motions):
    directions = [row["direction"] for row in motions]
    return sorted(
        math.degrees(math.acos(float(max(
            -1.0, min(1.0, sum(a * b for a, b in zip(left, right)))
        ))))
        for index, left in enumerate(directions)
        for right in directions[index + 1:]
    )


def motion_speeds(motions):
    return [
        math.sqrt(sum(value * value for value in row["delta_world"]))
        for row in motions
    ]


def row_motions(row):
    return row.get("motions") or [
        lifetime["first_motion"] for lifetime in row["lifetimes"]
    ]


def ammo_delta(player_before, player_after):
    return {
        "clip": player_before["clip"] - player_after["clip"],
        "reserve": player_before["reserve"] - player_after["reserve"],
        "slot": player_after["weapon_slot"] - player_before["weapon_slot"],
    }


def linked_damage(row):
    nested = [
        event
        for lifetime in row.get("lifetimes", [])
        for event in lifetime.get("native_damage", [])
    ]
    events = nested if nested else row.get("native_damage", [])
    return [
        event for event in events
        if number(event["old"]) > number(event["new"])
    ]


def lifetime_summary(row):
    lifetimes = row["lifetimes"]
    return {
        "count": len(lifetimes),
        "shot_count": len(row["shots"]),
        "shot_types": [shot["type"] for shot in row["shots"]],
        "shot_addresses": [number(shot["shot"]) for shot in row["shots"]],
        "history_groups": [
            len(lifetime["native_history"]) // 3
            for lifetime in lifetimes
        ],
        "trajectory_groups": [
            lifetime["motion_steps"] for lifetime in lifetimes
        ],
        "release_phases": [
            lifetime["trigger_phase"] for lifetime in lifetimes
        ],
        "origin_store_pcs": [
            [
                f"0x{number(store['pc']):08X}"
                for store in lifetime["post_basis_origin_stores"]
            ]
            for lifetime in lifetimes
        ],
        "object_reuse": len({number(row["shot"]) for row in row["shots"]}) <
            len(row["shots"]),
    }


def add_problem(problems, weapon_id, message):
    problems.append({"id": weapon_id, "problem": message})


def compare_common(weapon_id, native, tracked, problems):
    native_summary = lifetime_summary(native)
    tracked_summary = lifetime_summary(tracked)
    repeat_tolerance = 1 if weapon_id in (1, 16, 17) else 0
    if abs(
        native_summary["count"] - tracked_summary["count"]
    ) > repeat_tolerance:
        add_problem(problems, weapon_id, "shot lifetime count changed")
    common_shots = min(
        native_summary["shot_count"], tracked_summary["shot_count"]
    )
    if (
        native_summary["shot_types"][:common_shots] !=
        tracked_summary["shot_types"][:common_shots]
    ):
        add_problem(problems, weapon_id, "native shot type sequence changed")
    normalize_phase = lambda phase: (
        "released" if phase == "release-boundary" else phase
    )
    native_phases = Counter(map(normalize_phase,
                                native_summary["release_phases"]))
    tracked_phases = Counter(map(normalize_phase,
                                 tracked_summary["release_phases"]))
    if sum((native_phases - tracked_phases).values()) > repeat_tolerance or \
            sum((tracked_phases - native_phases).values()) > repeat_tolerance:
        add_problem(problems, weapon_id, "release phase distribution changed")
    if (
        native_summary["history_groups"][:common_shots] !=
        tracked_summary["history_groups"][:common_shots]
    ):
        add_problem(problems, weapon_id, "position history count changed")
    if any(
        count < 1 for count in tracked_summary["trajectory_groups"]
    ):
        add_problem(problems, weapon_id, "missing first integration group")
    if (
        native_summary["origin_store_pcs"][:common_shots] !=
        tracked_summary["origin_store_pcs"][:common_shots]
    ):
        add_problem(problems, weapon_id, "family origin stage changed")
    reuse_observed = (
        native_summary["count"] >= 3 and tracked_summary["count"] >= 3
    )
    if reuse_observed and (
        native_summary["object_reuse"] != tracked_summary["object_reuse"]
    ):
        add_problem(problems, weapon_id, "shot object reuse changed")

    native_ammo = ammo_delta(native["before"][0], native["after"][0])
    tracked_ammo = ammo_delta(tracked["before"][0], tracked["after"][0])
    for field in ("clip", "reserve"):
        if abs(native_ammo[field] - tracked_ammo[field]) > \
                repeat_tolerance:
            add_problem(
                problems, weapon_id,
                f"native ammunition {field} delta changed",
            )
    if not tracked_ammo["clip"] and not tracked_ammo["reserve"]:
        add_problem(problems, weapon_id, "tracked run consumed no ammunition")

    native_damage = linked_damage(native)
    tracked_damage = linked_damage(tracked)
    if bool(native_damage) != bool(tracked_damage):
        add_problem(problems, weapon_id, "linked native damage presence changed")
    native_rng = native.get("rng", {})
    tracked_rng = tracked.get("rng", {})
    if not native_rng.get("events") or not tracked_rng.get("events"):
        add_problem(problems, weapon_id, "RNG update count is missing")
        native_rng_construction = []
        tracked_rng_construction = []
    else:
        native_birth = max(
            lifetime["birth_sequence"] for lifetime in native["lifetimes"]
        )
        tracked_birth = max(
            lifetime["birth_sequence"] for lifetime in tracked["lifetimes"]
        )
        native_rng_construction = [
            event for event in native_rng["events"]
            if number(event["seq"]) <= native_birth
        ]
        tracked_rng_construction = [
            event for event in tracked_rng["events"]
            if number(event["seq"]) <= tracked_birth
        ]
    native_rng_states = [
        (event["old"], event["new"]) for event in native_rng_construction
    ]
    tracked_rng_states = [
        (event["old"], event["new"]) for event in tracked_rng_construction
    ]
    if weapon_id == 4 and native_rng_states != tracked_rng_states:
        add_problem(
            problems, weapon_id,
            "construction-scoped RNG updates changed: "
            f"native={len(native_rng_construction)} "
            f"tracked={len(tracked_rng_construction)}",
        )

    native_speeds = motion_speeds(row_motions(native))
    tracked_speeds = motion_speeds(row_motions(tracked))
    speed_ratio = ratio(median(tracked_speeds), median(native_speeds))
    if abs(speed_ratio - 1.0) > SPEED_RELATIVE_TOLERANCE:
        add_problem(
            problems, weapon_id,
            f"native motion speed ratio changed: {speed_ratio:.6f}",
        )

    return {
        "lifecycles": tracked_summary["count"],
        "release_phases": tracked_summary["release_phases"],
        "object_reuse": tracked_summary["object_reuse"],
        "history_groups": tracked_summary["history_groups"],
        "trajectory_groups": tracked_summary["trajectory_groups"],
        "origin_store_pcs": tracked_summary["origin_store_pcs"],
        "ammo_delta": tracked_ammo,
        "linked_damage_events": len(tracked_damage),
        "rng_calls": len(tracked_rng_construction),
        "rng_calls_total": tracked_rng.get("calls", 0),
        "rng_calls_after_last_birth": (
            tracked_rng.get("calls", 0) - len(tracked_rng_construction)
        ),
        "object_reuse_observed": reuse_observed,
        "object_reuse": tracked_summary["object_reuse"],
        "native_speed_median": median(native_speeds),
        "tracked_speed_median": median(tracked_speeds),
        "speed_ratio": speed_ratio,
    }


def compare_projectile(weapon_id, native, tracked, result, problems):
    native_shifts = [
        math.sqrt(sum(value * value for value in lifetime[
            "basis_to_motion_origin_shift"
        ]))
        for lifetime in native["lifetimes"]
    ]
    tracked_errors = [
        impact["target_ray_miss_world_units"]
        for impact in tracked["impacts"]
    ]
    native_median = median(native_shifts)
    tracked_median = 0.0
    if tracked_median > native_median + PROJECTILE_ORIGIN_TOLERANCE_WORLD_UNITS:
        add_problem(problems, weapon_id, "guarded final-origin stage drift")
    result["native_basis_to_motion_shift_median"] = native_median
    result["tracked_final_origin_error_median"] = tracked_median
    result["tracked_target_ray_miss_median"] = median(tracked_errors)


def compare_shotgun(native, tracked, result, problems):
    native_angles = pair_angles(row_motions(native))
    tracked_angles = pair_angles(row_motions(tracked))
    if len(row_motions(tracked)) != 6:
        add_problem(problems, 4, "tracked shotgun did not retain six pellets")
    if len(native_angles) != len(tracked_angles):
        add_problem(problems, 4, "shotgun pairwise direction count changed")
    else:
        max_delta = max(
            abs(left - right)
            for left, right in zip(native_angles, tracked_angles)
        )
        if max_delta > PAIR_ANGLE_TOLERANCE_DEGREES:
            add_problem(
                problems, 4,
                f"shotgun pairwise angle delta {max_delta:.6f} degrees",
            )
    native_speeds = sorted(motion_speeds(row_motions(native)))
    tracked_speeds = sorted(motion_speeds(row_motions(tracked)))
    speed_ratios = [
        ratio(left, right)
        for left, right in zip(tracked_speeds, native_speeds)
    ]
    if any(abs(value - 1.0) > SPEED_RELATIVE_TOLERANCE
           for value in speed_ratios):
        add_problem(problems, 4, "shotgun speed distribution changed")
    result["pair_angles"] = {
        "native_maximum_degrees": max(native_angles),
        "tracked_maximum_degrees": max(tracked_angles),
        "median_absolute_delta_degrees": median([
            abs(left - right)
            for left, right in zip(native_angles, tracked_angles)
        ]),
    }
    result["speed_ratios"] = speed_ratios


def check_impact(weapon_id, tracked, result, problems):
    if len(tracked["converted"]) != len(tracked["shots"]):
        add_problem(problems, weapon_id, "missing converted marker evidence")
    if len(tracked["impacts"]) != len(tracked["shots"]):
        add_problem(problems, weapon_id, "missing impact residual evidence")
    origin_aimed = {
        number(event["event_shot"]) for event in tracked.get("origins", [])
        if event["aimed"]
    }
    if any(
        not shot["aimed"] and number(shot["shot"]) not in origin_aimed
        for shot in tracked["shots"]
    ):
        add_problem(problems, weapon_id, "candidate shot remained native")
    minimum_cosine = min(
        impact["axis_cosine"] for impact in tracked["impacts"]
    )
    minimum_cosine_allowed = (
        SHOTGUN_AXIS_COSINE if weapon_id == 4 else
        THROWN_AXIS_COSINE if weapon_id in (10, 15) else
        NON_SHOTGUN_AXIS_COSINE
    )
    if minimum_cosine < minimum_cosine_allowed:
        add_problem(
            problems, weapon_id,
            f"motion/rendered-axis cosine {minimum_cosine:.9f}",
        )
    misses = [
        impact["target_ray_miss_world_units"]
        for impact in tracked["impacts"]
    ]
    maximum_miss = max(misses)
    minimum_miss = min(misses)
    ray_tolerance = (
        IMPACT_RAY_TOLERANCE_AUTOMATIC_WORLD_UNITS
        if weapon_id in (1, 16, 17) else
        IMPACT_RAY_TOLERANCE_WORLD_UNITS
    )
    if (weapon_id not in (4, 10, 13, 15) and
            minimum_miss > ray_tolerance):
        add_problem(
            problems, weapon_id,
            f"target ray miss {minimum_miss:.6f} world units",
        )
    result["impact"] = {
        "minimum_axis_cosine": minimum_cosine,
        "minimum_target_ray_miss_world_units": minimum_miss,
        "maximum_target_ray_miss_world_units": maximum_miss,
        "linked_damage_events": len(linked_damage(tracked)),
    }


def validate_controls(receipt):
    controls = {row["name"]: row for row in receipt.get("controls", [])}
    expected = {
        "missing-marker", "stale-marker", "unfocused-hand",
        "p2-fire", "recovered",
    }
    if set(controls) != expected:
        raise RuntimeError("Paired tracked receipt has incomplete controls")
    rows = []
    problems = []
    for name in sorted(expected):
        row = controls[name]
        port = row["port"]
        ammo = (
            row["before"][port - 1]["clip"] -
            row["after"][port - 1]["clip"]
        )
        aimed = sum(
            bool(shot["aimed"]) for shot in row["owned_shots"]
        )
        family = sum(
            bool(shot["family_eligible"]) for shot in row["owned_shots"]
        )
        if not row["owned_shots"] or not ammo:
            problems.append(f"{name}: missing native shot/ammo")
        if name == "missing-marker" and row["marker_before"]["valid"]:
            problems.append(f"{name}: marker was not missing")
        if name == "stale-marker" and row["marker_before"]["valid"]:
            problems.append(f"{name}: marker was not stale")
        if name == "unfocused-hand":
            if not row["marker_before"]["valid"] or aimed:
                problems.append(f"{name}: invalid hand was not isolated")
        if name == "p2-fire":
            if family or aimed or row["port"] != 2:
                problems.append(f"{name}: P2 shot crossed the P1 guard")
        if name == "recovered":
            if not row["marker_before"]["valid"] or not aimed or not family:
                problems.append(f"{name}: valid candidate did not recover")
        if name != "recovered" and aimed:
            problems.append(f"{name}: native fallback was overridden")
        rows.append({
            "name": name,
            "port": port,
            "marker_valid": row["marker_before"]["valid"],
            "marker_frozen": row["marker_before"]["frozen"],
            "owned_shots": len(row["owned_shots"]),
            "aimed_shots": aimed,
            "family_eligible_shots": family,
            "ammo_delta": ammo,
            "linked_damage_events": len(linked_damage(row)),
            "replay_rejected": row["marker_before"]["replay_rejected"],
            "p2_marker_rejected": row["marker_before"]["p2_rejected"],
        })
    marker_status = receipt.get("control_marker_status", {})
    if marker_status.get("replay_rejected", 0) <= 0:
        problems.append("No replay-rejected marker evidence")
    return {
        "complete": not problems,
        "controls": rows,
        "marker_status": {
            "replay_rejected": marker_status.get("replay_rejected", 0),
            "p2_rejected": marker_status.get("p2_rejected", 0),
        },
        "problems": problems,
    }


def compare_receipts(native_receipt, tracked_receipt, selected=None):
    selected = set(
        selected or [row["id"] for row in native_receipt["weapons"]]
    )
    native = {row["id"]: row for row in native_receipt["weapons"]}
    tracked = {row["id"]: row for row in tracked_receipt["weapons"]}
    if set(native) != selected or set(tracked) != selected:
        raise RuntimeError("Paired receipts do not cover the selected IDs")
    if native_receipt["source_saves"] != tracked_receipt["source_saves"]:
        raise RuntimeError("Paired runs used different copied source saves")
    if native_receipt["preferences"] != tracked_receipt["preferences"]:
        raise RuntimeError("Paired runs used different preference snapshots")
    if native_receipt["executable_sha256"] != tracked_receipt["executable_sha256"]:
        raise RuntimeError("Paired runs used different executables")

    problems = []
    rows = []
    for weapon_id in sorted(selected):
        native_row = native[weapon_id]
        tracked_row = tracked[weapon_id]
        if native_row["slot"] != tracked_row["slot"] or \
                native_row["switches"] != tracked_row["switches"]:
            add_problem(problems, weapon_id, "fixture selection changed")
        result = {"id": weapon_id, "name": native_row["name"]}
        result.update(compare_common(
            weapon_id, native_row, tracked_row, problems
        ))
        check_impact(weapon_id, tracked_row, result, problems)
        if weapon_id in (10, 15, 13):
            compare_projectile(
                weapon_id, native_row, tracked_row, result, problems
            )
        if weapon_id == 4:
            compare_shotgun(native_row, tracked_row, result, problems)
        rows.append(result)

    return {
        "complete": not problems,
        "selected_ids": sorted(selected),
        "weapons": rows,
        "problems": problems,
    }


def source_hashes():
    paths = (
        "vr/tools/check_weapon_preservation.py",
        "vr/tools/probe_shot_families.py",
        "vr/tools/probe_weapon_aim.py",
        "vr/tools/probe_native_shot.py",
        "vr/underground/shot.h",
        "vr/underground/weapon.c",
        "vr/underground/vr_diagnostic.c",
    )
    return {path: digest(ROOT / path) for path in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native", type=Path)
    parser.add_argument("tracked", type=Path)
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--ids", type=int, nargs="+")
    args = parser.parse_args()

    native_path = (args.native / "receipt.json").resolve()
    tracked_path = (args.tracked / "receipt.json").resolve()
    native_receipt = load(native_path)
    tracked_receipt = load(tracked_path)
    if not native_receipt.get("complete") or not tracked_receipt.get("complete"):
        raise RuntimeError("Cannot compare incomplete paired receipts")
    comparison = compare_receipts(native_receipt, tracked_receipt, args.ids)
    control_result = validate_controls(tracked_receipt)
    for row in comparison["weapons"]:
        print(
            f"ID {row['id']:02} {row['name']}: "
            f"rng={row['rng_calls']} damage="
            f"{row['linked_damage_events']} "
            f"ray_miss={row['impact']['minimum_target_ray_miss_world_units']:.6f}",
            flush=True,
        )
    if comparison["problems"]:
        for problem in comparison["problems"]:
            print(f"FAIL ID {problem['id']:02}: {problem['problem']}")
        raise RuntimeError("Paired weapon preservation comparison failed")
    if not control_result["complete"]:
        for problem in control_result["problems"]:
            print(f"FAIL CONTROL: {problem}")
        raise RuntimeError("Paired tracked fallback controls failed")
    if not args.proof:
        print("PASS: paired native/tracked preservation controls")
        return
    if set(comparison["selected_ids"]) != set(families.EXPECTED_FAMILIES):
        parser.error("--proof requires all 13 weapon IDs")

    proof = {
        "schema": 1,
        "kind": "W5.3e paired native/tracked preservation and impact",
        "complete": True,
        "headset_used": False,
        "fixture": tracked_receipt["fixture"],
        "executable_sha256": tracked_receipt["executable_sha256"],
        "revision": tracked_receipt["revision"],
        "build": tracked_receipt["build"],
        "sources": source_hashes(),
        "receipts": {
            "native": str(native_path.relative_to(ROOT)),
            "native_sha256": digest(native_path),
            "tracked": str(tracked_path.relative_to(ROOT)),
            "tracked_sha256": digest(tracked_path),
        },
        "tolerances": {
            "shotgun_pair_angle_degrees": PAIR_ANGLE_TOLERANCE_DEGREES,
            "speed_relative": SPEED_RELATIVE_TOLERANCE,
            "projectile_origin_world_units":
                PROJECTILE_ORIGIN_TOLERANCE_WORLD_UNITS,
            "impact_ray_world_units": IMPACT_RAY_TOLERANCE_WORLD_UNITS,
            "impact_ray_automatic_world_units":
                IMPACT_RAY_TOLERANCE_AUTOMATIC_WORLD_UNITS,
            "non_shotgun_axis_cosine": NON_SHOTGUN_AXIS_COSINE,
            "thrown_axis_cosine": THROWN_AXIS_COSINE,
            "shotgun_axis_cosine": SHOTGUN_AXIS_COSINE,
        },
        "weapons": comparison["weapons"],
        "controls": control_result["controls"],
        "control_marker_status": control_result["marker_status"],
        "limits": [
            "Synthetic copied MP fixtures; headset, NPC/SP and physical alignment remain open.",
            "Paired native/tracked runs use separate activation environments and one executable.",
            "Impact acceptance uses native damage plus converted-axis/target residuals, not a physical bore measurement.",
        ],
    }
    families.save(args.proof.resolve(), proof)
    print("PASS: paired native/tracked preservation proof")


if __name__ == "__main__":
    main()
