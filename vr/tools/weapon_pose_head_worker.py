"""Fresh-process head-only phase for check_weapon_pose_spaces.py."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import check_weapon_pose_spaces as spaces
import inspect_weapon_sets as native


def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    copies = out / "saves/openbios"
    copies.mkdir(parents=True)
    for suffix in ("pst", "thumb"):
        source = native.ROOT / f"saves/openbios/state_8001F844_slot01.{suffix}"
        shutil.copyfile(source, copies / source.name)
    if native.game_pids():
        raise RuntimeError("existing game before head worker")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("diagnostic port occupied before head worker")
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PSX_", "MOHU_VR_"))
    }
    env.update(
        PSX_DEV_INPUT="0",
        PSX_VSYNC="0",
        PSX_OPENXR_ENABLE="0",
        PSX_STEREO_SHED="0",
        PSX_RENDER_PASS_VERIFY="1",
        PSX_VR_WEAPON_POSE="1",
        MOHU_VR_MP_CONTROL="1",
        MOHU_VR_STEREO_PROOF="1",
        MOHU_VR_EYE_RENDER_VIEW="1",
        MOHU_VR_EYE_GUEST_SUBMIT="1",
        MOHU_VR_EYE_OFFSET="0",
    )
    exe = native.ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    receipt = {
        "executable_sha256": native.digest(exe),
        "head_only": [],
        "cases": [],
        "complete": False,
    }
    with (out / "stdout.log").open("w") as stdout, (
        out / "stderr.log"
    ).open("w") as stderr:
        process = subprocess.Popen(
            [
                str(exe),
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
        receipt["owned_pid"] = process.pid
        try:
            deadline = time.monotonic() + 40
            while True:
                if process.poll() is not None:
                    raise RuntimeError("head worker game exited during startup")
                try:
                    spaces.command("ping")
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.1)
            receipt["load"] = native.load(1)
            receipt["combined"] = spaces.run_head_suite(out, receipt)
            receipt["players_after"] = native.players()
            receipt["complete"] = True
            native.save(out / "head-result.json", receipt)
        except BaseException as error:
            receipt["error"] = str(error)
            native.save(out / "head-result.json", receipt)
            raise
        finally:
            try:
                spaces.command("openxr_hands_override", clear=1)
                spaces.command(
                    "mod_cmd", name="mohu.vr.stereo.pose", args="reset"
                )
                spaces.command(
                    "mod_cmd", name="mohu.vr.weapon.pose", args="reset"
                )
                spaces.command("render_pass_refuse", on=1)
                native.frames(4)
                spaces.command("quit")
            except (OSError, RuntimeError):
                pass
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=8)
            receipt["exit_code"] = process.returncode
            receipt["remaining_game_pids"] = native.game_pids()
            native.save(out / "head-result.json", receipt)
    if not receipt["complete"] or receipt["remaining_game_pids"]:
        raise RuntimeError("head worker did not close cleanly")


if __name__ == "__main__":
    main()
