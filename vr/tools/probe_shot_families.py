"""Map native multiplayer shot families across all measured weapon IDs.

The probe uses copied root MP slots 1-4 and the existing saved combinations.
It enables only read-only shot capture; P38 remains the sole override.
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

import check_mp_view as eye
import inspect_weapon_sets as native
import probe_native_shot as shot
import probe_p38_headset as comparison
import probe_weapon_profiles as profiles


ROOT = native.ROOT
CYCLES = profiles.CYCLES
R2 = 0x0200
P38_TYPE = 0x13F6
BASIS_CALLER = 0x800488D8
RNG_FILTER = (0x80016D9C, 0x80016DD0)
RNG_STORE_PC = 0x80016DBC
EXPECTED_FAMILIES = {
    0: 0x13F6,
    1: 0x13F7,
    4: 0x13F7,
    5: 0x13F6,
    8: 0x13F6,
    9: 0x13F6,
    10: 0x13F3,
    12: 0x13F6,
    13: 0x13F1,
    14: 0x13FA,
    15: 0x13F3,
    16: 0x13F7,
    17: 0x13F7,
}


def command(name, **values):
    return eye.command(name, **values)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def seal_receipt(path, receipt):
    """Hash the final raw bytes without embedding their hash into themselves."""
    raw = {key: value for key,value in receipt.items()
           if key != "raw_receipt_sha256"}
    save(path, raw)
    return {**raw, "raw_receipt_sha256": native.digest(path)}


def first_occurrences():
    rows = []
    seen = set()
    for slot in sorted(CYCLES):
        for switches, weapon_id in enumerate(CYCLES[slot]):
            if weapon_id in seen:
                continue
            seen.add(weapon_id)
            rows.append((slot, switches, weapon_id))
    if seen != set(native.WEAPONS):
        raise RuntimeError("Mixture cycles do not cover the measured weapon IDs")
    return rows


def number(value):
    return int(value, 0) if isinstance(value, str) else int(value)


def summarize_samples(samples, expected_id, owner):
    owned = [row for row in samples if number(row["owner"]) == owner]
    if not owned:
        raise RuntimeError(f"ID {expected_id}: no player-owned basis samples")
    wrong = [row for row in owned if row["weapon"] != expected_id]
    if wrong:
        raise RuntimeError(f"ID {expected_id}: basis owner reported another weapon")
    for row in owned:
        if not row["code_valid"]:
            raise RuntimeError(f"ID {expected_id}: missing code guard evidence")
        if number(row["argument"]) != number(row["shot"]):
            raise RuntimeError(f"ID {expected_id}: basis argument is not the shot")
    types = sorted({number(row["type"]) for row in owned})
    callers = sorted({number(row["caller"]) for row in owned})
    if types != [EXPECTED_FAMILIES[expected_id]]:
        raise RuntimeError(
            f"ID {expected_id}: unexpected shot family {types}"
        )
    if callers != [BASIS_CALLER]:
        raise RuntimeError(
            f"ID {expected_id}: unexpected basis callers {callers}"
        )
    if expected_id == 4 and len(owned) < 6:
        raise RuntimeError("Shotgun did not construct six pellets")
    return {
        "samples": owned,
        "owned_count": len(owned),
        "ignored_count": len(samples) - len(owned),
        "types": types,
        "callers": callers,
        "eligible_count": sum(bool(row["eligible"]) for row in owned),
        "aimed_count": sum(bool(row["aimed"]) for row in owned),
        "camera_invalid_count": sum(
            not bool(row["camera_valid"]) for row in owned
        ),
    }


def player_key(player):
    return {
        key: player[key]
        for key in ("weapon_slot", "weapon_id", "clip", "reserve")
    }


def fire_control(weapon_id):
    if weapon_id == 5:
        return {"scoped": False, "hold_frames": 60, "release_frames": 90,
                "approach_frames": 0}
    if weapon_id == 10:
        return {"scoped": False, "hold_frames": 60, "release_frames": 720,
                "approach_frames": 0}
    if weapon_id == 15:
        return {"scoped": False, "hold_frames": 60, "release_frames": 720,
                "approach_frames": 180}
    if weapon_id in (13, 14):
        return {"scoped": False, "hold_frames": 36, "release_frames": 360,
                "approach_frames": 0}
    return {"scoped": False, "hold_frames": 24, "release_frames": 180,
            "approach_frames": 0}


def prepare_weapon(slot, switches):
    native.load(slot)
    comparison.release_load_override()
    for _ in range(switches):
        native.switch()
        comparison.release_load_override()
    native.frames(6)


def trace_lifecycle(samples, collector):
    """Associate native construction/motion with each distinct shot object.

    Frames alone are insufficient: six shotgun objects are born in one frame.
    Automatic fire can recycle an object even within one capture window. Split
    by global write sequence, matching each basis sample to one constructor.
    """
    addresses = [number(row["shot"]) for row in samples]
    births = {}
    for address in set(addresses):
        events = [row for row in collector.entries("constructor")
                  if number(row["s0"]) == address and
                  number(row["pc"]) == 0x80048790]
        if len(events) != addresses.count(address):
            raise RuntimeError(f"Shot {address:08X}: ambiguous native construction count")
        births[address] = events
    consumed = dict.fromkeys(addresses,0)
    result = []
    for sample, address in zip(samples, addresses):
        occurrence = consumed[address]
        construction = births[address][occurrence]
        consumed[address] += 1
        if number(construction["new"]) != sample["type"]:
            raise RuntimeError(f"Shot {address:08X}: ambiguous native construction")
        born = construction["frame"]
        begin = construction["seq"]
        end = (births[address][occurrence+1]["seq"]
               if occurrence+1 < len(births[address]) else None)
        def inside(row):
            return row["seq"] > begin and (end is None or row["seq"] < end)
        motion = [row for row in collector.entries("motion")
                  if number(row["s0"]) == address and inside(row)]
        if not motion:
            raise RuntimeError(f"Shot {address:08X}: no constructor-to-motion path")
        xyz = shot.first_motion(motion, address)
        groups = []
        for index in range(0, len(motion), 3):
            stores = motion[index:index+3]
            if (len(stores) != 3 or
                    tuple(number(row["pc"]) for row in stores) != shot.MOTION_PCS or
                    len({row["frame"] for row in stores}) != 1):
                raise RuntimeError(f"Shot {address:08X}: incomplete later XYZ motion")
            if any((number(row["addr"]) & 0x1FFFFFFF) !=
                   ((address+0x220+axis*4) & 0x1FFFFFFF)
                   for axis,row in enumerate(stores)):
                raise RuntimeError(f"Shot {address:08X}: motion store targets another field")
            groups.append({
                "frame": stores[0]["frame"],
                "before": [shot.signed(row["old"])/65536 for row in stores],
                "after": [shot.signed(row["new"])/65536 for row in stores],
            })
        history = [row for row in collector.entries("constructor")
                   if number(row["s0"]) == address and inside(row) and
                   number(row["pc"]) in (0x800488EC, 0x800488F0, 0x800488F4)]
        if (tuple(number(row["pc"]) for row in history) !=
                (0x800488EC, 0x800488F0, 0x800488F4) or
                any(row["frame"] != born for row in history)):
            raise RuntimeError(f"Shot {address:08X}: missing native position history")
        offsets = [row for row in collector.entries("constructor")
                   if number(row["s0"]) == address and inside(row) and
                   number(row["pc"]) in (0x80048A20,0x80048A48,0x80048A70)]
        first_position = [shot.signed(row["old"]) for row in xyz["stores"]]
        damage = [row for row in collector.entries("damage")
                  if number(row["s1"]) == address and inside(row) and
                  number(row["a2"]) == address and
                  number(row["pc"]) == 0x8004EB80 and
                  number(row["ra"]) == 0x80050900 and
                  number(row["old"]) > number(row["new"])]
        result.append({
            "shot": address, "type": sample["type"], "birth_frame": born,
            "birth_sequence": begin, "next_birth_sequence": end,
            "basis_position": sample["position"], "basis_angles": sample["angles"],
            "native_history": [shot.signed(row["new"]) for row in history],
            "post_basis_origin_stores": offsets,
            "basis_to_motion_origin_shift": [
                (a-b)/65536 for a,b in zip(first_position,sample["position"])],
            "first_motion": xyz, "motion_steps": len(groups),
            "trajectory": groups,
            "native_damage": damage,
        })
    return result


def spread_summary(lifetimes, weapon_id):
    if weapon_id != 4:
        return None
    if len(lifetimes) != 6:
        raise RuntimeError("Shotgun lifecycle requires exactly six distinct pellets")
    directions = [row["first_motion"]["direction"] for row in lifetimes]
    minimum = min(sum(a*b for a,b in zip(left, right))
                  for i,left in enumerate(directions) for right in directions[i+1:])
    angle = math.degrees(math.acos(max(-1.0, min(1.0, minimum))))
    # A native spread control must prove differing trajectories; six identical
    # basis-angle records alone cannot certify a pellet spread contract.
    if angle <= .01:
        raise RuntimeError("Six shotgun pellets did not show measurable native spread")
    return {"pellets": 6, "maximum_pair_angle_degrees": angle,
            "basis_angle_variants": len({tuple(row["basis_angles"]) for row in lifetimes}),
            "motion_direction_variants": len({tuple(row) for row in directions})}


def probe_weapon(
    slot, switches, expected_id, *, lifecycle=False, trace_path=None,
    settle_frames=0,
):
    prepare_weapon(slot, switches)
    before = native.players()
    if before[0]["weapon_id"] != expected_id:
        raise RuntimeError(
            f"Slot {slot} switch {switches} selected "
            f"{before[0]['weapon_id']}, expected {expected_id}"
        )
    control = fire_control(expected_id)
    if control["approach_frames"]:
        command("press", buttons="0xffff", ly=0,
                frames=control["approach_frames"])
        native.frames(control["approach_frames"] + 12)
        before = native.players()
    shot.shot_command("stop")
    shot.shot_command("start-p1")
    native.frames(12)
    camera = shot.shot_command("camera")
    if not camera["valid"]:
        raise RuntimeError(f"ID {expected_id}: canonical camera was not captured")
    if settle_frames:
        # W5.3e pairs this native run with the tracked hand-pose settling time.
        native.frames(settle_frames)

    if control["scoped"]:
        command("set_input", buttons=str(0xFFFF ^ R2))
        native.frames(30)
    collector = None
    if lifecycle:
        command("wtrace_range", lo="0x800B0000", hi="0x801FF000")
        command("wtrace_clear")
        collector = shot.TraceCollector({**shot.FILTERS,
            "motion_context": (0x8006EB8C,0x8006F7D0),
            "shot_update": (0x80047720,0x80047C80),
            "rng": RNG_FILTER})
    trigger_start = command("frame")["frame"]
    command("openxr_input_override", right_trigger=1000)
    wait = collector.wait if collector else native.frames
    wait(min(control["hold_frames"], 8))
    release_before = command("frame")["frame"]
    command("openxr_input_override", clear=1)
    release_after = command("frame")["frame"]
    if control["scoped"]:
        command("set_input", buttons="0xffff")
    wait(control["release_frames"])
    if collector:
        command("wtrace_range", lo="0", hi="0")
        collector.collect()
    shot.shot_command("stop")
    native.command("openxr_input_override", clear=1)

    status = shot.shot_command("status")
    if status["overflow"]:
        raise RuntimeError(f"ID {expected_id}: shot sample ring overflow")
    samples = [
        shot.shot_command(f"read={index}") for index in range(status["count"])
    ]
    after = native.players()
    summary = summarize_samples(
        samples, expected_id, int(before[0]["actor"], 16)
    )
    if summary["aimed_count"]:
        raise RuntimeError("Read-only family probe unexpectedly overrode a shot")
    effects = {
        "before": player_key(before[0]),
        "after": player_key(after[0]),
    }
    effects["changed"] = {
        key: [effects["before"][key], effects["after"][key]]
        for key in effects["before"]
        if effects["before"][key] != effects["after"][key]
    }
    if not effects["changed"]:
        raise RuntimeError(f"ID {expected_id}: no native ammo or slot consumption")
    if expected_id == 0 and summary["types"] != [P38_TYPE]:
        raise RuntimeError(f"P38 type changed: {summary['types']}")

    family = "|".join(f"{value:04X}" for value in summary["types"])
    row = {
        "id": expected_id,
        "name": native.WEAPONS[expected_id],
        "slot": slot,
        "switches": switches,
        "control": control,
        "trigger_window": {"start": trigger_start,
                           "release_before": release_before,
                           "release_after": release_after,
                           "requested_hold_frames": min(control["hold_frames"],8)},
        "before": before,
        "after": after,
        "effects": effects,
        "camera": camera,
        "types": summary["types"],
        "callers": [f"0x{value:08X}" for value in summary["callers"]],
        "family": family,
        "owned_count": summary["owned_count"],
        "ignored_count": summary["ignored_count"],
        "eligible_count": summary["eligible_count"],
        "aimed_count": summary["aimed_count"],
        "camera_invalid_count": summary["camera_invalid_count"],
        "shots": summary["samples"],
    }
    if collector:
        row["raw_traces"] = {key: collector.entries(key) for key in collector.filters}
        if trace_path:
            save(trace_path, {"shots": summary["samples"],
                              "traces": row["raw_traces"],
                              "trigger_window": row["trigger_window"]})
        row["lifetimes"] = trace_lifecycle(summary["samples"], collector)
        for lifetime in row["lifetimes"]:
            born = lifetime["birth_frame"]
            lifetime["trigger_phase"] = (
                "held" if born < release_before else
                "released" if born > release_after else "release-boundary")
        row["spread"] = spread_summary(row["lifetimes"], expected_id)
        rng = [entry for entry in collector.entries("rng")
               if number(entry["pc"]) == RNG_STORE_PC]
        if not rng:
            raise RuntimeError(f"ID {expected_id}: missing native RNG updates")
        row["rng"] = {
            "calls": len(rng),
            "store_pc": f"0x{RNG_STORE_PC:08X}",
            "events": [
                {"seq": entry["seq"], "old": entry["old"], "new": entry["new"]}
                for entry in rng
            ],
            "states_before": [entry["old"] for entry in rng],
            "states_after": [entry["new"] for entry in rng],
        }
        row["trace_counts"] = {key: len(value) for key,value in collector.rows.items()}
    print(
        f"ID {expected_id:02} {row['name']}: type {family}, "
        f"samples {row['owned_count']}",
        flush=True,
    )
    return row


def write_proof(path, receipt):
    proof = {
        key: receipt[key]
        for key in (
            "schema", "kind", "complete", "headset_used", "fixture",
            "executable_sha256", "revision", "build", "sources",
            "source_saves", "preferences", "weapons", "families",
            "source_saves_unchanged", "preferences_unchanged",
            "remaining_game_pids", "exit_code",
        )
    }
    proof["lifecycle"] = receipt["lifecycle"]
    proof["weapons"] = []
    for source in receipt["weapons"]:
        row = {key: value for key,value in source.items() if key != "raw_traces"}
        if "lifetimes" in row:
            row["lifetimes"] = []
            for lifetime in source["lifetimes"]:
                item = dict(lifetime)
                trajectory = item.pop("trajectory")
                item["trajectory_first"] = trajectory[:3]
                item["trajectory_last"] = trajectory[-1:]
                row["lifetimes"].append(item)
        proof["weapons"].append(row)
    proof["raw_receipt"] = receipt["raw_receipt"]
    proof["raw_receipt_sha256"] = receipt["raw_receipt_sha256"]
    proof["limits"] = [
        "Read-only native shot-family/lifecycle mapping; this run enables no shot override.",
        "Native motion/damage evidence is a baseline, not all-weapon tracked-aim acceptance.",
        "Synthetic desktop controls do not establish live NPC or SP isolation.",
        "Physical attachment, recoil alignment and impact acceptance remain open.",
    ]
    save(path, proof)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--ids", type=int, nargs="+")
    parser.add_argument("--lifecycle", action="store_true",
                        help="Trace each native construction through motion and damage")
    parser.add_argument(
        "--pair-settle-frames", type=int, default=0,
        help="Wait after camera capture to match a tracked-pose arm",
    )
    args = parser.parse_args()
    if args.pair_settle_frames < 0:
        parser.error("--pair-settle-frames cannot be negative")
    selected = set(args.ids or native.WEAPONS)
    unknown = selected - set(native.WEAPONS)
    if unknown:
        parser.error(f"Unknown weapon IDs: {sorted(unknown)}")
    if args.proof and selected != set(native.WEAPONS):
        parser.error("--proof requires the complete weapon family map")
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic TCP port 4372 occupied")

    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    copies = out / "saves/openbios"
    copies.mkdir(parents=True)
    source_hashes = {}
    for slot in CYCLES:
        for suffix in ("pst", "thumb"):
            source = ROOT / (
                f"saves/openbios/state_8001F844_slot{slot:02}.{suffix}"
            )
            shutil.copyfile(source, copies / source.name)
            source_hashes[str(source.relative_to(ROOT))] = native.digest(source)
    preferences = comparison.hash_existing(comparison.preference_paths())
    executable = ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    receipt = {
        "schema": 1,
        "kind": "W5.3 native MP shot-family lifecycle" if args.lifecycle else "W5.3 native MP shot-family map",
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
                "vr/tools/probe_shot_families.py",
                "vr/tools/probe_native_shot.py",
                "vr/tools/probe_weapon_profiles.py",
                "vr/tools/inspect_weapon_sets.py",
            )
        },
        "source_saves": source_hashes,
        "preferences": preferences,
        "weapons": [],
        "families": {},
        "lifecycle": args.lifecycle,
    }
    env = comparison.environment("native", True)
    env["PSX_INTERNAL_RESOLUTION"] = "native"
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
            comparison.wait_for_ping(process)
            for slot, switches, weapon_id in first_occurrences():
                if weapon_id not in selected:
                    continue
                receipt["weapons"].append(
                    probe_weapon(slot, switches, weapon_id, lifecycle=args.lifecycle,
                                 trace_path=out / f"id-{weapon_id:02}-traces.json",
                                 settle_frames=args.pair_settle_frames)
                )
                for row in receipt["weapons"]:
                    family = row["family"]
                    receipt["families"].setdefault(family, []).append(row["id"])
                save(out / "receipt.json", receipt)
            receipt["complete"] = True
        except BaseException as error:
            receipt["error"] = str(error)
            save(out / "receipt.json", receipt)
            raise
        finally:
            try:
                command("set_input", buttons="0xffff")
                command("wtrace_range", lo="0", hi="0")
                shot.shot_command("stop")
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
                for path, value in preferences.items()
            )
            receipt["remaining_game_pids"] = native.game_pids()
            save(out / "receipt.json", receipt)

    if not (
        receipt["complete"] and set(row["id"] for row in receipt["weapons"]) == selected
        and receipt["source_saves_unchanged"]
        and receipt["preferences_unchanged"]
        and not receipt["remaining_game_pids"]
        and receipt["exit_code"] == 0
    ):
        raise RuntimeError("Shot-family probe did not close cleanly")
    if args.proof:
        receipt["raw_receipt"] = str(
            (out / "receipt.json").relative_to(ROOT)
        )
        receipt = seal_receipt(out / "receipt.json", receipt)
        write_proof(args.proof, receipt)
    print(f"PASS: {len(selected)} native MP weapon families captured"
          + (" with constructor-to-motion lifetimes" if args.lifecycle else ""), flush=True)


if __name__ == "__main__":
    main()
