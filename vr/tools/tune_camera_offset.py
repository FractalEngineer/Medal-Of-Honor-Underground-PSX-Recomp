"""Adjust the Slot 03 objective-camera model without restarting the game.

Coordinates are controller-local metres:
  right   positive moves away from the left controller
  up      positive moves toward the head
  forward positive moves toward the rifle/camera lens

Provided axes replace the live absolute offset; omitted axes stay unchanged.
`--reset` returns all axes to the built-in wrist origin. A running debug build
is updated through its TCP command; production builds poll the same atomically
written file every few frames.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inspect_weapon_sets as native

DEFAULT = (0.0, 0.0, 0.0)
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "analysis/runtime/vr/camera-offset.txt"


def tuning_path():
    configured = os.environ.get("MOHU_VR_CAMERA_TUNING_FILE")
    return Path(configured) if configured else DEFAULT_PATH


def read_file():
    path = tuning_path()
    if not path.is_file():
        return dict(zip(("right", "up", "forward"), DEFAULT))
    values = [float(value) for value in path.read_text(encoding="ascii").split()]
    if len(values) != 3 or any(value < -1.0 or value > 1.0 for value in values):
        raise RuntimeError(f"invalid camera tuning file: {path}")
    return dict(zip(("right", "up", "forward"), values))


def write_file(value):
    path = tuning_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        f"{value['right']:.6f} {value['up']:.6f} {value['forward']:.6f}\n",
        encoding="ascii",
    )
    temporary.replace(path)


def camera_offset(**changes):
    values = " ".join(f"{name}={value}" for name, value in changes.items())
    result = native.command(
        "mod_cmd", name="mohu.vr.weapon.camera-offset", args=values
    )
    if result.get("result") != 1:
        raise RuntimeError(f"camera offset rejected: {result}")
    return json.loads(result["reply"])


def debug_endpoint_available():
    with socket.socket() as sock:
        sock.settimeout(0.1)
        return sock.connect_ex(("127.0.0.1", 4372)) == 0


def read_live():
    if not debug_endpoint_available():
        return read_file()
    try:
        result = native.command(
            "mod_cmd", name="mohu.vr.weapon.camera-offset", args=""
        )
        return json.loads(result["reply"])
    except (OSError, RuntimeError):
        return read_file()


def apply_offsets(value):
    write_file(value)
    if not debug_endpoint_available():
        return value
    try:
        return camera_offset(**{
            name: f"{number:.6f}" for name, number in value.items()
        })
    except (OSError, RuntimeError):
        return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--right", type=float)
    parser.add_argument("--up", type=float)
    parser.add_argument("--forward", type=float)
    parser.add_argument("--read", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if args.reset and any(
        value is not None for value in (args.right, args.up, args.forward)
    ):
        parser.error("--reset cannot be combined with axis values")
    if args.read and (
        args.reset or any(
            value is not None
            for value in (args.right, args.up, args.forward)
        )
    ):
        parser.error("--read cannot be combined with updates")
    if args.reset:
        value = apply_offsets(dict(zip(("right", "up", "forward"), DEFAULT)))
    elif args.read:
        value = read_live()
    else:
        updates = {}
        for name in ("right", "up", "forward"):
            setting = getattr(args, name)
            if setting is not None:
                updates[name] = setting
        if not updates:
            parser.error("provide an axis, --read, or --reset")
        changes = read_live()
        changes.update(updates)
        value = apply_offsets(changes)
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
