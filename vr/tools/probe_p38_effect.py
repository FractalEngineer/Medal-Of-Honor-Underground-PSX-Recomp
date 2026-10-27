"""Capture a bounded P38 muzzle-effect and player-object diagnostic.

Uses a copied MP or SP fixture, synthetic hand input and the existing
read-only diagnostics. No source save, health, ammo or guest code is edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import time

import inspect_weapon_sets as native
import probe_native_shot as shot
import probe_p38_headset as comparison


ROOT = native.ROOT
sys.path.insert(0, str(ROOT / "psxrecomp/tools"))
import psx_gpu_frame as gpu


def copy_fixture(out, slot):
    destination = out / "saves/openbios"
    destination.mkdir(parents=True)
    sources = []
    for extension in ("pst", "thumb"):
        source = (
            ROOT
            / f"saves/openbios/state_8001F844_slot{slot:02}.{extension}"
        )
        shutil.copyfile(source, destination / source.name)
        sources.append(
            {
                "path": str(source.relative_to(ROOT)),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        )
    return sources


def changed_words(before, after):
    count = min(len(before), len(after)) // 4
    changes = []
    for index in range(count):
        old = struct.unpack_from("<I", before, index * 4)[0]
        new = struct.unpack_from("<I", after, index * 4)[0]
        if old != new:
            changes.append(
                {
                    "offset": f"0x{index * 4:03X}",
                    "old": f"0x{old:08X}",
                    "new": f"0x{new:08X}",
                }
            )
    return changes


def save_json(path, value):
    path.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run(directory, hand_x_mm=0, hand_y_mm=0, sp=False,
        native_flags=False):
    out = directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "frames").mkdir()
    source_hashes = copy_fixture(out, 0 if sp else 1)
    preference_hashes = {
        str(path): native.digest(path)
        for path in comparison.preference_paths()
        if path.is_file()
    }
    executable = (
        ROOT
        / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    )
    env = comparison.environment("tracked", True, hand_fixed=True)
    if sp:
        env["MOHU_VR_UNITS_PER_METER"] = "238.80597014925373"
        for key in ("MOHU_VR_MP_CONTROL", "MOHU_VR_MP_FRUSTUM"):
            env.pop(key, None)
        env["MOHU_VR_WEAPON_TRACE"] = "1"
        if native_flags:
            for key in tuple(env):
                if key.startswith(("PSX_VR_WEAPON_", "MOHU_VR_WEAPON_")):
                    env.pop(key, None)
    command = [
        str(executable),
        "--headless-opengl",
        "--no-launcher",
        "--game",
        str(ROOT / "analysis/vr-baseline/game-interp.toml"),
        "--memcard-dir",
        str(out / "saves"),
        "--debug-port",
        "4372",
    ]
    receipt = {
        "schema": 1,
        "kind": (
            "bounded SP P38 muzzle-effect player-object diagnostic"
            if sp else "bounded MP P38 muzzle-effect player-object diagnostic"
        ),
        "complete": False,
        "executable_sha256": native.digest(executable),
        "source_fixture": source_hashes,
        "frames": [],
        "limits": [
            "Synthetic desktop input; not physical acceptance.",
            "Actor/input snapshots include animation and telemetry changes.",
        ],
    }
    with (
        (out / "stdout.log").open("w", encoding="utf-8") as stdout,
        (out / "stderr.log").open("w", encoding="utf-8") as stderr,
    ):
        process = subprocess.Popen(
            command,
            cwd=out,
            env=env,
            stdout=stdout,
            stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            comparison.wait_for_ping(process)
            native.load(0 if sp else 1)
            comparison.release_load_override()
            if hand_x_mm or hand_y_mm:
                x = 0.15 + hand_x_mm / 1000.0
                y = -0.15 + hand_y_mm / 1000.0
                shot.poses.set_hand_pair(
                    grip=(x, y, -0.40), aim=(x, y, -0.45)
                )
            else:
                comparison.set_desktop_hands()
            native.frames(12)
            if sp:
                actor = struct.unpack(
                    "<I", native.read(0x800AA17C, 4)
                )[0]
                player_input = struct.unpack(
                    "<I", native.read(actor + 0x39C, 4)
                )[0]
                player_snapshot = {
                    "actor": f"0x{actor:08X}",
                    "input": f"0x{player_input:08X}",
                }
            else:
                players = native.players()
                actor = int(players[0]["actor"], 16)
                player_input = int(players[0]["input"], 16)
                player_snapshot = players[0]
            if not sp:
                shot.shot_command("stop")
                shot.shot_command("start-p1")
            native.frames(4)
            actor_before = native.read(actor, 0x1000)
            input_before = native.read(player_input, 0x400)
            trace_lo = actor + (0x5F0 if sp else 0xC80)
            trace_hi = actor + (0x680 if sp else 0xD00)
            native.command(
                "wtrace_range", lo=hex(trace_lo), hi=hex(trace_hi)
            )
            native.command("wtrace_clear")

            capture_index = 0
            native.command(
                "screenshot_hires",
                path=str(out / "frames" / f"{capture_index:02}.png"),
            )
            receipt["frames"].append(
                {
                    "index": capture_index,
                    "phase": "before",
                    "frame": native.command("frame"),
                    "player": player_snapshot,
                }
            )
            eyes = out / "sp-eyes"  # Retain the historical evidence path.
            eyes.mkdir()
            native.command("stereo_dump", path=eyes.as_posix(), count=6)
            if sp:
                native.command("set_input", buttons="0xbfff")
            else:
                native.command("openxr_input_override", right_trigger=1000)
            for capture_index in range(1, 13):
                native.frames(1)
                native.command(
                    "screenshot_hires",
                    path=str(
                        out / "frames" / f"{capture_index:02}.png"
                    ),
                )
                receipt["frames"].append(
                    {
                        "index": capture_index,
                        "phase": "fire",
                        "frame": native.command("frame"),
                        "player": player_snapshot,
                    }
                )
                time.sleep(0.005)
            if sp:
                native.command("set_input", buttons="0xffff")
            else:
                native.command("openxr_input_override", clear=1)
            native.frames(24)
            for capture_index in (13, 14, 15):
                native.command(
                    "screenshot_hires",
                    path=str(
                        out / "frames" / f"{capture_index:02}.png"
                    ),
                )
                receipt["frames"].append(
                    {
                        "index": capture_index,
                        "phase": "after",
                        "frame": native.command("frame"),
                        "player": player_snapshot,
                    }
                )
            first_frame = int(receipt["frames"][0]["frame"]["frame"])
            last_frame = int(receipt["frames"][-1]["frame"]["frame"])
            gpu_dir = out / "gpu-frames"
            gpu_dir.mkdir()
            flash_quads = []
            for frame in range(first_frame, last_frame + 1):
                reply = native.command(
                    "gpu_frame_dump", frame=frame, count=65536
                )
                if "entries" not in reply:
                    continue
                prims = gpu.decode_entries(reply.get("entries", []))
                for prim in prims:
                    if (
                        prim.get("semi")
                        and int(prim.get("src", "0"), 16)
                        in ({(actor + 0x600) & 0x1FFFFFFF,
                             (actor + 0x628) & 0x1FFFFFFF} if sp else
                            {(actor + 0xCBC) & 0x1FFFFFFF})
                    ):
                        vertices = prim["verts"]
                        flash_quads.append(
                            {
                                "frame": frame,
                                "source": prim["src"],
                                "center": [
                                    sum(vertex[0] for vertex in vertices)
                                    / len(vertices),
                                    sum(vertex[1] for vertex in vertices)
                                    / len(vertices),
                                ],
                                "vertices": vertices,
                            }
                        )
                dump = {
                    "kind": gpu.DUMP_KIND,
                    "version": gpu.DUMP_VERSION,
                    "label": f"p38-effect-{frame}",
                    "frame": int(reply.get("frame", frame)),
                    "raw_count": int(reply.get("count", 0)),
                    "requested": 65536,
                    "capped": int(reply.get("count", 0)) >= 65536,
                    "max_words": int(reply.get("max_words", 12)),
                    "prims": prims,
                    "funcs": gpu.attribute(prims),
                }
                summary = gpu.summarise_dump(dump, f"{frame}.json")
                save_json(gpu_dir / f"{frame}.summary.json", summary)
                if any(entry.get("semi") for entry in prims):
                    save_json(gpu_dir / f"{frame}.json", dump)
            actor_after = native.read(actor, 0x1000)
            input_after = native.read(player_input, 0x400)
            trace = native.command(
                "wtrace_dump",
                count=4096,
                frame_lo=first_frame,
                addr_lo=hex(trace_lo),
                addr_hi=hex(trace_hi),
            )
            if sp:
                status = {"capture": 0, "count": 0, "overflow": 0}
                shots = []
            else:
                status = shot.shot_command("status")
                shots = [
                    shot.shot_command(f"read={index}")
                    for index in range(status["count"])
                ]
            native.command("wtrace_range", lo="0", hi="0")
            receipt["actor_changes"] = changed_words(
                actor_before, actor_after
            )
            receipt["input_changes"] = changed_words(
                input_before, input_after
            )
            receipt["shot_status"] = status
            receipt["shots"] = shots
            receipt["actor_trace"] = trace
            receipt["counters"] = native.command("mod_counters")
            values = {
                row["name"]: row["count"]
                for row in receipt["counters"]["counters"]
            }
            receipt["flash"] = {
                "aligned": values.get("mohu.vr.flash.align", 0),
                "fallbacks": values.get("mohu.vr.flash.fallback", 0),
                "quads": flash_quads,
            }
            receipt["complete"] = True
        finally:
            try:
                native.command("openxr_input_override", clear=1)
                native.command("wtrace_range", lo="0", hi="0")
                if not sp:
                    shot.shot_command("stop")
                native.command("quit")
            except (OSError, RuntimeError):
                pass
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                receipt["forced_cleanup"] = True
                process.terminate()
                process.wait(timeout=8)
            receipt["exit_code"] = process.returncode
            receipt["remaining_game_pids"] = native.game_pids()
            receipt["source_saves_unchanged"] = all(
                hashlib.sha256(
                    (ROOT / row["path"]).read_bytes()
                ).hexdigest() == row["sha256"]
                for row in source_hashes
            )
            receipt["preferences_unchanged"] = all(
                native.digest(Path(path)) == value
                for path, value in preference_hashes.items()
            )
            save_json(out / "receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--hand-x-mm", type=int, default=0)
    parser.add_argument("--hand-y-mm", type=int, default=0)
    parser.add_argument("--sp", action="store_true")
    parser.add_argument("--native", action="store_true")
    args = parser.parse_args()
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic TCP port 4372 is occupied")
    receipt = run(
        args.directory, args.hand_x_mm, args.hand_y_mm, sp=args.sp,
        native_flags=args.native
    )
    if (
        not receipt["complete"]
        or receipt.get("exit_code") != 0
        or receipt.get("forced_cleanup")
        or receipt["remaining_game_pids"]
        or not receipt.get("source_saves_unchanged")
        or not receipt.get("preferences_unchanged")
        or not receipt["flash"]["aligned"]
        or receipt["flash"]["fallbacks"]
    ):
        raise RuntimeError("P38 effect diagnostic did not close cleanly")
    print(
        f"PASS: captured {len(receipt['frames'])} frames, "
        f"{len(receipt['actor_changes'])} actor-word changes and "
        f"{len(receipt['input_changes'])} input-word changes",
        flush=True,
    )


if __name__ == "__main__":
    main()
