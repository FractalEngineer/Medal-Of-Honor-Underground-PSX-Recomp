"""Verify tiny scoped mouse steps and real projectile paths in an owned session."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vr/tools"))
import inspect_weapon_sets as native


def pad(fire=False, rx=128):
    native.command("set_input", layer="host", buttons=0xBDFF if fire else 0xFDFF,
                   pad_type=1, lx=128, ly=128, rx=rx, ry=128)


def motion(x, y):
    native.command("mod_cmd", name="mohu.mkb.test", args=f"motion {x} {y}")
    native.frames(6)


def snapshot():
    player = int.from_bytes(native.read(0x800AA17C, 4), "little")
    camera = int.from_bytes(native.read(0x800AA160, 4), "little")
    if not 0x800B0000 <= player <= 0x801FC000 or not 0x800B0000 <= camera <= 0x801FC000:
        raise RuntimeError("Invalid campaign roots")
    inp = player + 0x3FC
    return dict(player=player, camera=camera,
                angles=list(struct.unpack("<3i", native.read(player + 0x23C, 12))),
                eye=list(struct.unpack("<3i", native.read(camera + 0x220, 12))),
                target=list(struct.unpack("<3i", native.read(inp + 0x1B0, 12))),
                matrix=list(struct.unpack("<9h", native.read(camera + 0x4FC, 18))),
                depth=int.from_bytes(native.read(inp + 0xAC, 4), "little"))


def reset():
    native.load(1)
    native.command("clear_input")
    motion(0, 0)
    pad()
    native.frames(180)  # Native zoom eases to its final focal length.


def project(point, eye, state):
    d = [(a - b) / 65536 for a, b in zip(point, eye)]
    m = state["matrix"]
    v = [sum(m[3 * row + j] * d[j] for j in range(3)) for row in range(3)]
    if v[2] <= 1:
        raise RuntimeError("Projectile sample is behind the scope")
    return [256 + state["depth"] * v[0] / v[2], 120 + state["depth"] * v[1] / v[2]]


def groups(entries, shot):
    pending = {}
    result = []
    for row in entries:
        axis = ((int(row["addr"], 16) | 0x80000000) - shot - 0x220) // 4
        if axis == 0:
            pending = {}
        if axis not in range(3):
            continue
        v = int(row["new"], 16)
        pending[axis] = v - 2**32 if v & 0x80000000 else v
        if len(pending) == 3:
            result.append(dict(frame=row["frame"], pc=row["pc"],
                               position=[pending[i] for i in range(3)]))
    return result


def fire_case(rx=128):
    state = snapshot()
    native.command("set_snapshot", slot=3, addr=hex(state["camera"] + 0x220))
    native.frames(3)
    pad(rx=rx)
    native.frames(10 if rx != 128 else 3)
    native.command("wtrace_range", lo="0x800B0000", hi="0x801FC000")
    native.command("wtrace_clear")
    pad(True, rx)
    events = []
    for _ in range(20):
        trace = native.command("wtrace_dump", count=32, pc_lo="0x800484CC", pc_hi="0x800484D0")
        events = [e for e in trace["entries"] if int(e["new"], 16) == 0x13F6 and
                  int(e["s2"], 16) == state["player"]]
        if events:
            break
        native.frames(1)
    pad()
    if len(events) != 1:
        raise RuntimeError("Expected one real owned scoped projectile")
    event = events[0]
    shot = int(event["s0"], 16)
    construction = native.command("wtrace_dump", count=256,
                                  pc_lo="0x8004815C", pc_hi="0x80048700")
    origin_rows = [e for e in construction["entries"] if e["pc"] in
                   ("0x800481A0", "0x800481A4", "0x800481A8") and int(e["s0"], 16) == shot]
    origin = [int(e["new"], 16) for e in origin_rows]
    origin = [v - 2**32 if v & 0x80000000 else v for v in origin]
    if len(origin) != 3:
        raise RuntimeError("Incomplete scoped construction trace")
    native.command("wtrace_range", lo=hex(shot + 0x220), hi=hex(shot + 0x368))
    native.frames(55)
    trace = native.command("wtrace_dump", count=256,
                           addr_lo=hex(shot + 0x220), addr_hi=hex(shot + 0x22C))
    points = [r for r in groups(trace["entries"], shot) if r["pc"] in
              ("0x8007941C", "0x8007971C")]
    for row in points:
        row["pixel"] = project(row["position"], origin, state)
    frame_eye = list(struct.unpack("<3i", bytes.fromhex(native.command("read_frame_ram",
        frame=event["frame"], addr=hex(state["camera"] + 0x220), len=12)["hex"])))
    native.command("wtrace_range", lo="0", hi="0")
    return dict(state=state, event=event, origin=origin, frame_eye=frame_eye,
                construction=construction, trajectory=points)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--sensitivity", type=float, default=50)
    parser.add_argument("--scoped-sensitivity", type=float, default=80)
    parser.add_argument("--pixel-tolerance", type=float, default=3,
                        help="Native 512x240 pixel budget for fixed-point casting, velocity and collision rounding")
    args = parser.parse_args()
    native.require_debugger_owner(args.pid)
    args.out.mkdir(parents=True, exist_ok=True)
    hashes = {str(p): native.digest(p) for p in (ROOT / "saves").rglob("*") if p.is_file()}
    receipt = dict(binary_sha256=native.digest(ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"),
                   pixel_tolerance=args.pixel_tolerance, checks={}, cases={})
    old_snapshot = native.command("get_snapshots")["snapshots"][3]
    try:
        reset()
        samples = [snapshot()]
        for _ in range(8):
            motion(1, 0)
            samples.append(snapshot())
        gain = args.sensitivity / 100 * args.scoped_sensitivity / 100 * 400 / samples[0]["depth"]
        wrap = 4096 * 65536
        receipt["checks"]["single_count_fractional_angle"] = all(
            abs((b["angles"][1] - a["angles"][1]) % wrap - gain * 65536) <= 1
            for a, b in zip(samples, samples[1:]))
        first, last = samples[0]["matrix"], samples[-1]["matrix"]
        view_delta = ((math.atan2(last[6], last[8]) - math.atan2(first[6], first[8])) *
                      4096 / math.tau) % 4096
        receipt["checks"]["camera_tracks_fractional_total"] = abs(view_delta - 8 * gain) < 0.12
        receipt["cases"]["single_counts"] = samples
        for name, dx, dy, rx in (("centre", 0, 0, 128), ("yaw_pitch", 300, -120, 128),
                                  ("opposite", -400, 160, 128), ("moving", 0, 0, 255)):
            reset()
            motion(dx, dy)
            case = fire_case(rx)
            receipt["cases"][name] = case
            trajectory = case["trajectory"]
            case["max_pixel_error"] = max((math.hypot(r["pixel"][0] - 256, r["pixel"][1] - 120)
                                           for r in trajectory), default=None)
            receipt["checks"][name + "_live_eye_origin"] = case["origin"] == case["frame_eye"]
            receipt["checks"][name + "_real_projectile_motion"] = bool(trajectory)
            receipt["checks"][name + "_trajectory_in_reticle"] = bool(trajectory) and \
                case["max_pixel_error"] < args.pixel_tolerance
        receipt["counters"] = native.command("mod_counters")
    finally:
        native.command("wtrace_range", lo="0", hi="0")
        native.command("set_snapshot", slot=3, addr=old_snapshot["addr"] if old_snapshot["active"] else "0")
        native.command("clear_input")
        native.command("mod_cmd", name="mohu.mkb.test", args="release")
        receipt["source_saves_unchanged"] = all(native.digest(Path(p)) == h for p, h in hashes.items())
        (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    failures = [name for name, ok in receipt["checks"].items() if not ok]
    print(json.dumps(dict(checks=len(receipt["checks"]), failures=failures,
                          source_saves_unchanged=receipt["source_saves_unchanged"]), indent=2))
    if failures or not receipt["source_saves_unchanged"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
