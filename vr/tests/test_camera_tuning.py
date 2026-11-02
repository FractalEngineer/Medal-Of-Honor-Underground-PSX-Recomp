import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "vr/tools"))
import tune_camera_offset


class CameraTuningTest(unittest.TestCase):
    def test_file_mode_reads_writes_and_preserves_absolute_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "camera-offset.txt"
            with mock.patch.dict(
                os.environ, {"MOHU_VR_CAMERA_TUNING_FILE": str(path)}
            ), mock.patch.object(
                tune_camera_offset.native,
                "command",
                side_effect=OSError("debug server unavailable"),
            ):
                self.assertEqual(
                    tune_camera_offset.read_live(),
                    {"right": 0.0, "up": 0.0, "forward": 0.0},
                )
                value = tune_camera_offset.apply_offsets({
                    "right": 0.01,
                    "up": -0.02,
                    "forward": 0.03,
                })
                self.assertEqual(value["up"], -0.02)
                self.assertEqual(
                    path.read_text(encoding="ascii").strip(),
                    "0.010000 -0.020000 0.030000",
                )
                self.assertEqual(
                    tune_camera_offset.read_live(),
                    {"right": 0.01, "up": -0.02, "forward": 0.03},
                )

    def test_file_mode_rejects_out_of_range_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "camera-offset.txt"
            path.write_text("0 2 0\n", encoding="ascii")
            with mock.patch.dict(
                os.environ, {"MOHU_VR_CAMERA_TUNING_FILE": str(path)}
            ), self.assertRaises(RuntimeError):
                tune_camera_offset.read_file()


if __name__ == "__main__":
    unittest.main()
