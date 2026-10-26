"""Reject incomplete or behavior-changing paired weapon evidence."""

import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_weapon_preservation as preserve


def lifetime(shot=0x80100000, phase="held"):
    return {
        "shot": shot,
        "native_history": [0, 0, 0],
        "motion_steps": 2,
        "birth_sequence": 100,
        "trigger_phase": phase,
        "post_basis_origin_stores": [],
        "basis_to_motion_origin_shift": [0.0, 0.0, 0.0],
    }


def weapon(weapon_id=0, count=1):
    motions = [
        {"direction": [0.0, 0.0, 1.0],
         "delta_world": [0.0, 0.0, 600.0]}
        for _ in range(count)
    ]
    shots = [
        {"shot": 0x80100000 + index,
         "type": 0x13F6,
         "aimed": True}
        for index in range(count)
    ]
    return {
        "id": weapon_id,
        "name": "fixture",
        "slot": 1,
        "switches": 0,
        "shots": shots,
        "motions": motions,
        "lifetimes": [
            lifetime(shot["shot"]) for shot in shots
        ],
        "converted": [
            {"world_axis": [0.0, 0.0, 1.0]} for _ in shots
        ],
        "impacts": [
            {"axis_cosine": 1.0, "target_ray_miss_world_units": 0.0}
            for _ in shots
        ],
        "before": [{"clip": 8, "reserve": 20, "weapon_slot": 0}],
        "after": [{"clip": 7, "reserve": 20, "weapon_slot": 0}],
        "native_damage": [{"old": "0x00200000", "new": "0x001D0000"}],
        "rng": {
            "calls": 3,
            "events": [
                {"seq": 90 + index, "old": f"0x{index:08X}",
                 "new": f"0x{index + 1:08X}"}
                for index in range(3)
            ],
        },
    }


def receipt(row):
    return {
        "complete": True,
        "fixture": "copied fixture",
        "source_saves": {"slot": "hash"},
        "preferences": {"settings": "hash"},
        "executable_sha256": "exe",
        "revision": "revision",
        "build": {},
        "weapons": [row],
    }


class WeaponPreservationTests(unittest.TestCase):
    def test_matching_pair_closes(self):
        native = weapon()
        tracked = weapon()
        result = preserve.compare_receipts(receipt(native), receipt(tracked))
        self.assertTrue(result["complete"], result["problems"])

    def test_rng_change_is_rejected(self):
        native = weapon(weapon_id=4, count=6)
        tracked = weapon(weapon_id=4, count=6)
        tracked["rng"]["calls"] += 1
        tracked["rng"]["events"].append(
            {"seq": 93, "old": "0x00000003", "new": "0x00000004"}
        )
        result = preserve.compare_receipts(receipt(native), receipt(tracked))
        self.assertFalse(result["complete"])
        self.assertTrue(any("RNG" in row["problem"]
                            for row in result["problems"]))

    def test_ammo_and_release_changes_are_rejected(self):
        native = weapon(count=2)
        tracked = weapon(count=2)
        tracked["lifetimes"][1]["trigger_phase"] = "released"
        tracked["after"][0]["clip"] = 6
        result = preserve.compare_receipts(receipt(native), receipt(tracked))
        messages = " ".join(row["problem"] for row in result["problems"])
        self.assertIn("release phase", messages)
        self.assertIn("ammunition", messages)

    def test_shotgun_pair_angle_tolerance(self):
        native = weapon(weapon_id=4, count=6)
        tracked = copy.deepcopy(native)
        for index, motion in enumerate(tracked["motions"]):
            angle = math.radians(index)
            motion["direction"] = [
                math.sin(angle), 0.0, math.cos(angle)
            ]
            native["motions"][index]["direction"] = [
                math.sin(angle * 0.5), 0.0, math.cos(angle * 0.5)
            ]
        result = preserve.compare_receipts(receipt(native), receipt(tracked))
        self.assertFalse(result["complete"])
        self.assertTrue(any(
            "pairwise angle" in row["problem"]
            for row in result["problems"]
        ))

    def test_impact_axis_must_match(self):
        native = weapon()
        tracked = weapon()
        tracked["impacts"][0]["axis_cosine"] = 0.99
        result = preserve.compare_receipts(receipt(native), receipt(tracked))
        self.assertTrue(any(
            "rendered-axis" in row["problem"]
            for row in result["problems"]
        ))


if __name__ == "__main__":
    unittest.main()
