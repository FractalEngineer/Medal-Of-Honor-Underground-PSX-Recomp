"""Capture the VR frontend through both the guest buffer and SteamVR layer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "psxrecomp/tools"))
sys.path.insert(0, str(ROOT / "vr"))
from debug_client import connect, send_cmd
from headless_steamvr import Compositor


def command(name: str, **values):
    with connect(port=4372, timeout=25) as sock:
        result = send_cmd(sock, {"cmd": name, **values})
    if not result.get("ok"):
        raise RuntimeError(f"{name}: {result}")
    return result


def game_pids():
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process Medal_of_Honor_Underground_Recompiled "
         "-ErrorAction SilentlyContinue | ForEach-Object { $_.Id }"],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return [int(value) for value in result.stdout.split()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--seconds", type=int, default=22)
    parser.add_argument("--settle-seconds", type=float, default=8.0)
    parser.add_argument("--slot", type=int)
    parser.add_argument("--synthetic-scope", action="store_true")
    parser.add_argument("--allow-native-frontend", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--steam-root", type=Path, default=Path("C:/Program Files (x86)/Steam")
    )
    args = parser.parse_args()
    if game_pids():
        raise RuntimeError("Close the existing game before this owned probe")

    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    saves = output / "saves"
    shutil.copytree(ROOT / "saves", saves)
    psx = Path(
        r"C:\Users\titan\.cache\codex-runtimes\codex-primary-runtime"
        r"\dependencies\native\powershell\pwsh.exe"
    )
    launch = [
        str(psx),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ROOT / "vr/run_vr.ps1"),
        "-Headless",
        "-Seconds",
        str(args.seconds),
        "-DebugPort",
        "4372",
        "-MemcardDirectory",
        str(saves),
        "-LogDirectory",
        str(output),
    ]
    receipt = {
        "schema": 1,
        "kind": "VR native frontend presentation",
        "complete": False,
        "seconds": args.seconds,
        "settle_seconds": args.settle_seconds,
        "slot": args.slot,
        "synthetic_scope": args.synthetic_scope,
    }
    if args.slot is not None:
        launch += ["-Slot", str(args.slot), "-WristHudTest"]
    if args.synthetic_scope:
        launch += ["-SyntheticScope"]
    if args.allow_native_frontend:
        launch += ["-AllowNativeFrontend"]
    stdout = (output / "launcher.stdout.log").open("w")
    stderr = (output / "launcher.stderr.log").open("w")
    process = subprocess.Popen(
        launch,
        cwd=ROOT,
        stdout=stdout,
        stderr=stderr,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        deadline = time.monotonic() + 70.0
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"VR launcher exited early ({process.returncode})")
            if (output / "startup.json").is_file() and game_pids():
                break
            time.sleep(0.25)
        else:
            raise TimeoutError("VR frontend did not become ready")
        time.sleep(args.settle_seconds)
        pids = game_pids()
        if len(pids) != 1:
            raise RuntimeError(f"Unexpected game process inventory: {pids}")
        if args.debug:
            receipt["screenshot"] = command(
                "screenshot_file", path=str(output / "guest.png")
            )
            counters = command("mod_counters")["counters"]
            receipt["menu_counters"] = {
                row["name"]: row["count"]
                for row in counters
                if "native_surface" in row["name"]
            }
        receipt["compositor"] = Compositor(
            args.steam_root / "steamapps/common/SteamVR"
        ).capture(output / "layers", pids[0], reject_blank=False)
        receipt["complete"] = True
    finally:
        try:
            process.wait(timeout=args.seconds + 40)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=20)
        receipt["launcher_exit_code"] = process.returncode
        receipt["remaining_game_pids"] = game_pids()
        stdout.close()
        stderr.close()
        (output / "receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
