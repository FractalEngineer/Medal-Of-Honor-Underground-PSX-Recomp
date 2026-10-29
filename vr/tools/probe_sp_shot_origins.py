"""Measure SP projectile origin and first native motion in copied fixtures.

This is a read-only trace. It uses naturally available SP weapons, consumes
disposable-fixture ammo, and never edits guest inventory, health or saves.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import socket
import struct
import subprocess

import inspect_weapon_sets as native
import probe_p38_headset as comparison
import probe_shot_families as families
import check_weapon_pose_spaces as poses


ROOT = native.ROOT
SP_PLAYER = 0x800AA17C
SP_INPUT_OFFSET = 0x39C
SP_VIEWMODEL_OFFSET = 0x114
SP_INPUT_VIEWMODEL_OFFSET = 0x330
TYPE_STORE_PC = 0x800484CC
POSITION_OFFSET = 0x220
ANGLE_OFFSET = 0x23C
SP_MOTION_PCS = (0x800793E4, 0x80079400, 0x8007941C)
CASES = (
    (3, 0, 0),   # P38
    (4, 0, 16),  # Sten
    (2, 2, 13),  # Panzerfaust
    (3, 1, 15),  # petrol bomb, measured separately
)
DEFAULT_IDS = (0, 16, 13)


def read_word(address: int) -> int:
    return struct.unpack("<I", native.read(address, 4))[0]


def signed(value) -> int:
    value = int(value, 0) if isinstance(value, str) else int(value)
    return value - 2**32 if value & 0x80000000 else value


def shot_type(weapon_id: int) -> int:
    if weapon_id not in families.EXPECTED_FAMILIES:
        raise ValueError(f"Unsupported SP trace weapon ID {weapon_id}")
    return families.EXPECTED_FAMILIES[weapon_id]


def trace_dump(**values) -> dict:
    return native.command("wtrace_dump", count=4096, **values)


def find_constructor(
    weapon_id: int, buttons: tuple[str, ...], press: bool = False
) -> tuple[dict, dict, str]:
    expected_type = shot_type(weapon_id)
    cursor_total = 0
    for button_value in buttons:
        if press:
            native.command("press", buttons=button_value, frames=24)
        else:
            native.command("set_input", buttons=button_value)
        for frame in range(20 if press else 60):
            trace = trace_dump(
                pc_lo=hex(TYPE_STORE_PC - 0x80),
                pc_hi=hex(TYPE_STORE_PC + 0x80),
            )
            if trace["total"] - trace["available"] > cursor_total:
                raise RuntimeError("SP constructor trace ring lost records")
            cursor_total = trace["total"]
            events = [
                row for row in trace["entries"]
                if int(row["pc"], 0) == TYPE_STORE_PC and
                int(row["new"], 0) == expected_type and
                int(row["s2"], 0) == read_word(SP_PLAYER)
            ]
            if expected_type == 0x13F3 and not events:
                events = [
                    row for row in trace["entries"]
                    if int(row["new"], 0) == expected_type and
                    int(row["s2"], 0) == read_word(SP_PLAYER)
                ]
            if events:
                event = events[0]
                shot = int(event["s0"], 0)
                if not 0x800B0000 <= shot <= 0x801FC000:
                    raise RuntimeError(
                        "SP constructor returned an invalid shot object"
                    )
                return event, trace, button_value
            if not press and frame == 30:
                native.command("set_input", buttons="0xffff")
            native.frames(1)
        native.command("set_input", buttons="0xffff")
        native.frames(4)
    raise TimeoutError(f"ID {weapon_id} did not construct a native projectile")


def position_groups(
    entries: list[dict], shot: int, start_sequence: int
) -> list[dict]:
    by_frame = {}
    for row in entries:
        if int(row["seq"]) <= start_sequence:
            continue
        low = int(row["addr"], 0) & 0x1FFFFFFF
        for axis in range(3):
            if low == (
                shot + POSITION_OFFSET + axis * 4
            ) & 0x1FFFFFFF:
                by_frame.setdefault(int(row["frame"]), {})[axis] = row
    groups = []
    for frame in sorted(by_frame):
        rows = by_frame[frame]
        if set(rows) != {0, 1, 2}:
            continue
        ordered = [rows[axis] for axis in range(3)]
        if len({row["seq"] for row in ordered}) != 3:
            continue
        before = [signed(row["old"]) / 65536 for row in ordered]
        after = [signed(row["new"]) / 65536 for row in ordered]
        delta = [new - old for old, new in zip(before, after)]
        groups.append({
            "frame": frame,
            "sequence": [int(row["seq"]) for row in ordered],
            "pc": [row["pc"] for row in ordered],
            "before": before,
            "after": after,
            "delta": delta,
            "moved": any(abs(value) > 0 for value in delta),
        })
    return groups


def angle_snapshot(
    entries: list[dict], shot: int, start_sequence: int
) -> list[dict]:
    result = []
    for row in entries:
        if int(row["seq"]) <= start_sequence:
            continue
        low = int(row["addr"], 0) & 0x1FFFFFFF
        for axis in range(3):
            if low == (shot + ANGLE_OFFSET + axis * 4) & 0x1FFFFFFF:
                result.append({
                    "seq": row["seq"],
                    "frame": row["frame"],
                    "axis": axis,
                    "pc": row["pc"],
                    "old": row["old"],
                    "new": row["new"],
                })
    return result


def snapshot(weapon_id: int, switches: int) -> dict:
    actor = read_word(SP_PLAYER)
    player_input = read_word(actor + SP_INPUT_OFFSET)
    object_address = read_word(actor + SP_VIEWMODEL_OFFSET)
    if player_input != actor + 0x3FC:
        raise RuntimeError("Not the measured SP input layout")
    if object_address != player_input + SP_INPUT_VIEWMODEL_OFFSET:
        raise RuntimeError("Not the measured SP viewmodel layout")
    live_id = native.read(player_input + 93, 1)[0]
    if live_id != weapon_id:
        raise RuntimeError(
            f"Natural switch selected ID {live_id}, expected {weapon_id}"
        )
    weapon_slot = native.read(player_input + 92, 1)[0]
    clip_address = player_input + 110 + weapon_slot * 2
    reserve_address = player_input + 94 + weapon_slot * 2
    return {
        "actor": hex(actor),
        "input": hex(player_input),
        "viewmodel": hex(object_address),
        "weapon_id": live_id,
        "weapon": native.WEAPONS[live_id],
        "switches": switches,
        "weapon_slot": weapon_slot,
        "clip": struct.unpack("<h", native.read(clip_address, 2))[0],
        "reserve": struct.unpack("<h", native.read(reserve_address, 2))[0],
    }


def run_case(
    slot: int, switches: int, weapon_id: int, hand_yaw_deg: float,
    head_yaw_deg: float, tracking_loss: bool,
) -> dict:
    native.load(slot)
    comparison.release_load_override()
    for _ in range(switches):
        native.switch()
        comparison.release_load_override()
    comparison.set_desktop_hands()
    if hand_yaw_deg or tracking_loss:
        angle = math.radians(hand_yaw_deg)
        q = (0.0, math.sin(angle / 2), 0.0, math.cos(angle / 2))
        poses.set_hand_pair(
            grip=(0.15, -0.15, -0.4),
            aim=(0.15, -0.15, -0.4),
            grip_q=q,
            aim_q=q,
            focused=0 if tracking_loss else 1,
        )
    if head_yaw_deg:
        native.command(
            "mod_cmd",
            name="mohu.vr.stereo.pose",
            args=f"yaw={round(head_yaw_deg * 1000)}",
        )
    native.frames(10)
    before = snapshot(weapon_id, switches)
    before_counters = comparison.counter_values()
    native.command("wtrace_range", lo="0x800B0000", hi="0x801FF000")
    native.command("wtrace_clear")
    native.command("set_input", buttons="0xffff")
    button_candidates = (
        ("0xbdff", "0xbfff", "0x7fff", "0xdfff", "0xefff",
         "0xf7ff", "0xfbff", "0xfdff", "0xfeff")
        if weapon_id in (10, 15) else ("0xbfff",)
    )
    constructor, constructor_trace, fire_buttons = find_constructor(
        weapon_id, button_candidates, press=weapon_id in (10, 15)
    )
    shot = int(constructor["s0"], 0)
    initial_position = [
        struct.unpack(
            "<i", native.read(shot + POSITION_OFFSET + axis * 4, 4)
        )[0] / 65536
        for axis in range(3)
    ]
    initial_angles = [
        signed(read_word(shot + ANGLE_OFFSET + axis * 4)) / 65536
        for axis in range(3)
    ]
    native.command("set_input", buttons="0xffff")
    object_rows = {}
    object_trace = {}
    for _ in range(8):
        native.frames(4)
        object_trace = trace_dump(
            addr_lo=hex(shot),
            addr_hi=hex(shot + 0x500),
        )
        if object_trace["emitted"] >= 4096:
            raise RuntimeError("Object-filtered SP projectile trace truncated")
        for row in object_trace["entries"]:
            object_rows[int(row["seq"])] = row
    entries = [object_rows[key] for key in sorted(object_rows)]
    groups = position_groups(entries, shot, 0)
    motion = next(
        (
            group for group in groups
            if tuple(int(pc, 0) for pc in group["pc"]) == SP_MOTION_PCS
        ),
        None,
    )
    final_origin = {
        "pc": ["initial-read"],
        "before": [0.0, 0.0, 0.0],
        "after": initial_position,
        "delta": initial_position,
        "moved": any(initial_position),
    }
    if motion is not None:
        motion_index = groups.index(motion)
        if motion_index:
            final_origin = groups[motion_index - 1]
    after = snapshot(weapon_id, switches)
    after_counters = comparison.counter_values()
    aimed = (
        after_counters.get("mohu.vr.shot.sp.aimed", 0) -
        before_counters.get("mohu.vr.shot.sp.aimed", 0)
    )
    fallback = (
        after_counters.get("mohu.vr.shot.sp.fallback", 0) -
        before_counters.get("mohu.vr.shot.sp.fallback", 0)
    )
    tracking_fallback = (
        after_counters.get("mohu.vr.shot.sp.tracking_fallback", 0) -
        before_counters.get("mohu.vr.shot.sp.tracking_fallback", 0)
    )
    ammo_consumed = (
        after["clip"] < before["clip"] or
        after["reserve"] < before["reserve"]
    )
    checks = {
        "native_first_motion": motion is not None,
        "tracked_control": (
            aimed == 0 and tracking_fallback > 0 if tracking_loss
            else aimed > 0 and tracking_fallback == 0
        ),
        "native_ammo_consumed": ammo_consumed,
        "no_other_fallback": fallback == 0,
    }
    writer_pcs = sorted({
        pc for group in groups for pc in group["pc"]
    })
    code = {}
    for pc_text in writer_pcs:
        pc = int(pc_text, 0)
        start = pc - 16
        code[pc_text] = {
            "start": hex(start),
            "bytes": native.read(start, 48).hex(),
            "disasm": native.command("disasm", addr=hex(start), count=12)["lines"],
        }
    return {
        "slot": slot,
        "weapon_id": weapon_id,
        "weapon": native.WEAPONS[weapon_id],
        "type": shot_type(weapon_id),
        "fire_buttons": fire_buttons,
        "before": before,
        "after": after,
        "shot_counters": {
            "aimed": aimed,
            "fallback": fallback,
            "tracking_fallback": tracking_fallback,
        },
        "checks": checks,
        "control_passed": all(checks.values()),
        "constructor": constructor,
        "constructor_trace_counts": {
            key: constructor_trace[key]
            for key in ("total", "available", "emitted")
        },
        "shot": hex(shot),
        "shot_type_before_release": signed(read_word(shot + 8)),
        "initial_position": initial_position,
        "initial_angles": initial_angles,
        "position_groups": groups,
        "final_origin": final_origin,
        "first_motion": motion,
        "motion_pcs": [f"0x{pc:08X}" for pc in SP_MOTION_PCS],
        "angle_writes": angle_snapshot(entries, shot, 0),
        "writer_code": code,
        "object_trace_counts": {
            "motion": {
                key: object_trace[key]
                for key in ("total", "available", "emitted")
            },
        },
        "object_trace": entries if motion is None else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--ids", type=int, nargs="+")
    parser.add_argument("--hand-yaw", type=float, default=0.0)
    parser.add_argument("--head-yaw", type=float, default=0.0)
    parser.add_argument("--tracking-loss", action="store_true")
    args = parser.parse_args()
    if not -180.0 <= args.hand_yaw <= 180.0:
        parser.error("hand yaw must be in -180..180 degrees")
    if not -180.0 <= args.head_yaw <= 180.0:
        parser.error("head yaw must be in -180..180 degrees")
    selected = set(args.ids or DEFAULT_IDS)
    unknown = selected - {case[2] for case in CASES}
    if unknown:
        parser.error(f"unsupported trace IDs: {sorted(unknown)}")
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic TCP port 4372 is occupied")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    saves = out / "saves/openbios"
    saves.mkdir(parents=True)
    hashes = {}
    for slot in sorted({case[0] for case in CASES}):
        for suffix in ("pst", "thumb"):
            source = ROOT / (
                "analysis/fixtures/sp/openbios/"
                f"state_8001F844_slot{slot:02}.{suffix}"
            )
            shutil.copyfile(source, saves / source.name)
            hashes[str(source.relative_to(ROOT))] = native.digest(source)
    preferences = comparison.hash_existing(comparison.preference_paths())
    executable = (
        ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    )
    env = comparison.environment("tracked", True, hand_fixed=True)
    env.update(
        PSX_INTERNAL_RESOLUTION="native",
        PSX_RENDER_PASS_VERIFY="0",
        MOHU_VR_MP_CONTROL="0",
        MOHU_VR_MP_FRUSTUM="0",
        MOHU_VR_WEAPON_TRACE="0",
    )
    receipt = {
        "schema": 1,
        "kind": "G7a/G7c/G7d SP projectile origin and first motion",
        "complete": False,
        "headset_used": False,
        "fixture_hashes": hashes,
        "executable_sha256": native.digest(executable),
        "build": comparison.build_configuration(
            ROOT / "build-release/CMakeCache.txt"
        ),
        "cases": [],
        "hand_yaw_deg": args.hand_yaw,
        "head_yaw_deg": args.head_yaw,
        "tracking_loss": args.tracking_loss,
        "limits": [
            "Natural SP fixtures cover only IDs 0, 13, 15 and 16.",
            "Tracing does not prove projectile direction under a changed hand pose.",
            "This probe consumes disposable-fixture ammunition only.",
        ],
    }
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
            for slot, switches, weapon_id in CASES:
                if weapon_id not in selected:
                    continue
                receipt["cases"].append(
                    run_case(
                        slot, switches, weapon_id,
                        args.hand_yaw, args.head_yaw, args.tracking_loss,
                    )
                )
                comparison.save_json(out / "receipt.json", receipt)
            receipt["complete"] = True
        except BaseException as error:
            receipt["error"] = str(error)
            raise
        finally:
            try:
                native.command("set_input", buttons="0xffff")
                native.command("openxr_input_override", clear=1)
                native.command("wtrace_range", lo="0", hi="0")
                native.command("openxr_hands_override", clear=1)
                native.command("quit")
            except (OSError, RuntimeError):
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                receipt["forced_cleanup"] = True
                process.terminate()
                process.wait(timeout=8)
            receipt["exit_code"] = process.returncode
            receipt["source_saves_unchanged"] = all(
                native.digest(ROOT / path) == digest
                for path, digest in hashes.items()
            )
            receipt["preferences_unchanged"] = (
                comparison.hash_existing(comparison.preference_paths()) ==
                preferences
            )
            receipt["remaining_game_pids"] = native.game_pids()
            receipt["complete"] = bool(
                receipt["complete"] and
                receipt["exit_code"] == 0 and
                not receipt.get("forced_cleanup") and
                not receipt["remaining_game_pids"] and
                receipt["source_saves_unchanged"] and
                receipt["preferences_unchanged"]
            )
            comparison.save_json(out / "receipt.json", receipt)
    summary = [
        {
            "id": row["weapon_id"],
            "weapon": row["weapon"],
            "final_origin_pcs": (
                row["final_origin"]["pc"] if row["final_origin"] else None
            ),
            "first_motion_pcs": (
                row["first_motion"]["pc"] if row["first_motion"] else None
            ),
            "first_motion_delta": (
                row["first_motion"]["delta"] if row["first_motion"] else None
            ),
        }
        for row in receipt["cases"]
    ]
    print(json.dumps({"complete": receipt["complete"], "cases": summary}))
    if not receipt["complete"] or not all(
        row.get("control_passed") for row in receipt["cases"]
    ):
        raise RuntimeError("SP projectile origin probe did not close cleanly")


if __name__ == "__main__":
    main()
