import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "vr/tools"))
import inspect_weapon_sets as tool


class P2DamageTraceTest(unittest.TestCase):
    def test_masks_the_guest_actor_address(self):
        self.assertEqual(
            tool.p2_health_address({"actor": "0x80145810"}),
            0x00145918,
        )

    def test_detects_damage_before_respawn_restores_health(self):
        trace = {
            "entries": [
                {"addr": "0x00145918", "old": "0x00200000",
                 "new": "0x00070000"},
                {"addr": "0x00145918", "old": "0x00000000",
                 "new": "0x00200000"},
            ]
        }
        self.assertTrue(
            tool.p2_damage_in_trace(trace, {"actor": "0x80145810"})
        )

    def test_rejects_self_damage_and_restore_only(self):
        trace = {
            "entries": [
                {"addr": "0x001484D8", "old": "0x00200000",
                 "new": "0x00000000"},
                {"addr": "0x00145918", "old": "0x00000000",
                 "new": "0x00200000"},
            ]
        }
        self.assertFalse(
            tool.p2_damage_in_trace(trace, {"actor": "0x80145810"})
        )


if __name__ == "__main__":
    unittest.main()
