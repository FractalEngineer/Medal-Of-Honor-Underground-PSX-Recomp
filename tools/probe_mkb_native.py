"""Collect Underground native aim evidence in an isolated flat test session.

Only copied saves are loaded. This is a research tool, not a mouse mod or a
production input path. No VR activation, code patches, or source-save writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vr/tools"))
import inspect_weapon_sets as native
import probe_p38_headset as shared

RESEARCH_CASES = [
    ("readonly", 0, 0, 0),
    ("entry_yaw", 0x800892C8, 32, 0), ("look_yaw", 0x8008F984, 32, 0),
    ("adjust_yaw", 0x8008F9BC, 32, 0), ("entry_pitch", 0x800892C8, 0, 32),
    ("look_pitch", 0x8008F984, 0, 32), ("adjust_pitch", 0x8008F9BC, 0, 32),
    ("fire_base", 0, 0, 0), ("fire_entry_yaw", 0x800892C8, 32, 0),
    ("fire_settled_yaw", 0, 0, 0),
    ("scene_order", 0, 0, 0),
    ("camera_order", 0x8004A744, 0, 0),
    ("camera_yaw", 0x8004A744, 32, 0),
    ("camera_yaw_wrap", 0x8004A744, 256, 0),
    ("camera_yaw_negative", 0x8004A744, -32, 0),
    ("camera_pitch_negative", 0x8004A744, 0, -32),
    ("fire_camera_base", 0x8004A744, 0, 0),
    ("fire_camera_yaw", 0x8004A744, 32, 0),
    ("fire_camera_pitch", 0x8004A744, 0, 32),
    ("fire_camera_yaw_negative", 0x8004A744, -32, 0),
    ("fire_camera_pitch_negative", 0x8004A744, 0, -32),
    ("fire_camera_pitch_large", 0x8004A744, 0, 64),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--slot", type=int, choices=range(12), default=3)
    parser.add_argument("--cold", action="store_true", help="Reach gameplay through native menus instead of loading a save")
    parser.add_argument("--fixtures", type=Path, default=ROOT / "saves/openbios")
    parser.add_argument("--inject", action="store_true", help="Research only: perturb the statically traced native aim targets")
    parser.add_argument("--trace-only", action="store_true", help="Collect a short native action/aim call window without angle perturbations")
    parser.add_argument("--research", action="store_true", help="Run the separately built one-update research harness")
    parser.add_argument("--research-direct", action="store_true", help="Explicitly test the native direct-target branch in the research harness")
    parser.add_argument("--research-prepare", action="store_true", help="Research only: prepare the native camera pitch before its callback")
    parser.add_argument("--gate-fire", action="store_true", help="Wait for the native sampled button word before starting a firing window")
    parser.add_argument("--aim-states", action="store_true", help="Capture native neutral/R2/Cross states and movement")
    parser.add_argument("--dump-hud", action="store_true", help="Read campaign HUD code for the render-only crosshair gate")
    parser.add_argument("--exe", type=Path, default=ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe")
    parser.add_argument("--gameplay-checks", action="store_true", help="Check final host-pad R2 suppression, movement, look and fire")
    parser.add_argument("--direct-checks", action="store_true", help="Check direct displacement, no drift, native switching and reload")
    parser.add_argument("--sensitivity", type=float, default=50,
                        help="Mouse sensitivity percent selected in the MKB mod (direct checks)")
    parser.add_argument("--camera-writes", action="store_true", help="Trace native camera-matrix stores around each research window")
    parser.add_argument("--camera-target-writes", action="store_true", help="Trace camera look-at target stores instead of its matrix")
    parser.add_argument("--research-cases", nargs="+", choices=[x[0] for x in RESEARCH_CASES])
    parser.add_argument("--interpreter", action="store_true", help="Request diagnostic interpreter controls")
    args = parser.parse_args()
    if native.game_pids():
        raise RuntimeError("Existing game session; leave it untouched")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    target = out / "saves/openbios"
    target.mkdir(parents=True)
    source = args.fixtures.resolve()
    fixtures = [] if args.cold else sorted(source.glob(f"*slot{args.slot:02}.*"))
    if not args.cold and sorted(p.suffix for p in fixtures) != [".pst", ".thumb"]:
        raise RuntimeError("Expected one operator fixture and thumbnail")
    hashes = {str(p): native.digest(p) for p in fixtures}
    for path in fixtures:
        shutil.copyfile(path, target / path.name)
    preferences = shared.hash_existing(shared.preference_paths())
    exe = args.exe.resolve()
    env = shared.clean_environment(os.environ)
    env.update(SDL_AUDIODRIVER="dummy", PSX_DEV_INPUT="0", PSX_LOAD_SLOT="-1")
    config = ROOT / "game.toml"
    if args.interpreter:
        env["PSX_OVERLAY_NATIVE_OFF"] = "1"
        contents = config.read_text(encoding="utf-8")
        contents, changes = re.subn(r"(?m)^overlay_cache\s*=\s*true$", "overlay_cache = false", contents)
        if changes != 1:
            raise RuntimeError("Expected one overlay cache configuration")
        contents = re.sub(r'(?m)^exe = .*$', lambda _: 'exe = ' + json.dumps(str(ROOT / 'disc/SLUS_012.70')), contents)
        config = out / "game-interpreter.toml"
        config.write_text(contents, encoding="utf-8")
    receipt = dict(collection_complete=False, native_mouse_aim_verified=False,
                   call_order_verified=False,
                   binary_sha256=native.digest(exe), source_hashes=hashes,
                   config_sha256=native.digest(config),
                   vr_requested=False, interpreter_diagnostic=args.interpreter,
                   research_direct=args.research_direct, research_schema=5,
                   research_prepare=args.research_prepare, gated_fire=args.gate_fire,
                   aim_states=[], samples=[])
    if args.research:
        receipt["research_source_sha256"] = native.digest(ROOT / "controls/research/moh_mkb_research.c")

    def snapshot(label):
        player = int.from_bytes(native.read(0x800AA17C, 4), "little")
        if not 0x800B0000 <= player <= 0x801FC000:
            raise RuntimeError(f"Invalid SP player {player:#x}")
        data = native.read(player, 0x500)
        if player & 3 or struct.unpack_from("<I", data, 8)[0] != 1:
            raise RuntimeError("SP root does not own a player actor")
        (out / f"{label}.actor.bin").write_bytes(data)
        inp = struct.unpack_from("<I", data, 0x39C)[0]
        if inp != player + 0x3FC:
            raise RuntimeError("Unrecognized campaign input layout")
        code = native.read(0x800892C8, 0xF20)
        if hashlib.sha256(code).hexdigest() != "6517965996647b2589bf95f282f5c3bd7f1b8c6bf0118b0a3b6495960e16d401":
            raise RuntimeError("Unsupported single-player overlay")
        controls = native.read(inp, 0x300)
        (out / f"{label}.input.bin").write_bytes(controls)
        row = dict(label=label, frame=native.command("frame"), player=hex(player),
                   input=hex(inp), pad=native.command("pad_status"),
                   position=struct.unpack_from("<3i", data, 0x220),
                   rotation_q16=struct.unpack_from("<3i", data, 0x23C),
                   rotation_velocity_q16=struct.unpack_from("<3i", data, 0x248),
                   input_flags=hex(struct.unpack_from("<I", controls)[0]),
                   aim_pitch_q16=struct.unpack_from("<i", controls, 0x184)[0],
                   aim_yaw_q16=struct.unpack_from("<i", controls, 0x190)[0],
                   weapon_id=controls[93],
                   weapon_slot=controls[92],
                   clip=struct.unpack_from("<h", controls, 0x6E + 2 * controls[92])[0] if controls[92] < 8 else None,
                   pause=int.from_bytes(native.read(0x800A70F0, 4), "little"))
        receipt["samples"].append(row)
        print(json.dumps({k: v for k, v in row.items() if k != "pad"}), flush=True)
        return row

    with (out / "stdout.log").open("w") as so, (out / "stderr.log").open("w") as se:
        proc = subprocess.Popen([
            str(exe), "--no-launcher", "--headless-opengl", "--game", str(config),
            "--disc", str(ROOT / "Medal of Honor - Underground/Medal of Honor - Underground (USA).cue"),
            "--memcard-dir", str(out / "saves"), "--debug-port", "4372"],
            cwd=out, env=env, stdout=so, stderr=se, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            shared.wait_for_ping(proc)
            if args.cold:
                native.command("set_input", buttons="0xffff")
                native.frames(1200)
                receipt["menu_inputs"] = []
                for buttons in ["0xfff7"] * 4 + ["0xbfff"] * 12:
                    player = int.from_bytes(native.read(0x800AA17C, 4), "little")
                    if 0x800B0000 <= player <= 0x801FC000 and int.from_bytes(native.read(player + 8, 4), "little") == 1:
                        break
                    receipt["menu_inputs"].append(dict(buttons=buttons, frame=native.command("frame")))
                    native.command("set_input", buttons=buttons)
                    native.frames(5)
                    native.command("set_input", buttons="0xffff")
                    native.frames(150)
                native.frames(120)
            else:
                receipt["load"] = native.load(args.slot)
            native.command("set_input", buttons="0xffff", pad_type=1, lx=128, ly=128, rx=128, ry=128)
            native.frames(90)
            neutral = snapshot("neutral")
            if args.direct_checks:
                native.command("clear_input")
                native.command("set_input", layer="host", buttons=0xffff, pad_type=1,
                               lx=128, ly=128, rx=128, ry=128)

                def direct(label, dx, dy):
                    info = native.command("mod_cmd", name="mohu.mkb.test", args=f"motion {dx} {dy}")
                    if info["result"] != 1:
                        raise RuntimeError(f"Direct command rejected: {info}")
                    native.frames(8)
                    return snapshot(label)

                base = direct("direct_zero", 0, 0)
                turned = direct("direct_yaw", 32, 0)
                native.frames(90)
                idle = snapshot("direct_idle")
                pitched = direct("direct_pitch", 0, -32)
                fast = direct("direct_fast", 200, 0)
                returned = direct("direct_return", -232, 32)
                wrap = 4096 * 65536
                checks = {
                    "yaw_exact": abs((turned["rotation_q16"][1] - base["rotation_q16"][1]) % wrap - 32 * 65536 * args.sensitivity / 100) <= 1,
                    "no_idle_drift": idle["rotation_q16"] == turned["rotation_q16"],
                    "pitch_exact": abs(pitched["rotation_q16"][0] - idle["rotation_q16"][0] - 32 * 65536 * args.sensitivity / 100) <= 1,
                    "fast_flick_not_stick_capped": abs((fast["rotation_q16"][1] - pitched["rotation_q16"][1]) % wrap - 200 * 65536 * args.sensitivity / 100) <= 1,
                    "return_exact": returned["rotation_q16"] == base["rotation_q16"],
                }
                native.command("screenshot_hires", path=str(out / "direct-look.png"))
                native.command("set_input", layer="host", buttons=0xbfff,
                               lx=128, ly=128, rx=128, ry=128)
                native.frames(10)
                native.command("set_input", layer="host", buttons=0xffff)
                native.frames(30)
                fired = snapshot("direct_fire")
                checks["native_fire"] = fired["clip"] < returned["clip"]
                native.command("set_input", layer="host", buttons=0x7fff)
                native.frames(90)
                native.command("set_input", layer="host", buttons=0xffff)
                native.frames(30)
                reloaded = snapshot("direct_reload")
                checks["native_reload"] = reloaded["clip"] > fired["clip"]
                inp = int(reloaded["input"], 16)
                count = int.from_bytes(native.read(0x800AB5B4, 4), "little")
                reserves = list(struct.unpack("<8h", native.read(inp + 0x5e, 16)))
                receipt["weapon_inventory"] = dict(count=count, reserves=reserves)
                owned = [i for i in range(min(count, 8)) if reserves[i] != -1]
                if len(owned) > 1:
                    current = reloaded["weapon_slot"]
                    target = next(i for i in owned if i != current)
                    native.command("mod_cmd", name="mohu.mkb.test", args=f"select {target + 1}")
                    native.frames(90)
                    selected = snapshot("number_select")
                    checks["number_select"] = selected["weapon_slot"] == target
                    native.command("mod_cmd", name="mohu.mkb.test", args="wheel -1")
                    native.frames(90)
                    previous = snapshot("wheel_previous")
                    expected = owned[(owned.index(target) - 1) % len(owned)]
                    checks["wheel_previous"] = previous["weapon_slot"] == expected
                    native.command("mod_cmd", name="mohu.mkb.test", args="wheel 1")
                    native.frames(90)
                    following = snapshot("wheel_next")
                    checks["wheel_next"] = following["weapon_slot"] == target
                receipt["direct_checks"] = checks
                receipt["mod_counters"] = native.command("mod_counters")
                native.command("mod_cmd", name="mohu.mkb.test", args="release")
                if not all(checks.values()):
                    raise RuntimeError("Direct-control check failed; inspect receipt")
                receipt["collection_complete"] = True
                return
            if args.gameplay_checks:
                native.command("savestate", op="save", slot=0)
                native.frames(15)
                receipt["saved_fixture"] = native.command("savestate_status")
                if receipt["saved_fixture"]["pending"] or not receipt["saved_fixture"]["last_ok"]:
                    raise RuntimeError("Compatible fixture save did not complete")
                native.command("clear_input")

                def host_sample(label, *, buttons=0xffff, lx=128, ly=128, rx=128, ry=128, frames=30):
                    native.command("set_input", layer="host", buttons=buttons,
                                   pad_type=1, lx=lx, ly=ly, rx=rx, ry=ry)
                    native.frames(frames)
                    row = snapshot(label)
                    native.command("screenshot_hires", path=str(out / f"{label}.png"))
                    return row

                start = host_sample("host_neutral")
                moved = host_sample("rmb_forward", buttons=0xfdff, ly=0, frames=45)
                settled = host_sample("host_settled")
                looked = host_sample("host_look", lx=220, frames=24)
                before_fire = host_sample("before_fire")
                fired = host_sample("host_fire", buttons=0xbfff, frames=10)
                released = host_sample("host_release")
                receipt["gameplay_checks"] = {
                    "rmb_allows_movement": moved["position"] != start["position"],
                    "rmb_does_not_enter_aim": not (int(moved["input_flags"], 16) & 0x20),
                    "final_pad_releases_r2": bool(int(moved["pad"]["slot0"]["buttons"], 16) & 0x200),
                    "native_look_changes_yaw_target": looked["aim_yaw_q16"] != settled["aim_yaw_q16"],
                    "native_fire_uses_ammo": fired["clip"] < before_fire["clip"],
                    "release_keeps_ammo": released["clip"] == fired["clip"],
                }
                receipt["mod_counters"] = native.command("mod_counters")
                if not all(receipt["gameplay_checks"].values()):
                    raise RuntimeError("Gameplay check failed; inspect receipt")
                receipt["collection_complete"] = True
                return
            if args.dump_hud:
                for label, address, size in [("campaign", 0x800892C8, 0x6E00),
                                             ("hud", 0x8006C874, 0x4CC)]:
                    (out / f"{label}.code.bin").write_bytes(native.read(address, size))
                receipt["hud_disasm"] = native.command("disasm", addr="0x8008f9f4", count=128)
                receipt["mod_counters"] = native.command("mod_counters")
                native.command("screenshot_hires", path=str(out / "neutral.png"))
                receipt["collection_complete"] = True
                return
            if args.aim_states:
                def aim_word(*buttons):
                    word = 0xffff
                    for button in buttons:
                        word &= ~button
                    return f"0x{word:04x}"

                def aim_capture(label, buttons, *, ly=128, frames=24):
                    native.command("set_input", buttons=buttons, pad_type=1,
                                   lx=128, ly=ly, rx=128, ry=128)
                    native.frames(frames)
                    path = out / f"{label}.png"
                    info = native.command("screenshot_hires", path=str(path))
                    if not path.is_file():
                        raise RuntimeError(f"Missing aim-state frame: {info}")
                    native.frames(30)
                    row = snapshot(label)
                    row["screenshot"] = dict(
                        file=path.name, sha256=native.digest(path),
                        bytes=path.stat().st_size, **info)
                    receipt["aim_states"].append(row)
                    return row

                neutral = aim_capture("neutral", "0xffff")
                aim = aim_capture("aim", aim_word(0x0200))
                fire_state = aim_capture("fire", aim_word(0x4000))
                aim_fire = aim_capture("aim_fire", aim_word(0x0200, 0x4000))
                forward = aim_capture("forward", "0xffff", ly=0, frames=45)
                native.command("set_input", buttons="0xffff", pad_type=1,
                               lx=128, ly=128, rx=128, ry=128)
                native.frames(30)
                forward_settled = snapshot("forward_settled")
                aim_forward_start = snapshot("aim_forward_start")
                aim_forward = aim_capture(
                    "aim_forward", aim_word(0x0200), ly=0, frames=45)
                native.command("set_input", buttons="0xffff", pad_type=1,
                               lx=128, ly=128, rx=128, ry=128)
                native.frames(30)
                aim_forward_settled = snapshot("aim_forward_settled")
                receipt.update(
                    aim_changed_pose=(
                        aim["position"] != neutral["position"] or
                        aim["rotation_q16"] != neutral["rotation_q16"]),
                    aim_fire_constructed=aim_fire["clip"] != aim["clip"],
                    single_fire_constructed=fire_state["clip"] != neutral["clip"],
                    movement=dict(
                        neutral_forward_delta=[
                            forward_settled["position"][axis] - neutral["position"][axis]
                            for axis in range(3)],
                        aim_forward_delta=[
                            aim_forward_settled["position"][axis] - aim_forward_start["position"][axis]
                            for axis in range(3)]),
                    collection_complete=True)
                return
            if args.research:
                receipt["rejected_commands"] = []
                for invalid in ["arm 0", "arm 17", "inject 1 1 0", "inject 800892c8 257 0", "inject 0 1 0", "inject 800892c8 1 0 trailing", "direct 2", "refresh 2", "prepare 2", "fire_gate 2"]:
                    result = native.command("mod_cmd", name="mohu.mkb.research", args=invalid)
                    if result["result"] != 0:
                        raise RuntimeError(f"Invalid research command accepted: {invalid}: {result}")
                    receipt["rejected_commands"].append(invalid)
                def research_command(value):
                    result = native.command("mod_cmd", name="mohu.mkb.research", args=value)
                    if result["result"] != 1:
                        raise RuntimeError(result)
                    return json.loads(result["reply"])
                def capture(value, fire=False, frame_path=None):
                    research_command(f"fire_gate {int(fire and args.gate_fire)}")
                    armed = research_command(value)
                    if armed != {"armed": True}:
                        raise RuntimeError(f"Research harness not armed: {armed}")
                    if fire:
                        native.command("set_input", buttons="0xbfff", pad_type=1)
                    deadline = time.monotonic() + 10
                    released = False
                    frame = None

                    def capture_frame():
                        if not fire or frame_path is None:
                            return None
                        if not frame_path.exists():
                            info = native.command("screenshot_hires", path=str(frame_path))
                            if not frame_path.is_file():
                                raise RuntimeError(f"Endpoint screenshot missing: {info}")
                        return dict(file=frame_path.name, sha256=native.digest(frame_path),
                                    bytes=frame_path.stat().st_size, **info)

                    while time.monotonic() < deadline:
                        result = research_command("dump")
                        if fire and not released and result.get("shot_seen"):
                            # Keep observing the first blip, but do not hold the
                            # trigger long enough to consume a second round.
                            native.command("set_input", buttons="0xffff", pad_type=1)
                            released = True
                        if fire and frame is None and result.get("shot_released"):
                            frame = capture_frame()
                        if result.get("state") == 3:
                            if fire and not released:
                                native.command("set_input", buttons="0xffff", pad_type=1)
                            if fire and frame is None:
                                frame = capture_frame()
                            result["rows"] = [research_command(f"row {i}")["values"] for i in range(result["count"])]
                            result["frame"] = frame
                            return result
                        time.sleep(.02)
                    raise TimeoutError("No complete owned player update observed")
                receipt["research"] = []
                for name, site, yaw, pitch in RESEARCH_CASES:
                    if args.research_cases and name not in args.research_cases:
                        continue
                    if name != "readonly":
                        native.load(args.slot)
                        native.command("set_input", buttons="0xffff", pad_type=1)
                        native.frames(90)
                        if int.from_bytes(native.read(0x800A70F0, 4), "little") == 1:
                            # Restoring pad presentation can enter the game's
                            # native pause screen. Resume with native Start;
                            # never edit the pause flag or snapshot identity.
                            native.command("set_input", buttons="0xfff7", pad_type=1)
                            native.frames(6)
                            native.command("set_input", buttons="0xffff", pad_type=1)
                            native.frames(30)
                    before = snapshot(name + "_before")
                    if before["pause"]:
                        raise RuntimeError("Native campaign is paused; no research write armed")
                    if args.research_direct:
                        research_command("direct 1")
                        native.frames(6)
                        before = snapshot(name + "_direct_before")
                    if args.research_prepare:
                        research_command("prepare 1")
                    if args.camera_writes or args.camera_target_writes:
                        camera = int.from_bytes(native.read(0x800AA160, 4), "little")
                        camera_input = int.from_bytes(native.read(camera + 0x39C, 4), "little")
                        (out / f"{name}.camera-before.bin").write_bytes(native.read(camera, 0x600))
                        offset, size = (0, 12) if args.camera_target_writes else (0x100, 0x20)
                        native.command("wtrace_range", lo=hex(camera_input + offset), hi=hex(camera_input + offset + size))
                        native.command("wtrace_clear")
                    preparation = None
                    if name == "fire_settled_yaw":
                        preparation = capture("inject 800892c8 32 0")
                        native.frames(30)
                        before = snapshot(name + "_prepared")
                    fire = name.startswith("fire_")
                    updates = (16 if fire else
                               4 if name in ("scene_order", "camera_order", "camera_yaw") else 1)
                    command = "arm" if not site else f"inject {site:x} {yaw} {pitch}"
                    if updates != 1:
                        command = f"arm {updates}" if not site else command + f" {updates}"
                    result = capture(
                        command,
                        fire,
                        out / f"{name}.endpoint.png" if fire else None,
                    )
                    if args.camera_writes or args.camera_target_writes:
                        (out / f"{name}.camera-writes.json").write_text(json.dumps(native.command("wtrace_dump", count=256), indent=2) + "\n")
                        (out / f"{name}.camera-after.bin").write_bytes(native.read(camera, 0x600))
                    native.frames(120)
                    after = snapshot(name + "_settled")
                    receipt["research"].append(dict(name=name, request=dict(site=site, yaw=yaw, pitch=pitch, updates=updates), preparation=preparation, before=before, observation=result, after=after))
                    print(json.dumps(dict(name=name, rows=len(result["rows"]), applied=result["applied"], rejected=result["rejected"])), flush=True)
                receipt["collection_complete"] = True
                return
            def collect_call_order():
                # Compiled log_call_entry forwards virtual addresses unchanged.
                # The earlier physical filter excluded every KSEG0 callback.
                native.command("fn_filter", lo="0x80076000", hi="0x80090000")
                native.command("fn_clear")
                watched = "0x800892C8,0x8008EAF0,0x80078FBC,0x80076C28,0x8008AD04,0x8008D81C"
                receipt["watched_targets"] = native.command("xprobe_watch", targets=watched)
                player = int.from_bytes(native.read(0x800AA17C, 4), "little")
                ray = int.from_bytes(native.read(player + 0x39C, 4), "little") + 0x1A4
                native.command("wtrace_range", lo=hex(ray), hi=hex(ray + 24))
                native.command("wtrace_clear")
                receipt["overlay_before"] = native.command("overlay_native_ring")["ring"]
                native.command("set_input", buttons="0xbfff", pad_type=1)
                native.frames(6)
                native.command("set_input", buttons="0xffff", pad_type=1)
                trace = native.command("fn_entry_dump", count=2048)
                receipt["trace_stats"] = native.command("fn_stats")
                native.command("fn_disable")
                receipt["overlay_after"] = native.command("overlay_native_ring")["ring"]
                (out / "aim_ray_writes.json").write_text(json.dumps(native.command("wtrace_dump", count=256), indent=2) + "\n")
                (out / "aim_dirty_flow.json").write_text(json.dumps(native.command("dirty_flow_log", target_lo="0x80076000", target_hi="0x80090000", count=256), indent=2) + "\n")
                (out / "aim_call_order.json").write_text(json.dumps(trace, indent=2) + "\n")
                internal = native.command("xprobe")
                (out / "aim_xprobe.json").write_text(json.dumps(internal, indent=2) + "\n")
                receipt["function_trace_entries"] = len(trace["entries"])
                receipt["internal_trace_events"] = len(internal["xprobe"]["watched"])
                if not trace["entries"] and not receipt["internal_trace_events"]:
                    receipt["unresolved"] = "No internal player-update entries reached the trace ring; call ordering and update ownership are unproven"
            if args.trace_only:
                collect_call_order()
                snapshot("after_fire")
                receipt["collection_complete"] = True
                return
            if args.inject:
                for label, offset in [("yaw_target", 0x190), ("pitch_target", 0x184)]:
                    native.frames(120)
                    before = snapshot(label + "_before")
                    address = int(before["input"], 16) + offset + 2
                    byte = native.read(address, 1)[0]
                    delta = 32 if byte < 224 else -32
                    receipt.setdefault("injections", []).append(dict(address=hex(address), before=byte, after=byte + delta,
                                                                     native_angle_delta=delta))
                    native.command("write_ram", addr=hex(address), val=hex(byte + delta))
                    native.frames(4)
                    snapshot(label + "_early")
                    native.frames(120)
                    snapshot(label + "_settled")
                collect_call_order()
            for label, axes in [("turn_right", dict(lx=255)), ("turn_left", dict(lx=0)),
                                ("look_up", dict(ry=0)), ("look_down", dict(ry=255))]:
                native.command("set_input", buttons="0xffff", pad_type=1, lx=128, ly=128, rx=128, ry=128)
                before = snapshot(label + "_before")
                player = int(before["player"], 16)
                native.command("wtrace_range", lo=hex(player + 0x220), hi=hex(player + 0x260))
                native.command("wtrace_clear")
                native.command("set_input", buttons="0xffff", pad_type=1, **axes)
                native.frames(12)
                snapshot(label + "_held")
                trace = native.command("wtrace_dump", count=128)
                (out / f"{label}.writes.json").write_text(json.dumps(trace, indent=2) + "\n")
                native.command("set_input", buttons="0xffff", pad_type=1, lx=128, ly=128, rx=128, ry=128)
                native.frames(12)
                snapshot(label + "_after")
            native.command("screenshot_hires", path=str(out / "baseline.png"))
            # Read resident overlay bytes in bounded debugger packets.
            ram = bytearray()
            for offset in range(0, 0x100000, 0x1000):
                ram.extend(native.read(0x80000000 + offset, 0x1000))
            (out / "resident.bin").write_bytes(ram)
            for label, address, count in [("player_update", 0x800892C8, 970),
                                          ("analog_converter", 0x80083C6C, 81),
                                          ("player_movement", 0x8008D800, 2300),
                                          ("actor_dispatch", 0x80078E08, 200)]:
                result = [native.command("disasm", addr=hex(address + offset * 4), count=min(256, count - offset))
                          for offset in range(0, count, 256)]
                (out / f"{label}.disasm.json").write_text(json.dumps(result, indent=2) + "\n")
            native.command("savestate", op="save", slot=0)
            native.frames(15)
            receipt["saved_fixture"] = native.command("savestate_status")
            if receipt["saved_fixture"]["pending"] or not receipt["saved_fixture"]["last_ok"]:
                raise RuntimeError("Probe fixture save did not complete successfully")
            receipt["collection_complete"] = True
        except Exception as error:
            receipt["error"] = f"{type(error).__name__}: {error}"
            raise
        finally:
            try:
                native.command("quit")
            except (OSError, RuntimeError):
                pass
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                receipt["forced_cleanup"] = True
                proc.terminate()
                proc.wait(timeout=8)
            receipt.update(exit_code=proc.returncode,
                           source_saves_unchanged=all(native.digest(Path(k)) == v for k, v in hashes.items()),
                           preferences_unchanged=shared.hash_existing(shared.preference_paths()) == preferences,
                           remaining_game_pids=native.game_pids())
            (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps({k: v for k, v in receipt.items() if k not in ("samples", "research", "overlay_before", "overlay_after")}), flush=True)


if __name__ == "__main__":
    main()
