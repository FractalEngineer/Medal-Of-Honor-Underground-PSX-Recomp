"""Measure the native flat scope transition from a copied Slot 01 save.

The probe is read-only outside its disposable save directory. It captures the
idle and fully scoped native frames plus the active camera/view descriptor so
the title-specific host range extension can be matched to game-owned state.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess

import inspect_weapon_sets as native
import probe_p38_headset as comparison


ROOT = native.ROOT
SP_PLAYER_POINTER = 0x800AA17C
R2_MASK = 0x0200


def read_words(address: int, count: int) -> list[int]:
    data = native.read(address, count * 4)
    return list(struct.unpack(f"<{count}I", data))


def descriptor_snapshot() -> dict:
    camera = int.from_bytes(native.read(0x800AA160, 4), "little")
    player = int.from_bytes(native.read(SP_PLAYER_POINTER, 4), "little")
    result = {
        "camera_pointer": hex(camera),
        "player_pointer": hex(player),
    }
    if not 0x80000000 <= camera <= 0x801FFFFC:
        return result
    camera_words = read_words(camera, 0x400 // 4)
    input_pointer = camera_words[0x39C // 4]
    result["camera_words"] = [f"{value:08X}" for value in camera_words]
    result["input_pointer"] = hex(input_pointer)
    if not 0x80000000 <= input_pointer <= 0x801FFFFC:
        return result
    input_words = read_words(input_pointer, 0xD0 // 4)
    descriptor = input_words[0xC8 // 4]
    result["input_words"] = [f"{value:08X}" for value in input_words]
    result["descriptor_pointer"] = hex(descriptor)
    if not 0x80000000 <= descriptor <= 0x801FFFFC:
        return result
    descriptor_words = read_words(descriptor, 0x200 // 4)
    result["descriptor_words"] = [f"{value:08X}" for value in descriptor_words]
    selection = input_words[0xC // 4] & 0xFFFF
    actor = int.from_bytes(
        native.read(0x800AA1A0 + selection * 4, 4), "little"
    )
    if 0x80000000 <= actor <= 0x801FFFFC:
        player_input = int.from_bytes(native.read(actor + 0x39C, 4), "little")
        if 0x80000000 <= player_input <= 0x801FFFFC:
            fog_source = player_input + 0xAC
            result["fog_source_pointer"] = hex(fog_source)
            result["fog_source"] = int.from_bytes(
                native.read(fog_source, 4), "little"
            )
    return result


def snapshot(output: Path, label: str, ram: bytes) -> dict:
    image = output / f"{label}.png"
    native.command("screenshot_file", path=str(image))
    (output / f"{label}-ram.bin").write_bytes(ram)
    return {
        "label": label,
        "frame": native.command("frame")["frame"],
        "screenshot": image.name,
        "descriptor": descriptor_snapshot(),
    }


def changed_regions(before: bytes, after: bytes) -> list[dict]:
    if len(before) != len(after):
        raise ValueError("RAM snapshots differ in size")
    changed = [
        offset
        for offset in range(0, len(before), 4)
        if before[offset:offset + 4] != after[offset:offset + 4]
    ]
    if not changed:
        return []
    regions: list[dict] = []
    start = previous = changed[0]
    for offset in changed[1:]:
        if offset > previous + 0x100:
            regions.append(_region(before, after, start, previous + 4))
            start = offset
        previous = offset
    regions.append(_region(before, after, start, previous + 4))
    return regions


def _region(before: bytes, after: bytes, start: int, end: int) -> dict:
    words = []
    for address in range(start, end, 4):
        old = before[address:address + 4]
        new = after[address:address + 4]
        if old != new:
            words.append({
                "address": f"{0x80000000 + address:08X}",
                "old": old.hex(),
                "new": new.hex(),
            })
    return {
        "start": f"{0x80000000 + start:08X}",
        "end": f"{0x80000000 + end:08X}",
        "changed_words": len(words),
        "words": words[:512],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--slot", type=int, default=1)
    parser.add_argument("--settle-frames", type=int, default=240)
    parser.add_argument("--build-dir", type=Path, default=Path("build-diagnostic"))
    parser.add_argument("--force-fog", type=int)
    args = parser.parse_args()
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic TCP port 4372 is occupied")

    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    saves = output / "saves/openbios"
    saves.mkdir(parents=True)
    fixture_hashes = {}
    for suffix in ("pst", "thumb"):
        source = (
            ROOT / "saves/openbios" /
            f"state_8001F844_slot{args.slot:02}.{suffix}"
        )
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copyfile(source, saves / source.name)
        fixture_hashes[str(source)] = native.digest(source)

    executable = (
        (args.build_dir if args.build_dir.is_absolute()
         else ROOT / args.build_dir) /
        "Medal_of_Honor_Underground_Recompiled.exe"
    )
    env = comparison.clean_environment(os.environ)
    env.update(
        PSX_DEV_INPUT="0",
        PSX_VSYNC="0",
        PSX_DITHERING="0",
        PSX_INTERNAL_RESOLUTION="native",
        PSX_RENDER_PASS_VERIFY="1",
    )
    receipt = {
        "schema": 1,
        "kind": "native flat scope range measurement",
        "complete": False,
        "slot": args.slot,
        "fixture_hashes": fixture_hashes,
        "executable_sha256": native.digest(executable),
        "settle_frames": args.settle_frames,
        "snapshots": [],
        "limits": [
            "Desktop measurement only; no headset claim.",
            "No guest code or source save is modified.",
        ],
    }
    with (output / "stdout.log").open("w") as stdout, \
            (output / "stderr.log").open("w") as stderr:
        process = subprocess.Popen(
            [
                str(executable),
                "--headless-opengl",
                "--no-launcher",
                "--game",
                str(executable.parent / "game.toml"),
                "--memcard-dir",
                str(output / "saves"),
                "--debug-port",
                "4372",
            ],
            cwd=executable.parent,
            env=env,
            stdout=stdout,
            stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        receipt["owned_pid"] = process.pid
        try:
            comparison.wait_for_ping(process)
            receipt["load"] = native.load(args.slot)
            comparison.release_load_override()
            comparison.set_desktop_hands()
            native.frames(30)

            idle_ram = native.read(0x80000000, 0x200000)
            receipt["snapshots"].append(snapshot(output, "idle", idle_ram))
            descriptor_address = int(
                receipt["snapshots"][-1]["descriptor"]["descriptor_pointer"],
                16,
            )
            native.command(
                "wtrace_range",
                lo=hex(descriptor_address + 0x3C),
                hi=hex(descriptor_address + 0x40),
            )
            native.command("wtrace_clear")
            native.frames(12)
            receipt["idle_fog_writes"] = native.command(
                "wtrace_dump", count=2048
            )
            if args.force_fog is not None:
                descriptor = receipt["snapshots"][-1]["descriptor"]
                address = int(descriptor["fog_source_pointer"], 16)
                native.command(
                    "write_ram",
                    addr=hex(address),
                    val=struct.pack("<I", args.force_fog).hex(),
                )
                native.frames(30)
                forced_ram = native.read(0x80000000, 0x200000)
                receipt["snapshots"].append(
                    snapshot(output, "forced-fog", forced_ram)
                )
                native.command(
                    "write_ram",
                    addr=hex(address),
                    val=struct.pack("<I", descriptor["fog_source"]).hex(),
                )
                native.frames(30)
            native.command("wtrace_clear")
            native.command("set_input", buttons=f"{0xFFFF ^ R2_MASK:04x}")
            native.frames(args.settle_frames)
            scoped_ram = native.read(0x80000000, 0x200000)
            receipt["snapshots"].append(snapshot(output, "scoped", scoped_ram))
            receipt["scoped_fog_writes"] = native.command(
                "wtrace_dump", count=2048
            )
            native.command("wtrace_range", lo="0", hi="0")
            native.command("set_input", buttons="0xffff")
            native.frames(90)
            released_ram = native.read(0x80000000, 0x200000)
            receipt["snapshots"].append(
                snapshot(output, "released", released_ram)
            )

            receipt["idle_to_scoped_changes"] = changed_regions(
                idle_ram, scoped_ram
            )
            receipt["scoped_to_released_changes"] = changed_regions(
                scoped_ram, released_ram
            )
            receipt["complete"] = True
            native.save(output / "receipt.json", receipt)
        finally:
            if process.poll() is None:
                try:
                    native.command("quit")
                except RuntimeError:
                    process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            receipt["source_saves_unchanged"] = all(
                native.digest(Path(path)) == value
                for path, value in fixture_hashes.items()
            )
            receipt["remaining_game_pids"] = native.game_pids()
            native.save(output / "receipt.json", receipt)


if __name__ == "__main__":
    main()
