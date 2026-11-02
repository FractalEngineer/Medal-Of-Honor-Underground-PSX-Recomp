from __future__ import annotations

import json
import sys
import tempfile
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

    def test_capture_series_retains_blank_samples(self) -> None:
        class FakeCompositor:
            def __init__(self) -> None:
                self.calls = []

            def capture(self, destination, expected_pid, require_projection=True,
                        reject_blank=True):
                self.calls.append((destination, expected_pid, require_projection,
                                   reject_blank))
                destination.mkdir()
                return {
                    "images": [
                        {"kind": "application_layer",
                         "flat": len(self.calls) == 2}
                    ]
                }

        compositor = FakeCompositor()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "series"
            series = headless_steamvr.capture_series(
                compositor, destination, 4242, 2, 0, reject_blank=False
            )
            self.assertEqual(len(series["samples"]), 2)
            self.assertFalse(series["clean"])
            self.assertTrue((destination / "capture-series.json").is_file())
        self.assertEqual(len(compositor.calls), 2)
        self.assertEqual(compositor.calls[0][1], 4242)
        self.assertFalse(compositor.calls[0][3])

    def test_capture_series_require_clean_fails_after_writing_receipt(self) -> None:
        class FlatCompositor:
            def capture(self, destination, expected_pid, require_projection=True,
                        reject_blank=True):
                destination.mkdir()
                return {"images": [{"kind": "application_layer", "flat": True}]}

        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "series"
            with self.assertRaisesRegex(RuntimeError, "Flat/black"):
                headless_steamvr.capture_series(
                    FlatCompositor(), destination, 4242, 1, 0,
                    reject_blank=False, require_clean=True,
                )
            self.assertTrue((destination / "capture-series.json").is_file())


if __name__ == "__main__":
    unittest.main()
