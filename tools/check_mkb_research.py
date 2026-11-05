"""Validate observed native research behavior; never infer a finished mouse mod."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

UPDATE, LOOK, ADJUST, INTEGRATE, BASIS = 0x800892C8, 0x8008F984, 0x8008F9BC, 0x80078FBC, 0x80076C28


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
        mutations = [(i, r) for i, r in enumerate(rows) if r[0] & 1]
        assert len(mutations) == observation["applied"] == bool(request["site"])
        for i, row in mutations:
            previous = rows[i - 1]
            assert row[0] == request["site"] | 1 and previous[0] == request["site"]
            for index, delta in ((8, request["pitch"]), (9, request["yaw"]),
                                 (12, request["pitch"]), (13, request["yaw"])):
                assert signed(row[index]) - signed(previous[index]) == delta * 65536
            assert row[10:12] == previous[10:12] and row[14:20] == previous[14:20]
        result_delta = [a - b for a, b in zip(case["after"]["rotation_q16"], case["before"]["rotation_q16"])]
        if summary["direct_target_test"]:
            assert result_delta == [request["pitch"] * 65536, request["yaw"] * 65536, 0], (case["name"], result_delta)
        result = dict(name=case["name"], updates=len(entries), writes=observation["applied"],
                      final_pitch_delta_units=result_delta[0] / 65536,
                      final_yaw_delta_units=result_delta[1] / 65536)
        if case["name"].startswith("fire_"):
            shots = [r for r in rows if r[0] == BASIS and r[6] != r[4]]
            assert shots and case["after"]["clip"] < case["before"]["clip"]
            assert all(r[5] == 0x8004860C for r in shots)
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
