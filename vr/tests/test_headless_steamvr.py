from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "vr"))

import headless_steamvr  # noqa: E402


class NullSettingsTests(unittest.TestCase):
    def test_forces_null_driver_and_preserves_unrelated_settings(self) -> None:
        original = {
            "custom": {"keep": 7},
            "steamvr": {"installID": "fixture", "forcedDriver": "oculus"},
            "dashboard": {"lastAccessedExternalOverlayKey": "fixture"},
        }
        configured = json.loads(
            headless_steamvr.null_settings(json.dumps(original))
        )
        self.assertEqual(configured["custom"], {"keep": 7})
        self.assertEqual(configured["steamvr"]["installID"], "fixture")
        self.assertEqual(configured["steamvr"]["forcedDriver"], "null")
        self.assertFalse(configured["steamvr"]["activateMultipleDrivers"])
        self.assertTrue(configured["driver_null"]["enable"])
        self.assertFalse(configured["dashboard"]["enableDashboard"])

    def test_rejects_non_object_settings(self) -> None:
        with self.assertRaises(ValueError):
            headless_steamvr.null_settings("[]")


if __name__ == "__main__":
    unittest.main()
