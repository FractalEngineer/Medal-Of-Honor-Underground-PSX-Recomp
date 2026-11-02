"""Copied Slot 01 VR range transitions; never records physical acceptance."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import inspect_weapon_sets as n
import probe_p38_headset as p
from probe_menu_native_surface import Compositor

ROOT = n.ROOT


def word(address):
    return int.from_bytes(n.read(address, 4), "little")


def write_word(address, value):
    # The debug command writes one byte, not a hex byte string.
    for offset, byte in enumerate(value.to_bytes(4, "little")):
        n.command("write_ram", addr=hex(address + offset), val=hex(byte))
    assert word(address) == value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    if n.game_pids():
        raise RuntimeError("Close existing game before owned probe")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    saves = out / "saves/openbios"
    saves.mkdir(parents=True)
    sources = list((ROOT / "saves/openbios").glob("*slot01.*"))
    hashes = p.hash_existing(sources + list(p.preference_paths()))
    for source in sources:
        shutil.copyfile(source, saves / source.name)
    receipt = dict(complete=False, physical_acceptance=False,
                   source_hashes=hashes, stages=[])
    launch = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
              str(ROOT / "vr/run_vr.ps1"), "-Headless", "-Slot", "1",
              "-MemcardDirectory", str(out / "saves"), "-DebugPort", "4372",
              "-LogDirectory", str(out), "-Seconds", "90", "-AllowNativeFrontend"]
    compositor = None

    def control(**values):
        n.command("openxr_input_override", **values)
        n.frames(10)

    def capture(label):
        n.frames(12)
        player = word(0x800AA17C)
        inp = word(player + 0x39C)
        scene = word(0x800A977C)
        stage = dict(label=label, frame=n.command("frame"),
                     native_h=word(inp + 0xAC), target_h=word(inp + 0xB0),
                     cutoff=word(0x800B7480), scene_fog=word(scene + 0xCC) & 65535,
                     input_flags=hex(word(inp)), weapon=n.read(inp + 93, 1)[0],
                     position=list(n.read(player + 0x220, 12)),
                     pad=n.command("pad_status"), xr=n.command("openxr_stats"),
                     hands=n.command("openxr_hands"))
        stage["restoration"] = n.command("render_pass_stats")
        stage["capture"] = compositor.capture(out / label, n.game_pids()[0],
                                               reject_blank=False)
        receipt["stages"].append(stage)
        n.save(out / "receipt.json", receipt)
        return stage

    with (out / "stdout.log").open("w") as so, (out / "stderr.log").open("w") as se:
        env = dict(os.environ, PSX_RENDER_PASS_VERIFY="1")
        process = subprocess.Popen(launch, cwd=out, env=env, stdout=so, stderr=se,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            p.wait_for_ping(process)
            deadline = time.monotonic() + 50
            while not (out / "startup.json").exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Launcher startup failed")
                time.sleep(.2)
            compositor = Compositor(Path("C:/Program Files (x86)/Steam/steamapps/common/SteamVR"))
            n.load(1)
            p.release_load_override()
            p.set_desktop_hands()
            control()
            if word(0x800A70F0):
                control(left_buttons=4)
                control()
            assert word(0x800A70F0) == 0
            capture("before")
            control(right_squeeze=1000)
            held = capture("held")
            assert held["native_h"] == 400 and held["cutoff"] == 250
            assert int(held["pad"]["slot0"]["buttons"], 0) & 0x200
            # Same 2.5x eye projection, range disabled through disposable target.
            inp = word(word(0x800AA17C) + 0x39C)
            target = word(inp + 0xB0)
            write_word(inp + 0xB0, 400)
            control_stage = capture("zoom-only-control")
            assert control_stage["target_h"] == 400
            write_word(inp + 0xB0, target)
            control()
            capture("released")
            control(right_squeeze=1000)
            n.command("openxr_hands_override", hand="right", pose="aim", active=0)
            capture("tracking-lost")
            p.set_desktop_hands()
            capture("tracking-restored")
            control(right_squeeze=1000, right_buttons=2)
            control(right_squeeze=1000)
            switched = capture("weapon-switched")
            assert switched["weapon"] != 5
            n.load(1)
            p.release_load_override()
            p.set_desktop_hands()
            control(right_squeeze=1000)
            if word(0x800A70F0):
                control(left_buttons=4)
                control(right_squeeze=1000)
            control(right_squeeze=1000, left_buttons=4)
            control(right_squeeze=1000)
            capture("paused")
            assert word(0x800A70F0) == 1
            control(right_squeeze=1000, left_buttons=4)
            control(right_squeeze=1000)
            before = n.read(word(0x800AA17C) + 0x220, 12)
            control(right_squeeze=1000, ly=500)
            n.frames(20)
            moved = capture("moving-held")
            assert bytes(moved["position"]) != before
            receipt["movement_changed_position"] = True
            receipt["complete"] = True
        finally:
            try:
                n.command("quit")
            except (RuntimeError, OSError):
                pass
            process.wait(timeout=40)
            receipt["source_files_unchanged"] = p.hash_existing([Path(x) for x in hashes]) == hashes
            receipt["remaining_game_pids"] = n.game_pids()
            n.save(out / "receipt.json", receipt)


if __name__ == "__main__":
    main()
