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

    def test_playable_launch_does_not_auto_select_interpreter(self) -> None:
        script = LAUNCHER.read_text(encoding="utf-8")
        block = re.search(r"if \(-not \$GameConfig\) \{(.*?)\n\}", script, re.S)
        self.assertIsNotNone(block)
        self.assertIn("$GameConfig = Join-Path $repoRoot 'game.toml'", block.group(1))
        self.assertNotIn('game-interp.toml', block.group(1))

    def test_flat_and_vr_share_explicit_user_saves(self) -> None:
        script = LAUNCHER.read_text(encoding='utf-8')
        flat = (ROOT/'RunFlat.bat').read_text(encoding='utf-8')
        self.assertIn("$MemcardDirectory = Join-Path $repoRoot 'saves'", script)
        self.assertIn('--memcard-dir "%~dp0saves"', flat)
        self.assertNotIn('$diagnosticSaves', script)
        self.assertNotIn('analysis\\vr-baseline\\saves', script)
        self.assertIn('Headless diagnostics require -MemcardDirectory', script)
        self.assertNotIn('$ExecutableName', script)

    def test_automated_sources_are_fixtures_not_personal_saves(self) -> None:
        # Prevent a future cleanup/launcher change from turning operator saves
        # into implicit test input or a writable diagnostic destination again.
        for name in ('inspect_weapon_sets.py','probe_p38_headset.py','profile_sp_production.py',
                     'probe_sp_issues.py','probe_sp_performance.py','run_headset_batch.py'):
            text = (ROOT/'vr/tools'/name).read_text(encoding='utf-8')
            with self.subTest(tool=name):
                self.assertNotIn('analysis/vr-baseline/saves', text)
                self.assertNotRegex(text, r'''ROOT\s*/\s*f?["']saves/openbios''')

    def test_flat_launch_clears_weapon_experiment_activation(self) -> None:
        script = (ROOT / "RunFlat.bat").read_text(encoding="utf-8")
        cleared = re.search(r"for %%V in \((.*?)\) do set", script, re.S)
        self.assertIsNotNone(cleared)
        variables = set(cleared.group(1).split())
        self.assertTrue({"PSX_VR_WEAPON_POSE", "MOHU_VR_WEAPON_FLAT_PROBE",
                         "MOHU_VR_MP_CONTROL", "MOHU_VR_MP_FRUSTUM",
                         "MOHU_VR_MP_FRUSTUM_CAPTURE",
                         "MOHU_VR_P38_CALIBRATED", "MOHU_VR_P38_AIM",
                         "MOHU_VR_WEAPON_GUN_ONLY",
                         "MOHU_VR_WEAPON_CALIBRATED",
                         "MOHU_VR_WEAPON_AIM",
                         "MOHU_VR_WEAPON_SYNTHETIC_X",
                         "MOHU_VR_WEAPON_SYNTHETIC_YAW_MDEG"} <= variables)


if __name__ == "__main__":
    unittest.main()
