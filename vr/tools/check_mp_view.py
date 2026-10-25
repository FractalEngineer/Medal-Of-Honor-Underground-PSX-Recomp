"""Exercise guarded P1-only MP eye replay in a fresh copied-save process."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import time

from PIL import Image, ImageChops, ImageStat

import inspect_weapon_sets as native


def command(cmd, **values):
    deadline = time.monotonic() + 15
    while True:
        try:
            return native.command(cmd, **values)
        except (RuntimeError, OSError) as error:
            if "busy or frozen" not in str(error) or time.monotonic() > deadline:
                raise
            time.sleep(.05)


def pair(directory):
    directory.mkdir()
    command("stereo_dump", path=directory.as_posix(), count=1)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        left = list(directory.glob("*_left.png"))
        right = list(directory.glob("*_right.png"))
        if len(left) == len(right) == 1:
            try:
                images = [Image.open(p).convert("RGB") for p in (left[0], right[0])]
                break
            except OSError:
                pass
        time.sleep(.05)
    else:
        raise RuntimeError("No fresh complete eye pair")
    if any(im.size != (512, 120) or len(set(im.getdata())) < 100 or
           sum(ImageStat.Stat(im).mean) < 10 for im in images):
        raise RuntimeError("Empty or incorrectly sized MP view")
    return images, {p.name: native.digest(p) for p in (left[0], right[0])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--all-weapons", action="store_true")
    parser.add_argument("--eye-offset", type=int, default=0)
    parser.add_argument("--native-projection", action="store_true")
    parser.add_argument("--reject-recover", action="store_true")
    parser.add_argument("--fire-pistol", action="store_true")
    parser.add_argument("--frustum", action="store_true")
    args = parser.parse_args()
    if native.game_pids():
        raise RuntimeError("Close the existing game before this owned control")
    # Refuse a listening diagnostic endpoint before launching anything.
    import socket
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4372)) == 0:
            raise RuntimeError("Diagnostic port 4372 is occupied")
    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    copies = out / "saves/openbios"
    copies.mkdir(parents=True)
    slots = [1, 2, 3, 4] if args.all_weapons else [1]
    sources = []
    for slot in slots:
        for suffix in ("pst", "thumb"):
            source = native.ROOT / f"saves/openbios/state_8001F844_slot{slot:02}.{suffix}"
            shutil.copyfile(source, copies / source.name)
            sources.append(source)
    hashes = {str(p): native.digest(p) for p in sources}
    preferences = [native.ROOT / "build-release/settings.toml",
                   native.ROOT / "build-release/keybinds.ini",
                   Path("C:/Program Files (x86)/Steam/config/steamvr.vrsettings")]
    preference_hashes = {str(p): native.digest(p) for p in preferences if p.exists()}
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PSX_", "MOHU_VR_"))}
    env.update(PSX_DEV_INPUT="0", PSX_VSYNC="0", PSX_OPENXR_ENABLE="0",
               PSX_STEREO_SHED="0", PSX_RENDER_PASS_VERIFY="1",
               MOHU_VR_MP_CONTROL="1", MOHU_VR_STEREO_PROOF="1",
               MOHU_VR_EYE_RENDER_VIEW="0" if args.native_projection else "1",
               MOHU_VR_EYE_GUEST_SUBMIT="1",
               MOHU_VR_EYE_OFFSET=str(args.eye_offset), PSX_VR_WEAPON_POSE="1",
               MOHU_VR_WEAPON_SYNTHETIC_X="1",
               MOHU_VR_MP_FRUSTUM="1" if args.frustum else "0")
    # A nonzero synthetic pose selects the diagnostic tracking source. Identity
    # controls are selected through the command after loading the fixture.
    exe = native.ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    receipt = {"complete": False, "eye_offset": args.eye_offset,
               "mp_frustum": args.frustum,
               "executable_sha256": native.digest(exe), "source_saves": hashes,
               "preferences": preference_hashes, "weapons": [], "cycles": {},
               "sources": {str(p.relative_to(native.ROOT)): native.digest(p) for p in
                           (native.ROOT / "vr/underground/vr_diagnostic.c",
                            native.ROOT / "vr/underground/mp_view.h")}}
    with (out / "stdout.log").open("w") as stdout, (out / "stderr.log").open("w") as stderr:
        process = subprocess.Popen([str(exe), "--headless-opengl", "--no-launcher",
            "--game", str(native.ROOT / "analysis/vr-baseline/game-interp.toml"),
            "--memcard-dir", str(out / "saves"), "--debug-port", "4372"],
            cwd=out, env=env, stdout=stdout, stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 40
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Diagnostic game exited during startup")
                try:
                    command("ping")
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(.1)
            for slot in slots:
                native.load(slot)
                first_weapon = native.players()[0]["weapon_id"]
                for index in range(4 if args.all_weapons else 1):
                    players = native.players()
                    weapon_id = players[0]["weapon_id"]
                    row = {"slot": slot, "switches": index, "id": weapon_id,
                           "players": players, "cases": []}
                    receipt["weapons"].append(row)
                    native_image = None
                    for label, x, yaw, lost in (("native", 0, 0, 1),
                                                ("translated", 24, 0, 0),
                                                ("yawed", 1, 12000, 0),
                                                ("lost", 24, 0, 1)):
                        command("mod_cmd", name="mohu.vr.weapon.pose",
                                args=f"x={x} yaw={yaw} lost={lost}")
                        native.frames(6)  # Let the VBlank command latch settle.
                        before_counts = {c["name"]: c["count"] for c in command("mod_counters")["counters"]}
                        before = command("stereo_stats")["pairs"]
                        deadline = time.monotonic() + 15
                        while command("stereo_stats")["pairs"] < before + 4:
                            if time.monotonic() > deadline:
                                raise RuntimeError("MP stereo replay did not advance")
                            time.sleep(.05)
                        images, files = pair(out / f"slot-{slot:02}-weapon-{index}-{label}")
                        if args.eye_offset == 0 and ImageChops.difference(*images).getbbox():
                            raise RuntimeError("Zero-offset MP eyes differ")
                        stats = command("stereo_stats")
                        deadline = time.monotonic() + 3
                        while (stats["eye_hashes"][0] != stats["eye_hashes"][1] or
                               stats["eye_cycles"][0] != stats["eye_cycles"][1]):
                            if time.monotonic() > deadline:
                                raise RuntimeError("MP eye state/cycles did not match")
                            time.sleep(.02)
                            stats = command("stereo_stats")
                        checks = command("render_pass_stats")
                        counters = command("mod_counters")
                        after_counts = {c["name"]: c["count"] for c in counters["counters"]}
                        delta = {k: v - before_counts.get(k, 0) for k, v in after_counts.items()}
                        for eye in ("left", "right"):
                            if not delta.get("mohu.vr.mp.draw." + eye, 0):
                                raise RuntimeError("Missing P1 draw in one eye")
                            applications = delta.get("mohu.vr.weapon.apply." + eye, 0)
                            if (lost and applications) or (not lost and not applications):
                                raise RuntimeError("Weapon tracking/fallback failed in one eye")
                            if args.frustum:
                                if not delta.get(
                                        "mohu.vr.mp.frustum.override." + eye, 0):
                                    raise RuntimeError(
                                        "MP eye frustum did not cover one eye")
                                if delta.get(
                                        "mohu.vr.mp.frustum.fallback." + eye, 0):
                                    raise RuntimeError(
                                        "MP eye frustum fell back in guarded fixture: " +
                                        str({key: value for key, value in delta.items()
                                             if key.startswith("mohu.vr.mp.frustum.")}))
                            elif any(value for key, value in delta.items()
                                     if key.startswith(
                                         "mohu.vr.mp.frustum.override.")):
                                raise RuntimeError(
                                    "MP eye frustum ran with its guard disabled")
                        if lost and after_counts.get("mohu.vr.weapon.viewmodel_apply", 0) != after_counts.get("mohu.vr.weapon.viewmodel_restore", 0):
                            raise RuntimeError("Weapon control scope did not drain")
                        if (not checks["verify_checks"] or any(checks[k] for k in
                            ("verify_mismatch", "vram_leaks", "watchdog", "nesting_repairs"))
                                or stats["failed"]):
                            raise RuntimeError("MP replay rollback failed")
                        world_changes = None
                        gun_changes = None
                        if label == "native":
                            native_image = images[0]
                        else:
                            world_changes = ImageChops.difference(
                                native_image.crop((110, 30, 190, 65)),
                                images[0].crop((110, 30, 190, 65))).getbbox()
                            if world_changes:
                                raise RuntimeError("Weapon pose moved sampled world pixels")
                            gun_changes = ImageChops.difference(
                                native_image.crop((270, 100, 512, 120)),
                                images[0].crop((270, 100, 512, 120))).getbbox()
                            if not lost and not gun_changes:
                                raise RuntimeError("Tracked pose did not move the visible weapon")
                        after_players = native.players()
                        if after_players[0]["weapon_id"] != weapon_id or after_players[1]["health_raw"] != players[1]["health_raw"]:
                            raise RuntimeError("Pose control changed weapon selection or P2 health")
                        row["cases"].append({"case": label, "images": files,
                                              "stereo": stats, "rollback": checks,
                                              "counters": counters, "counter_delta": delta,
                                              "sampled_world_difference": world_changes,
                                              "weapon_difference": gun_changes})
                        native.save(out / "receipt.json", receipt)
                        print(slot, weapon_id, label, stats["pairs"], flush=True)
                    if args.all_weapons:
                        native.switch()
                if args.all_weapons:
                    receipt["cycles"][str(slot)] = native.players()[0]["weapon_id"] == first_weapon
                    if not receipt["cycles"][str(slot)]:
                        raise RuntimeError("Native MP inventory cycle did not close")
            if args.fire_pistol:
                if native.players()[0]["weapon_id"] != 0:
                    raise RuntimeError("Pistol fire control requires ID 0")
                command("mod_cmd", name="mohu.vr.weapon.pose", args="x=24 yaw=0 lost=0")
                native.frames(12)
                before_fire = native.players()
                health = int(before_fire[1]["actor"], 16) + 0x108
                command("wtrace_range", lo=hex(health), hi=hex(health + 4))
                command("wtrace_clear")
                command("press", buttons=65535 ^ 0x4000, frames=24)
                native.frames(264)
                command("set_input", buttons="0xffff")
                after_fire = native.players()
                trace = command("wtrace_dump", count=2048)
                if (trace["total"] != trace["available"] or trace["emitted"] != trace["total"]
                        or not native.p2_damage_in_trace(trace, before_fire[1])
                        or after_fire[0]["clip"] >= before_fire[0]["clip"]):
                    raise RuntimeError("Native firing/ammo/P2 damage failed during MP replay")
                receipt["pistol_fire"] = {"before": before_fire, "after": after_fire,
                                          "native_health_trace": trace}
            if args.reject_recover:
                before = command("stereo_stats")
                try:
                    command("render_pass_refuse", on=1)
                    native.frames(18)
                    refused = command("stereo_stats")
                    refused_passes = command("render_pass_stats")
                finally:
                    command("render_pass_refuse", on=0)
                deadline = time.monotonic() + 15
                while True:
                    recovered = command("stereo_stats")
                    if (recovered["pairs"] > refused["pairs"] + 3 and
                            recovered["eye_hashes"][0] == recovered["eye_hashes"][1] and
                            recovered["eye_cycles"][0] == recovered["eye_cycles"][1]):
                        break
                    if time.monotonic() > deadline:
                        raise RuntimeError("MP stereo did not recover after rejected draws")
                    time.sleep(.05)
                checks = command("render_pass_stats")
                _, recovery_images = pair(out / "recovered-pair")
                recovery_pair_id = int(next(iter(recovery_images)).split("_")[0][1:])
                receipt["reject_recover"] = {"before": before, "refused": refused,
                    "refused_passes": refused_passes, "recovered": recovered, "rollback": checks,
                    "fresh_image_pair_id": recovery_pair_id, "fresh_image_hashes": recovery_images}
                if (refused["refused"] <= before["refused"] or
                        any(checks[k] for k in ("verify_mismatch", "vram_leaks", "watchdog", "nesting_repairs"))
                        or recovered["failed"] != refused["failed"]
                        or recovered["last_pair_id"] <= recovered["last_failed_attempt"]
                        or recovery_pair_id <= recovered["last_failed_attempt"]):
                    raise RuntimeError("MP rejected-draw recovery contract failed")
            receipt["complete"] = True
        except BaseException as error:
            receipt["error"] = str(error)
            raise
        finally:
            if process.poll() is None:
                try:
                    # Stop admitting new eye transactions before TCP shutdown.
                    # This switch is process-local and never writes settings.
                    command("render_pass_refuse", on=1)
                    native.frames(6)
                    command("quit")
                except (RuntimeError, OSError):
                    pass
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=8)
                    receipt["forced_cleanup"] = True
            receipt["exit_code"] = process.returncode
            receipt["source_saves_unchanged"] = all(native.digest(Path(p)) == h for p, h in hashes.items())
            receipt["preferences_unchanged"] = all(native.digest(Path(p)) == h for p, h in preference_hashes.items())
            receipt["remaining_game_pids"] = native.game_pids()
            native.save(out / "receipt.json", receipt)
    if not (receipt["source_saves_unchanged"] and receipt["preferences_unchanged"]
            and not receipt["remaining_game_pids"] and receipt["exit_code"] == 0):
        raise RuntimeError("MP control cleanup failed")


if __name__ == "__main__":
    main()
