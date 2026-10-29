"""Prepare isolated MP weapon sets / SP smoke, then run one operator-selected case.

Uses the production binary and native game.toml, with no debug TCP or capture.
Each case is a fresh process; source saves and preferences are hashed, never edited.
"""
from __future__ import annotations

import argparse
import ctypes
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

import inspect_weapon_sets as native
import probe_p38_headset as shared

ROOT = Path(__file__).resolve().parents[2]
CASES = {
    "mp1": ("analysis/fixtures/mp", 1, ["P38", "MP40", "StG44", "Stick grenade"]),
    "mp2": ("analysis/fixtures/mp", 2, ["Colt .45", "Sten", "Shotgun", "Petrol bomb"]),
    "mp3": ("analysis/fixtures/mp", 3, ["Silenced pistol", "Crossbow", "Scoped rifle", "Stick grenade"]),
    "mp4": ("analysis/fixtures/mp", 4, ["M1 Garand", "StG44", "Panzerfaust", "Petrol bomb"]),
    "sp": ("analysis/fixtures/sp", 3, ["P38 SP visibility / flash / movement smoke"]),
}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def prepare(out):
    out.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": 1, "cases": {}, "physical_acceptance": False}
    for name, (source, slot, weapons) in CASES.items():
        target = out / name / "saves/openbios"
        target.mkdir(parents=True)
        paths = sorted((ROOT / source / "openbios").glob(f"*slot{slot:02}.*"))
        if sorted(p.suffix for p in paths) != [".pst", ".thumb"]:
            raise RuntimeError(f"Expected exactly PST and thumbnail: {paths}")
        hashes = {str(p): native.digest(p) for p in paths}
        for path in paths:
            shutil.copyfile(path, target / path.name)
            if native.digest(target / path.name) != hashes[str(path)]:
                raise RuntimeError("Fixture copy mismatch")
        manifest["cases"][name] = dict(slot=slot, weapons=weapons, source_hashes=hashes)
    save(out / "session.json", manifest)
    print(json.dumps(manifest, indent=2), flush=True)


def close_owned_window(proc):
    """Ask only this child PID's windows to close normally."""
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def close(hwnd, unused):
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
        if pid.value == proc.pid:
            user32.PostMessageW(ctypes.c_void_p(hwnd), 0x0010, 0, 0)
        return True

    user32.EnumWindows(callback_type(close), 0)


def run(out, case, seconds, desktop, laser=False):
    if native.game_pids():
        raise RuntimeError("Close the existing Underground game before starting another case")
    manifest = json.loads((out / "session.json").read_text(encoding="utf-8"))
    fixture = manifest["cases"][case]
    build = shared.build_configuration(ROOT / "build-release/CMakeCache.txt")
    if any(build.get(k) != v for k, v in {
        "PSX_DEBUG_TOOLS": "OFF", "PSX_OPENXR": "ON",
        "MOHU_VR_DIAGNOSTICS": "ON", "configuration": "Release",
    }.items()):
        raise RuntimeError(f"Expected production VR Release/debug OFF build: {build}")
    run_dir = out / case / (("desktop" if desktop else "headset") + ("-laser" if laser else ""))
    run_dir.mkdir(exist_ok=False)
    env = shared.environment("tracked", desktop,
                             runtime_manifest=None if desktop else shared.resolve_vdxr_manifest(),
                             hand_fixed=True)
    env.update(PSX_VR_LASER=str(int(laser)),
               PSX_LOAD_SLOT=str(fixture["slot"]), PSX_RENDER_PASS_VERIFY="0",
               PSX_FRAME_REPORT_MS="1000", PSX_RUNTIME_PERF_DIAG="1",
               PSX_RUNTIME_PERF_DIAG_MS="1000", MOHU_VR_UNITS_PER_METER="238.80597014925373",
               MOHU_VR_WEAPON_TRACE="0", MOHU_VR_SP_WEAPON_SPARE_ARENA="1")
    if case == "sp":
        env.update(MOHU_VR_MP_CONTROL="0", MOHU_VR_MP_FRUSTUM="0")
    ready_path = run_dir / "startup.json"
    env["PSX_OPENXR_READY_FILE"] = str(ready_path)
    exe = ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    config = ROOT / "game.toml"
    prefs = shared.hash_existing(shared.preference_paths())
    r = dict(case=case, desktop_check=desktop, weapons=fixture["weapons"],
             binary_sha256=native.digest(exe), config_sha256=native.digest(config),
             build=build, source_hashes=fixture["source_hashes"],
             physical_acceptance=False, operator_feedback=None, forced_cleanup=False,
             environment={k: v for k, v in env.items() if k.startswith(("PSX_", "MOHU_", "XR_"))})
    save(run_dir / "receipt.json", r)
    command = [str(exe), "--game", str(config), "--no-launcher",
               "--memcard-dir", str(out / case / "saves")]
    if desktop:
        command.append("--hidden-window")
        env["SDL_AUDIODRIVER"] = "dummy"
    print(f"Starting {case}: {' -> '.join(fixture['weapons'])}; {seconds}s", flush=True)
    with (run_dir / "stdout.log").open("w") as so, (run_dir / "stderr.log").open("w") as se:
        proc = subprocess.Popen(command, cwd=run_dir, env=env, stdout=so, stderr=se,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        start = time.monotonic()
        announced = False
        ready_at = None
        try:
            while proc.poll() is None:
                elapsed = time.monotonic() - start
                if not desktop and not announced and ready_path.exists():
                    try:
                        ready = json.loads(ready_path.read_text(encoding="utf-8-sig"))
                    except (ValueError, OSError):
                        ready = {}
                    if ready.get("ready") and ready.get("openxr", {}).get("submitted", 0) > 0:
                        announced = True
                        ready_at = time.monotonic()
                        print("HEADSET READY: right B changes weapon; A reloads; trigger fires", flush=True)
                    elif ready.get("ready") is False:
                        raise RuntimeError(f"Startup/load failed: {ready}")
                if desktop and elapsed >= seconds:
                    break
                if announced and time.monotonic() - ready_at >= seconds:
                    break
                if not desktop and not announced and elapsed > 60:
                    raise RuntimeError("No ready headset submission within 60 seconds")
                time.sleep(0.2)
        finally:
            if proc.poll() is None:
                close_owned_window(proc)
                try:
                    proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    r["forced_cleanup"] = True
                    proc.terminate()
                    proc.wait(timeout=10)
            text = (run_dir / "stdout.log").read_text(encoding="utf-8", errors="replace")
            pairs = re.findall(r"stereo_proof attempt=(\d+) pairs=(\d+) rendered=(\d+)", text)
            native_calls = re.findall(r"overlay native=\+(\d+)", text)
            r.update(exit_code=proc.returncode, elapsed_seconds=time.monotonic() - start,
                     headset_ready=announced, final_stereo=pairs[-1] if pairs else None,
                     native_calls=sum(map(int, native_calls)),
                     source_saves_unchanged=all(native.digest(Path(k)) == v for k, v in fixture["source_hashes"].items()),
                     preferences_unchanged=shared.hash_existing(shared.preference_paths()) == prefs)
            r["transport_passed"] = bool(proc.returncode == 0 and not r["forced_cleanup"]
                and pairs and int(pairs[-1][1]) > 0 and r["native_calls"] > 0
                and r["source_saves_unchanged"] and r["preferences_unchanged"]
                and (desktop or announced))
            save(run_dir / "receipt.json", r)
    print(json.dumps(r, indent=2), flush=True)
    if not r["transport_passed"]:
        raise RuntimeError("Transport/preflight incomplete; inspect receipt and logs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--desktop-check", action="store_true")
    parser.add_argument("--laser", action="store_true", help="Enable existing right-squeeze laser")
    parser.add_argument("--seconds", type=int, default=180)
    args = parser.parse_args()
    if not 5 <= args.seconds <= 600:
        parser.error("--seconds must be 5..600")
    if not args.prepare and not args.case:
        parser.error("Choose --prepare or --case")
    out = args.session.resolve()
    if args.prepare:
        prepare(out)
    if args.case:
        run(out, args.case, args.seconds, args.desktop_check, args.laser)


if __name__ == "__main__":
    main()
