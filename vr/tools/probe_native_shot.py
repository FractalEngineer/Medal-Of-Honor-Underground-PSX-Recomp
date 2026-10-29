"""Trace native MP P38 construction, first motion and real damage without XR.

Adapts the reference check_weapon_aim.py streaming PC-filtered write collector.
Uses only copied saves, native input and read-only shot/camera instrumentation.
No ammo, health, source-save or guest-code edits. Bulk code/traces stay in analysis.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import time
import numpy as np
from PIL import Image, ImageChops, ImageDraw

import inspect_weapon_sets as native
import probe_p38_headset as comparison
import check_weapon_pose_spaces as poses

ROOT = native.ROOT
FUNCTIONS = {
    "constructor": (0x800486D0, 1052),
    "pose_selection": (0x80048528, 424),
    "basis": (0x8006C8B0, 260),
    "motion_collision": (0x8006EB8C, 3140),
    "shot_update": (0x80047720, 1376),
    "shot_collision_callback": (0x80047E64, 248),
    "damage": (0x8004EAB4, 532),
    "shot_target_hit": (0x800503F4, 1340),
    "native_level": (0x8006C61C, 656),
}
FILTERS = {
    "constructor": (0x80048528, 0x80048AEC),
    "basis": (0x8006C8B0, 0x8006C9B4),
    "motion": (0x8006F0B4, 0x8006F108),
    "collision": (0x80047E64, 0x80047F5C),
    "damage": (0x8004EAB4, 0x8004ECC8),
}
MOTION_PCS = (0x8006F0CC, 0x8006F0E8, 0x8006F104)


def signed(value):
    value = int(value, 0) if isinstance(value, str) else value
    return value - 2**32 if value & 0x80000000 else value


def shot_command(args):
    result = native.command("mod_cmd", name="mohu.vr.shot", args=args)
    if result["result"] != 1:
        raise RuntimeError(f"Shot diagnostic rejected: {result}")
    return json.loads(result["reply"])


class TraceCollector:
    def __init__(self, filters=None):
        self.filters = dict(FILTERS if filters is None else filters)
        self.rows = {name: {} for name in self.filters}
        self.cursors = {name: {"total": 0, "frame": -1} for name in self.filters}
        self.windows = {name: [] for name in self.filters}

    def collect(self):
        for name, (lo, hi) in self.filters.items():
            cursor = self.cursors[name]
            trace = native.command(
                "wtrace_dump", pc_lo=hex(lo), pc_hi=hex(hi), count=2048,
                frame_lo=max(-1, cursor["frame"] - 1),
            )
            if (trace["total"] - trace["available"] > cursor["total"]
                    or trace["emitted"] >= 2048):
                raise RuntimeError(f"Incomplete {name} trace; narrow the recorded ranges")
            for entry in trace["entries"]:
                self.rows[name][entry["seq"]] = entry
                cursor["frame"] = max(cursor["frame"], entry["frame"])
            cursor["total"] = trace["total"]
            self.windows[name].append({
                key: trace[key] for key in ("total", "available", "emitted")
            })

    def wait(self, frames):
        start = native.command("frame")["frame"]
        deadline = time.monotonic() + 35
        while native.command("frame")["frame"] < start + frames:
            if time.monotonic() > deadline:
                raise TimeoutError("Native shot guest-frame deadline")
            self.collect()
            time.sleep(0.01)
        self.collect()

    def entries(self, name):
        return [self.rows[name][key] for key in sorted(self.rows[name])]


def first_motion(entries, shot):
    rows = [row for row in entries if int(row["s0"], 0) == shot]
    if not rows:
        raise RuntimeError(f"No first motion for shot {shot:08X}")
    first = rows[:3]
    if tuple(int(row["pc"], 0) for row in first) != MOTION_PCS:
        raise RuntimeError("Incomplete or reordered XYZ first-motion stores")
    if len({row["frame"] for row in first}) != 1:
        raise RuntimeError("First motion spans different guest frames")
    delta = [(signed(row["new"]) - signed(row["old"])) / 65536 for row in first]
    length = math.sqrt(sum(v*v for v in delta))
    if length <= 0:
        raise RuntimeError("Shot did not move")
    return {"stores": first, "delta_world": delta,
            "direction": [value / length for value in delta]}


def verify_muzzle(shot, motion):
    calibration = json.loads(comparison.CALIBRATION_PROOF.read_text(encoding="utf-8"))["animated_model"]
    rt, tr = poses.decode_control([f"{w:08X}" for w in shot["weapon_control"]])
    rt = rt / 4096.0
    camera, camera_tr = poses.decode_control([f"{w:08X}" for w in shot["camera"]])
    inverse = np.linalg.inv(camera / 4096.0)
    origin = inverse @ (rt @ np.array(calibration["muzzle"]) + tr - camera_tr)
    direction = inverse @ rt @ np.array(calibration["forward"])
    direction /= np.linalg.norm(direction)
    error = float(np.max(np.abs(origin - np.array(shot["aimed_position"])/65536.0)))
    cosine = float(np.dot(direction, motion["direction"]))
    if error > 1.0/65536.0 or cosine < .999995:
        raise RuntimeError(f"Native shot disagrees with rendered muzzle: origin={error}, cosine={cosine}")
    return {"origin_error_world_units": error, "motion_axis_cosine": cosine,
            "origin_world": origin.tolist(), "rendered_world_axis": direction.tolist()}


def source_hashes():
    paths = [ROOT / f"analysis/fixtures/mp/openbios/state_8001F844_slot01.{ext}"
             for ext in ("pst", "thumb")]
    paths += [path for path in comparison.preference_paths() if path.is_file()]
    return {str(path): native.digest(path) for path in paths}


def target_pose(before, *, away=False, translated=False, **invalid):
    camera = shot_command("camera")
    if not camera["valid"]:
        raise RuntimeError("No canonical native camera for aim control")
    rt, tr = poses.decode_control([f"{w:08X}" for w in camera["control"]])
    rt = rt / 4096.0
    # The diagnostic MP camera is only 120 high with H=400. Keep this test gun
    # within that measured frustum; physical placement still needs acceptance.
    grip = np.array([.25 if translated else .15, 0.0, -.5])
    origin = grip * [1, -1, -1] * poses.HAND_UNITS_PER_METRE
    # Aim at the native upper-body hit volume, 150 world units above actor feet.
    target = np.asarray(before[1]["position"], dtype=float) / 65536.0
    target[1] -= 150.0
    d = rt @ target + tr - origin
    yaw = math.atan2(d[0], d[2]) + (math.pi/2 if away else 0)
    pitch = math.atan2(-d[1], math.hypot(d[0],d[2]))
    q = poses.quat_multiply(poses.quat_axis(1, -math.degrees(yaw)),
                            poses.quat_axis(0, math.degrees(pitch)))
    values = {"grip": grip.tolist(), "aim_q": q.tolist(), "grip_q": q.tolist(), **invalid}
    poses.set_hand_pair(**values)
    return {"values": values, "target_world": target.tolist(), "camera": camera}


def run_case(out, name, *, port=1, turn=False, head=False, fire=True,
             tracked=False, away=False, translated=False, invalid=None,
             switches=0, approach=0):
    native.command("wtrace_range", lo="0", hi="0")
    shot_command("stop")
    native.load(1)
    comparison.release_load_override()
    poses.set_head(yaw_mdeg=15000 if head else 0,
                   x_milli=100000 if head else 0)
    for _ in range(switches):
        native.switch()
        comparison.release_load_override()
    if approach:
        native.command("openxr_input_override", ly=1000 if approach > 0 else -1000)
        native.frames(abs(approach))
        native.command("openxr_input_override", clear=1)
        native.frames(4)
    if turn:
        native.command("openxr_input_override", rx=1000)
        native.frames(24)
        native.command("openxr_input_override", clear=1)
        native.frames(4)
    shot_command("start")
    native.frames(12)  # natural P1 camera, not an eye's RT/TR
    camera = shot_command("camera")
    if not camera["valid"]:
        raise RuntimeError("Native camera capture missing")
    camera_rt, camera_tr = poses.decode_control([f"{w:08X}" for w in camera["control"]])
    recovered_camera = -np.linalg.inv(camera_rt / 4096.0) @ camera_tr
    camera_error = float(np.max(np.abs(recovered_camera-np.array(camera["native_position"])/65536.0)))
    # RT is Q12, TR and its input coordinates are integer native world units.
    if camera_error > 2.0:
        raise RuntimeError(f"Canonical matrix does not invert to native camera actor: {camera_error}")
    before = native.players()
    request = None
    if tracked:
        request = target_pose(before, away=away, translated=translated, **(invalid or {}))
        native.frames(8)
    capture = None
    if tracked and not invalid and not switches:
        for _ in range(8):
            capture = poses.capture_space(node=13)
            if capture["restored"]:
                break
            time.sleep(.02)
        comparison.save_json(out / (name + "-render.json"), capture)
        poses.capture_eyes(out / (name + "-eyes"))
        if (not capture["restored"] or capture["native_gte"] != capture["restored_gte"]
                or capture["view_h_ref"] != 133):
            raise RuntimeError(f"Calibrated weapon projection/restore mismatch: {capture}")
    render_state = shot_command("render")
    if name in ("tracked-toward", "tracked-translated", "recovered"):
        if render_state["masked_arm_vertices"] != [142,142] or min(render_state["visible_gun_vertices"]) < 90:
            raise RuntimeError(f"Gun-only visible mesh control failed: {render_state}")
    native.command("wtrace_range", lo="0x800B0000", hi="0x801FF000")
    native.command("wtrace_clear")
    collector = TraceCollector()
    if fire:
        if port == 1:
            native.command("openxr_input_override", right_trigger=1000)
        else:
            native.command("set_input", port=2, buttons=65535 ^ 0x4000)
    collector.wait(4)
    firing_pad = native.command("pad_status")
    native.command("openxr_input_override", clear=1)
    native.command("set_input", port=2, buttons=65535)
    collector.wait(45)
    native.command("wtrace_range", lo="0", hi="0")
    collector.collect()
    status = shot_command("status")
    if status["overflow"]:
        raise RuntimeError("Shot sample ring overflow")
    shots = [shot_command(f"read={index}") for index in range(status["count"])]
    after = native.players()
    summary = {"name": name, "port": port, "before": before, "after": after,
               "request": request, "rendered_weapon": capture,
               "gun_only": render_state,
               "native_camera": camera, "camera_recovery_error": camera_error,
               "pad": firing_pad, "shots": shots, "first_motion": [],
               "p2_damage": native.p2_damage_in_trace(
                   {"entries": collector.entries("damage")}, before[1]),
               "trace_counts": {key: len(collector.rows[key]) for key in FILTERS}}
    summary["health_writes"] = [row for row in collector.entries("damage")
        if (int(row["addr"],0)&0x1FFFFFFF) == native.p2_health_address(before[1])
        and int(row["old"],0) > int(row["new"],0)]
    for row in summary["health_writes"]:
        if (int(row["pc"],0) != 0x8004EB80 or int(row["ra"],0) != 0x80050900
                or int(row["s1"],0) not in {s["shot"] for s in shots}
                or int(row["a2"],0) != int(row["s1"],0)):
            raise RuntimeError("P2 damage is not linked to the observed native shot")
    if fire:
        owner = int(before[port-1]["actor"], 0)
        owned = [s for s in shots if s["owner"] == owner]
        if not owned or after[port-1]["clip"] >= before[port-1]["clip"]:
            raise RuntimeError(f"{name}: no native shot/ammunition consumption")
        for shot in owned:
            if bool(shot["eligible"]) != (port == 1 and not switches):
                raise RuntimeError(f"{name}: P1 ownership guard mismatch")
            if not shot["code_valid"] or not shot["camera_valid"]:
                raise RuntimeError(f"{name}: missing guarded canonical camera/code")
            summary["first_motion"].append(
                first_motion(collector.entries("motion"), shot["shot"]))
            want_aim = tracked and not invalid and port == 1 and not switches
            if bool(shot["aimed"]) != bool(want_aim):
                raise RuntimeError(f"{name}: unexpected tracked shot/fallback {shot}")
            if want_aim:
                first = summary["first_motion"][-1]
                first["muzzle_check"] = verify_muzzle(shot, first)
                if [signed(row["old"]) for row in first["stores"]] != shot["aimed_position"]:
                    raise RuntimeError("Native first motion did not start at the declared muzzle")
                if capture and [int(w,16) & 0xffff if i==4 else int(w,16)
                    for i,w in enumerate(capture["tracked_gte"])] != shot["weapon_control"]:
                    raise RuntimeError("Rendered and simulated weapon affines disagree")
    elif shots or before[0]["clip"] != after[0]["clip"] or summary["p2_damage"]:
        raise RuntimeError("Idle control constructed or damaged a shot")
    if name in ("fire", "head-only-fire", "tracked-toward", "tracked-translated", "tracked-head", "tracked-body", "tracked-near", "tracked-far", "recovered") and not summary["p2_damage"]:
        raise RuntimeError(f"{name}: no exact native P2 health decrease")
    if name in ("idle", "turned-away", "p2-fire", "tracked-away", "tracked-p2") and summary["p2_damage"]:
        raise RuntimeError(f"{name}: unexpected P2 damage")
    if name == "p2-fire" and any(s["eligible"] for s in shots):
        raise RuntimeError("P2 shot passed P1 gate")
    raw = {"summary": summary, "windows": collector.windows,
           "traces": {key: collector.entries(key) for key in FILTERS}}
    comparison.save_json(out / (name + ".json"), raw)
    native.command("openxr_hands_override", clear=1)
    print(name, "shots", len(shots), "P2 damage", summary["p2_damage"], flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--tracked", action="store_true", help="Opt-in calibrated P38 render/shot candidate")
    parser.add_argument("--case", help="Run one named control for a focused diagnosis; no proof overwrite")
    args = parser.parse_args()
    if args.case and args.proof:
        parser.error("--case cannot publish a full-suite --proof")
    if native.game_pids():
        raise RuntimeError("Close the existing game before the owned diagnostic")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Port 4372 already occupied")
    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    copies = out / "saves/openbios"
    copies.mkdir(parents=True)
    for ext in ("pst", "thumb"):
        source = ROOT / f"analysis/fixtures/mp/openbios/state_8001F844_slot01.{ext}"
        shutil.copyfile(source, copies / source.name)
    before_hashes = source_hashes()
    executable = ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    receipt = {"schema": 1, "kind": "W4 native MP P38 contract", "complete": False,
               "headset_used": False, "shot_override": args.tracked,
               "executable_sha256": native.digest(executable),
               "revision": subprocess.check_output(["git", "rev-parse", "HEAD"],
                   cwd=ROOT, text=True).strip(), "sources": {}, "cases": []}
    receipt["contract"] = {"shot_position":"+0x220/+0x224/+0x228 signed 16.16 world units",
        "shot_angles":"+0x23C/+0x240/+0x244 signed 16.16, 4096 units/turn",
        "basis":"+0x354 native matrix; constructor initializes history at +0x26C and input+0x88",
        "basis_call":"0x800488D0=0x0C01B22C; delay=0xAE200048; RA=0x800488D8",
        "damage_call":"0x800508F8=0x0C013AAD; RA=0x80050900; shot in A2/S1",
        "camera":"native visibility helper 80096AC8 loads global RT/TR at 800A2CEC; entry GTE is not canonical",
        "origin_tolerance_world_units":1/65536,"motion_axis_min_cosine":.999995,
        "camera_recovery_tolerance_world_units":2.0}
    receipt["build"] = comparison.build_configuration(ROOT / "build-release/CMakeCache.txt")
    receipt["limits"] = ["Synthetic desktop P38 candidate; physical acceptance remains open.",
        "Other weapon IDs remain native; no live NPC fixture was exercised.",
        "Fixed W3.1 idle muzzle markers; animated recoil/reload muzzle calibration remains open."]
    for name in ("vr/underground/vr_diagnostic.c", "vr/underground/shot.h",
                 "vr/underground/weapon.c", "vr/underground/weapon.h", "vr/underground/inverse.h",
                 "psxrecomp/runtime/src/vr_geometry_math.c", "psxrecomp/runtime/src/vr_pose_math.c",
                 "vr/tools/probe_native_shot.py", "vr/tools/probe_p38_headset.py",
                 "vr/proof/weapon-p38-complete-calibration-receipt.json"):
        receipt["sources"][name] = native.digest(ROOT / name)
    env = comparison.environment("native", True)
    env["PSX_INTERNAL_RESOLUTION"] = "native"
    if args.tracked:
        env.update(PSX_VR_WEAPON_POSE="1", MOHU_VR_P38_CALIBRATED="1", MOHU_VR_P38_AIM="1")
        receipt["kind"] = "W5 P38 desktop rendered-muzzle native combat candidate"
    with (out / "stdout.log").open("w") as stdout, (out / "stderr.log").open("w") as stderr:
        process = subprocess.Popen([
            str(executable), "--headless-opengl", "--no-launcher", "--game",
            str(ROOT / "analysis/vr-baseline/game-interp.toml"), "--memcard-dir",
            str(out / "saves"), "--debug-port", "4372"], cwd=out, env=env,
            stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            comparison.wait_for_ping(process)
            native.load(1)
            functions = {}
            for name, (address, size) in FUNCTIONS.items():
                data = native.read(address, size)
                functions[name] = {"address": hex(address), "size": size,
                    "sha256": hashlib.sha256(data).hexdigest()}
                (out / (name + ".bin")).write_bytes(data)
            receipt["functions"] = functions
            receipt["dithering"] = native.command("dithering")
            if receipt["dithering"]["mode"] != 0:
                raise RuntimeError("Comparison dithering override not effective")
            cases = (
                ("idle", {"fire": False}), ("fire", {}),
                ("turned-away", {"turn": True}), ("p2-fire", {"port": 2}),
                ("head-only-fire", {"head": True}),
            )
            if args.tracked:
                cases = (
                    ("tracked-toward", {"tracked": True}),
                    ("tracked-away", {"tracked": True, "away": True}),
                    ("tracked-translated", {"tracked": True, "translated": True}),
                    ("tracked-head", {"tracked": True, "head": True}),
                    ("tracked-body", {"tracked": True, "turn": True}),
                    ("tracked-near", {"tracked": True, "approach": 30}),
                    ("tracked-far", {"tracked": True, "approach": -20}),
                    ("tracked-p2", {"tracked": True, "port": 2}),
                    ("unsupported-mp40", {"tracked": True, "switches": 1}),
                    ("unfocused", {"tracked": True, "invalid": {"focused": 0}}),
                    ("inactive", {"tracked": True, "invalid": {"active": 0}}),
                    ("partial", {"tracked": True, "invalid": {"flags": 1}}),
                    ("stale", {"tracked": True, "invalid": {"age_ms": 151}}),
                    ("recovered", {"tracked": True}),
                )
            if args.case:
                cases = tuple((name,values) for name,values in cases if name == args.case)
                if not cases:
                    raise ValueError(f"Unknown control {args.case}")
            for name, values in cases:
                receipt["cases"].append(run_case(out, name, **values))
            rows = {c["name"]: c for c in receipt["cases"]}
            base, head_case = ("tracked-toward", "tracked-head") if args.tracked else ("fire", "head-only-fire")
            if not args.case and rows[base]["shots"][0]["camera"] != rows[head_case]["shots"][0]["camera"]:
                raise RuntimeError("Canonical native camera changed with render-only head pose")
            if args.tracked and not args.case:
                first = Image.open(next((out / "tracked-toward-eyes").glob("*left.png"))).convert("RGB")
                second = Image.open(next((out / "tracked-translated-eyes").glob("*left.png"))).convert("RGB")
                diff = ImageChops.difference(first, second)
                world_changes = sum(pixel != (0,0,0) for pixel in diff.crop(poses.WORLD_ROI).getdata())
                gun_changes = sum(pixel != (0,0,0) for pixel in diff.crop((270,20,512,110)).getdata())
                if world_changes or gun_changes < 20:
                    raise RuntimeError(f"Independent visible gun control failed: world={world_changes}, gun={gun_changes}")
                receipt["image_control"] = {"world_roi_changed_pixels": world_changes,
                    "gun_roi_changed_pixels": gun_changes}
                for label in ("tracked-near", "tracked-far"):
                    distance = lambda c: float(np.linalg.norm((np.array(c["before"][1]["position"])-np.array(c["before"][0]["position"]))/65536.0))
                    rows[label]["target_distance_world_units"] = distance(rows[label])
                receipt["base_target_distance_world_units"] = distance(rows[base])
            receipt["render"] = native.command("render_pass_stats")
            receipt["stereo"] = native.command("stereo_stats")
            if receipt["render"]["verify_mismatch"] or receipt["stereo"]["failed"]:
                raise RuntimeError("Stereo/rollback regression")
            receipt["counters"] = native.command("mod_counters")
            receipt["complete"] = True
        except BaseException as error:
            receipt["error"] = str(error)
            raise
        finally:
            try:
                native.command("openxr_input_override", clear=1)
                native.command("wtrace_range", lo="0", hi="0")
                native.command("quit")
            except (OSError, RuntimeError):
                pass
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=8)
            receipt["exit_code"] = process.returncode
            receipt["sources_and_preferences_unchanged"] = before_hashes == source_hashes()
            receipt["source_save_preference_hashes"] = before_hashes
            receipt["remaining_game_pids"] = native.game_pids()
            comparison.save_json(out / "receipt.json", receipt)
    if not receipt["sources_and_preferences_unchanged"] or receipt["remaining_game_pids"]:
        raise RuntimeError("Diagnostic cleanup/provenance check failed")
    if args.proof:
        receipt["raw_receipt"] = str((out / "receipt.json").relative_to(ROOT))
        receipt["raw_sha256"] = native.digest(out / "receipt.json")
        if args.tracked:
            panels=[]
            for name in ("tracked-toward", "tracked-translated", "tracked-head", "tracked-body"):
                panel=Image.new("RGB",(1024,138))
                ImageDraw.Draw(panel).text((4,2),name,fill="white")
                for index, side in enumerate(("left","right")):
                    path=next((out / (name+"-eyes")).glob("*"+side+".png"))
                    panel.paste(Image.open(path).convert("RGB"),(index*512,18))
                panels.append(panel)
            sheet=Image.new("RGB",(1024,138*len(panels)))
            for index,panel in enumerate(panels): sheet.paste(panel,(0,index*138))
            path=args.proof.with_name("weapon-p38-aim-controls.png")
            sheet.save(path)
            receipt["control_sheet"]={"path":str(path),"sha256":native.digest(path)}
        comparison.save_json(args.proof, receipt)


if __name__ == "__main__":
    main()
