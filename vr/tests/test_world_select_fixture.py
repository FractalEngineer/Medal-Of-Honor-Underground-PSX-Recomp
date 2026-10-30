"""Compile and run the conservative per-eye world selection fixture."""

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


class WorldSelectFixtureTest(unittest.TestCase):
    def test_selection_fixture_passes(self) -> None:
        fixture = ROOT / "vr/tests/test_world_select.c"
        sources = [
            ROOT / "vr/underground/world_select.c",
            ROOT / "vr/underground/world_decode.c",
            ROOT / "psxrecomp/runtime/src/vr_geometry_math.c",
        ]
        include = ROOT / "psxrecomp/runtime/include"
        for path in [fixture, *sources]:
            self.assertTrue(path.is_file(), path)
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / (
                "world_select_test.exe" if os.name == "nt" else "world_select_test"
            )
            subprocess.run(
                [
                    compiler(),
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    f"-I{include}",
                    f"-I{ROOT / 'vr/underground'}",
                    str(fixture),
                    *[str(source) for source in sources],
                    "-lm",
                    "-o",
                    str(executable),
                ],
                check=True,
            )
            result = subprocess.run(
                [str(executable)], check=True, capture_output=True, text=True
            )
            self.assertIn(
                "conservative per-eye world selection, far-plane policy, "
                "saturation, budget and argument guards",
                result.stdout,
            )


if __name__ == "__main__":
    unittest.main()
