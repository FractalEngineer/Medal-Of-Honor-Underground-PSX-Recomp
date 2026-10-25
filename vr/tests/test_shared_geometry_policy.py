"""Compile the shared VR geometry test through this title's framework copy."""

from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def compiler() -> str:
    cache = ROOT / "build-release" / "CMakeCache.txt"
    if cache.is_file():
        match = re.search(
            r"^CMAKE_C_COMPILER(?::[^=]+)?=(.+)$",
            cache.read_text(encoding="utf-8", errors="replace"),
            re.MULTILINE,
        )
        if match and Path(match.group(1).strip()).is_file():
            return match.group(1).strip()
    for name in ("clang", "gcc", "cc"):
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError("No C compiler found")


class SharedGeometryPolicyTest(unittest.TestCase):
    def test_framework_accepts_both_title_policies(self) -> None:
        source = ROOT / "psxrecomp/runtime/src/vr_geometry_math.c"
        fixture = ROOT / "psxrecomp/runtime/tests/test_vr_geometry_math.c"
        include = ROOT / "psxrecomp/runtime/include"
        self.assertTrue(source.is_file())
        self.assertTrue(fixture.is_file())
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / (
                "vr_geometry_test.exe"
                if os.name == "nt"
                else "vr_geometry_test"
            )
            subprocess.run(
                [
                    compiler(),
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    f"-I{include}",
                    str(fixture),
                    str(source),
                    "-lm",
                    "-o",
                    str(executable),
                ],
                check=True,
            )
            result = subprocess.run(
                [str(executable)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn(
                "shared VR inverse, conservative visibility and slab geometry",
                result.stdout,
            )


if __name__ == "__main__":
    unittest.main()
