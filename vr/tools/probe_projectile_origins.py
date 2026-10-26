"""Find native origin writers after the common projectile basis constructor.

Record a broad ring briefly, then filter its full retained history by the actual
captured object address. No allocation prediction, breakpoint or guest edits.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import socket
import subprocess
import time

import inspect_weapon_sets as native
import probe_native_shot as shot
import probe_shot_families as family
import probe_p38_headset as comparison

ROOT = native.ROOT
CONTROLS = ((1,3,10),(2,3,15),(4,2,13))


def origin_writers(sample, entries):
    address = sample["shot"]
    births = [r for r in entries if int(r["pc"],0) == 0x80048790
              and (int(r["addr"],0)&0x1FFFFFFF) == ((address+8)&0x1FFFFFFF)]
    if len(births) != 1 or int(births[0]["new"],0) != sample["type"]:
        raise RuntimeError("Native birth anchor missing/ambiguous; ring loss or reused object")
    begin = births[0]["seq"]
    motion = shot.first_motion([r for r in entries if r["seq"] > begin
                               and int(r["pc"],0) in shot.MOTION_PCS],address)
    first = motion["stores"][0]["seq"]
    writes = []
    for axis in range(3):
        rows = [r for r in entries if begin < r["seq"] < first and r["w"] == 4
                and (int(r["addr"],0)&0x1FFFFFFF) ==
                    ((address+0x220+axis*4)&0x1FFFFFFF)]
        if not rows:
            raise RuntimeError("Incomplete constructor-to-motion origin history")
        if shot.signed(rows[-1]["new"]) != shot.signed(motion["stores"][axis]["old"]):
            raise RuntimeError("Last retained writer does not establish first-motion origin")
        writes.append(rows)
    return {"shot":address,"type":sample["type"],"birth_sequence":begin,
            "basis_position":sample["position"],"first_motion":motion,
            "origin_writes":writes,"last_origin_writers":[r[-1] for r in writes],
            "basis_to_motion_shift":[(shot.signed(motion["stores"][axis]["old"])-
                                      sample["position"][axis])/65536 for axis in range(3)]}


def probe(slot, switches, weapon_id, out):
    family.prepare_weapon(slot,switches)
    control = family.fire_control(weapon_id)
    if control["approach_frames"]:
        native.command("press",buttons="0xffff",ly=0,frames=control["approach_frames"])
        native.frames(control["approach_frames"]+12)
    before = native.players()
    if before[0]["weapon_id"] != weapon_id:
        raise RuntimeError("Wrong native weapon fixture")
    shot.shot_command("start-p1")
    native.frames(12)
    native.command("wtrace_range",lo="0x800B0000",hi="0x801FF000")
    native.command("wtrace_clear")
    native.command("openxr_input_override",right_trigger=1000)
    native.frames(8)  # same accepted trigger window as the family probe
    native.command("openxr_input_override",clear=1)
    deadline = time.monotonic()+25
    sample = None
    while time.monotonic() < deadline:
        status = shot.shot_command("status")
        if status["overflow"] or status["count"] > 1:
            raise RuntimeError("Origin control needs one unambiguous native construction")
        if status["count"]:
            sample = shot.shot_command("read=0")
            if sample["weapon"] != weapon_id or sample["aimed"]:
                raise RuntimeError("Wrong weapon or unexpected pose override")
            address = sample["shot"]
            trace = native.command("wtrace_dump",addr_lo=hex(address),
                                   addr_hi=hex(address+0x400),count=2048)
            family.save(out/f"id-{weapon_id:02}-trace.json",{"sample":sample,"trace":trace})
            if trace["emitted"] >= 2048:
                raise RuntimeError("Object-filtered origin trace truncated")
            if sum(int(r["pc"],0) in shot.MOTION_PCS and
                   int(r["s0"],0)==address for r in trace["entries"]) >= 3:
                result = origin_writers(sample,trace["entries"])
                native.command("wtrace_range",lo="0",hi="0")
                shot.shot_command("stop")
                result.update(id=weapon_id,name=native.WEAPONS[weapon_id],
                              before=before,after=native.players())
                result["code_windows"] = []
                for pc in sorted({int(r["pc"],0) for r in result["last_origin_writers"]}):
                    start = pc-32
                    result["code_windows"].append({"start":hex(start),
                        "bytes":native.read(start,96).hex(),
                        "disasm":native.command("disasm",addr=hex(start),count=24)["lines"]})
                print(f"ID {weapon_id}: last origin writers " +
                      ",".join(r["pc"] for r in result["last_origin_writers"]),flush=True)
                return result
        native.frames(1)
    family.save(out/f"id-{weapon_id:02}-failure.json",{
        "status":shot.shot_command("status"),"before":before,
        "after":native.players(),"pad":native.command("pad_status")})
    raise TimeoutError("Native projectile did not reach a complete first XYZ integration")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    parser.add_argument("--proof",type=Path)
    args = parser.parse_args()
    if native.game_pids():raise RuntimeError("Close the existing game before this owned probe")
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1",4372))==0:raise RuntimeError("Port 4372 occupied")
    out = args.directory.resolve();out.mkdir(parents=True,exist_ok=False)
    saves = out/"saves/openbios";saves.mkdir(parents=True)
    hashes = {}
    for slot in (1,2,4):
        for suffix in ("pst","thumb"):
            source=ROOT/f"saves/openbios/state_8001F844_slot{slot:02}.{suffix}"
            shutil.copyfile(source,saves/source.name);hashes[str(source)]=native.digest(source)
    preferences=comparison.hash_existing(comparison.preference_paths())
    exe=ROOT/"build-release/Medal_of_Honor_Underground_Recompiled.exe"
    receipt={"schema":1,"kind":"W5.3c native projectile origin writers","complete":False,
             "headset_used":False,"executable_sha256":native.digest(exe),
             "source_saves":hashes,"preferences":preferences,"weapons":[],
             "sources":{str(p):native.digest(ROOT/p) for p in (
                 "vr/tools/probe_projectile_origins.py","vr/tools/probe_shot_families.py",
                 "vr/tools/probe_native_shot.py","vr/underground/vr_diagnostic.c")}}
    env=comparison.environment("native",True);env["PSX_INTERNAL_RESOLUTION"]="native"
    with (out/"stdout.log").open("w") as stdout,(out/"stderr.log").open("w") as stderr:
        process=subprocess.Popen([str(exe),"--headless-opengl","--no-launcher","--game",
            str(ROOT/"analysis/vr-baseline/game-interp.toml"),"--memcard-dir",str(out/"saves"),
            "--debug-port","4372"],cwd=out,env=env,stdout=stdout,stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            comparison.wait_for_ping(process)
            for slot,switches,weapon_id in CONTROLS:
                receipt["weapons"].append(probe(slot,switches,weapon_id,out))
                family.save(out/"receipt.json",receipt)
            receipt["complete"]=True
        except BaseException as error:
            receipt["error"]=str(error)
            raise
        finally:
            try:
                native.command("openxr_input_override",clear=1)
                native.command("wtrace_range",lo="0",hi="0")
                shot.shot_command("stop");native.command("quit")
            except (OSError,RuntimeError):pass
            try:process.wait(timeout=8)
            except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=8)
            receipt["exit_code"]=process.returncode
            receipt["source_saves_unchanged"]=all(native.digest(Path(p))==h for p,h in hashes.items())
            receipt["preferences_unchanged"]=all(native.digest(Path(p))==h for p,h in preferences.items())
            receipt["remaining_game_pids"]=native.game_pids()
            family.save(out/"receipt.json",receipt)
    if not (receipt["complete"] and receipt["exit_code"]==0 and
            receipt["source_saves_unchanged"] and receipt["preferences_unchanged"] and
            not receipt["remaining_game_pids"]):raise RuntimeError("Origin probe did not close cleanly")
    if args.proof:
        receipt["raw_receipt"]=str((out/"receipt.json").relative_to(ROOT))
        receipt=family.seal_receipt(out/"receipt.json",receipt)
        family.save(args.proof,receipt)
    print("PASS: native origin writer identified for both thrown items and rocket",flush=True)


if __name__=="__main__":main()
