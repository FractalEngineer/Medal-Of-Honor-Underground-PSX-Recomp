import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_shared_geometry_policy import compiler

ROOT = Path(__file__).resolve().parents[2]


class RenderedMuzzleTests(unittest.TestCase):
    def test_quantized_affine_eye_composition_and_pair_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            exe = Path(temporary) / ("muzzle.exe" if os.name == "nt" else "muzzle")
            subprocess.run([
                compiler(), "-std=c11", "-Wall", "-Wextra", "-Werror",
                f"-I{ROOT / 'vr/underground'}",
                f"-I{ROOT / 'psxrecomp/runtime/include'}",
                str(ROOT / "vr/tests/test_rendered_muzzle.c"),
                "-lm", "-o", str(exe),
            ], check=True)
            self.assertIn("PASS:", subprocess.check_output([str(exe)], text=True))


if __name__ == "__main__":
    unittest.main()
