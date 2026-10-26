import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "vr" / "tools"))
import derive_weapon_calibrations as calibration


class WeaponCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = json.loads(
            (ROOT / "vr/proof/weapon-provisional-calibrations-receipt.json")
            .read_text(encoding="utf-8")
        )

    def test_all_unique_ids_are_present(self):
        self.assertTrue(self.proof["complete"])
        self.assertEqual(
            {row["id"] for row in self.proof["weapons"]},
            set(calibration.NOMINAL_LENGTHS_M),
        )

    def test_p38_values_are_the_accepted_exact_profile(self):
        row = next(row for row in self.proof["weapons"] if row["id"] == 0)
        for key, expected in calibration.P38.items():
            actual = row["calibration"][key]
            if isinstance(expected, list):
                self.assertEqual(actual, expected)
            else:
                self.assertTrue(math.isclose(actual, expected, rel_tol=0, abs_tol=0))

    def test_every_axis_frame_is_orthonormal_and_muzzle_is_forward(self):
        for row in self.proof["weapons"]:
            calibration_row = row["calibration"]
            axes = np.asarray([
                calibration_row["right"],
                calibration_row["up"],
                calibration_row["forward"],
            ])
            self.assertLess(
                float(np.max(np.abs(axes @ axes.T - np.eye(3)))), 1e-9
            )
            projection = (
                np.asarray(calibration_row["muzzle"])
                - np.asarray(calibration_row["grip_pivot"])
            ) @ np.asarray(calibration_row["forward"])
            self.assertGreater(projection, 0)
            self.assertAlmostEqual(
                calibration_row["model_units_per_metre"],
                calibration_row["forward_span_units"]
                / calibration_row["reference_length_m"],
            )


if __name__ == "__main__":
    unittest.main()
