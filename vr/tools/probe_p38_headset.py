"""Prepare a bounded P38 native-versus-tracked headset comparison.

The runner uses a fresh copy of root multiplayer slot 1 for each mode, enables
movement and the accepted multiplayer controller path, and never records user
acceptance automatically. Desktop mode uses synthetic hands for a transport
check; it is not headset evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "vr/tools"))
import inspect_weapon_sets as native


P38_ID = 0
P38_SLOT = 0
P38_FACE_COUNT = 354
P38_NODE_COUNT = 14
P38_MESH_MAGIC = 0x000E0007
P38_GEOMETRY_FNV32 = 0x8544F8B9
DEFAULT_SECONDS = 30
MAX_SECONDS = 120
MODES = ("native", "tracked")
CALIBRATION_PROOF = ROOT / "vr/proof/weapon-p38-complete-calibration-receipt.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def comparison_modes(requested):
    if requested == "compare":
        return MODES
    if requested not in MODES:
        raise ValueError(f"Unknown comparison mode: {requested}")
    return (requested,)


def validate_seconds(seconds):
    if not 1 <= seconds <= MAX_SECONDS:
        raise ValueError(f"seconds must be in 1..{MAX_SECONDS}")
    return seconds


def clean_environment(source):
    return {
        key: value
        for key, value in source.items()
        if key != "XR_RUNTIME_JSON"
        and not key.startswith(("PSX_", "MOHU_VR_"))
    }


def pose_active(hands, hand=1, pose=1):
    try:
        value = hands["pose"][hand][pose]
    except (IndexError, KeyError, TypeError):
        return False
    return (
        bool(value.get("active"))
        and (int(value.get("flags", 0)) & 3) == 3
    )


def hand_pose_ready(hands):
    return (
        bool(hands.get("focused"))
        and bool(hands.get("origin_valid"))
        and pose_active(hands, 1, 0)
        and pose_active(hands, 1, 1)
    )


def hands_are_live(hands):
    return bool(int(hands.get("synthetic", 1)) == 0) and hand_pose_ready(
        hands
    )


def summarize_samples(samples):
    hands = [sample["hands"] for sample in samples]
    inputs = [sample["input"] for sample in samples]
    live = sum(hands_are_live(value) for value in hands)
    pose_ready = sum(hand_pose_ready(value) for value in hands)
    focused = sum(bool(value.get("focused")) for value in hands)
    positions = [
        value["pose"][1][0]["position_m"]
        for value in hands
        if pose_active(value, 1, 0)
    ]
    travel = 0.0
    if positions:
        first = positions[0]
        travel = max(
            math.dist(first, position) for position in positions
        )
    moved = any(
        abs(value["stick"][0][0]) > 0.2
        or abs(value["stick"][0][1]) > 0.2
        or abs(value["stick"][1][0]) > 0.2
        or bool(value["trigger_active"][1])
        or bool(value["buttons_active"][1])
        for value in inputs
    )
    return {
        "samples": len(samples),
        "live_hand_samples": live,
        "pose_ready_samples": pose_ready,
        "focused_samples": focused,
        "right_hand_travel_m": travel,
        "user_input_observed": moved,
    }


def p38_model_matches(model):
    return (
        int(model["magic"], 16) == P38_MESH_MAGIC
        and model["face_count"] == P38_FACE_COUNT
        and model["node_count"] == P38_NODE_COUNT
        and int(model["geometry_fnv32"], 16) == P38_GEOMETRY_FNV32
    )


def calibration_provenance():
    value = json.loads(CALIBRATION_PROOF.read_text(encoding="utf-8"))
    asset = value.get("asset", {})
    scale = value.get("scale", {})
    if (
        asset.get("id") != P38_ID
        or asset.get("node") != 13
        or asset.get("vertex_count") != 69
        or scale.get("provisional") is not True
    ):
        raise RuntimeError("W3.1 P38 calibration receipt no longer matches")
    return {
        "path": str(CALIBRATION_PROOF.relative_to(ROOT)),
        "sha256": digest(CALIBRATION_PROOF),
        "node": asset["node"],
        "vertex_count": asset["vertex_count"],
        "provisional_scale": scale["model_units_per_metre"],
        "physical_acceptance": scale["physical_acceptance"],
    }


def build_configuration(path):
    text = path.read_text(encoding="utf-8")
    result = {}
    for key in (
        "PSX_DEBUG_TOOLS",
        "MOHU_VR_DIAGNOSTICS",
        "PSX_OPENXR",
    ):
        match = re.search(rf"^{key}:[^=]*=(ON|OFF)$", text, re.MULTILINE)
        result[key] = match.group(1) if match else "missing"
    result["configuration"] = (
        "Release"
        if re.search(r"^CMAKE_BUILD_TYPE:[^=]*=Release$", text, re.MULTILINE)
        else "missing"
    )
    return result


def preference_paths():
    return (
        ROOT / "build-release/settings.toml",
        ROOT / "build-release/keybinds.ini",
        Path("C:/Program Files (x86)/Steam/config/steamvr.vrsettings"),
    )


def hash_existing(paths):
    return {str(path): digest(path) for path in paths if path.is_file()}


def resolve_vdxr_manifest():
    roots = (
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
    )
    candidates = []
    if roots[0]:
        candidates.append(
            Path(roots[0])
            / "Virtual Desktop Streamer/OpenXR/virtualdesktop-openxr.json"
        )
    if roots[1]:
        candidates.append(
            Path(roots[1])
            / "Virtual Desktop Streamer/OpenXR/virtualdesktop-openxr.json"
        )
    if roots[2]:
        candidates.append(
            Path(roots[2])
            / "Programs/VirtualDesktopStreamer/OpenXR"
            / "virtualdesktop-openxr.json"
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError("Virtual Desktop OpenXR runtime manifest not found")


def environment(mode, desktop, runtime_manifest=None, *, hand_fixed=False):
    env = clean_environment(os.environ)
    env.update(
        PSX_DEV_INPUT="0",
        PSX_VSYNC="0",
        PSX_DITHERING="0",
        PSX_STEREO_SHED="0",
        PSX_INTERNAL_RESOLUTION="1080p",
        PSX_RENDER_PASS_VERIFY=str(int(desktop)),
        PSX_VR_MOVEMENT="1",
        PSX_VR_HEAD_FRUSTUM="1",
        PSX_VR_SUPPRESS_FLAT_HUD="1",
        PSX_VR_LASER="0",
        PSX_VR_WEAPON_POSE=str(int(mode == "tracked")),
        MOHU_VR_P38_CALIBRATED=str(int(mode == "tracked")),
        MOHU_VR_P38_AIM=str(int(mode == "tracked")),
        MOHU_VR_MP_CONTROL="1",
        MOHU_VR_MP_FRUSTUM="1",
        MOHU_VR_STEREO_PROOF="1",
        MOHU_VR_EYE_RENDER_VIEW="1",
        MOHU_VR_EYE_GUEST_SUBMIT="1",
        MOHU_VR_EYE_OFFSET="0",
    )
    if hand_fixed and mode == "tracked":
        env.update(MOHU_VR_WEAPON_CALIBRATED="1", MOHU_VR_WEAPON_AIM="1",
                   MOHU_VR_WEAPON_GUN_ONLY="1", MOHU_VR_P38_CALIBRATED="0",
                   MOHU_VR_P38_AIM="0")
    if desktop:
        env["PSX_OPENXR_ENABLE"] = "0"
    else:
        if runtime_manifest is None:
            raise ValueError("Headset mode requires an OpenXR runtime manifest")
        env.update(
            PSX_OPENXR_ENABLE="1",
            MOHU_VR_OPENXR="1",
            XR_RUNTIME_JSON=str(runtime_manifest),
            MOHU_VR_UNITS_PER_METER="238.80597014925373",
            MOHU_VR_MENU_DISTANCE="2",
            MOHU_VR_MENU_WIDTH="2",
        )
    return env


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def release_load_override():
    """Release load()'s absolute debug pad so the controller source can run."""
    native.command("clear_input")
    native.command("set_input", layer="host", buttons=65535)


def collect_case_receipts(out, receipt):
    known = {case.get("mode") for case in receipt["cases"]}
    for path in sorted(out.glob("*/receipt.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        if case.get("mode") not in known:
            receipt["cases"].append(case)
            known.add(case.get("mode"))


def wait_for_ping(process):
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Diagnostic game exited during startup: {process.returncode}"
            )
        try:
            native.command("ping")
            return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("Diagnostic TCP endpoint did not start")


def set_desktop_hands():
    values = {
        "hand": "right",
        "focused": 1,
        "active": 1,
        "flags": 15,
        "age_ms": 0,
        "origin_valid": 1,
        "ox_mm": 0,
        "oy_mm": 0,
        "oz_mm": 0,
        "oqx": 0,
        "oqy": 0,
        "oqz": 0,
        "oqw": 1000000,
    }
    for pose, position in (
        ("grip", (150, -150, -400)),
        ("aim", (150, -150, -450)),
    ):
        native.command(
            "openxr_hands_override",
            pose=pose,
            px_mm=position[0],
            py_mm=position[1],
            pz_mm=position[2],
            qx=0,
            qy=0,
            qz=0,
            qw=1000000,
            **values,
        )


def wait_for_headset(process, mode):
    deadline = time.monotonic() + 35
    last_stats = {}
    last_hands = {}
    last_error = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Headset game exited: {process.returncode}")
        try:
            stats = native.command("openxr_stats")
            hands = native.command("openxr_hands")
        except (OSError, RuntimeError) as error:
            last_error = str(error)
            time.sleep(0.2)
            continue
        last_stats = stats
        last_hands = hands
        stage = stats.get("stage", "unknown")
        if not stats.get("enabled") and stage not in ("requested", "off"):
            raise RuntimeError(
                "OpenXR begin failed at "
                f"stage={stage} result={stats.get('result')} "
                f"failure={stats.get('last_failure')} "
                f"result_code={stats.get('last_failure_result')}"
            )
        if (
            stats.get("running")
            and stats.get("submitted", 0) > 0
            and stats.get("tracking")
            and stats.get("submitted_source") == 1
            and (mode != "tracked" or hands_are_live(hands))
        ):
            return stats, hands
        time.sleep(0.2)
    detail = {
        "stats": last_stats,
        "hands": last_hands,
        "last_error": last_error,
    }
    if mode == "tracked":
        raise TimeoutError(
            "Tracked P38 needs a focused, active right controller or hand: "
            + json.dumps(detail, separators=(",", ":"))
        )
    raise TimeoutError(
        "OpenXR did not submit stereo frames: "
        + json.dumps(detail, separators=(",", ":"))
    )


def run_case(out, mode, seconds, desktop, runtime_manifest, *, hand_fixed=False):
    case_dir = out / mode
    session = case_dir / "session"
    saves = session / "saves/openbios"
    saves.mkdir(parents=True)
    config = session / "game.toml"
    shutil.copyfile(ROOT / "analysis/vr-baseline/game-interp.toml", config)
    copied = []
    for suffix in ("pst", "thumb"):
        source = ROOT / f"saves/openbios/state_8001F844_slot01.{suffix}"
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copyfile(source, saves / source.name)
        copied.append(source)

    executable = (
        ROOT
        / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    )
    env = environment(mode, desktop, runtime_manifest, hand_fixed=hand_fixed)
    command_line = [
        str(executable),
        "--no-launcher",
        "--game",
        str(config),
        "--memcard-dir",
        str(session / "saves"),
        "--debug-port",
        "4372",
    ]
    if desktop:
        command_line.insert(1, "--headless-opengl")

    case = {
        "mode": mode,
        "desktop_synthetic": desktop,
        "runtime_manifest": (
            str(runtime_manifest) if runtime_manifest is not None else None
        ),
        "seconds": seconds,
        "fixture": [str(path.relative_to(ROOT)) for path in copied],
        "executable_sha256": digest(executable),
        "environment": {
            key: env[key]
            for key in (
                "PSX_OPENXR_ENABLE",
                "MOHU_VR_OPENXR",
                "XR_RUNTIME_JSON",
                "PSX_VR_MOVEMENT",
                "PSX_VR_HEAD_FRUSTUM",
                "MOHU_VR_MP_CONTROL",
                "MOHU_VR_MP_FRUSTUM",
                "MOHU_VR_WEAPON_CALIBRATED",
                "MOHU_VR_WEAPON_AIM",
                "MOHU_VR_WEAPON_GUN_ONLY",
                "PSX_VR_WEAPON_POSE",
                "PSX_VR_LASER",
                "PSX_DITHERING",
                "MOHU_VR_P38_CALIBRATED",
                "MOHU_VR_P38_AIM",
            )
            if key in env
        },
        "complete": False,
        "forced_cleanup": False,
        "aim_policy": "hand-fixed all-family" if hand_fixed else "legacy P38/native",
        "execution_account": subprocess.check_output(["whoami"], text=True).strip(),
    }
    with (
        (case_dir / "stdout.log").open("w", encoding="utf-8") as stdout,
        (case_dir / "stderr.log").open("w", encoding="utf-8") as stderr,
    ):
        process = subprocess.Popen(
            command_line,
            cwd=session,
            env=env,
            stdout=stdout,
            stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        case["owned_pid"] = process.pid
        try:
            wait_for_ping(process)
            native.command("openxr_input_override", clear=1)
            native.command("openxr_hands_override", clear=1)
            case["load"] = native.load(1)
            release_load_override()
            players = native.players()
            if (
                players[0]["weapon_slot"],
                players[0]["weapon_id"],
            ) != (P38_SLOT, P38_ID):
                raise RuntimeError("Copied slot 1 is not the P38 fixture")
            model = native.first_person_model()
            if not p38_model_matches(model):
                raise RuntimeError(f"Unexpected P38 first-person model: {model}")
            case["players"] = players
            case["model"] = {
                key: model[key]
                for key in (
                    "magic",
                    "face_count",
                    "node_count",
                    "geometry_fnv32",
                    "node_table_sha256",
                )
            }

            if desktop:
                set_desktop_hands()
                case["xr_before"] = None
                case["hands_before"] = native.command("openxr_hands")
            else:
                case["xr_before"], case["hands_before"] = wait_for_headset(
                    process, mode
                )
            native.frames(18)
            case["stereo_before"] = native.command("stereo_stats")
            case["render_before"] = native.command("render_pass_stats")
            case["input_before"] = native.command("openxr_input")

            operation = (
                "native weapon pose"
                if mode == "native"
                else "right-hand tracked weapon pose"
            )
            print(
                f"START P38 {operation}: {seconds}s, movement enabled. "
                "Hold the controller, move the head, walk, fire and reload.",
                flush=True,
            )
            started = time.monotonic()
            samples = []
            while time.monotonic() - started < seconds:
                if process.poll() is not None:
                    raise RuntimeError(f"Game exited: {process.returncode}")
                elapsed = time.monotonic() - started
                if not samples or elapsed - samples[-1]["seconds"] >= 1:
                    samples.append(
                        {
                            "seconds": round(elapsed, 3),
                            "frame": native.command("frame"),
                            "stereo": native.command("stereo_stats"),
                            "hands": native.command("openxr_hands"),
                            "input": native.command("openxr_input"),
                        }
                    )
                time.sleep(0.04)
            case["elapsed_seconds"] = round(
                time.monotonic() - started, 3
            )
            case["samples"] = samples
            case["sample_summary"] = summarize_samples(samples)
            case["stereo_after"] = native.command("stereo_stats")
            case["render_after"] = native.command("render_pass_stats")
            case["input_after"] = native.command("openxr_input")
            if desktop:
                case["xr_after"] = None

            if (
                case["stereo_after"]["pairs"]
                <= case["stereo_before"]["pairs"]
            ):
                raise RuntimeError("No fresh stereo pair during comparison")
            if not desktop:
                case["xr_after"] = native.command("openxr_stats")
                if (
                    case["xr_after"]["submitted"]
                    <= case["xr_before"]["submitted"]
                ):
                    raise RuntimeError("No fresh OpenXR submission")
                if case["sample_summary"]["live_hand_samples"] == 0:
                    raise RuntimeError("Tracked case had no live hand samples")
            if case["render_after"]["verify_mismatch"]:
                raise RuntimeError("Render rollback verification failed")
            if mode == "tracked" and desktop:
                if case["sample_summary"]["pose_ready_samples"] == 0:
                    raise RuntimeError("Synthetic tracked control was not live")
            case["complete"] = True
            print(f"END P38 {mode}", flush=True)
        except BaseException as error:
            case["error"] = str(error)
            save_json(out / "receipt.json", case)
            raise
        finally:
            try:
                native.command("openxr_input_override", clear=1)
                native.command("openxr_hands_override", clear=1)
            except (OSError, RuntimeError):
                pass
            if process.poll() is None:
                try:
                    native.command("render_pass_refuse", on=1)
                    native.frames(4)
                    native.command("quit")
                except (OSError, RuntimeError):
                    pass
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    case["forced_cleanup"] = True
                    process.terminate()
                    process.wait(timeout=8)
            case["exit_code"] = process.returncode
            if case["forced_cleanup"] or case["exit_code"] != 0:
                case["transport_complete"] = bool(case["complete"])
                case["complete"] = False
                case["cleanup_error"] = "Nonzero exit or forced cleanup; not clean headset acceptance"
            save_json(case_dir / "receipt.json", case)
    return case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "--mode", choices=("native", "tracked", "compare"), default="compare"
    )
    parser.add_argument("--seconds", type=int, default=DEFAULT_SECONDS)
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="Use synthetic hands and headless OpenGL; not headset evidence",
    )
    parser.add_argument(
        "--runtime-json",
        type=Path,
        help="Explicit OpenXR runtime manifest; defaults to Virtual Desktop",
    )
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--hand-fixed", action="store_true",
                        help="Test the current hand-fixed all-family candidate on P38")
    args = parser.parse_args()
    try:
        seconds = validate_seconds(args.seconds)
        modes = comparison_modes(args.mode)
    except ValueError as error:
        parser.error(str(error))
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic TCP port 4372 is occupied")

    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    runtime_manifest = None
    if not args.desktop:
        runtime_manifest = (
            args.runtime_json.resolve()
            if args.runtime_json
            else resolve_vdxr_manifest()
        )
        if not runtime_manifest.is_file():
            raise FileNotFoundError(runtime_manifest)
    executable = (
        ROOT
        / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    )
    if not executable.is_file():
        raise FileNotFoundError(executable)
    config = build_configuration(ROOT / "build-release/CMakeCache.txt")
    if (
        config["PSX_DEBUG_TOOLS"] != "ON"
        or config["MOHU_VR_DIAGNOSTICS"] != "ON"
        or config["PSX_OPENXR"] != "ON"
    ):
        raise RuntimeError(f"W3.2 requires diagnostic build flags: {config}")

    source_saves = [
        ROOT / "saves/openbios/state_8001F844_slot01.pst",
        ROOT / "saves/openbios/state_8001F844_slot01.thumb",
    ]
    source_hashes = hash_existing(source_saves)
    preferences = hash_existing(preference_paths())
    receipt = {
        "schema": 1,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "kind": "W3.2 P38 bounded movement-enabled comparison",
        "desktop_synthetic": args.desktop,
        "runtime_manifest": (
            str(runtime_manifest) if runtime_manifest is not None else None
        ),
        "headset_acceptance": False,
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "executable_sha256": digest(executable),
        "build": config,
        "calibration": calibration_provenance(),
        "fixture": {
            "source": "root multiplayer slot 1",
            "weapon_id": P38_ID,
            "weapon": "P38 pistol",
            "switches": 0,
            "fire_policy": "operator may fire; runner never edits ammo",
            "source_hashes": source_hashes,
        },
        "comparison": {
            "modes": list(modes),
            "seconds_per_mode": seconds,
            "movement_enabled": True,
            "mp_control_enabled": True,
            "laser_disabled": True,
        },
        "cases": [],
        "complete": False,
    }
    try:
        for mode in modes:
            receipt["cases"].append(
                run_case(
                    out, mode, seconds, args.desktop, runtime_manifest,
                    hand_fixed=args.hand_fixed
                )
            )
        receipt["complete"] = all(case["complete"] for case in receipt["cases"])
    except BaseException as error:
        receipt["error"] = str(error)
        raise
    finally:
        collect_case_receipts(out, receipt)
        receipt["source_saves_unchanged"] = all(
            digest(Path(path)) == value
            for path, value in source_hashes.items()
        )
        receipt["preferences_unchanged"] = all(
            digest(Path(path)) == value
            for path, value in preferences.items()
        )
        receipt["remaining_game_pids"] = native.game_pids()
        receipt["checks"] = {
            "all_cases_complete": all(
                case.get("complete") for case in receipt["cases"]
            ),
            "source_saves_unchanged": receipt["source_saves_unchanged"],
            "preferences_unchanged": receipt["preferences_unchanged"],
            "remaining_game_pids": receipt["remaining_game_pids"],
        }
        save_json(out / "receipt.json", receipt)
        if args.proof:
            compact = {
                key: receipt[key]
                for key in (
                    "schema",
                    "date",
                    "kind",
                    "desktop_synthetic",
                    "headset_acceptance",
                    "revision",
                    "executable_sha256",
                    "build",
                    "calibration",
                    "fixture",
                    "comparison",
                    "complete",
                    "checks",
                )
            }
            compact["raw_receipt"] = str(
                (out / "receipt.json").relative_to(ROOT)
            )
            compact["raw_receipt_sha256"] = digest(out / "receipt.json")
            compact["cases"] = [
                {
                    key: case.get(key)
                    for key in (
                        "mode",
                        "seconds",
                        "elapsed_seconds",
                        "complete",
                        "error",
                        "exit_code",
                        "model",
                        "sample_summary",
                        "stereo_before",
                        "stereo_after",
                        "xr_before",
                        "xr_after",
                    )
                }
                for case in receipt["cases"]
            ]
            compact["status"] = (
                "blocked"
                if receipt.get("error")
                else (
                    "desktop synthetic dry run"
                    if args.desktop
                    else "headset run"
                )
            )
            compact["error"] = receipt.get("error")
            compact["limits"] = [
                "No operator acceptance is inferred.",
                "W3.1 P38 calibration remains provisional.",
                "Physical grip, scale, recoil, reload, switch and wall checks are W3.3.",
            ]
            save_json(args.proof, compact)

    if (
        not receipt["complete"]
        or not receipt["source_saves_unchanged"]
        or not receipt["preferences_unchanged"]
        or receipt["remaining_game_pids"]
    ):
        raise RuntimeError("W3.2 comparison did not close cleanly")
    print(
        f"PASS: W3.2 P38 {args.mode} comparison, "
        f"{'desktop synthetic' if args.desktop else 'headset'}",
        flush=True,
    )


if __name__ == "__main__":
    main()
