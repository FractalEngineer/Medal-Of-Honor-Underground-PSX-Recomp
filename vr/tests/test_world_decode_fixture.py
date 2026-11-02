"""Compile and run the strict static-world decoder fixture."""

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


class WorldDecodeFixtureTest(unittest.TestCase):
    def test_decoder_fixture_passes(self) -> None:
        fixture = ROOT / "vr/tests/test_world_decode.c"
        source = ROOT / "vr/underground/world_decode.c"
        include = ROOT / "psxrecomp/runtime/include"
        self.assertTrue(fixture.is_file())
        self.assertTrue(source.is_file())
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / (
                "world_decode_test.exe" if os.name == "nt" else "world_decode_test"
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
                    "-o",
                    str(executable),
                ],
                check=True,
            )
            result = subprocess.run(
                [str(executable)], check=True, capture_output=True, text=True
            )
            self.assertIn(
                "static-world leaf/strip decode, winding, masks, bounds, "
                "record material/CLUT/texpage mapping, named rejections, "
                "visible-entry parity path and snapshot cache",
                result.stdout,
            )


if __name__ == "__main__":
    unittest.main()
