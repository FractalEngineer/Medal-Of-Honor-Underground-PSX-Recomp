"""Validate observed native research behavior; never infer a finished mouse mod."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

UPDATE, LOOK, ADJUST, INTEGRATE, BASIS = 0x800892C8, 0x8008F984, 0x8008F9BC, 0x80078FBC, 0x80076C28
CAMERA, REFRESHED, SKIPPED = 0x8004A744, 0xFF000010, 0xFF000014
RAY, CONSTRUCT, PREPARED, PREPARE_SKIPPED = 0x8008D81C, 0x8004815C, 0xFF000018, 0xFF00001C


def signed(value):
    return value if value < 0x80000000 else value - 0x100000000


def verify(receipt):
    for key in ("collection_complete", "source_saves_unchanged", "preferences_unchanged"):
        assert receipt[key], key
    assert receipt["exit_code"] == 0 and not receipt["remaining_game_pids"]
    summary = dict(schema=1, binary_sha256=receipt["binary_sha256"],
                   research_source_sha256=receipt.get("research_source_sha256"),
                   rejected_commands=len(receipt.get("rejected_commands", [])),
                   direct_target_test=receipt.get("research_direct", False),
                   early_ray_test=receipt.get("research_refresh", False),
                   camera_preparation_test=receipt.get("research_prepare", False),
                   production_mouse_mod_verified=False, cases=[])
    for case in receipt["research"]:
        request, observation = case["request"], case["observation"]
        rows = observation["rows"]
        assert rows and not observation["dropped"] and not observation["rejected"]
        cycles = [r[1] + (r[2] << 32) for r in rows]
        assert cycles == sorted(cycles), case["name"] + ": cycle order"
        entries = [r for r in rows if r[0] == UPDATE]
        assert len(entries) == request["updates"], case["name"] + ": update count"
        assert all(r[5] == 0x800784DC and r[4] == int(case["before"]["player"], 16) for r in entries)
        assert len({r[3] for r in entries}) == request["updates"]
        for entry in entries:
            group = [r for r in rows if r[3] == entry[3] and not (r[0] & 1)]
            observed = [r[0] for r in group if r[0] in (UPDATE, LOOK, ADJUST, INTEGRATE)]
            assert observed == [UPDATE, LOOK, ADJUST, INTEGRATE], (case["name"], observed)
            if request["site"] == CAMERA:
                assert group[0][0] == CAMERA, (case["name"], "camera before player")
            if summary["early_ray_test"]:
                sites = [r[0] for r in group]
                assert sites.count(REFRESHED) == sites.count(SKIPPED) == 1
                assert sites.index(UPDATE) < sites.index(REFRESHED) < sites.index(LOOK) < sites.index(SKIPPED) < sites.index(ADJUST)
                assert all(sites.index(REFRESHED) < i for i, r in enumerate(group) if r[0] == BASIS and r[6] != r[4])
            if receipt.get("research_schema", 0) >= 2:
                sites = [r[0] for r in group]
                assert sites.count(RAY) == 1 and REFRESHED not in sites and SKIPPED not in sites
                assert sites.index(LOOK) < sites.index(RAY) < sites.index(ADJUST)
                assert all(sites.index(ADJUST) < i for i, r in enumerate(group) if r[0] == CONSTRUCT)
                assert all(r[31:33] == [0, 0] for r in group)
        if receipt.get("research_schema", 0) >= 2:
            calls = [r for r in rows if r[0] == RAY]
            assert [r[33] for r in calls] == list(range(1, request["updates"] + 1))
            prepared = [r for r in rows if r[0] == PREPARED]
            skipped = [r for r in rows if r[0] == PREPARE_SKIPPED]
            expected = bool(summary["camera_preparation_test"] and request["site"] == CAMERA and request["pitch"])
            assert len(prepared) == len(skipped) == expected
            if expected:
                assert prepared[0][3] == skipped[0][3] == entries[0][3]
                assert skipped[0][5] == 0x8008F9C8
                assert rows.index(prepared[0]) < rows.index(entries[0]) < rows.index(skipped[0])
        mutations = [(i, r) for i, r in enumerate(rows) if r[0] & 1]
        assert len(mutations) == observation["applied"] == bool(request["yaw"] or request["pitch"])
        for i, row in mutations:
            previous = rows[i - 1]
            assert row[0] == request["site"] | 1 and previous[0] == request["site"]
            for index, delta in ((8, request["pitch"]), (9, request["yaw"]),
                                 (12, request["pitch"]), (13, request["yaw"])):
                assert signed(row[index]) - signed(previous[index]) == delta * 65536
            assert row[10:12] == previous[10:12] and row[14:20] == previous[14:20]
        result_delta = [a - b for a, b in zip(case["after"]["rotation_q16"], case["before"]["rotation_q16"])]
        # Native integration may canonicalize a yaw crossing one revolution.
        result_delta[1] = (result_delta[1] + (2048 << 16)) % (4096 << 16) - (2048 << 16)
        if summary["direct_target_test"]:
            assert result_delta == [request["pitch"] * 65536, request["yaw"] * 65536, 0], (case["name"], result_delta)
        result = dict(name=case["name"], updates=len(entries), writes=observation["applied"],
                      final_pitch_delta_units=result_delta[0] / 65536,
                      final_yaw_delta_units=result_delta[1] / 65536)
        if receipt.get("research_schema", 0) >= 2:
            result.update(original_ray_calls=len(calls), camera_preparations=len(prepared),
                          matching_preparation_skips=len(skipped))
        if case["name"].startswith("fire_"):
            shots = [r for r in rows if r[0] == BASIS and r[6] != r[4]]
            assert shots and case["after"]["clip"] < case["before"]["clip"]
            assert all(r[5] == 0x8004860C for r in shots)
            if receipt.get("research_schema", 0) >= 2:
                constructors = [r for r in rows if r[0] == CONSTRUCT]
                assert len(constructors) == len(shots) and all(r[5] == 0x800482CC for r in constructors)
                assert [(r[3], r[6]) for r in constructors] == [(r[3], r[6]) for r in shots]
                result["first_shot_same_update"] = shots[0][3] == entries[0][3]
                if receipt.get("synchronized_fire") or receipt.get("gated_fire"):
                    assert result["first_shot_same_update"], case["name"] + ": fire scheduling"
                if receipt.get("gated_fire"):
                    assert entries[0][34] & 0xFFFF == 0x40 and entries[0][35] & 0xFFFF == 0, case["name"] + ": fresh native press"
                if len(shots[0]) >= 40:
                    assert all(r[36:39] == r[25:28] and r[39] == 0x13F6 for r in shots), case["name"] + ": native muzzle origin"
            result["shots"] = [dict(update=r[3], pitch_units=signed(r[8]) / 65536,
                                    yaw_units=signed(r[9]) / 65536,
                                    player_pitch_units=signed(r[22]) / 65536,
                                    player_yaw_units=signed(r[23]) / 65536) for r in shots]
        summary["cases"].append(result)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = verify(json.loads(args.receipt.read_text(encoding="utf-8")))
    result["raw_receipt_sha256"] = hashlib.sha256(args.receipt.read_bytes()).hexdigest()
    encoded = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.write_text(encoded, encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
