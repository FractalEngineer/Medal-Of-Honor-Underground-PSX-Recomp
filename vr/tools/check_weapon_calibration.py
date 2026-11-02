"""Validate the captured P38 calibration markers and retain a compact receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
GRIP_VERTICES = tuple(range(47, 65))
MUZZLE_VERTICES = (11, 12, 25, 26, 38)
REFERENCE_LENGTH_M = 0.216
EXPECTED_GRIP = np.array(
    [76.555555555556, 100.777777777778, 287.888888888889]
)
EXPECTED_MUZZLE = np.array([76.2, 109.8, 396.8])
EXPECTED_FORWARD = np.array(
    [-0.003253478173, 0.082557008645, 0.996581032934]
)
EXPECTED_SPAN = 114.525481833051
EXPECTED_SCALE = 530.210564041902


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive_markers(vertices):
    points = np.asarray([row[:3] for row in vertices], dtype=np.float64)
    if points.shape != (69, 3):
        raise RuntimeError(f"Expected 69 P38 vertices, got {points.shape}")
    grip = points[list(GRIP_VERTICES)].mean(axis=0)
    muzzle = points[list(MUZZLE_VERTICES)].mean(axis=0)
    forward = muzzle - grip
    forward /= np.linalg.norm(forward)
    down = np.array([0.0, 1.0, 0.0])
    down -= down.dot(forward) * forward
    down /= np.linalg.norm(down)
    right = np.cross(down, forward)
    right /= np.linalg.norm(right)
    up = -down
    projected = (points - grip) @ forward
    span = float(projected.max() - projected.min())
    scale = span / REFERENCE_LENGTH_M
    return {
        "grip_pivot": grip,
        "muzzle": muzzle,
        "right": right,
        "up": up,
        "forward": forward,
        "forward_span_units": span,
        "model_units_per_metre": scale,
        "bounds_min": points.min(axis=0),
        "bounds_max": points.max(axis=0),
    }


def close(name, actual, expected, tolerance=1e-9):
    error = float(np.max(np.abs(np.asarray(actual) - np.asarray(expected))))
    if error > tolerance:
        raise RuntimeError(f"{name} error {error} exceeds {tolerance}")
    return error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    raw_path = args.capture.resolve()
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    for key in (
        "complete",
        "source_saves_unchanged",
        "preferences_unchanged",
    ):
        if raw.get(key) is not True:
            raise RuntimeError(f"Capture did not pass {key}")
    if raw.get("remaining_game_pids"):
        raise RuntimeError("Capture left an owned game process")
    capture = raw["capture"]
    model = raw["model"]
    if (
        capture.get("id") != 0
        or capture.get("node") != 13
        or model.get("vertex_count") != 69
        or capture.get("local") != model["local_vertices_xyzw"][0]
        or capture.get("animated") != model["animated_vertices_xyzw"][0]
    ):
        raise RuntimeError("Captured P38 identity or first vertex mismatch")

    animated = derive_markers(model["animated_vertices_xyzw"])
    source = derive_markers(model["local_vertices_xyzw"])
    errors = {
        "grip_pivot": close(
            "grip pivot", animated["grip_pivot"], EXPECTED_GRIP
        ),
        "muzzle": close(
            "muzzle", animated["muzzle"], EXPECTED_MUZZLE
        ),
        "forward": close(
            "forward", animated["forward"], EXPECTED_FORWARD
        ),
        "forward_span": abs(
            animated["forward_span_units"] - EXPECTED_SPAN
        ),
        "model_units_per_metre": abs(
            animated["model_units_per_metre"] - EXPECTED_SCALE
        ),
    }
    if max(errors.values()) > 1e-9:
        raise RuntimeError(f"Calibration mismatch: {errors}")
    for name in ("right", "up", "forward"):
        norm = float(np.linalg.norm(animated[name]))
        if abs(norm - 1.0) > 1e-12:
            raise RuntimeError(f"{name} axis is not unit length: {norm}")
    if abs(float(animated["right"].dot(animated["up"]))) > 1e-12:
        raise RuntimeError("Right and up axes are not orthogonal")
    if abs(float(animated["right"].dot(animated["forward"]))) > 1e-12:
        raise RuntimeError("Right and forward axes are not orthogonal")
    if abs(float(animated["up"].dot(animated["forward"]))) > 1e-12:
        raise RuntimeError("Up and forward axes are not orthogonal")

    proof = {
        "schema": 1,
        "date": "2026-10-26",
        "kind": "W3.1 P38 provisional model-local calibration",
        "capture": str(raw_path.relative_to(ROOT)),
        "capture_sha256": sha256(raw_path),
        "fixture": raw["fixture"],
        "executable_sha256": raw["executable_sha256"],
        "capture_source_hashes": raw["source_hashes"],
        "asset": {
            "id": 0,
            "name": "P38 pistol",
            "node": 13,
            "vertex_count": 69,
            "source_face_count": model["source_face_count"],
            "local_sha256": model["local_sha256"],
            "animated_sha256": model["animated_sha256"],
            "object_state_sha256": model["object_state_sha256"],
        },
        "coordinate_space": "8008DB98 animated-model output",
        "units": "integer native model units",
        "marker_groups": {
            "grip_vertex_indices": list(GRIP_VERTICES),
            "muzzle_vertex_indices": list(MUZZLE_VERTICES),
            "grip_method": "arithmetic mean of rear grip block",
            "muzzle_method": "arithmetic mean of maximum-forward cap",
        },
        "animated_model": {
            key: (
                value.tolist() if isinstance(value, np.ndarray) else value
            )
            for key, value in animated.items()
        },
        "source_node_local": {
            key: (
                value.tolist() if isinstance(value, np.ndarray) else value
            )
            for key, value in source.items()
        },
        "scale": {
            "provisional": True,
            "reference": "P38 nominal overall length",
            "reference_length_m": REFERENCE_LENGTH_M,
            "model_units_per_metre": animated[
                "model_units_per_metre"
            ],
            "physical_acceptance": "open; W3.3",
        },
        "checks": {
            "max_abs_marker_error": max(errors.values()),
            "orthonormal_axes": True,
            "left_right_eye_hashes_equal": (
                raw["stereo"]["eye_hashes"][0]
                == raw["stereo"]["eye_hashes"][1]
            ),
            "render_verify_mismatch": raw["render_pass"][
                "verify_mismatch"
            ],
            "source_saves_unchanged": True,
            "preferences_unchanged": True,
            "remaining_game_pids": 0,
        },
        "limits": [
            "One idle multiplayer P38 fixture; no recoil or reload animation.",
            "Scale uses a nominal 216 mm reference length, not headset size acceptance.",
            "Markers are provisional and do not change renderer or shot behavior.",
        ],
    }
    if args.proof:
        args.proof.parent.mkdir(parents=True, exist_ok=True)
        args.proof.write_text(
            json.dumps(proof, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(
        "PASS: P38 grip/muzzle/axes/scale, "
        f"max marker error {max(errors.values()):.3g} model units"
    )


if __name__ == "__main__":
    main()
