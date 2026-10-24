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


if __name__ == "__main__":
    unittest.main()
