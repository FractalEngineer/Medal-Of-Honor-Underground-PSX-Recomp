#!/usr/bin/env python3
"""Compile and run the two title adapters against one host-only vector set."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_value(root: Path, *args: str) -> str | None:
    safe = f"safe.directory={root.as_posix()}"
    try:
        result = subprocess.run(
            ["git", "-c", safe, "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def default_compiler(underground_root: Path) -> str:
    explicit = os.environ.get("CC")
    if explicit:
        return explicit
    cache = underground_root / "build-release" / "CMakeCache.txt"
    if cache.is_file():
        match = re.search(
            r"^CMAKE_C_COMPILER(?::[^=]+)?=(.+)$",
            cache.read_text(encoding="utf-8", errors="replace"),
            re.MULTILINE,
        )
        if match:
            candidate = match.group(1).strip()
            if Path(candidate).is_file():
                return candidate
    for name in ("clang", "gcc", "cc"):
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit("no C compiler found; pass --cc or set CC")


def run(command: list[str], cwd: Path) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    with (cwd / "compile.log").open("a", encoding="utf-8") as log:
        log.write("$ " + " ".join(command) + "\n" + result.stdout)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}"
        )
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-root", required=True, type=Path)
    parser.add_argument("--underground-root", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--cc")
    args = parser.parse_args()

    underground = (
        args.underground_root.resolve()
        if args.underground_root
        else Path(__file__).resolve().parents[2]
    )
    reference = args.reference_root.resolve()
    output = args.out_dir.resolve()
    if output.exists():
        raise SystemExit(f"output directory must be fresh: {output}")

    required = {
        "underground fixtures": underground / "vr/tests/reference_parity_vectors.c",
        "Underground adapter": underground / "vr/tests/underground_parity_adapter.c",
        "reference adapter": reference / "vr/tests/reference_parity_adapter.c",
        "reference inverse": reference / "vr/moh_vr_aim.c",
        "shared geometry implementation": (
            underground / "psxrecomp/runtime/src/vr_geometry_math.c"
        ),
        "reference geometry implementation": (
            reference / "psxrecomp/runtime/src/vr_geometry_math.c"
        ),
        "reference framework": reference / "psxrecomp/runtime/include/mod_plugins.h",
        "Underground framework": underground / "psxrecomp/runtime/include/mod_plugins.h",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        raise SystemExit("missing parity inputs: " + ", ".join(missing))

    output.mkdir(parents=True)
    cc = args.cc or default_compiler(underground)
    common = [
        cc,
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-Wno-unused-function",
    ]
    fixture_object = output / "reference_parity_vectors.o"
    reference_object = output / "reference_parity_adapter.o"
    underground_object = output / "underground_parity_adapter.o"
    inverse_object = output / "reference_inverse.o"
    pose_object = output / "reference_pose_math.o"
    geometry_object = output / "vr_geometry_math.o"
    executable = output / (
        "reference_parity.exe" if os.name == "nt" else "reference_parity"
    )

    run(
        common
        + [
            f"-I{underground / 'vr/tests'}",
            "-c",
            str(underground / "vr/tests/reference_parity_vectors.c"),
            "-o",
            str(fixture_object),
        ],
        output,
    )
    run(
        common
        + [
            f"-I{underground / 'psxrecomp/runtime/include'}",
            "-c",
            str(underground / "psxrecomp/runtime/src/vr_geometry_math.c"),
            "-o",
            str(geometry_object),
        ],
        output,
    )
    run(
        common
        + [
            f"-I{underground / 'vr/tests'}",
            f"-I{underground / 'psxrecomp/runtime/include'}",
            "-c",
            str(underground / "vr/tests/underground_parity_adapter.c"),
            "-o",
            str(underground_object),
        ],
        output,
    )
    run(
        common
        + [
            f"-I{underground / 'vr/tests'}",
            f"-I{reference / 'vr'}",
            f"-I{reference / 'psxrecomp/runtime/include'}",
            "-c",
            str(reference / "vr/tests/reference_parity_adapter.c"),
            "-o",
            str(reference_object),
        ],
        output,
    )
    run(
        common
        + [
            f"-I{reference / 'vr'}",
            f"-I{reference / 'psxrecomp/runtime/include'}",
            "-c",
            str(reference / "vr/moh_vr_aim.c"),
            "-o",
            str(inverse_object),
        ],
        output,
    )
    run(
        common
        + [
            f"-I{reference / 'psxrecomp/runtime/include'}",
            "-c",
            str(reference / "psxrecomp/runtime/src/vr_pose_math.c"),
            "-o",
            str(pose_object),
        ],
        output,
    )
    run(
        [
            cc,
            str(fixture_object),
            str(underground_object),
            str(reference_object),
            str(inverse_object),
            str(pose_object),
            str(geometry_object),
            "-lm",
            "-o",
            str(executable),
        ],
        output,
    )
    output_text = run([str(executable)], output)
    underground_geometry_hash = source_hash(
        underground / "psxrecomp/runtime/src/vr_geometry_math.c"
    )
    reference_geometry_hash = source_hash(
        reference / "psxrecomp/runtime/src/vr_geometry_math.c"
    )
    if underground_geometry_hash != reference_geometry_hash:
        raise RuntimeError("title framework copies of vr_geometry_math.c differ")
    cases = [
        line
        for line in output_text.splitlines()
        if line.startswith(("CASE|", "FAIL|", "SUMMARY|"))
    ]
    receipt = {
        "schema": 1,
        "kind": "cross-game-vr-parity-baseline",
        "reference": {
            "root": str(reference),
            "head": git_value(reference, "rev-parse", "HEAD"),
            "framework": git_value(
                reference / "psxrecomp", "rev-parse", "HEAD"
            ),
            "adapter_sha256": source_hash(
                reference / "vr/tests/reference_parity_adapter.c"
            ),
        },
        "underground": {
            "root": str(underground),
            "head": git_value(underground, "rev-parse", "HEAD"),
            "framework": git_value(
                underground / "psxrecomp", "rev-parse", "HEAD"
            ),
            "adapter_sha256": source_hash(
                underground / "vr/tests/underground_parity_adapter.c"
            ),
            "fixture_sha256": source_hash(
                underground / "vr/tests/reference_parity_vectors.c"
            ),
            "geometry_math_sha256": underground_geometry_hash,
        },
        "shared_geometry_math_sha256": underground_geometry_hash,
        "reference_geometry_math_sha256": reference_geometry_hash,
        "compiler": cc,
        "cases": cases,
        "passed": "SUMMARY|PASS|0" in output_text,
    }
    (output / "baseline.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(output_text, end="")
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
