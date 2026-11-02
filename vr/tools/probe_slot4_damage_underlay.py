"""Capture the slot 04 under-fire HUD after a native damage pulse.

The probe copies the source save into a disposable directory, runs the
null-headset OpenXR path, waits for the native damage triangle to be moved to
the left wrist surface, and records both the wrist RGBA output and stereo eyes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import socket
import subprocess
import time

import inspect_weapon_sets as native
from PIL import Image
import probe_native_hud as native_hud
import probe_p38_headset as shared


ROOT = Path(__file__).resolve().parents[2]
SLOT = 4


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    if native.game_pids():
        raise RuntimeError("Close the existing game before starting the HUD probe")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 4372))

    source = ROOT / "saves/openbios"
    target = out / "saves/openbios"
    target.mkdir(parents=True)
    fixtures = sorted(source.glob(f"*slot{SLOT:02}.*"))
    if sorted(path.suffix for path in fixtures) != [".pst", ".thumb"]:
        raise RuntimeError(f"Expected slot {SLOT:02} PST and thumbnail: {fixtures}")
    source_hashes = {str(path): native.digest(path) for path in fixtures}
    for path in fixtures:
        shutil.copyfile(path, target / path.name)

    preferences = shared.hash_existing(shared.preference_paths())
    log_dir = out / "runtime"
    run_dir = out / "capture"
    run_dir.mkdir()
    launch = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ROOT / "vr/run_vr.ps1"),
        "-Headless",
        "-Slot",
        str(SLOT),
        "-MemcardDirectory",
        str(out / "saves"),
        "-BuildDirectory",
        "analysis/builds/mp40-diagnostic",
        "-DebugPort",
        "4372",
        "-InternalResolution",
        "native",
        "-NoLaser",
        "-LogDirectory",
        str(log_dir),
        "-Seconds",
        "45",
    ]
    receipt: dict[str, object] = {
        "schema": 1,
        "slot": SLOT,
        "source_hashes": source_hashes,
        "headset_acceptance": False,
        "complete": False,
    }
    with (
        (out / "stdout.log").open("w") as stdout,
        (out / "stderr.log").open("w") as stderr,
    ):
        process = subprocess.Popen(
            launch,
            cwd=out,
            stdout=stdout,
            stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            shared.wait_for_ping(process)
            deadline = time.monotonic() + 40
            while not (log_dir / "openxr-smoke.json").exists():
                if process.poll() is not None:
                    raise RuntimeError("Null-headset startup exited early")
                if time.monotonic() >= deadline:
                    raise TimeoutError("No null-headset stereo proof")
                time.sleep(0.1)

            for hand, x_mm in (("left", -180), ("right", 180)):
                native.command(
                    "openxr_hands_override",
                    hand=hand,
                    pose="grip",
                    active=1,
                    flags=15,
                    px_mm=x_mm,
                    py_mm=-180,
                    pz_mm=-450,
                    qw=1000000,
                )
            native.frames(8)

            deadline = time.monotonic() + 35
            counters: dict[str, int] = {}
            while time.monotonic() < deadline:
                counters = shared.counter_values()
                if (
                    counters.get("mohu.vr.hud.damage", 0) > 0
                    and counters.get("mohu.vr.hud.damage_native", 0) > 0
                    and counters.get("mohu.vr.hud.damage_screen_suppressed", 0) > 0
                ):
                    break
                time.sleep(0.02)
            else:
                raise TimeoutError("No wrist-owned native damage pulse")

            native.frames(2)
            receipt["hud"] = native_hud.hud()
            receipt["counters"] = counters
            native_hud.hud(f"dump={run_dir.as_posix()}")
            receipt["art"] = native_hud.verify(run_dir)
            eyes = run_dir / "eyes"
            eyes.mkdir()
            native.command(
                "stereo_dump", path=eyes.as_posix(), count=6
            )
            native.frames(8)
            screen_red_pixels = 0
            eye_images = sorted(eyes.glob("p*_left.png"))
            for image_path in eye_images:
                image = Image.open(image_path).convert("RGB")
                scale_x = image.width / 512
                scale_y = image.height / 240
                for y in range(round(24 * scale_y), round(50 * scale_y)):
                    for x in range(round(24 * scale_x), round(94 * scale_x)):
                        red, green, blue = image.getpixel((x, y))
                        if red > 120 and green < 40 and blue < 40:
                            screen_red_pixels += 1
            receipt["stereo_eye_images"] = len(eye_images)
            receipt["screen_damage_red_pixels"] = screen_red_pixels
            if not eye_images or screen_red_pixels:
                raise RuntimeError("Screen-space damage marker remained in stereo eyes")
            receipt["stereo"] = native.command("stereo_stats")
            receipt["render_pass"] = native.command("render_pass_stats")
            receipt["complete"] = True
        finally:
            try:
                native.command("quit")
            except Exception:
                pass
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=15)
                receipt["forced_cleanup"] = True
            receipt["sources_unchanged"] = all(
                native.digest(Path(path)) == digest
                for path, digest in source_hashes.items()
            )
            receipt["preferences_unchanged"] = (
                shared.hash_existing(shared.preference_paths()) == preferences
            )
            (out / "receipt.json").write_text(
                json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
            )
    print(
        json.dumps(
            {
                key: receipt.get(key)
                for key in (
                    "complete",
                    "sources_unchanged",
                    "preferences_unchanged",
                    "counters",
                    "stereo",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
