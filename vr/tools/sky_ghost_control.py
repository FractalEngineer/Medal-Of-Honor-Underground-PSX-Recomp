"""Bounded raw-eye/application-layer control using the one release build.

Run from the repository root. Requires debug tools in build-release. Saves only
two raw pairs and one compositor/application-layer capture per XR control.
The launcher owns runtime shutdown and settings restoration, even on failure.
"""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "psxrecomp/tools"))
sys.path.insert(0, str(ROOT / "vr"))
from debug_client import connect, send_cmd
from headless_steamvr import Compositor


def command(name, **kwargs):
    with connect(port=4372, timeout=10) as sock:
        result = send_cmd(sock, {"cmd": name, **kwargs})
    if not result.get("ok"):
        raise RuntimeError(f"{name}: {result}")
    return result


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def game_pids():
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process Medal_of_Honor_Underground_Recompiled -ErrorAction SilentlyContinue | ForEach-Object { $_.Id }"],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return [int(x) for x in result.stdout.split()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--case", choices=("baseline", "clear", "colour", "native-off",
                        "keep-hud", "native-frustum", "scene-colour", "replay-only", "sky", "zero", "yaw-positive", "yaw-negative"),
                        default="baseline")
    parser.add_argument("--steam-root", type=Path, default=Path("C:/Program Files (x86)/Steam"))
    parser.add_argument("--pitch-mdeg", type=int, default=0)
    parser.add_argument("--clear-before-submit", action="store_true")
    parser.add_argument("--keep-replay-submit", action="store_true")
    parser.add_argument("--trace-hud", action="store_true")
    args = parser.parse_args()
    output = args.directory.resolve()
    output.mkdir(parents=True, exist_ok=False)
    copied = output/'saves/openbios'
    copied.mkdir(parents=True)
    sources = list((ROOT/'analysis/fixtures/sp/openbios').glob('*slot03.*'))
    if len(sources) != 2: raise RuntimeError('Expected frozen SP slot-3 state/thumbnail')
    for source in sources: shutil.copyfile(source, copied/source.name)
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Refusing occupied diagnostic port 4372")
    if game_pids():
        raise RuntimeError("Close existing game before this owned control")
    env = os.environ.copy()
    # Explicit controls prevent inherited experiment state contaminating a run.
    for key in tuple(env):
        if key.startswith("MOHU_VR_") or key.startswith("PSX_VR_") or key.startswith("PSX_OPENXR"):
            del env[key]
    env.update(PSX_RENDER_PASS_VERIFY="1", PSX_STEREO_SHED="0")
    if args.clear_before_submit:
        env["MOHU_VR_CLEAR_BEFORE_SUBMIT"] = "1"
    if args.keep_replay_submit:
        env["MOHU_VR_KEEP_REPLAY_SUBMIT"] = "1"
    if args.trace_hud:
        env["MOHU_VR_HUD_TRACE"] = "1"
    if args.case in ("clear", "colour"):
        env["MOHU_VR_CLEAR_ONLY"] = "1"
    if args.case in ("colour", "scene-colour"):
        env["MOHU_VR_CLEAR_RGB"] = "0xC020D0"  # GP0 low byte is red.
    if args.case == "native-off":
        env["MOHU_VR_NO_NATIVE_SURFACE"] = "1"
    xr = args.case not in ("replay-only", "sky", "zero", "yaw-positive", "yaw-negative")
    if args.case == "replay-only":
        env["MOHU_VR_SKIP_FINAL_SUBMIT"] = "1"
    settings = args.steam_root / "config/steamvr.vrsettings"
    backup = settings.read_bytes() if xr else None
    if backup is not None:
        (output / "steamvr.vrsettings.pre-headless").write_bytes(backup)
    if xr:
        launch = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                  str(ROOT / "vr/run_vr.ps1"), "-Headless", "-Seconds", "12",
                  "-DebugPort", "4372", "-LogDirectory", str(output),
                  "-Slot", "3", "-MemcardDirectory", str(output/'saves')]
        if args.case == "keep-hud":
            launch += ["-KeepFlatHud"]
        if args.case == "native-frustum":
            launch += ["-NoHeadFrustumDiagnostic"]
    else:
        env.update(MOHU_VR_STEREO_PROOF="1", MOHU_VR_EYE_RENDER_VIEW="1",
                   MOHU_VR_EYE_GUEST_SUBMIT="1", MOHU_VR_EYE_OFFSET="0" if args.case == "zero" else "24",
                   PSX_VR_HEAD_FRUSTUM="1", PSX_VR_SUPPRESS_FLAT_HUD="1",
                   PSX_INTERNAL_RESOLUTION="1080p", PSX_LOAD_SLOT="3", PSX_VSYNC="0",
                   PSX_DITHERING="0")
        env["MOHU_VR_EYE_YAW_MDEG"] = {"replay-only": "0", "sky": "0", "zero": "0", "yaw-positive": "90000", "yaw-negative": "-90000"}[args.case]
        env["MOHU_VR_EYE_PITCH_MDEG"] = str(args.pitch_mdeg)
        launch = [str(ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"),
                  "--headless-opengl", "--no-launcher", "--debug-port", "4372",
                  "--game", str(ROOT / "analysis/vr-baseline/game-interp.toml"),
                  "--memcard-dir", str(output/'saves')]
    result = {"case": args.case, "revision": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "controls": {"pitch_mdeg": args.pitch_mdeg, "clear_before_submit": args.clear_before_submit,
                     "keep_replay_submit": args.keep_replay_submit, "trace_hud": args.trace_hud,
                     "synthetic_xr_pose": bool(xr and args.pitch_mdeg)},
        "executable_sha256": hashlib.sha256((ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe").read_bytes()).hexdigest()}
    with (output / "control.stdout.log").open("w") as stdout, (output / "control.stderr.log").open("w") as stderr:
        process = subprocess.Popen(launch, cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        compositor = None
        try:
            deadline = time.monotonic() + 50
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"Control exited early ({process.returncode}); inspect logs")
                if xr and not (output / "openxr-smoke.json").exists():
                    time.sleep(0.2)
                    continue
                try:
                    state = command("savestate_status")
                    if state.get("generation", 0) and not state.get("pending") and not state.get("last_ok"):
                        raise RuntimeError("Invalid save: ask the operator for a fresh PGXP slot")
                    stereo = command("stereo_stats")
                    if stereo.get("pairs", 0) > 5:
                        break
                except (OSError, TimeoutError):
                    pass
                time.sleep(0.2)
            else:
                raise TimeoutError("No fresh stereo pair; inspect slot and startup logs")
            save(output / "savestate.json", state)
            if xr and args.pitch_mdeg:
                result["pose_override"] = command("openxr_pose_override", pitch_mdeg=args.pitch_mdeg)
                time.sleep(0.4)
            save(output / "frame-render-code.json", command("read_ram", addr="0x80053BB4", len=240))
            save(output / "hud-bar-packets.json", command("read_ram", addr="0x800F109C", len=80))
            for address, size in (("0x80053D4C", 512), ("0x8006B64C", 692), ("0x80053CA4", 168)):
                save(output / (address + ".json"), command("read_ram", addr=address, len=size))
            result["before"] = {name: command(name) for name in ("openxr_stats", "openxr_views", "stereo_stats", "render_pass_stats")}
            raw = output / "raw"
            raw.mkdir()
            command("stereo_dump", path=raw.as_posix(), count=2)
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline and len(list(raw.glob("*_right.png"))) < 2:
                time.sleep(0.1)
            if len(list(raw.glob("*_right.png"))) != 2:
                raise RuntimeError("Expected exactly two completed raw pairs")
            if xr:
                owned = game_pids()
                if len(owned) != 1:
                    raise RuntimeError(f"Unexpected game process inventory: {owned}")
                compositor = Compositor(args.steam_root / "steamapps/common/SteamVR")
                result["capture"] = compositor.capture(output / "layers", owned[0], reject_blank=False)
            time.sleep(0.4)
            result["after"] = {name: command(name) for name in ("openxr_stats", "openxr_views", "stereo_stats", "render_pass_stats")}
            before, after = result["before"], result["after"]
            checks = after["render_pass_stats"]
            if not checks["verify_checks"] or any(checks[key] for key in
                    ("verify_mismatch", "vram_leaks", "nesting_repairs", "watchdog")):
                raise RuntimeError("Rollback verification failed or was disabled")
            stereo = after["stereo_stats"]
            deadline = time.monotonic() + 2
            while (stereo["eye_hashes"][0] != stereo["eye_hashes"][1] or
                   stereo["eye_cycles"][0] != stereo["eye_cycles"][1]) and time.monotonic() < deadline:
                time.sleep(0.02)
                stereo = after["stereo_stats"] = command("stereo_stats")
            if stereo["failed"] or stereo["retained_pair_id"] or stereo["stale_frames"]:
                raise RuntimeError("Stereo failure, retained pair, or stale frame")
            if stereo["eye_hashes"][0] != stereo["eye_hashes"][1] or stereo["eye_cycles"][0] != stereo["eye_cycles"][1]:
                raise RuntimeError("Eye transaction state/cycles differ")
            if xr:
                first, last = before["openxr_stats"], after["openxr_stats"]
                if (last["submitted_layer"], last["submitted_source"]) != (1, 1) or last["empty"] or last["failures"]:
                    raise RuntimeError("Expected fresh projection with no empty submissions or XR failures")
                if after["openxr_views"]["submitted_pair_id"] <= before["openxr_views"]["submitted_pair_id"]:
                    raise RuntimeError("Submitted stereo pair did not advance")
            from PIL import Image, ImageStat
            result["raw"] = [{"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                              "size": Image.open(path).size, "mean": ImageStat.Stat(Image.open(path).convert("RGB")).mean,
                              "extrema": Image.open(path).convert("RGB").getextrema()}
                             for path in sorted(raw.glob("*_left.png")) + sorted(raw.glob("*_right.png"))]
        except BaseException as exc:
            result["error"] = str(exc)
            raise
        finally:
            if xr and args.pitch_mdeg and process.poll() is None:
                try:
                    result["pose_cleared"] = command("openxr_pose_override", clear=1)
                except OSError as exc:
                    result["pose_clear_error"] = str(exc)
            if compositor:
                compositor.close()
            if xr:
                # Never kill the launcher: its finally block restores SteamVR.
                try:
                    process.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    command("quit")
                    process.wait(timeout=30)
            elif process.poll() is None:
                result["intentional_termination"] = True
                process.terminate()
                process.wait(timeout=10)
            result["exit_code"] = process.returncode
            result["settings_restored"] = backup is None or settings.read_bytes() == backup
            result["remaining_game_pids"] = game_pids()
            save(output / "receipt.json", result)
    if (result["exit_code"] and not result.get("intentional_termination")) or not result["settings_restored"] or result["remaining_game_pids"]:
        raise RuntimeError("Control cleanup failed; inspect receipt")
    print(json.dumps({"case": args.case, "settings_restored": result["settings_restored"], "remaining_game_pids": result["remaining_game_pids"]}))


if __name__ == "__main__":
    main()
