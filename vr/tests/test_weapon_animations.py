import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import probe_weapon_animations as probe


def frame(points, *, sequence=1, control=None):
    return {
        "frame": sequence,
        "sequence": sequence,
        "id": 0,
        "animated": points,
        "native_gte": control or ["00000000"] * 8,
        "animated_sha256": str(sequence),
    }


class WeaponAnimationTests(unittest.TestCase):
    def setUp(self):
        self.groups = {
            "grip": [[13, 0], [13, 1]],
            "muzzle": [[11, 0], [11, 1]],
        }
        self.baseline = frame({
            (13, 0): [0, 0, 0, 0],
            (13, 1): [0, 2, 0, 0],
            (11, 0): [0, 0, 100, 0],
            (11, 1): [0, 2, 100, 0],
        })

    def test_translation_keeps_fixed_marker_contract_rigid(self):
        moved = {
            key: [value[0] + 20, value[1], value[2], value[3]]
            for key, value in self.baseline["animated"].items()
        }
        result = probe.analyze(frame(moved, sequence=2), self.baseline,
                               self.groups)
        self.assertTrue(result["animated"])
        self.assertEqual(result["marker_contract"], "rigid")
        self.assertGreater(result["animated_vertex_motion"], 0)

    def test_deforming_muzzle_requires_a_moving_marker(self):
        moved = {
            key: list(value) for key, value in self.baseline["animated"].items()
        }
        moved[(11, 0)][2] += 10
        moved[(11, 1)][2] += 10
        result = probe.analyze(frame(moved, sequence=2), self.baseline,
                               self.groups)
        self.assertEqual(result["marker_contract"],
                         "moving-marker-required")
        self.assertGreater(result["distance_delta"], 1)

    def test_player_effect_reports_native_ammo_and_slot_changes(self):
        before = {"weapon_slot": 0, "weapon_id": 0, "clip": 8, "reserve": 20}
        after = {"weapon_slot": 1, "weapon_id": 1, "clip": 32, "reserve": 60}
        result = probe.player_effect(before, after)
        self.assertEqual(result["changed"]["weapon_slot"], [0, 1])
        self.assertEqual(result["changed"]["clip"], [8, 32])
        self.assertEqual(result["changed"]["reserve"], [20, 60])

    def test_marker_groups_cover_all_profiles(self):
        groups = probe.marker_groups()
        self.assertEqual(set(groups), set(probe.topology.PROFILES))
        self.assertIn([11, 24], groups[0]["muzzle"])
        self.assertIn([11, 28], groups[0]["muzzle"])

    def test_first_occurrence_subset_is_deterministic(self):
        rows = probe.first_occurrences({0, 5, 17})
        self.assertEqual({row[2] for row in rows}, {0, 5, 17})
        self.assertEqual(len(rows), 3)


if __name__ == "__main__":
    unittest.main()
