"""Exercise Underground's multiplayer controller bindings and lifecycle.

Launches copied multiplayer and single-player slots, records the live input
tables, and drives native pad actions through the framework controller source.
Writes only below the requested analysis directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import time

import inspect_weapon_sets as native


SP_PLAYER_ROOT = 0x800AA17C
MP_PLAYER_ROOT = 0x800A3604
CONVERTER = 0x80083C6C
CONVERTER_SIZE = 324
CONVERTER_HASH = 0x9CA131D0
DISPATCHER = 0x80083DB0
DISPATCHER_SIZE = 84
DISPATCHER_HASH = 0x2D93CB1C
SP_AXES = 0x800C47C8
SP_ACTIONS = 0x800C4AA8
SP_CURVE = 0x800AB12C
MP_CONVERTER = 0x800799E4
MP_CONVERTER_SIZE = 324
MP_DISPATCHER = 0x80079B28
MP_DISPATCHER_SIZE = 84
MP_AXES = 0x800C0BF0
MP_ACTIONS = 0x800C0ED0
MP_INVERSIONS = 0x800C0F20
MP_CURVE = 0x800A458C
MP_RAW_PAD = 0x800A9E00
MP_CONVERTER_HASH = 0x890B7F9F
MP_DISPATCHER_HASH = 0x9E630C72
MP_AXES_SHA256 = "55a8be31ca76c9d1219bb39dc6fe0c794cc52151c3c9f3f8ac1ec0328728e690"
MP_ACTIONS_SHA256 = "3979cabb60d68be209cf34dd702797504a68b39681f28cde4e1682869643f7dc"
MP_INVERSIONS_SHA256 = "496d31f9fe09a50a6c59d0a92ba417d3711a7e70648c82cee382a427b8f6d14f"
MP_CURVE_SHA256 = "856e2d9957e456645da61b67aab142f9711a06bd50ded980f4692f304813b017"

ACTION_LAYOUTS = (
    (0x40, 0x10, 0x20, 1, 0x80, 0x80, 0x800, 3, 2),
    (0x40, 0x10, 0x20, 1, 0x80, 0x80, 0x800, 0x200, 2),
)


def fnv1a(data):
    value = 2166136261
    for byte in data:
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value


def word(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def scan_patterns(start=0x80010000, end=0x801F0000, chunk_size=0x10000):
    actions = []
    axes = []
    cursor = start
    while cursor < end:
        size = min(chunk_size, end - cursor)
        data = native.read(cursor, size)
        for index in range(0, len(data) - 9 * 4 + 1, 4):
            values = struct.unpack_from("<9I", data, index)
            if values in ACTION_LAYOUTS:
                actions.append({
                    "address": f"0x{cursor + index:08X}",
                    "layout": [f"0x{value:X}" for value in values],
                })
        for index in range(0, len(data) - 160 + 1, 4):
            records = [
                struct.unpack_from("<10I", data, index + record * 40)
                for record in range(4)
            ]
            valid = all(
                record[0] in (2, 3, 0)
                and record[9] == 0
                and record[3] & 0xFF == 128
                and record[5]
                and record[6]
                and record[8]
                for record in records
            )
            native_axes = tuple(record[0] for record in records)
            if (
                valid
                and 2 in native_axes
                and 3 in native_axes
                and 0 in native_axes
            ):
                axes.append({
                    "address": f"0x{cursor + index:08X}",
                    "records": [
                        {
                            "native_axis": record[0],
                            "center": record[3] & 0xFF,
                            "negative_factor": record[5],
                            "positive_factor": record[6],
                            "scale": record[8],
                            "inversion": record[9],
                        }
                        for record in records
                    ],
                })
        cursor += size
    return actions, axes


def neutral(pad):
    return pad["buttons"] == "0xFFFF" and pad["sticks"] == [128] * 4


def counter_values():
    return {
        row["name"]: row["count"]
        for row in native.command("mod_counters")["counters"]
    }


def counter_delta(before, after):
    return {
        name: count - before.get(name, 0)
        for name, count in after.items()
        if count != before.get(name, 0)
    }


def wait_for_counter(name, before, max_frames=180):
    target = before.get(name, 0) + 1
    for _ in range(max_frames):
        native.frames(1)
        current = counter_values()
        if current.get(name, 0) >= target:
            return current
    raise RuntimeError(f"{name} did not advance within {max_frames} frames")


def wait_for_pairs(target, max_frames=180):
    for _ in range(max_frames):
        stats = native.command("stereo_stats")
        if stats["pairs"] >= target:
            return stats
        native.frames(1)
    raise RuntimeError(f"stereo pairs did not reach {target}")


def start_pulse(frames=6):
    before = counter_values()
    native.command("openxr_input_override", left_buttons=4)
    native.frames(frames)
    actions = native.command("openxr_input")
    pad = native.command("pad_status")["slot0"]
    after = counter_values()
    native.command("openxr_input_override", clear=1)
    native.frames(3)
    return {
        "actions": actions,
        "pad": pad,
        "counter_delta": counter_delta(before, after),
    }


def run_input_controls():
    command = native.command
    command("clear_input")
    command("set_input", layer="host", buttons=65535)
    try:
        before_counters = counter_values()
        cases = [
            ("neutral", {}, [128, 128, 128, 128], False, False),
            ("forward", {"ly": 1000}, [128, 1, 128, 128], True, False),
            ("back", {"ly": -1000}, [128, 254, 128, 128], True, False),
            ("strafe-right", {"lx": 1000}, [128, 128, 254, 128],
             True, False),
            ("strafe-left", {"lx": -1000}, [128, 128, 1, 128], True, False),
            ("turn-right", {"rx": 1000}, [245, 128, 128, 128], False, True),
            ("turn-left", {"rx": -1000}, [10, 128, 128, 128], False, True),
            ("focus-lost",
             {"ly": 1000, "rx": 1000, "right_trigger": 1000,
              "left_buttons": 15, "right_buttons": 3, "focused": 0},
             [128, 128, 128, 128], False, False),
            ("focus-recovered-forward", {"ly": 1000},
             [128, 1, 128, 128], True, False),
            ("inactive-sticks",
             {"ly": 1000, "rx": 1000, "left_active": 0, "right_active": 0},
             [128, 128, 128, 128], False, False),
        ]
        samples = []
        for name, values, expected_sticks, want_move, want_turn in cases:
            command("openxr_input_override", **values)
            before = native.players()[0]
            changed = []
            after = before
            for frame in range(1, 25):
                native.frames(1)
                after = native.players()[0]
                if (before["position"] != after["position"] or
                        before["rotation"] != after["rotation"]):
                    changed.append({
                        "frame": frame,
                        "position": after["position"],
                        "rotation": after["rotation"],
                    })
                if ((want_move and before["position"] != after["position"]) or
                        (want_turn and
                         before["rotation"] != after["rotation"])):
                    break
            pad = command("pad_status")["slot0"]
            sample = {
                "name": name,
                "actions": command("openxr_input"),
                "pad": pad,
                "before": before,
                "after": after,
                "changes": changed,
            }
            samples.append(sample)
            assert pad["sticks"] == expected_sticks, sample
            if name == "focus-lost" or name == "inactive-sticks":
                assert pad["buttons"] == "0xFFFF", sample
            if want_move:
                assert before["position"] != after["position"], sample
            if want_turn:
                assert before["rotation"] != after["rotation"], sample
            if not want_move and not want_turn:
                assert not changed, sample
            command("openxr_input_override", clear=1)
            native.frames(8)
            released = command("pad_status")["slot0"]
            sample["released"] = released
            assert neutral(released), sample

        button_cases = [
            ("cross-trigger", {"right_trigger": 1000}, "0xBFFF"),
            ("right-primary-square", {"right_buttons": 1}, "0x7FFF"),
            ("left-primary-square", {"left_buttons": 1}, "0x7FFF"),
            ("right-secondary-circle", {"right_buttons": 2}, "0xDFFF"),
            ("left-stick-triangle", {"left_buttons": 8}, "0xEFFF"),
            ("right-stick-l2", {"right_buttons": 8}, "0xFEFF"),
            ("combined-square-circle",
             {"right_buttons": 3}, "0x5FFF"),
        ]
        for name, values, expected_buttons in button_cases:
            command("openxr_input_override", **values)
            native.frames(3)
            pad = command("pad_status")["slot0"]
            sample = {
                "name": name,
                "actions": command("openxr_input"),
                "pad": pad,
            }
            samples.append(sample)
            assert pad["buttons"] == expected_buttons, sample
            command("openxr_input_override", clear=1)
            native.frames(3)
            released = command("pad_status")["slot0"]
            sample["released"] = released
            assert neutral(released), sample

        after_counters = counter_values()
        delta = counter_delta(before_counters, after_counters)
        checks = {
            "samples": len(samples),
            "callback_samples": delta.get("mohu.vr.input.callback", 0),
            "mp_samples": delta.get("mohu.vr.input.mode.mp", 0),
            "focus_lost_samples":
                delta.get("mohu.vr.input.focus_lost", 0),
            "render_time_samples":
                delta.get("mohu.vr.input.render_blocked", 0),
            "guard_fallbacks":
                delta.get("mohu.vr.input.guard_fallback", 0),
        }
        assert checks["callback_samples"] > 0, checks
        assert checks["mp_samples"] > 0, checks
        assert checks["focus_lost_samples"] > 0, checks
        assert checks["render_time_samples"] == 0, checks
        assert checks["guard_fallbacks"] == 0, checks
        return {
            "samples": samples,
            "counter_delta": delta,
            "checks": checks,
        }
    finally:
        native.command("openxr_input_override", clear=1)
        native.frames(4)
        native.command("set_input", layer="host", buttons=65535)


def run_lifecycle_controls():
    command = native.command
    command("openxr_input_override", clear=1)
    command("set_input", layer="host", buttons=65535)
    native.frames(8)
    before = {
        "stereo": command("stereo_stats"),
        "counters": counter_values(),
        "player": native.players()[0],
    }

    pause_sample = start_pulse()
    pause_pad = pause_sample["pad"]
    assert pause_pad["buttons"] == "0xFFF7", pause_sample
    native.frames(15)
    paused = {"stereo": command("stereo_stats")}
    paused_pad = command("pad_status")["slot0"]
    assert neutral(paused_pad), paused_pad

    paused_before = native.players()[0]
    command("openxr_input_override", ly=1000)
    native.frames(16)
    paused_after = native.players()[0]
    held_pad = command("pad_status")["slot0"]
    command("openxr_input_override", clear=1)
    native.frames(3)
    assert held_pad["sticks"][1] != 128, held_pad
    assert paused_before["position"] == paused_after["position"], {
        "before": paused_before,
        "after": paused_after,
    }

    paused["counters"] = counter_values()
    resume_start_sample = start_pulse()
    assert resume_start_sample["pad"]["buttons"] == "0xFFF7", \
        resume_start_sample
    native.frames(20)
    resumed_stereo = command("stereo_stats")
    resumed_counters = counter_values()

    resume_before = native.players()[0]
    command("openxr_input_override", ly=1000)
    native.frames(16)
    resume_after = native.players()[0]
    resume_forward_pad = command("pad_status")["slot0"]
    command("openxr_input_override", clear=1)
    native.frames(3)
    assert resume_forward_pad["sticks"][1] != 128, resume_forward_pad
    assert resume_before["position"] != resume_after["position"], {
        "before": resume_before,
        "after": resume_after,
    }
    render_blocked = (
        resumed_counters.get("mohu.vr.input.render_blocked", 0) -
        before["counters"].get("mohu.vr.input.render_blocked", 0)
    )
    assert render_blocked == 0, render_blocked

    return {
        "start": before,
        "pause_start": pause_sample,
        "paused": paused,
        "paused_forward_held": {
            "before": paused_before,
            "after": paused_after,
            "pad": held_pad,
            "position_unchanged": True,
        },
        "resumed": {
            "start": resume_start_sample,
            "forward_pad": resume_forward_pad,
            "stereo": resumed_stereo,
            "forward_before": resume_before,
            "forward_after": resume_after,
            "position_changed": True,
        },
        "counter_delta": counter_delta(
            before["counters"], resumed_counters
        ),
        "render_time_samples": render_blocked,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic port 4372 is occupied")

    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    copies = out / "saves/openbios"
    copies.mkdir(parents=True)
    sources = []
    for suffix in ("pst", "thumb"):
        source = native.ROOT / f"analysis/fixtures/mp/openbios/state_8001F844_slot01.{suffix}"
        shutil.copyfile(source, copies / source.name)
        sources.append(source)
    source_hashes = {str(path): native.digest(path) for path in sources}
    preferences = [
        native.ROOT / "build-release/settings.toml",
        native.ROOT / "build-release/keybinds.ini",
        Path("C:/Program Files (x86)/Steam/config/steamvr.vrsettings"),
    ]
    preference_hashes = {
        str(path): native.digest(path) for path in preferences if path.exists()
    }
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("PSX_", "MOHU_VR_"))
    }
    env.update(
        PSX_DEV_INPUT="0",
        PSX_VSYNC="0",
        PSX_OPENXR_ENABLE="0",
        PSX_STEREO_SHED="0",
        PSX_RENDER_PASS_VERIFY="1",
        PSX_VR_MOVEMENT="1",
        MOHU_VR_MP_CONTROL="1",
        MOHU_VR_STEREO_PROOF="1",
        MOHU_VR_EYE_RENDER_VIEW="1",
        MOHU_VR_EYE_GUEST_SUBMIT="1",
        MOHU_VR_EYE_OFFSET="0",
    )
    executable = (
        native.ROOT
        / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    )
    receipt = {
        "complete": False,
        "synthetic": True,
        "executable_sha256": native.digest(executable),
        "source_saves": source_hashes,
        "preferences": preference_hashes,
    }
    with (
        (out / "stdout.log").open("w") as stdout,
        (out / "stderr.log").open("w") as stderr,
    ):
        process = subprocess.Popen(
            [
                str(executable),
                "--headless-opengl",
                "--no-launcher",
                "--game",
                str(native.ROOT / "analysis/vr-baseline/game-interp.toml"),
                "--memcard-dir",
                str(out / "saves"),
                "--debug-port",
                "4372",
            ],
            cwd=out,
            env=env,
            stdout=stdout,
            stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            deadline = time.monotonic() + 40
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Diagnostic game exited during startup")
                try:
                    native.command("ping")
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.1)
            native.load(1)
            players = native.players()
            outputs = {}
            for name, address, size in (
                ("sp_converter", CONVERTER, CONVERTER_SIZE),
                ("sp_dispatcher", DISPATCHER, DISPATCHER_SIZE),
                ("sp_axes", SP_AXES, 160),
                ("sp_actions", SP_ACTIONS, 72),
                ("sp_curve", SP_CURVE, 128),
                ("mp_converter", MP_CONVERTER, MP_CONVERTER_SIZE),
                ("mp_dispatcher", MP_DISPATCHER, MP_DISPATCHER_SIZE),
                ("mp_axes", MP_AXES, 160),
                ("mp_axes_config1", MP_AXES + 160, 160),
                ("mp_actions", MP_ACTIONS, 72),
                ("mp_action_extension", MP_ACTIONS + 72, 8),
                ("mp_inversions", MP_INVERSIONS, 72),
                ("mp_curve", MP_CURVE, 128),
                ("mp_raw_pad", MP_RAW_PAD, 4),
                ("mp_input_enabled", 0x800A4578, 4),
            ):
                data = native.read(address, size)
                outputs[name] = {
                    "address": f"0x{address:08X}",
                    "size": size,
                    "fnv1a": f"0x{fnv1a(data):08X}",
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "hex": data.hex(),
                }
            actions, axes = scan_patterns()
            mp_actor = word(native.read(MP_PLAYER_ROOT, 4), 0)
            sp_actor = word(native.read(SP_PLAYER_ROOT, 4), 0)
            mp_current = word(native.read(0x800A35C4, 4), 0)
            mp_camera = word(native.read(0x800A35B0, 4), 0)
            mp_context = native.read(0x800A0B08, 12)
            receipt.update(
                players=players,
                ownership={
                    "mp_root": f"0x{MP_PLAYER_ROOT:08X}",
                    "mp_actor": f"0x{mp_actor:08X}",
                    "sp_root": f"0x{SP_PLAYER_ROOT:08X}",
                    "sp_actor": f"0x{sp_actor:08X}",
                    "mp_player_input": players[0]["input"],
                    "mp_current_player": f"0x{mp_current:08X}",
                    "mp_camera": f"0x{mp_camera:08X}",
                    "mp_context": {
                        "width": word(mp_context, 0),
                        "height": word(mp_context, 4),
                        "focal": word(mp_context, 8),
                    },
                },
                live=outputs,
                action_patterns=actions,
                axis_patterns=axes,
            )
            receipt["sp_converter_matches"] = (
                outputs["sp_converter"]["fnv1a"] == f"0x{CONVERTER_HASH:08X}"
            )
            receipt["sp_dispatcher_matches"] = (
                outputs["sp_dispatcher"]["fnv1a"] == f"0x{DISPATCHER_HASH:08X}"
            )
            receipt["mp_converter_matches"] = (
                outputs["mp_converter"]["fnv1a"] == f"0x{MP_CONVERTER_HASH:08X}"
            )
            receipt["mp_dispatcher_matches"] = (
                outputs["mp_dispatcher"]["fnv1a"] == f"0x{MP_DISPATCHER_HASH:08X}"
            )
            receipt["mp_axes_match"] = outputs["mp_axes"]["sha256"] == MP_AXES_SHA256
            receipt["mp_actions_match"] = (
                outputs["mp_actions"]["sha256"] == MP_ACTIONS_SHA256
            )
            receipt["mp_inversions_match"] = (
                outputs["mp_inversions"]["sha256"] == MP_INVERSIONS_SHA256
            )
            receipt["mp_curve_match"] = (
                outputs["mp_curve"]["sha256"] == MP_CURVE_SHA256
            )
            receipt["input_controls"] = run_input_controls()
            receipt["lifecycle_controls"] = run_lifecycle_controls()
            receipt["complete"] = all((
                receipt["mp_converter_matches"],
                receipt["mp_dispatcher_matches"],
                receipt["mp_axes_match"],
                receipt["mp_actions_match"],
                receipt["mp_inversions_match"],
                receipt["mp_curve_match"],
                receipt["input_controls"]["checks"]["render_time_samples"] == 0,
                receipt["input_controls"]["checks"]["guard_fallbacks"] == 0,
                receipt["lifecycle_controls"]["render_time_samples"] == 0,
            ))
            if not receipt["complete"]:
                raise RuntimeError("Measured MP input binding no longer matches")
        finally:
            if process.poll() is None:
                try:
                    native.command("quit")
                except (RuntimeError, OSError):
                    pass
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=8)
            receipt["exit_code"] = process.returncode
            receipt["source_saves_unchanged"] = all(
                native.digest(Path(path)) == digest
                for path, digest in source_hashes.items()
            )
            receipt["preferences_unchanged"] = all(
                native.digest(Path(path)) == digest
                for path, digest in preference_hashes.items()
            )
            receipt["remaining_game_pids"] = native.game_pids()
            native.save(out / "receipt.json", receipt)
    print(json.dumps({
        key: receipt[key] for key in (
            "complete",
            "sp_converter_matches",
            "sp_dispatcher_matches",
            "mp_converter_matches",
            "mp_dispatcher_matches",
            "mp_axes_match",
            "mp_actions_match",
            "mp_inversions_match",
            "mp_curve_match",
            "ownership",
            "action_patterns",
            "axis_patterns",
        )
    }, indent=2))


if __name__ == "__main__":
    main()
