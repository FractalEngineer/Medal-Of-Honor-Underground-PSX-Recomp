import copy
from functools import partial
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import probe_rendered_muzzle as probe


class RenderedMuzzleProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        proof = probe.combat.load(probe.ROOT / "vr/proof/weapon-rendered-muzzle-receipt.json")
        cls.result = proof["cases"][0]
        cls.cases = cls.result["cases"]
        # These retained controls predate authored-axis defaults. Validate them
        # against their recorded calibration, never against today's candidate.
        old = probe.combat.load(probe.ROOT / "vr/proof/weapon-provisional-calibrations-receipt.json")
        calibration = next(row['calibration'] for row in old['weapons'] if row['id'] == 0)
        cls.verify = staticmethod(partial(probe.verify_eye, calibration=calibration))

    def row(self):
        return copy.deepcopy(self.cases[0]["eyes"][0])

    def test_retained_both_eye_controls_have_independent_numeric_agreement(self):
        for case in self.cases:
            for row in case["eyes"]:
                self.verify(copy.deepcopy(row), row["hands"])

    def test_wrong_source_identity_is_rejected(self):
        row = self.row()
        row["hash"] ^= 1
        with self.assertRaisesRegex(RuntimeError, "ownership/source"):
            self.verify(row, row["hands"])

    def test_idle_tip_cannot_replace_copied_animation(self):
        idle = self.cases[0]["eyes"][0]["model_points"]
        moving = next(case["eyes"][0] for case in self.cases
                      if case["eyes"][0]["model_points"] != idle)
        row = copy.deepcopy(moving)
        row["model_points"] = idle
        with self.assertRaisesRegex(RuntimeError, "model_points"):
            self.verify(row, row["hands"])

    def test_applying_eye_translation_twice_is_rejected(self):
        row = self.row()
        row["eye_points"][3] += row["view_translation"][0]
        with self.assertRaisesRegex(RuntimeError, "eye_points"):
            self.verify(row, row["hands"])

    def test_wrong_w5_same_epoch_origin_is_rejected(self):
        row = self.row()
        row["w5_position"][0] += 65536
        with self.assertRaisesRegex(RuntimeError, "W5 helper"):
            self.verify(row, row["hands"])

    def test_false_canonical_epoch_equality_is_rejected(self):
        row = self.row()
        row["vertices"][0][5] += 1
        row["canonical_equal"] = 1
        with self.assertRaisesRegex(RuntimeError, "epoch equality"):
            self.verify(row, row["hands"])

    def test_hand_fixed_ray_survives_native_recoil_and_reload(self):
        baseline = self.cases[0]["eyes"]
        for case in self.cases:
            if case["name"] not in ("recoil", "reload"):
                continue
            for expected, actual in zip(baseline, case["eyes"]):
                self.assertEqual(actual["hand_fixed"], 1)
                self.assertNotEqual(actual["model_points"], expected["model_points"])
                self.assertEqual(actual["aim_base"], expected["aim_base"])
                self.assertEqual(actual["aim_axis"], expected["aim_axis"])

    def test_actual_shot_uses_the_same_hand_fixed_ray(self):
        shot, = self.result["native_shots"]
        baseline = self.cases[0]["eyes"][0]
        self.assertEqual(shot["hand_fixed"], 1)
        self.assertEqual(shot["aimed"], 1)
        self.assertEqual(shot["aimed_position"], baseline["w5_position"])
        self.assertEqual(shot["aimed_angles"], baseline["w5_angles"])

    def test_animated_origin_cannot_substitute_for_hand_fixed_ray(self):
        case = next(case for case in self.cases if case["name"] == "recoil")
        row = copy.deepcopy(case["eyes"][0])
        row["aim_base"] = row["base_points"][3:6]
        with self.assertRaisesRegex(RuntimeError, "Hand-fixed"):
            self.verify(row, row["hands"])


if __name__ == "__main__":
    unittest.main()
