"""Measure natural P1 animated markers available at native shot construction.

Reuses the existing copied-slot family controls, native pad, owned headless
process configuration and receipt finalizer. No shot override or XR runtime.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import socket
import subprocess

import numpy as np
import inspect_weapon_sets as native
import probe_p38_headset as comparison
import probe_shot_families as family
import probe_native_shot as shot
from probe_weapon_animations import marker_groups

ROOT=native.ROOT
MAX_AGE=2257920


def marker(args):
    reply=native.command("mod_cmd",name="mohu.vr.marker",args=args)
    if reply["result"]!=1:raise RuntimeError(f"Marker command rejected: {reply}")
    return json.loads(reply["reply"])


def verify_sample(index, expected_id, expected_valid=True, *, origin=False):
    sample=marker(f"{'origin' if origin else 'shot'}={index}")
    if bool(sample["valid"])!=bool(expected_valid):
        raise RuntimeError(f"Unexpected canonical marker validity: {sample}")
    if expected_valid and (sample["id"]!=expected_id or
            sample["generation"]!=sample["expected_generation"] or
            not 0<=sample["shot_cycle"]-sample["cycle"]<=MAX_AGE):
        raise RuntimeError(f"Wrong identity/load/freshness at native shot: {sample}")
    vertices=[]
    for start in range(0,sample["vertex_count"],4):
        page=marker(f"{'origin-vertices' if origin else 'vertices'}={index}:{start}")
        if (page["sequence"]!=sample["sequence"] or page["start"]!=start or
                page["total"]!=sample["vertex_count"]):
            raise RuntimeError("Canonical snapshot changed across pages")
        vertices.extend(page["vertices"])
    if vertices:
        groups=marker_groups()[sample["id"]]
        counts=[len(groups["grip"]),len(groups["muzzle"]),7 if sample["id"]==0 else 0]
        if len(vertices)!=sum(counts):raise RuntimeError("Incomplete selected-vertex snapshot")
        points=[];start=0
        for count in counts:
            points.append(np.asarray(vertices[start:start+count],dtype=float).mean(axis=0)
                          if count else points[0])
            start+=count
        error=max(float(np.max(np.abs(point-np.asarray(sample[name]))))
                  for point,name in zip(points,("grip","tip","axis_base")))
        if error>1e-8:raise RuntimeError(f"Marker mean differs from selected native vertices: {error}")
        sample["mean_error"]=error
        sample["selected_vertices"]=vertices
    return sample


def short_fire(name, *, valid=True, port=1):
    shot.shot_command("start")
    native.frames(12)
    before=native.players()
    if port==1:native.command("openxr_input_override",right_trigger=1000)
    else:native.command("set_input",port=2,buttons=65535^0x4000)
    native.frames(8)
    native.command("openxr_input_override",clear=1)
    native.command("set_input",port=2,buttons=65535)
    native.frames(30)
    shot.shot_command("stop")
    status=shot.shot_command("status")
    if status["overflow"]:raise RuntimeError("Shot ring overflow")
    owner=int(before[port-1]["actor"],0)
    records=[]
    for index in range(status["count"]):
        source=shot.shot_command(f"read={index}")
        if source["owner"]!=owner:continue
        if source["aimed"] or not source["code_valid"]:
            raise RuntimeError("Unexpected override or missing native code guard")
        records.append({"shot":source,"marker":verify_sample(index,0,valid)})
    after=native.players()
    if not records or after[port-1]["clip"]>=before[port-1]["clip"]:
        raise RuntimeError("Control did not fire natively")
    return {"name":name,"before":before,"after":after,"samples":records,"status":marker("status")}


def controls():
    family.prepare_weapon(1,0)
    fresh=short_fire("fresh")
    marker("freeze");frozen=marker("status")
    native.frames(8)
    stale=short_fire("stale",valid=False)
    if stale["status"]["sequence"]!=frozen["sequence"]:
        raise RuntimeError("Frozen cache refreshed")
    if any(r["marker"]["shot_cycle"]-r["marker"]["cycle"]<=MAX_AGE
           for r in stale["samples"]):raise RuntimeError("Stale control did not exceed declared freshness")
    marker("resume");native.frames(4)
    recovered=short_fire("recovered")
    marker("freeze");old=marker("status")
    family.prepare_weapon(1,0)
    after_load=marker("status")
    if after_load["valid"] or after_load["expected_generation"]<=old["expected_generation"]:
        raise RuntimeError("Load did not invalidate frozen host cache")
    loaded=short_fire("load-invalidated",valid=False)
    marker("resume");native.frames(4)
    p2=short_fire("p2-isolated",valid=False,port=2)
    marker("stop")
    disabled=short_fire("disabled",valid=False)
    return [fresh,stale,recovered,loaded,p2,disabled]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    parser.add_argument("--ids",type=int,nargs="+")
    parser.add_argument("--proof",type=Path)
    args=parser.parse_args();selected=set(args.ids or native.WEAPONS)
    if selected-set(native.WEAPONS):parser.error("Unknown measured weapon ID")
    if args.proof and selected!=set(native.WEAPONS):parser.error("Proof requires all 13 IDs")
    if native.game_pids():raise RuntimeError("Close existing game before owned probe")
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1",4372))==0:raise RuntimeError("Port 4372 occupied")
    out=args.directory.resolve();out.mkdir(parents=True,exist_ok=False)
    saves=out/"saves/openbios";saves.mkdir(parents=True)
    hashes={}
    for slot in family.CYCLES:
        for suffix in ("pst","thumb"):
            source=ROOT/f"analysis/fixtures/mp/openbios/state_8001F844_slot{slot:02}.{suffix}"
            shutil.copyfile(source,saves/source.name);hashes[str(source)]=native.digest(source)
    preferences=comparison.hash_existing(comparison.preference_paths())
    exe=ROOT/"build-release/Medal_of_Honor_Underground_Recompiled.exe"
    receipt={"schema":1,"kind":"W5.3c canonical animated marker measurement","complete":False,
        "headset_used":False,"executable_sha256":native.digest(exe),"source_saves":hashes,
        "preferences":preferences,"weapons":[],"controls":[],"sources":{
            p:native.digest(ROOT/p) for p in ("vr/underground/vr_diagnostic.c",
                "vr/underground/weapon_markers.h","vr/underground/weapon_marker_groups.inc",
                "vr/tools/probe_canonical_markers.py","vr/tools/probe_shot_families.py")}}
    env=comparison.environment("native",True);env["PSX_INTERNAL_RESOLUTION"]="native"
    with (out/"stdout.log").open("w") as stdout,(out/"stderr.log").open("w") as stderr:
        process=subprocess.Popen([str(exe),"--headless-opengl","--no-launcher","--game",
            str(ROOT/"analysis/vr-baseline/game-interp.toml"),"--memcard-dir",str(out/"saves"),
            "--debug-port","4372"],cwd=out,env=env,stdout=stdout,stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            comparison.wait_for_ping(process);marker("start")
            for slot,switches,weapon_id in family.first_occurrences():
                if weapon_id not in selected:continue
                origin_before=marker("origins")["count"]
                row=family.probe_weapon(slot,switches,weapon_id)
                row["markers"]=[verify_sample(index,weapon_id) for index in range(len(row["shots"]))]
                row["marker_status"]=marker("status")
                origin_status=marker("origins")
                if origin_status["overflow"]:raise RuntimeError("Final-origin marker ring overflow")
                row["final_origin_markers"]=[verify_sample(i,weapon_id,origin=True)
                    for i in range(origin_before,origin_status["count"])]
                if weapon_id in (10,15,13):
                    expected_pc={10:0x80084CDC,15:0x80084B74,13:0x80048AAC}[weapon_id]
                    if not row["final_origin_markers"] or any(
                        m["event_pc"]!=expected_pc or m["event_shot"] not in {s["shot"] for s in row["shots"]}
                        for m in row["final_origin_markers"]):
                        raise RuntimeError("Missing/mismatched final-origin marker event")
                receipt["weapons"].append(row);family.save(out/"receipt.json",receipt)
                print(f"ID {weapon_id}: fresh canonical markers at {len(row['markers'])} shot(s)",flush=True)
            if selected==set(native.WEAPONS):receipt["controls"]=controls()
            receipt["marker_status"]=marker("status")
            receipt["render_pass"]=native.command("render_pass_stats")
            receipt["stereo"]=native.command("stereo_stats")
            if receipt["render_pass"]["verify_mismatch"]:raise RuntimeError("Rollback mismatch")
            receipt["complete"]=True
        except BaseException as error:
            receipt["error"]=str(error)
            try:receipt["failure_status"]=marker("status")
            except (OSError,RuntimeError):pass
            raise
        finally:
            try:
                native.command("openxr_input_override",clear=1)
                native.command("set_input",port=2,buttons=65535)
                marker("stop");shot.shot_command("stop");native.command("quit")
            except (OSError,RuntimeError):pass
            try:process.wait(timeout=8)
            except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=8)
            receipt["exit_code"]=process.returncode
            receipt["source_saves_unchanged"]=all(native.digest(Path(p))==v for p,v in hashes.items())
            receipt["preferences_unchanged"]=all(native.digest(Path(p))==v for p,v in preferences.items())
            receipt["remaining_game_pids"]=native.game_pids()
            family.save(out/"receipt.json",receipt)
    if not (receipt["complete"] and receipt["source_saves_unchanged"] and
            receipt["preferences_unchanged"] and not receipt["remaining_game_pids"] and
            receipt["exit_code"]==0):raise RuntimeError("Canonical marker probe did not close cleanly")
    if args.proof:
        receipt["raw_receipt"]=str((out/"receipt.json").relative_to(ROOT))
        receipt=family.seal_receipt(out/"receipt.json",receipt);family.save(args.proof,receipt)
    print(f"PASS: canonical marker measurements for {len(selected)} IDs",flush=True)


if __name__=="__main__":main()
