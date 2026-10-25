import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "vr" / "run_vr.ps1"


class LauncherDefaultsTest(unittest.TestCase):
    def test_normal_boot_is_the_default(self) -> None:
        script = LAUNCHER.read_text(encoding="utf-8")
        match = re.search(r"\[int\]\$Slot\s*=\s*(-?\d+)", script)
        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(1)), -1)
        self.assertIn("PSX_LOAD_SLOT = $(if ($Slot -ge 0)", script)

    def test_flat_launch_clears_weapon_experiment_activation(self) -> None:
        script = (ROOT / "RunFlat.bat").read_text(encoding="utf-8")
        cleared = re.search(r"for %%V in \((.*?)\) do set", script, re.S)
        self.assertIsNotNone(cleared)
        variables = set(cleared.group(1).split())
        self.assertTrue({"PSX_VR_WEAPON_POSE", "MOHU_VR_WEAPON_FLAT_PROBE",
                         "MOHU_VR_MP_CONTROL",
                         "MOHU_VR_WEAPON_SYNTHETIC_X",
                         "MOHU_VR_WEAPON_SYNTHETIC_YAW_MDEG"} <= variables)


if __name__ == "__main__":
    unittest.main()
