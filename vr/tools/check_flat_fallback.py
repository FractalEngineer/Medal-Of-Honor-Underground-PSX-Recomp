"""Smoke the OpenXR-off flat executable with inherited VR experiments."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parents[2]
EXE_NAME = "Medal_of_Honor_Underground_Recompiled.exe"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "--build-directory",
        type=Path,
        default=ROOT / "build-flat-check",
    )
    args = parser.parse_args()
    output = args.directory.resolve()
    output.mkdir(parents=True, exist_ok=False)
    build = args.build_directory.resolve()
    executable = build / EXE_NAME
    game = build / "game.toml"
    if not executable.exists() or not game.exists():
        raise RuntimeError("Flat build executable or game config is missing")

    cache = (build / "CMakeCache.txt").read_text(encoding="utf-8")
    options = {}
    for key in ("PSX_OPENXR", "MOHU_VR_DIAGNOSTICS", "PSX_DEBUG_TOOLS"):
        values = [
            line.split("=", 1)[1]
            for line in cache.splitlines()
            if line.startswith(key + ":")
        ]
        if len(values) != 1:
            raise RuntimeError(f"Missing or duplicate {key} in CMakeCache")
        options[key] = values[0]
    if options != {
        "PSX_OPENXR": "OFF",
        "MOHU_VR_DIAGNOSTICS": "OFF",
        "PSX_DEBUG_TOOLS": "OFF",
    }:
        raise RuntimeError(f"Unexpected flat build options: {options}")

    saves = sorted((ROOT / "saves/openbios").glob("state_*"))
    save_hashes = {str(path): digest(path) for path in saves}
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PSX_", "MOHU_VR_", "XR_RUNTIME"))
    }
    env.update(
        PSX_DEV_INPUT="0",
        PSX_VR_MOVEMENT="1",
        PSX_OPENXR_ENABLE="1",
        PSX_VR_WEAPON_POSE="1",
        MOHU_VR_MP_CONTROL="1",
        MOHU_VR_MP_FRUSTUM="1",
        MOHU_VR_STEREO_PROOF="1",
        MOHU_VR_EYE_GUEST_SUBMIT="1",
        MOHU_VR_WEAPON_FLAT_PROBE="1",
        MOHU_VR_P38_CALIBRATED="1",
        MOHU_VR_P38_AIM="1",
    )
    stdout_path = output / "stdout.log"
    stderr_path = output / "stderr.log"
    result = {
        "complete": False,
        "intentional_termination": False,
        "executable": str(executable),
        "executable_sha256": digest(executable),
        "build_options": options,
        "inherited_environment": {
            key: env[key]
            for key in sorted(env)
            if key.startswith(("PSX_VR_", "MOHU_VR_"))
        },
        "source_saves": save_hashes,
    }
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        process = subprocess.Popen(
            [
                str(executable),
                "--headless-opengl",
                "--no-launcher",
                "--game",
                str(game),
            ],
            cwd=output,
            env=env,
            stdout=stdout,
            stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Flat executable exited during startup")
                time.sleep(0.25)
        finally:
            if process.poll() is None:
                process.terminate()
                result["intentional_termination"] = True
                process.wait(timeout=10)
            result["exit_code"] = process.returncode

    text = (
        stdout_path.read_text(encoding="utf-8", errors="replace") + "\n" +
        stderr_path.read_text(encoding="utf-8", errors="replace")
    )
    result["main_entered"] = "psxrecomp: main() entered" in text
    active_markers = [
        marker
        for marker in (
            "mohu-vr-input:",
            "mohu-vr-diag:",
            "mohu-vr-mp:",
            "stereo_proof",
        )
        if marker in text
    ]
    result["active_vr_markers"] = active_markers
    result["vr_active"] = bool(active_markers)
    result["source_saves_unchanged"] = all(
        digest(Path(path)) == digest_value
        for path, digest_value in save_hashes.items()
    )
    result["complete"] = all((
        result["intentional_termination"],
        result["main_entered"],
        not result["vr_active"],
        result["source_saves_unchanged"],
    ))
    (output / "receipt.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    if not result["complete"]:
        raise RuntimeError(f"Flat fallback failed: {result}")
    print(json.dumps({
        "complete": result["complete"],
        "active_vr_markers": active_markers,
        "source_saves_unchanged": result["source_saves_unchanged"],
    }))


if __name__ == "__main__":
    main()
