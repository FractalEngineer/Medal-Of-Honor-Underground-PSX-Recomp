import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import probe_shot_families as probe


def sample(owner=0x80140000, weapon=1, shot_type=0x13F7):
    return {
        "owner": hex(owner),
        "shot": "0x801103C0",
        "argument": "0x801103C0",
        "weapon": weapon,
        "type": shot_type,
        "caller": "0x800488D8",
        "eligible": 0,
        "aimed": 0,
        "code_valid": 1,
        "camera_valid": 1,
    }


class ShotFamilyTests(unittest.TestCase):
    def test_summary_filters_other_owners_and_groups_family(self):
        rows = [sample(), sample(), sample(owner=0x80150000)]
        result = probe.summarize_samples(rows, 1, 0x80140000)
        self.assertEqual(result["owned_count"], 2)
        self.assertEqual(result["ignored_count"], 1)
        self.assertEqual(result["types"], [0x13F7])
        self.assertEqual(result["callers"], [0x800488D8])

    def test_summary_rejects_weapon_and_guard_mismatch(self):
        with self.assertRaises(RuntimeError):
            probe.summarize_samples([sample(weapon=0)], 1, 0x80140000)
        bad = sample()
        bad["code_valid"] = 0
        with self.assertRaises(RuntimeError):
            probe.summarize_samples([bad], 1, 0x80140000)
        stale_camera = sample()
        stale_camera["camera_valid"] = 0
        result = probe.summarize_samples(
            [stale_camera], 1, 0x80140000
        )
        self.assertEqual(result["camera_invalid_count"], 1)
        no_player = sample(owner=0x80150000)
        with self.assertRaises(RuntimeError):
            probe.summarize_samples([no_player], 1, 0x80140000)

    def test_first_occurrences_cover_every_weapon_once(self):
        rows = probe.first_occurrences()
        self.assertEqual(len(rows), len(probe.native.WEAPONS))
        self.assertEqual(
            {row[2] for row in rows}, set(probe.native.WEAPONS)
        )

    def test_expected_families_cover_profiles(self):
        self.assertEqual(
            set(probe.EXPECTED_FAMILIES), set(probe.native.WEAPONS)
        )
        self.assertEqual(probe.EXPECTED_FAMILIES[13], 0x13F1)
        self.assertEqual(probe.EXPECTED_FAMILIES[4], 0x13F7)

    def test_special_controls_leave_ordinary_fire_short(self):
        self.assertGreater(
            probe.fire_control(15)["release_frames"],
            probe.fire_control(0)["release_frames"],
        )
        self.assertGreater(
            probe.fire_control(5)["hold_frames"],
            probe.fire_control(0)["hold_frames"],
        )


if __name__ == "__main__":
    unittest.main()
