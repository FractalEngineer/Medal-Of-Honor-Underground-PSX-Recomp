import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import probe_weapon_combat_states as combat


def marker(sequence, generation=1):
    return {
        "enabled": 1,
        "valid": 1,
        "id": 0,
        "sequence": sequence,
        "generation": generation,
        "expected_generation": generation,
        "loads": generation - 1,
        "load_cycle": 0,
        "shot_cycle": 100,
        "cycle": 90,
        "captures": sequence,
        "replay_rejected": 0,
        "p2_rejected": 0,
    }


def action(name, *, shots=1, ammo=1, damage=True, generation=1):
    return {
        "name": name,
        "shot_count": shots,
        "shot_types": [0x13F6] * shots,
        "ammo_delta": {"clip": ammo, "reserve": 0},
        "linked_damage": [{"old": "0x20", "new": "0x10"}] if damage else [],
        "converted": [
            {"origin_error_world_units": 0.0} for _ in range(shots)
        ],
        "marker_change": {
            "sequence_changed": True,
            "generation_changed": False,
            "load_generation_changed":
                name == "load-recovery",
            "loads_delta": 1 if name == "load-recovery" else 0,
            "before": marker(1, generation),
            "after": marker(2, generation + (name == "load-recovery")),
        },
        "load_change": {
            "load_generation_changed":
                name == "load-recovery",
        },
    }


def receipt(mode):
    rows = []
    for name in combat.CASES:
        if name in ("empty-fire", "switch-during-reload"):
            rows.append(action(name, shots=0, ammo=0, damage=False))
        else:
            rows.append(action(name))
    return {
        "mode": mode,
        "source_saves": {"slot": "hash"},
        "preferences": {"settings": "hash"},
        "executable_sha256": "exe",
        "cases": rows,
    }


class CombatStateTests(unittest.TestCase):
    def test_complete_pair_passes(self):
        result = combat.compare_pair(receipt("native"), receipt("tracked"))
        self.assertTrue(result["complete"], result["problems"])

    def test_empty_state_shot_count_mismatch_is_rejected(self):
        native = receipt("native")
        tracked = receipt("tracked")
        next(
            row for row in tracked["cases"]
            if row["name"] == "empty-fire"
        )["shot_count"] = 1
        result = combat.compare_pair(native, tracked)
        self.assertFalse(result["complete"])
        self.assertTrue(any(
            "empty-fire" in problem for problem in result["problems"]
        ))

    def test_ammo_delta_mismatch_is_rejected(self):
        native = receipt("native")
        tracked = receipt("tracked")
        next(
            row for row in tracked["cases"]
            if row["name"] == "reload-tail"
        )["ammo_delta"]["clip"] = 0
        result = combat.compare_pair(native, tracked)
        self.assertFalse(result["complete"])
        self.assertTrue(any(
            "ammo" in problem for problem in result["problems"]
        ))

    def test_missing_load_generation_is_rejected(self):
        native = receipt("native")
        tracked = receipt("tracked")
        row = next(
            item for item in tracked["cases"]
            if item["name"] == "load-recovery"
        )
        row["load_change"]["load_generation_changed"] = False
        result = combat.compare_pair(native, tracked)
        self.assertFalse(result["complete"])
        self.assertTrue(any(
            "load" in problem for problem in result["problems"]
        ))

    def test_protected_damage_ids_are_explicit(self):
        self.assertEqual(combat.DAMAGE_EXPECTED, set(combat.native.WEAPONS) - {
            10, 15,
        })

    def test_published_proof_metrics_are_bounded(self):
        proof = combat.load(
            combat.ROOT / "vr/proof/weapon-combat-states-receipt.json"
        )
        self.assertTrue(proof["complete"])
        for case in proof["comparison"]["cases"]:
            for row in case["tracked_converted"]:
                if row.get("native_fallback"):
                    continue
                self.assertGreaterEqual(row["axis_cosine"], -1.0)
                self.assertLessEqual(row["axis_cosine"], 1.0)
                self.assertLessEqual(
                    row["origin_error_world_units"], 1.0 / 65536.0
                )
                self.assertLessEqual(
                    row["first_motion_origin_error_world_units"],
                    combat.MOTION_TOLERANCE_WORLD_UNITS,
                )


if __name__ == "__main__":
    unittest.main()
