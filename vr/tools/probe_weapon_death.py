"""W5.4 P1 death/native respawn supplement; no health, ammo or save edits.

Reuse the existing owned-process combat runner and copied MP slot 1. P2's
native automatic fire kills P1, a P1 fire press respawns without constructing a shot,
then a later shot checks fresh animated-marker conversion. This supplement
links the accepted six-case matrix rather than repeating it.
"""
from __future__ import annotations

import argparse
from functools import partial
import math
from pathlib import Path
import struct

import probe_weapon_combat_states as combat


ROOT = combat.ROOT
BASE = ROOT / "vr/proof/weapon-combat-states-receipt.json"
CASE = "death-respawn"
SOURCES = (
    "vr/tools/probe_weapon_death.py",
    "vr/tests/test_weapon_death.py",
)


def snapshot():
    players = combat.native.players()
    return {
        "players": players,
        "angles": [struct.unpack("<3i", combat.native.read(
            int(p["actor"], 16) + 0x23C, 12)) for p in players],
        "marker": combat.marker("status"),
    }


def raw_trace(collector):
    return {
        "entries": {name: collector.entries(name)
                    for name in collector.rows},
        "windows": collector.windows,
    }


def lethal_write(entry, entries, victim, shots):
    number = combat.families.number
    if number(entry["addr"]) != (victim + 0x108) & 0x1FFFFFFF or \
            number(entry["pc"]) != 0x8004EB80 or \
            combat.shot.signed(entry["old"]) <= 0 or \
            combat.shot.signed(entry["new"]) > 0 or \
            number(entry["s1"]) not in shots or \
            number(entry["a2"]) != number(entry["s1"]):
        return False
    if number(entry["new"]) == 0:
        return True
    # Damage subtracts signed Q16 health first. A negative result is clamped
    # by the native death branch, rather than written as zero at the subtract.
    return any(number(clamp["pc"]) == 0x8004EC44 and
               clamp["frame"] == entry["frame"] and
               clamp["seq"] > entry["seq"] and
               number(clamp["addr"]) == number(entry["addr"]) and
               number(clamp["old"]) == number(entry["new"]) and
               number(clamp["new"]) == 0 and
               number(clamp["s1"]) == number(entry["s1"]) and
               number(clamp["a2"]) == number(entry["s1"])
               for clamp in entries)


def validate_transition(row, mode):
    """Recheck facts, including negative controls, before accepting receipts."""
    problems = []
    before, dead, respawn = (
        row[name] for name in ("before", "dead", "respawn")
    )
    p1 = int(before["players"][0]["actor"], 16)
    p2 = int(before["players"][1]["actor"], 16)
    attacks = row["attack_shots"]
    if not attacks or len(attacks) > 56 or any(
        shot["owner"] != p2 or shot["weapon"] not in (1, 17) or
        shot["type"] != 0x13F7 or not shot["code_valid"] or
        shot["family_eligible"] or shot["aimed"] or
        any(shot["aimed_position"]) for shot in attacks
    ):
        problems.append("P2 attack was missing, overridden or misidentified")
    attack_addresses = {shot["shot"] for shot in attacks}
    lethal = [entry for entry in row["lethal_damage"] if
              lethal_write(entry, row["lethal_damage"], p1, attack_addresses)]
    if not lethal or dead["players"][0]["health_raw"] != 0:
        problems.append("No exact linked native P1 death")
    if row["respawn_trigger_shots"]:
        problems.append("Respawn fire constructed an extra P1 shot")
    if respawn["players"][0]["health_raw"] != \
            before["players"][0]["health_raw"] or \
            respawn["players"][0]["position"] == \
            before["players"][0]["position"]:
        problems.append("Native respawn did not restore health and relocate P1")
    for phase in (dead, respawn):
        if int(phase["players"][0]["actor"], 16) != p1 or \
                phase["players"][0]["input"] != \
                before["players"][0]["input"]:
            problems.append("Fixture changed P1 actor/input ownership")
        if combat.player_key(phase["players"]) != \
                combat.player_key(before["players"]):
            problems.append("Death/respawn trigger changed P1 ammunition/loadout")
    if mode == "tracked":
        if not before["marker"]["valid"] or dead["marker"]["valid"]:
            problems.append("Alive/dead marker validity control failed")
        if not respawn["marker"]["valid"] or \
                respawn["marker"]["sequence"] <= dead["marker"]["sequence"]:
            problems.append("Respawn did not publish a fresh animated marker")
        if any(phase["marker"]["expected_generation"] !=
               before["marker"]["expected_generation"]
               for phase in (dead, respawn)):
            problems.append("A save load replaced the native respawn")
    recovered = row["recovered"]
    if recovered["shot_count"] != 1 or recovered["shot_types"] != [0x13F6] or \
            recovered["ammo_delta"] != {"clip": 1, "reserve": 0}:
        problems.append("Recovered shot did not preserve native type/ammo")
    if mode == "tracked":
        converted = recovered.get("converted", [])
        if len(converted) != 1 or any(
            item.get("native_fallback") or
            not all(math.isfinite(item[field]) for field in (
                "origin_error_world_units", "first_motion_origin_error_world_units",
                "axis_cosine")) or
            item["origin_error_world_units"] > 1.0 / 65536.0 or
            item["first_motion_origin_error_world_units"] >
            combat.MOTION_TOLERANCE_WORLD_UNITS or
            item["axis_cosine"] < combat.aim.NON_SHOTGUN_AXIS_COSINE or
            item["axis_cosine"] > 1.0 or
            item["marker"]["cycle"] <= dead["marker"]["shot_cycle"] or
            item["marker_generation"] !=
            before["marker"]["expected_generation"]
            for item in converted
        ):
            problems.append("Recovered shot lacked fresh converted markers/motion")
    return problems


def exercise(mode, *, directory):
    combat.families.prepare_weapon(1, 0)
    combat.native.command("press", port=2, buttons=65535 ^ combat.SWITCH,
                          frames=8)
    combat.native.frames(110)
    turn = []
    for _ in range(64):
        players = combat.native.players()
        yaw = struct.unpack("<i", combat.native.read(
            int(players[1]["actor"], 16) + 0x240, 4))[0] / 65536.0
        turn.append({"yaw": yaw})
        if yaw <= 35:
            break
        combat.native.command("press", port=2, buttons=65535 ^ 0x80,
                              frames=4)
        combat.native.frames(12)
    before = snapshot()
    combat.save(directory / "fixture-checkpoint.json", {
        "before": before, "native_turn_samples": turn, "yaw": yaw})
    if before["players"][0]["weapon_id"] != 0 or \
            before["players"][1]["weapon_id"] != 1 or not 20 <= yaw <= 35:
        raise RuntimeError("Native automatic-fire death fixture differs")
    collector = combat.start_capture(p1_only=False)
    attack_timeline = []
    for _ in range(40):
        current = combat.native.players()
        if current[0]["health_raw"] == 0:
            break
        if current[1]["weapon_id"] not in (1, 17) or \
                len(combat.shot_rows()) >= 54:
            break
        if current[1]["clip"] == 0:
            combat.native.command("press", port=2,
                                  buttons=65535 ^ combat.SWITCH, frames=8)
            collector.wait(110)
            continue
        combat.native.command("set_input", port=2, buttons=65535 ^ combat.FIRE)
        collector.wait(8)
        combat.native.command("set_input", port=2, buttons=65535)
        # Settling recoil retains useful native aim across the ammunition
        # supply. Continuous fire raises it out of P1's native hit volume.
        collector.wait(90)
        attack_timeline.append(combat.native.players())
        combat.save(directory / "attack-progress.json", {
            "players": attack_timeline, "shots": combat.shot_rows()})
    dead = snapshot()
    combat.save(directory / "attack-checkpoint.json", {
        "before": before, "dead": dead,
        "shots": combat.shot_rows(), "trace": raw_trace(collector),
    })
    if dead["players"][0]["health_raw"] != 0:
        raise RuntimeError("Native P2 bursts did not kill P1; retain the trace")
    respawn_attempts = []
    for _ in range(8):
        combat.fire_trigger(collector, 6)
        collector.wait(30)
        respawn = snapshot()
        respawn_attempts.append(respawn)
        if respawn["players"][0]["health_raw"] > 0:
            break
        # Fire is ignored during the native death timer. A later distinct
        # press requests respawn. Health restoration must be observed before
        # a subsequent input can be called a recovered shot.
        collector.wait(60)
    attacks_and_trigger = combat.stop_capture(collector)
    p1, p2 = [int(player["actor"], 16) for player in before["players"]]
    lethal = [entry for entry in collector.entries("damage") if
              combat.families.number(entry["addr"]) ==
              combat.native.p2_health_address(before["players"][0])]
    result = {
        "name": CASE,
        "mode": mode,
        "before": before,
        "p2_yaw_native_units": yaw,
        "native_turn_samples": turn,
        "attack_timeline": attack_timeline,
        "dead": dead,
        "respawn": respawn,
        "respawn_attempts": respawn_attempts,
        "attack_shots": [row for row in attacks_and_trigger
                         if row["owner"] == p2],
        "respawn_trigger_shots": [row for row in attacks_and_trigger
                                  if row["owner"] == p1],
        "lethal_damage": lethal,
        "transition_trace": raw_trace(collector),
    }
    # Save partial evidence even when the next recovery stage fails.
    combat.save(directory / "death-transition.json", result)
    if respawn["players"][0]["health_raw"] == 0:
        raise RuntimeError("Native respawn did not complete within eight presses")
    # Native respawn has a firing interlock after health/model restoration.
    # Drain its tail before testing a separately pressed recovered shot.
    combat.native.frames(120)
    before_players = combat.native.players()
    before_marker = combat.marker_state()
    recovery = combat.start_capture()
    request = combat.upward_request() if mode == "tracked" else None
    combat.native.frames(8)
    combat.fire_trigger(recovery, 6)
    recovery.wait(90)
    after_marker = combat.marker_state()
    after_players = combat.native.players()
    rows = combat.stop_capture(recovery)
    combat.release_all()
    combat.save(directory / "recovery-checkpoint.json", {
        "before": before_players, "after": after_players, "shots": rows,
        "request": request, "trace": raw_trace(recovery),
        "marker_before": before_marker, "marker_after": after_marker,
    })
    result["recovered"] = combat.summarize_action(
        "respawn-recovered-shot", before_marker, after_marker,
        before_players, after_players, recovery, rows,
        expected_shots=1, weapon_id=0, request=request, mode=mode,
    )
    result["recovery_trace"] = raw_trace(recovery)
    result["shot_count"] = result["recovered"]["shot_count"]
    result["linked_damage"] = result["recovered"]["linked_damage"]
    result["problems"] = validate_transition(result, mode)
    combat.save(directory / "death-transition.json", result)
    if result["problems"]:
        raise RuntimeError("; ".join(result["problems"]))
    return result


def compare_pair(left, right):
    for key in ("executable_sha256", "source_saves", "preferences", "sources"):
        if left[key] != right[key]:
            raise RuntimeError(f"Death pair differs: {key}")
    problems = []
    for receipt, mode in ((left, "native"), (right, "tracked")):
        if receipt["mode"] != mode or not receipt.get("complete") or \
                receipt.get("exit_code") != 0 or \
                not receipt.get("source_saves_unchanged") or \
                not receipt.get("preferences_unchanged") or \
                receipt.get("remaining_game_pids"):
            problems.append(f"{mode}: incomplete/unclean owned run")
        if len(receipt["cases"]) != 1 or \
                receipt["cases"][0]["name"] != CASE:
            raise RuntimeError("Death supplement requires its exact state case")
        problems += [f"{mode}: {problem}" for problem in
                     validate_transition(receipt["cases"][0], mode)]
    return {"complete": not problems, "problems": problems}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--mode", choices=("native", "tracked", "both"),
                        default="both")
    args = parser.parse_args()
    if args.proof and args.mode != "both":
        parser.error("A death supplement proof requires both modes")
    if not combat.load(BASE).get("complete"):
        raise RuntimeError("Accepted six-case combat matrix is incomplete")
    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    receipts = {}
    for mode in (("native", "tracked") if args.mode == "both"
                 else (args.mode,)):
        receipts[mode] = combat.run_mode(
            mode, out / mode, [CASE], case_functions={
                CASE: partial(exercise, directory=out / mode)},
            extra_sources=SOURCES,
        )
    if args.mode != "both":
        print(f"PASS: {args.mode} P1 death/native respawn", flush=True)
        return
    result = compare_pair(receipts["native"], receipts["tracked"])
    proof = {
        "schema": 1, "kind": "W5.4 P1 death/native respawn supplement",
        "complete": result["complete"], "headset_used": False,
        "base_matrix": {"path": str(BASE.relative_to(ROOT)),
                        "sha256": combat.digest(BASE)},
        "comparison": result,
        "executable_sha256": receipts["native"]["executable_sha256"],
        "sources": receipts["native"]["sources"],
        "modes": {mode: {
            "receipt": f"{mode}/receipt.json",
            "sha256": combat.digest(out / mode / "receipt.json"),
            "case": {key: value for key, value in receipt["cases"][0].items()
                     if key not in ("transition_trace", "recovery_trace")},
            "render_pass": receipt["render_pass"],
            "stereo": receipt["stereo"],
        } for mode, receipt in receipts.items()},
        "limits": [
            "Copied MP slot 1, P1 P38, native P2 MP40/StG44 bursts only.",
            "Recovered tracked shot aims upward; no recovered damage claim.",
            "Physical barrel alignment and live NPC/SP remain open.",
        ],
        "raw_receipt": str((out / "receipt.json").relative_to(ROOT)),
    }
    sealed = combat.families.seal_receipt(out / "receipt.json", proof)
    if not result["complete"]:
        raise RuntimeError("; ".join(result["problems"]))
    if args.proof:
        combat.save(args.proof, sealed)
    print("PASS: paired P1 death/native respawn and recovered shot", flush=True)


if __name__ == "__main__":
    main()
