"""Bounded synthetic XR action -> native pad/motion/release proof.

Uses build-release with debug tools temporarily enabled. Never edits saves.
The launcher owns null-HMD cleanup and restores the pre-run SteamVR settings.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import time

from sky_ghost_control import ROOT, command, game_pids, save


def read(address, size):
    return bytes.fromhex(command("read_ram", addr=hex(address), len=size)["hex"])


def actor():
    player = struct.unpack("<I", read(0x800AA17C, 4))[0]
    if not 0x80000000 <= player < 0x801FFC00:
        raise RuntimeError("No measured single-player actor")
    data = read(player + 0x220, 0x24)
    return {"player": hex(player), "position_fields": [struct.unpack_from("<i", data, i)[0]
            for i in (0, 8)], "rotation_fields": list(struct.unpack_from("<3h", data, 0x1C))}


def neutral(pad):
    return pad["buttons"] == "0xFFFF" and pad["sticks"] == [128] * 4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "--slot", type=int, default=2,
        help="isolated saves/openbios slot to load (default: SP regression slot 2)",
    )
    args = parser.parse_args()
    output = args.directory.resolve()
    output.mkdir(parents=True, exist_ok=False)
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic port already occupied")
    if game_pids():
        raise RuntimeError("Close the existing game before this owned test")
    settings = Path("C:/Program Files (x86)/Steam/config/steamvr.vrsettings")
    backup = settings.read_bytes()
    env = {k: v for k, v in os.environ.items() if not k.startswith(
        ("MOHU_VR_", "PSX_VR_", "PSX_OPENXR"))}
    env["PSX_RENDER_PASS_VERIFY"] = "1"
    result = {"synthetic": True, "atomic_queries": False, "fixture_slot": args.slot,
              "executable_sha256": hashlib.sha256((ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe").read_bytes()).hexdigest(),
              "samples": []}
    launch = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
              str(ROOT / "vr/run_vr.ps1"), "-Headless", "-Seconds", "40",
              "-DebugPort", "4372", "-LogDirectory", str(output),
              "-Slot", str(args.slot)]
    with (output / "launcher.stdout.log").open("w") as stdout, (output / "launcher.stderr.log").open("w") as stderr:
        process = subprocess.Popen(launch, cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 50
            while not (output / "openxr-smoke.json").exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("XR startup failed; inspect launcher logs")
                time.sleep(.2)
            state = command("savestate_status")
            if not state.get("last_ok"):
                raise RuntimeError("Ask the operator for a fresh PGXP slot")
            result["savestate"] = state
            counters_before = {
                row["name"]: row["count"]
                for row in command("mod_counters")["counters"]
            }
            result["calibration"] = {hex(a): read(a, n).hex() for a, n in
                                     ((0x800C47C8, 160), (0x800C4AA8, 72), (0x800AB12C, 128))}
            result["before"] = {name: command(name) for name in
                                ("openxr_stats", "stereo_stats", "render_pass_stats")}
            cases = [("neutral", {}), ("forward", {"ly": 1000}),
                     ("back", {"ly": -1000}), ("strafe-right", {"lx": 1000}),
                     ("strafe-left", {"lx": -1000}), ("turn-right", {"rx": 1000}),
                     ("turn-left", {"rx": -1000}), ("half-turn", {"rx": 600}),
                     ("diagonal", {"lx": 1000, "ly": 1000}),
                     ("focus-lost", {"lx": 1000, "rx": 1000, "right_trigger": 1000, "focused": 0}),
                     ("inactive", {"lx": 1000, "rx": 1000, "left_active": 0, "right_active": 0}),
                     ("fire-use-next", {"right_trigger": 1000, "right_buttons": 3}),
                     ("release", {})]
            for name, values in cases:
                command("openxr_input_override", **values)
                before = actor()
                time.sleep(.35)
                pad = command("pad_status")["slot0"]
                after = actor()
                sample = {"name": name, "actions": command("openxr_input"), "pad": pad,
                          "before": before, "after": after}
                result["samples"].append(sample)
                assert pad["analog"], sample
                if name in ("neutral", "focus-lost", "inactive", "release"):
                    assert neutral(pad), sample
                elif name in ("forward", "back"):
                    assert pad["sticks"][1] != 128 and pad["sticks"][0] == pad["sticks"][2] == 128, sample
                elif name.startswith("strafe"):
                    assert pad["sticks"][2] != 128 and pad["sticks"][0] == pad["sticks"][1] == 128, sample
                elif "turn" in name:
                    assert pad["sticks"][0] != 128 and pad["sticks"][1] == pad["sticks"][2] == 128, sample
                elif name == "fire-use-next":
                    assert pad["buttons"] == "0x1FFF", sample
                if name in ("forward", "back", "strafe-right", "strafe-left"):
                    assert before["position_fields"] != after["position_fields"], sample
                if name in ("turn-right", "turn-left"):
                    assert before["rotation_fields"] != after["rotation_fields"], sample
            command("openxr_input_override", clear=1)
            time.sleep(.25)
            result["cleared_pad"] = command("pad_status")["slot0"]
            assert neutral(result["cleared_pad"]), result["cleared_pad"]
            counters_after = {
                row["name"]: row["count"]
                for row in command("mod_counters")["counters"]
            }
            input_modes = {
                "sp": counters_after.get("mohu.vr.input.mode.sp", 0) -
                      counters_before.get("mohu.vr.input.mode.sp", 0),
                "mp": counters_after.get("mohu.vr.input.mode.mp", 0) -
                      counters_before.get("mohu.vr.input.mode.mp", 0),
                "menu": counters_after.get("mohu.vr.input.mode.menu", 0) -
                        counters_before.get("mohu.vr.input.mode.menu", 0),
                "render_time_samples":
                    counters_after.get("mohu.vr.input.render_blocked", 0) -
                    counters_before.get("mohu.vr.input.render_blocked", 0),
                "guard_fallbacks":
                    counters_after.get("mohu.vr.input.guard_fallback", 0) -
                    counters_before.get("mohu.vr.input.guard_fallback", 0),
            }
            result["input_mode_check"] = input_modes
            assert input_modes["sp"] > 0, input_modes
            assert input_modes["mp"] == 0, input_modes
            assert input_modes["render_time_samples"] == 0, input_modes
            assert input_modes["guard_fallbacks"] == 0, input_modes
            result["after"] = {name: command(name) for name in
                               ("openxr_stats", "stereo_stats", "render_pass_stats")}
            xr, stereo, checks = (result["after"][name] for name in
                                  ("openxr_stats", "stereo_stats", "render_pass_stats"))
            assert not xr["failures"] and not xr["empty"], xr
            assert not stereo["failed"] and stereo["pairs"] > result["before"]["stereo_stats"]["pairs"], stereo
            assert checks["verify_checks"] and not any(checks[k] for k in
                       ("verify_mismatch", "vram_leaks", "watchdog", "nesting_repairs")), checks
            result["passed"] = True
        finally:
            if process.poll() is None:
                try:
                    command("openxr_input_override", clear=1)
                except (OSError, RuntimeError):
                    pass
                process.wait(timeout=60)
            result["exit_code"] = process.returncode
            result["settings_restored"] = settings.read_bytes() == backup
            result["remaining_game_pids"] = game_pids()
            save(output / "receipt.json", result)
    assert result["exit_code"] == 0 and result["settings_restored"] and not result["remaining_game_pids"]
    print(json.dumps({k: result[k] for k in ("passed", "settings_restored", "remaining_game_pids")}))


if __name__ == "__main__":
    main()
