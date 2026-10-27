"""Exercise W5.4 combat-state transitions with native and tracked shots.

Each mode runs in its own owned process against copied MP fixtures. The probe
keeps native reload, empty-fire, switching, scope, recoil and load behavior;
the tracked mode adds only the existing opt-in animated-marker candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import socket
import subprocess

import numpy as np

import check_weapon_pose_spaces as poses
import inspect_weapon_sets as native
import probe_native_shot as shot
import probe_p38_headset as comparison
import probe_shot_families as families
import probe_weapon_aim as aim


ROOT = native.ROOT
PRESERVATION = ROOT / "vr/proof/weapon-preservation-receipt.json"
FAMILIES = ROOT / "vr/proof/weapon-shot-families-receipt.json"
RELOAD = 0x8000
SWITCH = 0x2000
FIRE = 0x4000
R2 = 0x0200
EXPECTED_IDS = set(native.WEAPONS)
DAMAGE_EXPECTED = EXPECTED_IDS - {10, 15}
MOTION_TOLERANCE_WORLD_UNITS = 2.0
IMPACT_RAY_TOLERANCE_WORLD_UNITS = 2.0


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    comparison.save_json(path, value)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def marker(args):
    result = native.command("mod_cmd", name="mohu.vr.marker", args=args)
    if result["result"] != 1:
        raise RuntimeError(f"Marker command rejected: {result}")
    return json.loads(result["reply"])


def marker_state():
    value = marker("status")
    return {
        key: value[key]
        for key in (
            "enabled", "valid", "id", "sequence", "generation",
            "expected_generation", "loads", "load_cycle", "shot_cycle",
            "cycle", "captures", "replay_rejected", "p2_rejected",
        )
    }


def marker_changed(before, after):
    return {
        "sequence_changed": before["sequence"] != after["sequence"],
        "generation_changed":
            before["generation"] != after["generation"],
        "load_generation_changed":
            before["expected_generation"] != after["expected_generation"],
        "loads_delta": after["loads"] - before["loads"],
        "before": before,
        "after": after,
    }


def player_key(players):
    player = players[0]
    return {
        "weapon_slot": player["weapon_slot"],
        "weapon_id": player["weapon_id"],
        "clip": player["clip"],
        "reserve": player["reserve"],
    }


def ammo_delta(before, after):
    return {
        field: before[field] - after[field]
        for field in ("clip", "reserve")
    }


def set_button(mask, frames=1):
    native.command("press", buttons=65535 ^ mask, frames=frames)


def hold_scope():
    native.command("set_input", buttons="0xfdff")


def release_all():
    native.command("set_input", buttons="0xffff")
    native.command("set_input", port=2, buttons="0xffff")
    native.command("openxr_input_override", clear=1)


def fire_trigger(collector, frames=6):
    native.command("openxr_input_override", right_trigger=1000)
    collector.wait(frames)
    native.command("openxr_input_override", clear=1)
    collector.wait(4)


def start_capture(settle_frames=12, p1_only=True):
    aim.shot_command("stop")
    aim.shot_command("start-p1" if p1_only else "start")
    if settle_frames:
        native.frames(settle_frames)
    filters = {
        name: shot.FILTERS[name]
        for name in ("constructor", "basis", "motion", "damage")
    } | {"rng": families.RNG_FILTER}
    native.command("wtrace_range", lo="0x80100000", hi="0x80180000")
    native.command("wtrace_clear")
    collector = shot.TraceCollector(filters)
    return collector


def shot_rows():
    status = aim.shot_command("status")
    if status["overflow"]:
        raise RuntimeError("Shot sample ring overflow")
    return [
        aim.shot_command(f"read={index}")
        for index in range(status["count"])
    ]


def damage_rows(collector, players):
    address = native.p2_health_address(players[1])
    return [
        row for row in collector.entries("damage")
        if (int(row["addr"], 0) & 0x1FFFFFFF) == address
        and int(row["old"], 0) > int(row["new"], 0)
    ]


def linked_damage(rows, traces):
    shot_addresses = {
        families.number(row["shot"]) for row in rows
    }
    return [
        row for row in traces
        if families.number(row["s1"]) in shot_addresses
        and families.number(row["a2"]) in shot_addresses
    ]


def stop_capture(collector):
    aim.shot_command("stop")
    native.command("wtrace_range", lo="0", hi="0")
    collector.collect()
    return shot_rows()


def convert_tracked(rows, collector, request, weapon_id,
                    allow_native_fallback=False):
    converted = []
    for index, sample in enumerate(rows):
        if sample["weapon"] != weapon_id:
            raise RuntimeError(
                f"ID {weapon_id}: unexpected shot weapon {sample['weapon']}"
            )
        if sample["type"] != families.EXPECTED_FAMILIES[weapon_id]:
            raise RuntimeError(
                f"ID {weapon_id}: unexpected native shot type "
                f"0x{sample['type']:X}"
            )
        if not sample["family_eligible"]:
            if allow_native_fallback:
                converted.append({
                    "native_fallback": True,
                    "fallback_reason": "family-guard-rejected-scoped-shot",
                    "marker": marker(f"shot={index}"),
                })
                continue
            raise RuntimeError(f"ID {weapon_id}: family guard rejected shot")
        snapshot = marker(f"shot={index}")
        if not snapshot["valid"] or snapshot["id"] != weapon_id:
            if sample["aimed"]:
                raise RuntimeError(
                    f"ID {weapon_id}: aimed shot lacks a marker"
                )
            converted.append({
                "native_fallback": True,
                "marker": snapshot,
            })
            continue
        origin = aim.verify_marker_conversion(
            sample, snapshot, request["camera"]
        )
        motion = shot.first_motion(
            collector.entries("motion"), sample["shot"]
        )
        motion_start = [
            shot.signed(row["old"]) for row in motion["stores"]
        ]
        aimed_delta = (
            np.asarray(sample["aimed_position"], dtype=float) / 65536.0
            - np.asarray(motion_start, dtype=float) / 65536.0
        )
        origin_error = float(np.linalg.norm(aimed_delta))
        axis_cosine = float(np.dot(
            origin["world_axis"], motion["direction"]
        ))
        if not -1.0 <= axis_cosine <= 1.0:
            raise RuntimeError(
                f"ID {weapon_id}: invalid normalized axis cosine"
            )
        minimum_axis_cosine = (
            aim.NON_SHOTGUN_AXIS_COSINE
            if weapon_id != 4 else aim.THROWN_AXIS_COSINE
        )
        if weapon_id != 4 and axis_cosine < minimum_axis_cosine:
            raise RuntimeError(
                f"ID {weapon_id}: motion axis disagrees with marker"
            )
        if origin_error > MOTION_TOLERANCE_WORLD_UNITS:
            raise RuntimeError(
                f"ID {weapon_id}: first motion does not start at origin"
            )
        miss = None if request["target_world"] is None else \
            aim.target_ray_miss(
                np.asarray(sample["aimed_position"], dtype=float) / 65536.0,
                origin["world_axis"], request["target_world"],
            )
        converted.append({
            "native_fallback": False,
            "marker": snapshot,
            "marker_generation": snapshot["generation"],
            "marker_sequence": snapshot["sequence"],
            "marker_age_cycles": snapshot["shot_cycle"] - snapshot["cycle"],
            "origin_error_world_units": origin["origin_error_world_units"],
            "first_motion_origin_error_world_units": origin_error,
            "axis_cosine": axis_cosine,
            "target_ray_miss_world_units": miss,
            "first_motion": motion,
        })
    if any(
        not row.get("native_fallback") and
        row["target_ray_miss_world_units"] is not None and
        row["target_ray_miss_world_units"] > IMPACT_RAY_TOLERANCE_WORLD_UNITS
        for row in converted
    ):
        raise RuntimeError(f"ID {weapon_id}: tracked target-ray miss")
    return converted


def summarize_action(
    name, before_marker, after_marker, before_players, after_players,
    collector, rows, *, expected_shots, weapon_id, request=None, mode="native",
    allow_empty_ammo=False, allow_state_change=False,
    allow_native_fallback=False,
):
    damage = damage_rows(collector, before_players)
    linked = linked_damage(rows, damage)
    summary = {
        "name": name,
        "mode": mode,
        "before_player": player_key(before_players),
        "after_player": player_key(after_players),
        "ammo_delta": ammo_delta(
            player_key(before_players), player_key(after_players)
        ),
        "shot_count": len(rows),
        "shot_types": [row["type"] for row in rows],
        "shots": rows,
        "native_damage": damage,
        "linked_damage": linked,
        "marker_change": marker_changed(before_marker, after_marker),
        "trace_counts": {
            key: len(value) for key, value in collector.rows.items()
        },
    }
    if mode == "tracked" and rows:
        if request is None:
            raise RuntimeError(f"{name}: missing tracked aim request")
        summary["converted"] = convert_tracked(
            rows, collector, request, weapon_id,
            allow_native_fallback=allow_native_fallback,
        )
    if expected_shots:
        if len(rows) != expected_shots:
            raise RuntimeError(
                f"{name}: got {len(rows)} shots, expected {expected_shots}"
            )
        if not any(summary["ammo_delta"].values()):
            raise RuntimeError(f"{name}: no native ammunition consumption")
        if any(
            row["type"] != families.EXPECTED_FAMILIES[weapon_id]
            for row in rows
        ):
            raise RuntimeError(f"{name}: unexpected native shot type")
    else:
        if rows:
            raise RuntimeError(f"{name}: empty/interrupted state fired")
        if any(summary["ammo_delta"].values()) and not (
                allow_empty_ammo or allow_state_change):
            raise RuntimeError(f"{name}: empty/interrupted state consumed ammo")
        if damage:
            raise RuntimeError(f"{name}: empty/interrupted state damaged P2")
    return summary


def resample_request(weapon_id, mode):
    if mode != "tracked":
        return None
    players = native.players()
    status = marker("status")
    if not status["valid"] or status["id"] != weapon_id:
        raise RuntimeError(
            f"ID {weapon_id}: fresh animated marker unavailable"
        )
    return aim.marker_aim(
        players, aim.calibrations()[weapon_id], status
    )


def upward_request():
    camera = aim.shot_command("camera")
    if not camera["valid"]:
        raise RuntimeError("No canonical camera for recoil follow-up")
    quaternion = poses.quat_axis(0, -75)
    poses.set_hand_pair(
        grip=(0.15, 0.0, -0.5),
        aim_q=quaternion.tolist(),
        grip_q=quaternion.tolist(),
    )
    return {"camera": camera, "target_world": None}


def fire_without_capture(shots=1, frames=6):
    for index in range(shots):
        native.command("openxr_input_override", right_trigger=1000)
        native.frames(frames)
        native.command("openxr_input_override", clear=1)
        native.frames(20)
    native.frames(30)


def wait_for_reload(before, maximum=120):
    set_button(RELOAD, frames=6)
    for frame in range(maximum):
        native.frames(1)
        current = player_key(native.players())
        if current["clip"] > before["clip"] and current["reserve"] < \
                before["reserve"]:
            return {"frames": frame + 1, "before": before, "after": current}
    raise RuntimeError("Native reload did not refill the clip")


def case_reload_tail(mode):
    families.prepare_weapon(1, 0)
    native.frames(8)
    fire_without_capture()
    empty = player_key(native.players())
    reload = wait_for_reload(empty)
    native.frames(2)
    interlock_marker = marker_state()
    interlock_players = native.players()
    interlock_collector = start_capture()
    fire_trigger(interlock_collector, 6)
    interlock_collector.wait(30)
    interlock_after_marker = marker_state()
    interlock_after_players = native.players()
    interlock_rows = stop_capture(interlock_collector)
    interlock = summarize_action(
        "reload-interlock", interlock_marker, interlock_after_marker,
        interlock_players, interlock_after_players, interlock_collector,
        interlock_rows, expected_shots=0, weapon_id=0, mode=mode,
    )
    interlock["before_marker"] = interlock_marker
    interlock["after_marker"] = interlock_after_marker
    native.frames(24)
    before_marker = marker_state()
    before_players = native.players()
    collector = start_capture()
    request = resample_request(0, mode)
    if request is not None:
        native.frames(8)
    fire_trigger(collector, 6)
    collector.wait(90)
    after_marker = marker_state()
    after_players = native.players()
    rows = stop_capture(collector)
    release_all()
    result = summarize_action(
        "reload-tail", before_marker, after_marker, before_players,
        after_players, collector, rows, expected_shots=1, weapon_id=0,
        request=request, mode=mode,
    )
    result["reload"] = reload
    result["interlock_control"] = interlock
    result["before_marker"] = before_marker
    result["after_marker"] = after_marker
    return result


def case_empty_fire(mode):
    families.prepare_weapon(1, 0)
    native.frames(8)
    fire_without_capture(shots=7, frames=8)
    players = native.players()
    if players[0]["weapon_id"] != 0 or players[0]["clip"] != 1:
        raise RuntimeError(
            "P38 fixture did not reach the final round: "
            f"{players[0]}"
        )
    before_marker = marker_state()
    collector = start_capture()
    request = resample_request(0, mode)
    if request is not None:
        native.frames(8)
    native.command("openxr_input_override", right_trigger=1000)
    final_count = None
    for _ in range(16):
        collector.wait(1)
        if player_key(native.players())["clip"] == 0:
            final_count = len(shot_rows())
            break
    if final_count is None:
        raise RuntimeError("P38 final round did not empty the clip")
    native.command("openxr_input_override", clear=1)
    native.command("openxr_input_override", right_trigger=1000)
    collector.wait(30)
    native.command("openxr_input_override", clear=1)
    collector.wait(90)
    after_marker = marker_state()
    after_players = native.players()
    rows = stop_capture(collector)
    release_all()
    if final_count != 1 or len(rows) != final_count:
        raise RuntimeError(
            "Empty trigger constructed additional shots: "
            f"{final_count}/{len(rows)}"
        )
    damage = linked_damage(rows, damage_rows(collector, players))
    result = {
        "name": "empty-fire",
        "mode": mode,
        "before_player": player_key(players),
        "after_player": player_key(after_players),
        "ammo_delta": {"clip": 0, "reserve": 0},
        "shot_count": 0,
        "shot_types": [],
        "shots": [],
        "native_damage": [],
        "linked_damage": [],
        "marker_change": marker_changed(before_marker, after_marker),
        "trace_counts": {
            key: len(value) for key, value in collector.rows.items()
        },
        "final_shot": {
            "count": len(rows),
            "rows": rows,
            "linked_damage": damage,
        },
        "reload_after_empty": player_key(after_players),
    }
    if mode == "tracked":
        result["final_shot"]["converted"] = convert_tracked(
            rows, collector, request, 0
        )
    result["before_marker"] = before_marker
    result["after_marker"] = after_marker
    return result


def case_switch_during_reload(mode):
    families.prepare_weapon(1, 0)
    native.frames(8)
    fire_without_capture()
    before_marker = marker_state()
    before_players = native.players()
    collector = start_capture()
    set_button(RELOAD, frames=6)
    native.frames(8)
    set_button(SWITCH, frames=8)
    collector.wait(120)
    after_marker = marker_state()
    after_players = native.players()
    rows = stop_capture(collector)
    release_all()
    result = summarize_action(
        "switch-during-reload", before_marker, after_marker,
        before_players, after_players, collector, rows,
        expected_shots=0, weapon_id=0, mode=mode,
        allow_state_change=True,
    )
    if result["after_player"]["weapon_slot"] == \
            result["before_player"]["weapon_slot"]:
        raise RuntimeError("Switch during reload did not change weapon slot")
    result["before_marker"] = before_marker
    result["after_marker"] = after_marker
    native.frames(90)
    return result


def case_scoped_fire(mode):
    families.prepare_weapon(3, 2)
    native.frames(8)
    before_marker = marker_state()
    before_players = native.players()
    collector = start_capture(p1_only=False)
    request = resample_request(5, mode)
    hold_scope()
    collector.wait(60)
    scoped_marker = marker_state()
    native.command("press", buttons=65535 ^ (FIRE | R2), frames=60)
    scoped_fire_players = native.players()
    collector.wait(720)
    after_marker = marker_state()
    after_players = native.players()
    rows = stop_capture(collector)
    release_all()
    result = summarize_action(
        "scoped-fire", before_marker, after_marker, before_players,
        after_players, collector, rows, expected_shots=2, weapon_id=5,
        request=request, mode=mode, allow_native_fallback=True,
    )
    result["scoped_marker"] = scoped_marker
    result["before_marker"] = before_marker
    result["after_marker"] = after_marker
    return result


def case_recoil_followup(mode):
    families.prepare_weapon(1, 0)
    native.frames(8)
    native.command("openxr_input_override", rx=1000)
    native.frames(24)
    native.command("openxr_input_override", clear=1)
    native.frames(4)
    first_collector = start_capture()
    if mode == "tracked":
        upward_request()
    native.frames(8)
    fire_trigger(first_collector, 6)
    first_collector.wait(4)
    stop_capture(first_collector)
    before_marker = marker_state()
    before_players = native.players()
    collector = start_capture(settle_frames=1)
    request = upward_request() if mode == "tracked" else None
    if request is not None:
        native.frames(1)
    fire_trigger(collector, 6)
    collector.wait(90)
    after_marker = marker_state()
    after_players = native.players()
    rows = stop_capture(collector)
    release_all()
    result = summarize_action(
        "recoil-followup", before_marker, after_marker, before_players,
        after_players, collector, rows, expected_shots=1, weapon_id=0,
        request=request, mode=mode,
    )
    result["before_marker"] = before_marker
    result["after_marker"] = after_marker
    return result


def case_load_recovery(mode):
    families.prepare_weapon(1, 0)
    native.frames(8)
    fire_without_capture()
    collector = start_capture()
    before_marker = marker_state()
    native.load(1)
    comparison.release_load_override()
    native.frames(12)
    after_load_marker = marker_state()
    request = resample_request(0, mode)
    if request is not None:
        native.frames(8)
    before_players = native.players()
    fire_trigger(collector, 6)
    collector.wait(90)
    after_marker = marker_state()
    after_players = native.players()
    rows = stop_capture(collector)
    release_all()
    result = summarize_action(
        "load-recovery", before_marker, after_marker, before_players,
        after_players, collector, rows, expected_shots=1, weapon_id=0,
        request=request, mode=mode,
    )
    result["after_load_marker"] = after_load_marker
    result["load_change"] = marker_changed(
        before_marker, after_load_marker
    )
    if mode == "tracked":
        change = result["load_change"]
        if not change["load_generation_changed"] or change["loads_delta"] < 1:
            raise RuntimeError("Load recovery did not advance marker generation")
    result["before_marker"] = before_marker
    result["after_marker"] = after_marker
    return result


CASES = {
    "reload-tail": case_reload_tail,
    "empty-fire": case_empty_fire,
    "switch-during-reload": case_switch_during_reload,
    "scoped-fire": case_scoped_fire,
    "recoil-followup": case_recoil_followup,
    "load-recovery": case_load_recovery,
}


def source_hashes():
    return {
        name: digest(ROOT / name)
        for name in (
            "vr/underground/vr_diagnostic.c",
            "vr/underground/shot.h",
            "vr/underground/weapon.c",
            "vr/underground/weapon.h",
            "vr/underground/weapon_markers.h",
            "vr/underground/weapon_marker_groups.inc",
            "vr/tools/probe_weapon_combat_states.py",
            "vr/tools/probe_weapon_aim.py",
            "vr/tools/probe_shot_families.py",
            "vr/tools/probe_native_shot.py",
        )
    }


def run_mode(mode, directory, selected_cases, *, case_functions=None,
             extra_sources=()):
    registry = CASES if case_functions is None else case_functions
    if any(name not in registry for name in selected_cases):
        raise ValueError("Unknown combat-state case")
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic TCP port 4372 occupied")
    out = directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    saves = out / "saves/openbios"
    saves.mkdir(parents=True)
    source_hashes_value = {}
    for slot in families.CYCLES:
        for suffix in ("pst", "thumb"):
            source = ROOT / (
                f"saves/openbios/state_8001F844_slot{slot:02}.{suffix}"
            )
            shutil.copyfile(source, saves / source.name)
            source_hashes_value[
                str(source.relative_to(ROOT))
            ] = native.digest(source)
    preferences = comparison.hash_existing(comparison.preference_paths())
    executable = (
        ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    )
    receipt = {
        "schema": 1,
        "kind": "W5.4 combat-state mode",
        "mode": mode,
        "complete": False,
        "headset_used": False,
        "fixture": "copied root MP slots 1-4; fresh load per state case",
        "executable_sha256": native.digest(executable),
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "build": comparison.build_configuration(
            ROOT / "build-release/CMakeCache.txt"
        ),
        "sources": source_hashes(),
        "source_saves": source_hashes_value,
        "preferences": preferences,
        "cases": [],
    }
    receipt["sources"].update({name: digest(ROOT / name)
                               for name in extra_sources})
    env = comparison.environment("native", True)
    env["PSX_INTERNAL_RESOLUTION"] = "native"
    # These controls exercise the measured native pad. Keep the MP controller
    # remap out of the path so its offline synthetic input cannot replace it.
    env["MOHU_VR_MP_CONTROL"] = "0"
    if mode == "tracked":
        env.update(
            PSX_VR_WEAPON_POSE="1",
            MOHU_VR_WEAPON_CALIBRATED="1",
            MOHU_VR_WEAPON_AIM="1",
        )
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
            if mode == "tracked":
                marker("start")
            for name in selected_cases:
                case = registry[name](mode)
                receipt["cases"].append(case)
                save(out / "receipt.json", receipt)
                print(
                    f"{mode} {name}: shots={case['shot_count']} "
                    f"damage={len(case['linked_damage'])}",
                    flush=True,
                )
            receipt["counters"] = native.command("mod_counters")
            receipt["render"] = aim.shot_command("render")
            receipt["render_pass"] = native.command("render_pass_stats")
            receipt["stereo"] = native.command("stereo_stats")
            if receipt["render_pass"]["verify_mismatch"] or \
                    receipt["render_pass"]["vram_leaks"] or \
                    receipt["stereo"]["refused"]:
                raise RuntimeError("Stereo/render rollback regression")
            receipt["complete"] = True
        except BaseException as error:
            receipt["error"] = str(error)
            raise
        finally:
            try:
                release_all()
                native.command("openxr_hands_override", clear=1)
                native.command(
                    "mod_cmd", name="mohu.vr.stereo.pose", args="reset"
                )
                native.command(
                    "mod_cmd", name="mohu.vr.weapon.pose", args="reset"
                )
                if mode == "tracked":
                    marker("stop")
                native.command("wtrace_range", lo="0", hi="0")
                aim.shot_command("stop")
                native.command("quit")
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
                for path, value in source_hashes_value.items()
            )
            receipt["preferences_unchanged"] = all(
                native.digest(Path(path)) == value
                for path, value in preferences.items()
            )
            receipt["remaining_game_pids"] = native.game_pids()
            save(out / "receipt.json", receipt)
    if not (
        receipt["complete"]
        and receipt["exit_code"] == 0
        and receipt["source_saves_unchanged"]
        and receipt["preferences_unchanged"]
        and not receipt["remaining_game_pids"]
    ):
        raise RuntimeError(f"{mode} combat-state probe did not close cleanly")
    return receipt


def validate_preservation_dependency():
    receipt = load(PRESERVATION)
    if not receipt.get("complete") or {
        row["id"] for row in receipt["weapons"]
    } != EXPECTED_IDS:
        raise RuntimeError("W5.3e all-ID preservation dependency is incomplete")
    for row in receipt["weapons"]:
        damage = row["linked_damage_events"]
        if row["id"] in DAMAGE_EXPECTED and damage < 1:
            raise RuntimeError(
                f"W5.3e damage gate missing ID {row['id']}"
            )
        if row["id"] not in DAMAGE_EXPECTED and damage:
            raise RuntimeError(
                f"W5.3e unexpected damage for ID {row['id']}"
            )
    family = load(FAMILIES)
    types = {
        row["id"]: int(row["family"], 16)
        for row in family["weapons"]
    }
    if types != families.EXPECTED_FAMILIES:
        raise RuntimeError("W5.3 family types disagree with the shot contract")
    return {
        "preservation": {
            "path": str(PRESERVATION.relative_to(ROOT)),
            "sha256": digest(PRESERVATION),
        },
        "families": {
            "path": str(FAMILIES.relative_to(ROOT)),
            "sha256": digest(FAMILIES),
        },
    }


def compare_pair(native_receipt, tracked_receipt):
    if native_receipt["mode"] != "native" or \
            tracked_receipt["mode"] != "tracked":
        raise RuntimeError("Combat-state receipts have the wrong modes")
    if native_receipt["source_saves"] != tracked_receipt["source_saves"] or \
            native_receipt["preferences"] != tracked_receipt["preferences"]:
        raise RuntimeError("Paired combat-state fixtures differ")
    if native_receipt["executable_sha256"] != \
            tracked_receipt["executable_sha256"]:
        raise RuntimeError("Paired combat-state executables differ")
    native_cases = {
        row["name"]: row for row in native_receipt["cases"]
    }
    tracked_cases = {
        row["name"]: row for row in tracked_receipt["cases"]
    }
    if set(native_cases) != set(CASES) or set(tracked_cases) != set(CASES):
        raise RuntimeError("Combat-state pair is not complete")
    rows = []
    problems = []
    for name in CASES:
        left = native_cases[name]
        right = tracked_cases[name]
        if left["shot_count"] != right["shot_count"]:
            problems.append(
                f"{name}: shot count {left['shot_count']}/"
                f"{right['shot_count']}"
            )
        if left["shot_types"] != right["shot_types"]:
            problems.append(f"{name}: shot types differ")
        if left["ammo_delta"] != right["ammo_delta"]:
            problems.append(f"{name}: ammo deltas differ")
        if bool(left["linked_damage"]) != bool(right["linked_damage"]):
            problems.append(f"{name}: linked damage presence differs")
        if left["shot_count"]:
            if left["linked_damage"] and not right["linked_damage"]:
                problems.append(f"{name}: tracked shot has no linked damage")
            if any(
                not row.get("native_fallback") and
                row.get("origin_error_world_units", math.inf) >
                1.0 / 65536.0
                for row in right["converted"]
            ):
                problems.append(f"{name}: converted origin differs")
        if name == "load-recovery" and \
                not right["load_change"]["load_generation_changed"]:
            problems.append(f"{name}: tracked marker load did not change")
        rows.append({
            "name": name,
            "shots": right["shot_count"],
            "types": right["shot_types"],
            "ammo_delta": right["ammo_delta"],
            "native_damage": bool(left["linked_damage"]),
            "tracked_damage": bool(right["linked_damage"]),
            "marker_sequence_changed":
                right["marker_change"]["sequence_changed"],
            "tracked_converted": right.get("converted", []),
        })
    return {
        "complete": not problems,
        "cases": rows,
        "problems": problems,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--mode", choices=("native", "tracked", "both"),
                        default="both")
    parser.add_argument("--cases", nargs="+", choices=tuple(CASES))
    args = parser.parse_args()
    selected = args.cases or list(CASES)
    if args.proof and (
        args.mode != "both" or set(selected) != set(CASES)
    ):
        parser.error("--proof requires both modes and every combat-state case")
    out = args.directory.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    dependencies = validate_preservation_dependency()
    receipts = {}
    modes = ("native", "tracked") if args.mode == "both" else (args.mode,)
    for mode in modes:
        receipts[mode] = run_mode(mode, out / mode, selected)
    if args.mode != "both":
        print(f"PASS: {args.mode} combat-state focused controls")
        return
    comparison_result = compare_pair(
        receipts["native"], receipts["tracked"]
    )
    save(out / "receipt.json", {
        "schema": 1,
        "kind": "W5.4 combat-state paired native/tracked controls",
        "complete": comparison_result["complete"],
        "headset_used": False,
        "dependencies": dependencies,
        "native_receipt": "native/receipt.json",
        "native_receipt_sha256": digest(out / "native/receipt.json"),
        "tracked_receipt": "tracked/receipt.json",
        "tracked_receipt_sha256": digest(out / "tracked/receipt.json"),
        "executable_sha256": receipts["native"]["executable_sha256"],
        "revision": receipts["native"]["revision"],
        "build": receipts["native"]["build"],
        "comparison": comparison_result,
        "limits": [
            "The all-13 damage and shot-type gate is the linked W5.3e "
            "desktop receipt, not a repeated 13-ID pair.",
            "Synthetic copied MP fixtures only; live NPC/SP and operator "
            "barrel-to-impact acceptance remain open.",
            "The scoped-fire control may remain native when the hidden scope "
            "model cannot expose a fresh animated marker.",
        ],
    })
    if not comparison_result["complete"]:
        raise RuntimeError("; ".join(comparison_result["problems"]))
    if args.proof:
        receipt = load(out / "receipt.json")
        receipt["raw_receipt"] = str(
            (out / "receipt.json").relative_to(ROOT)
        )
        receipt = families.seal_receipt(out / "receipt.json", receipt)
        save(args.proof, receipt)
    print("PASS: paired combat-state controls", flush=True)


if __name__ == "__main__":
    main()
