import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import probe_weapon_aim as probe


class WeaponAimProbeTests(unittest.TestCase):
    def test_rotation_between_maps_source_to_target(self):
        source = np.array([0.2, -0.4, 1.0])
        target = np.array([-0.7, 0.3, 0.5])
        rotation = probe.rotation_between(source, target)
        mapped = rotation @ (source / np.linalg.norm(source))
        expected = target / np.linalg.norm(target)
        self.assertLess(float(np.max(np.abs(mapped - expected))), 1e-12)
        self.assertAlmostEqual(float(np.linalg.det(rotation)), 1.0, places=12)

    def test_psx_quaternion_preserves_vector_rotation(self):
        rotation = probe.rotation_between(
            np.array([0.0, 0.0, 1.0]),
            np.array([1.0, 0.0, 0.0]),
        )
        quaternion = probe.psx_hand_quaternion(rotation)
        restored = probe.poses.psx_rotation(quaternion)
        self.assertLess(float(np.max(np.abs(restored - rotation))), 1e-12)

    def test_spread_summary_keeps_native_variation(self):
        motions = [
            {"direction": [0.0, 0.0, 1.0],
             "delta_world": [0.0, 0.0, 100.0]},
            {"direction": [math.sin(math.radians(5.0)), 0.0,
                           math.cos(math.radians(5.0))],
             "delta_world": [0.0, 0.0, 120.0]},
        ]
        result = probe.spread_summary(motions)
        self.assertEqual(result["pellets"], 2)
        self.assertAlmostEqual(
            result["maximum_pair_angle_degrees"], 5.0, places=10
        )
        self.assertAlmostEqual(result["speed_range"], 20.0)

    def test_provisional_receipt_covers_measured_profiles(self):
        table = probe.calibrations()
        self.assertEqual(set(table), set(probe.native.WEAPONS))
        for calibration in table.values():
            self.assertGreater(calibration["model_units_per_metre"], 1.0)
            self.assertEqual(len(calibration["right"]), 3)
            self.assertEqual(len(calibration["forward"]), 3)


if __name__ == "__main__":
    unittest.main()
