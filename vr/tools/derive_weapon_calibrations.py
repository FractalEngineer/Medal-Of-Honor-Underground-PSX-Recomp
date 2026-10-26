"""Derive provisional complete-gun calibration from captured animated vertices.

P38 retains its accepted complete-gun values exactly. Other profiles use a
repeatable geometry rule: mean of the closest 20% of gun vertices to the arm
island for the grip, the selected-geometry principal axis for forward, and the
mean of the five most-forward vertices for the muzzle. Nominal lengths are
display references only; physical acceptance remains open.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import check_weapon_meshes as topology


NOMINAL_LENGTHS_M = {
    0: 0.216,
    1: 0.833,
    4: 1.000,
    5: 1.110,
    8: 0.216,
    9: 0.300,
    10: 0.365,
    12: 1.107,
    13: 1.000,
    14: 0.800,
    15: 0.300,
    16: 0.762,
    17: 0.940,
}

P38 = {
    "grip_pivot": [76.555555555556, 100.777777777778, 287.888888888889],
    "muzzle": [81.8, 110.6, 447.6],
    "barrel_axis_base": [80.0, 109.428571428571, 367.857142857143],
    "right": [0.999745337201, 0.0, -0.022566806250],
    "up": [0.000331387923, -0.999892173236, 0.014681010987],
    "forward": [0.022564372944, 0.014684750646, 0.999637537897],
    "forward_span_units": 164.265769717169,
    "reference_length_m": 0.216,
    "model_units_per_metre": 760.489674616524,
}


def normalized(vector):
    length = float(np.linalg.norm(vector))
    if not np.isfinite(length) or length < 1e-9:
        raise ValueError("Degenerate calibration vector")
    return np.asarray(vector, dtype=np.float64) / length


def orthonormal_frame(forward):
    forward = normalized(forward)
    down_source = np.array([0.0, 1.0, 0.0])
    if abs(float(np.dot(down_source, forward))) > 0.9:
        down_source = np.array([0.0, 0.0, 1.0])
    down = down_source - np.dot(down_source, forward) * forward
    down = normalized(down)
    right = normalized(np.cross(down, forward))
    up = -down
    return right, up, forward


def derive(capture):
    weapon_id = capture["id"]
    profile = topology.PROFILES[weapon_id]
    selected = []
    arm = []
    selected_markers = []
    for node_text, row in capture["nodes"].items():
        node = int(node_text)
        points = np.asarray(row["animated"], dtype=np.float64)[:, :3]
        for index, point in enumerate(points):
            marker = (node, index)
            if topology.selected(profile, node, index):
                selected.append(point)
                selected_markers.append(marker)
            else:
                arm.append(point)
    selected = np.asarray(selected)
    arm_centroid = np.asarray(arm).mean(axis=0)

    if weapon_id == 0:
        calibration = dict(P38)
        calibration["provisional"] = True
        calibration["rule"] = "accepted complete-gun P38 receipt"
        return calibration

    centered = selected - selected.mean(axis=0)
    eigenvalues, eigenvectors = np.linalg.eigh(
        np.cov(centered, rowvar=False)
    )
    forward = normalized(eigenvectors[:, -1])
    farthest = selected[
        np.argmax(np.linalg.norm(selected - arm_centroid, axis=1))
    ]
    if weapon_id in (10, 15):
        if np.dot(forward, farthest - arm_centroid) < 0:
            forward = -forward
    elif forward[2] < 0:
        forward = -forward

    distances = np.linalg.norm(selected - arm_centroid, axis=1)
    grip_count = max(8, round(len(selected) * 0.20))
    grip_indices = np.argsort(distances)[:grip_count]
    grip = selected[grip_indices].mean(axis=0)
    projection = selected @ forward
    muzzle_indices = np.argsort(projection)[-5:]
    muzzle = selected[muzzle_indices].mean(axis=0)
    span = float(np.ptp(projection))
    right, up, forward = orthonormal_frame(forward)
    nominal = NOMINAL_LENGTHS_M[weapon_id]
    return {
        "grip_pivot": grip.tolist(),
        "muzzle": muzzle.tolist(),
        "right": right.tolist(),
        "up": up.tolist(),
        "forward": forward.tolist(),
        "forward_span_units": span,
        "reference_length_m": nominal,
        "model_units_per_metre": span / nominal,
        "provisional": True,
        "rule": "20% nearest-to-arm grip; selected-geometry principal axis; "
                "five-vertex forward tip",
        "grip_markers": [
            list(selected_markers[index]) for index in grip_indices
        ],
        "muzzle_markers": [
            list(selected_markers[index]) for index in muzzle_indices
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path)
    parser.add_argument("--proof", type=Path, required=True)
    args = parser.parse_args()
    source = args.captures.resolve()
    capture_receipt = json.loads(source.read_text(encoding="utf-8"))
    if not capture_receipt.get("complete"):
        raise ValueError("Capture receipt is incomplete")
    captures = {}
    for row in capture_receipt["weapons"]:
        captures.setdefault(row["id"], row)
    if set(captures) != set(topology.PROFILES):
        raise ValueError("Capture does not contain all 13 unique weapon IDs")

    weapons = []
    for weapon_id in sorted(captures):
        calibration = derive(captures[weapon_id])
        axes = np.asarray([
            calibration["right"],
            calibration["up"],
            calibration["forward"],
        ])
        if np.max(np.abs(axes @ axes.T - np.eye(3))) > 1e-9:
            raise ValueError(f"ID {weapon_id} axes are not orthonormal")
        projected = (
            np.asarray(calibration["muzzle"]) -
            np.asarray(calibration["grip_pivot"])
        ) @ np.asarray(calibration["forward"])
        if projected <= 0:
            raise ValueError(f"ID {weapon_id} muzzle is behind the grip")
        weapons.append({
            "id": weapon_id,
            "name": topology.PROFILES[weapon_id]["name"],
            "source_slot": captures[weapon_id]["slot"],
            "source_switches": captures[weapon_id]["switches"],
            "calibration": calibration,
        })

    proof = {
        "schema": 1,
        "kind": "W3.4 provisional complete-gun calibration data",
        "complete": True,
        "capture_receipt": str(source),
        "capture_receipt_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "weapons": weapons,
        "physical_acceptance": False,
        "limits": [
            "Nominal lengths are display references, not measured physical size.",
            "The recovery fixture is a fixed synthetic hand pose in multiplayer.",
            "Non-firearm prop forward axes are provisional animation-space axes.",
            "No normal-enablement, shot-alignment or headset acceptance is claimed.",
        ],
    }
    args.proof.parent.mkdir(parents=True, exist_ok=True)
    args.proof.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print("PASS: 13 provisional complete-gun calibrations derived")


if __name__ == "__main__":
    main()
