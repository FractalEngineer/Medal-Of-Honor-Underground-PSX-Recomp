import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "vr/tools"))

import probe_sp_shot_origins as origins
import probe_sp_weapon_inventory as inventory


class SpWeaponParityToolsTest(unittest.TestCase):
    def test_native_family_and_counter_helpers(self) -> None:
        self.assertEqual(origins.shot_type(0), 0x13F6)
        self.assertEqual(origins.shot_type(13), 0x13F1)
        self.assertEqual(origins.shot_type(15), 0x13F3)
        self.assertEqual(
            inventory.counter_delta(
                {"mohu.vr.shot.sp.aimed": 4},
                {"mohu.vr.shot.sp.aimed": 7},
                "mohu.vr.shot.sp.aimed",
            ),
            3,
        )

    def test_position_groups_require_complete_same_frame_xyz(self) -> None:
        shot = 0x800D5A50
        entries = [
            {
                "seq": index + 1,
                "frame": 706,
                "addr": f"0x{((shot + origins.POSITION_OFFSET + axis * 4) & 0x1FFFFFFF):08X}",
                "old": f"0x{(100 + axis):08X}",
                "new": f"0x{(200 + axis):08X}",
                "pc": f"0x{origins.SP_MOTION_PCS[axis]:08X}",
            }
            for index, axis in enumerate(range(3))
        ]
        groups = origins.position_groups(entries, shot, 0)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["pc"], [
            f"0x{pc:08X}" for pc in origins.SP_MOTION_PCS
        ])
        self.assertTrue(groups[0]["moved"])

        groups = origins.position_groups(entries[:2], shot, 0)
        self.assertEqual(groups, [])
        # A release correction and first integration in the same frame must
        # remain distinct, rather than overwriting the earlier XYZ group.
        second = [dict(row, seq=row["seq"] + 3) for row in entries]
        groups = origins.position_groups(entries + second, shot, 0)
        self.assertEqual([row["sequence"] for row in groups], [[1, 2, 3], [4, 5, 6]])


if __name__ == "__main__":
    unittest.main()
