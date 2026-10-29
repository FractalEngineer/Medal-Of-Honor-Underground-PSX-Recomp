"""Exercise guarded P1-only MP eye replay in a fresh copied-save process."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from PIL import Image, ImageChops, ImageDraw, ImageStat

import inspect_weapon_sets as native


def overlay_native_summary(response):
    ring = response.get("ring", {}) if isinstance(response, dict) else {}
    return {
        "native_exec": int(ring.get("native_exec", 0)),
        "calls_total": int(ring.get("calls_total", 0)),
        "would_run": int(ring.get("would_run", 0)),
        "in_progress": ring.get("in_progress"),
        "recent_addresses": [
            item.get("addr") for item in ring.get("recent", [])[:32]
        ],
    }


def command(cmd, **values):
    deadline = time.monotonic() + 15
    while True:
        try:
            return native.command(cmd, **values)
        except (RuntimeError, OSError) as error:
            if "busy or frozen" not in str(error) or time.monotonic() > deadline:
                raise
            time.sleep(.05)


def frustum_control(action):
    result = command(
        "mod_cmd", name="mohu.vr.mp.frustum", args=action
    )
    if result["result"] != 1:
        raise RuntimeError(f"MP frustum control rejected: {result}")
    return parse_reply(result["reply"])


def parse_reply(reply):
    values = {}
    for token in reply.split():
        key, separator, value = token.partition("=")
        if not separator or not key or not value:
            raise RuntimeError(f"Malformed selector reply token: {token}")
        values[key] = value
    return values


def wait_pairs(count=4):
    before = command("stereo_stats")["pairs"]
    deadline = time.monotonic() + 15
    while command("stereo_stats")["pairs"] < before + count:
        if time.monotonic() > deadline:
            raise RuntimeError("MP stereo replay did not advance")
        time.sleep(.05)


def settle_stereo(timeout=8):
    deadline = time.monotonic() + timeout
    while True:
        stats = command("stereo_stats")
        hashes = stats["eye_hashes"]
        cycles = stats["eye_cycles"]
        if (hashes[0] == hashes[1] and cycles[0] == cycles[1] and
                hashes[0] != "0" * len(hashes[0]) and cycles[0]):
            return stats
        if time.monotonic() > deadline:
            raise RuntimeError(f"stereo eyes did not settle: {stats}")
        native.frames(1)


def counter_values():
    return {
        row["name"]: row["count"]
        for row in command("mod_counters")["counters"]
    }


def counter_delta(before, after):
    return {
        key: value - before.get(key, 0)
        for key, value in after.items()
    }


def capture_selector_samples():
    frustum_control("disable")
    native.frames(6)
    frustum_control("start")
    wait_pairs(4)
    status = frustum_control("status")
    frustum_control("stop")
    wait_pairs(4)
    settle_stereo()
    count = int(status["count"])
    samples = []
    for index in range(count):
        raw = frustum_control(f"read={index}")
        samples.append({
            "node": raw["node"].upper(),
            "return_address": raw["ra"].upper(),
            "eye": int(raw["eye"]),
            "center": [int(value) for value in raw["center"].split(",")],
            "radius": int(raw["radius"]),
            "control": [value.upper() for value in raw["control"].split(",")],
            "screen": [int(value) for value in raw["screen"].split(",")],
            "projection": [int(value) for value in raw["projection"].split(",")],
            "camera": raw["camera"].upper(),
            "input": raw["input"].upper(),
            "view": raw["view"].upper(),
            "native_result": int(raw["native_result"]),
            "result_valid": int(raw["result_valid"]),
            "override_result": int(raw["override_result"]),
            "override_valid": int(raw["override_valid"]),
        })
    return samples


def compare_selector_samples(samples):
    by_eye = {0: {}, 1: {}}
    for sample in samples:
        eye = sample["eye"]
        if eye not in by_eye:
            raise RuntimeError(f"Unexpected selector eye {eye}")
        if not sample["result_valid"] or not sample["override_valid"]:
            raise RuntimeError(f"Selector result missing for {sample['node']}")
        if sample["screen"] != [540, 120]:
            raise RuntimeError(
                f"Selector bounds changed: {sample['node']} {sample['screen']}"
            )
        if sample["node"] in by_eye[eye]:
            raise RuntimeError(f"Duplicate selector node {sample['node']}")
        by_eye[eye][sample["node"]] = sample
    if set(by_eye[0]) != set(by_eye[1]):
        raise RuntimeError("Selector nodes differ between eyes")
    if not by_eye[0]:
        raise RuntimeError("Selector capture was empty")

    result = {}
    for eye, nodes in by_eye.items():
        native_visible = sorted(
            node for node, sample in nodes.items()
            if sample["native_result"]
        )
        override_visible = sorted(
            node for node, sample in nodes.items()
            if sample["override_result"]
        )
        native_set = set(native_visible)
        override_set = set(override_visible)
        result[str(eye)] = {
            "samples": len(nodes),
            "native_visible": native_visible,
            "override_visible": override_visible,
            "changed_nodes": sorted(native_set ^ override_set),
            "native_visible_count": len(native_set),
            "override_visible_count": len(override_set),
        }
    return result


def image_difference(first, second):
    difference = ImageChops.difference(first, second)
    return {
        "bbox": difference.getbbox(),
        "changed_pixels": sum(
            pixel != (0, 0, 0) for pixel in difference.getdata()
        ),
    }


def run_visibility_case(out, name, pose, selection):
    from check_weapon_pose_spaces import capture_eyes, set_head

    head = set_head(**pose)
    frustum_control("disable")
    native.frames(8)

    before_off = counter_values()
    samples = capture_selector_samples()
    decisions = compare_selector_samples(samples)
    off_dir = out / f"{name}-frustum-off"
    try:
        off_images, off_files = capture_eyes(
            off_dir, require_visible=selection != "changed"
        )
    except BaseException as error:
        native.save(out / f"{name}-off-capture-failure.json", {
            "case": name,
            "pose": head,
            "selection": selection,
            "decisions": decisions,
            "samples": samples,
        })
        raise RuntimeError(
            f"{name}: frustum-off capture failed: {error}"
        ) from error
    off_stats = settle_stereo()
    off_checks = command("render_pass_stats")
    after_off = counter_values()
    off_delta = counter_delta(before_off, after_off)

    before_on = counter_values()
    frustum_control("enable")
    wait_pairs(4)
    settle_stereo()
    on_dir = out / f"{name}-frustum-on"
    try:
        on_images, on_files = capture_eyes(on_dir)
    except BaseException as error:
        native.save(out / f"{name}-on-capture-failure.json", {
            "case": name,
            "pose": head,
            "selection": selection,
            "decisions": decisions,
            "samples": samples,
        })
        raise RuntimeError(
            f"{name}: frustum-on capture failed: {error}"
        ) from error
    on_stats = settle_stereo()
    on_checks = command("render_pass_stats")
    after_on = counter_values()
    on_delta = counter_delta(before_on, after_on)
    frustum_control("disable")
    native.frames(4)

    off_world = [
        world_region_populated(image) for image in off_images
    ]
    on_world = [
        world_region_populated(image) for image in on_images
    ]
    problems = []
    if not all(view["populated"] for view in on_world):
        problems.append("frustum-on world geometry is not populated")
    if (selection == "conservative" and
            not all(view["populated"] for view in off_world)):
        problems.append("frustum-off world geometry is not populated")
    if any(
        ImageChops.difference(*images).getbbox()
        for images in (off_images, on_images)
    ):
        problems.append("zero-offset MP eyes differ")
    if (off_stats["failed"] or on_stats["failed"] or
            on_stats["eye_hashes"][0] != on_stats["eye_hashes"][1] or
            on_stats["eye_cycles"][0] != on_stats["eye_cycles"][1]):
        problems.append("stereo replay state mismatch")
    for label, checks in (("off", off_checks), ("on", on_checks)):
        if (not checks["verify_checks"] or
                any(checks[key] for key in (
                    "verify_mismatch", "vram_leaks", "watchdog",
                    "nesting_repairs"))):
            problems.append(f"{label} rollback check failed")
    for eye in ("left", "right"):
        if not off_delta.get(f"mohu.vr.mp.draw.{eye}", 0):
            problems.append(f"missing off-state draw in {eye}")
        if off_delta.get(f"mohu.vr.mp.frustum.override.{eye}", 0):
            problems.append(f"override ran in off state for {eye}")
        if off_delta.get(f"mohu.vr.mp.frustum.fallback.{eye}", 0):
            problems.append(f"native capture used fallback in {eye}")
        if not on_delta.get(f"mohu.vr.mp.draw.{eye}", 0):
            problems.append(f"missing on-state draw in {eye}")
        if not on_delta.get(f"mohu.vr.mp.frustum.override.{eye}", 0):
            problems.append(f"missing override in {eye}")
        if on_delta.get(f"mohu.vr.mp.frustum.fallback.{eye}", 0):
            problems.append(f"override fell back in {eye}")

    for eye, decision in decisions.items():
        changed = decision["changed_nodes"]
        if selection == "conservative":
            missing = sorted(
                set(decision["native_visible"]) -
                set(decision["override_visible"])
            )
            if missing:
                problems.append(
                    f"eye {eye} override dropped native nodes: {missing}"
                )
        if selection == "changed" and not changed:
            problems.append(f"eye {eye} selector ignored head yaw")
    if problems:
        native.save(out / f"{name}-failure.json", {
            "case": name,
            "pose": head,
            "problems": problems,
            "decisions": decisions,
            "samples": samples,
            "off_stereo": off_stats,
            "on_stereo": on_stats,
            "off_rollback": off_checks,
            "on_rollback": on_checks,
            "off_counter_delta": off_delta,
            "on_counter_delta": on_delta,
            "off_world": off_world,
            "on_world": on_world,
        })
        raise RuntimeError(f"{name}: " + "; ".join(problems))

    off_left = next(off_dir.glob("*_left.png"))
    on_left = next(on_dir.glob("*_left.png"))
    row = {
        "case": name,
        "pose": head,
        "selector": decisions,
        "sample_count": len(samples),
        "samples": samples,
        "off_world": off_world,
        "on_world": on_world,
        "images": {
            "off": off_files,
            "on": on_files,
            "off_left_path": str(off_left),
            "on_left_path": str(on_left),
        },
        "frustum_off": {
            "stereo": off_stats,
            "rollback": off_checks,
            "counter_delta": off_delta,
        },
        "frustum_on": {
            "stereo": on_stats,
            "rollback": on_checks,
            "counter_delta": on_delta,
        },
        "off_vs_on_image": {
            "left": image_difference(off_images[0], on_images[0]),
            "right": image_difference(off_images[1], on_images[1]),
        },
    }
    return row


def move_until_near_wall(out, max_chunks=24, frames_per_chunk=15,
                         blocked_threshold=200000):
    initial = native.players()[0]["position"]
    current = initial
    chunks = []
    low_streak = 0
    try:
        for chunk in range(1, max_chunks + 1):
            command("set_input", buttons=65535, ly=1000)
            native.frames(frames_per_chunk)
            command("set_input", buttons=65535, ly=0)
            native.frames(8)
            previous = current
            current = native.players()[0]["position"]
            movement = max(
                abs(current[axis] - previous[axis]) for axis in range(3)
            )
            chunks.append({
                "chunk": chunk,
                "position": current,
                "max_abs_delta": movement,
            })
            low_streak = low_streak + 1 if movement <= blocked_threshold else 0
            if low_streak >= 2:
                break
    finally:
        command("set_input", buttons=65535, ly=0)
    if low_streak < 2:
        native.save(out / "near-wall-movement-failure.json", {
            "initial": initial,
            "final": current,
            "blocked_threshold": blocked_threshold,
            "chunks": chunks,
        })
        raise RuntimeError(
            "near-wall case did not reach two blocked movement chunks"
        )
    return {
        "initial": initial,
        "final": current,
        "blocked_chunks_required": 2,
        "blocked_threshold": blocked_threshold,
        "chunks": chunks,
    }


def world_region_populated(image):
    # Exclude the lower screen where the first-person weapon and body are drawn.
    crop = image.crop((0, 0, 512, 45))
    colors = len(set(crop.getdata()))
    nonblack = sum(pixel != (0, 0, 0) for pixel in crop.getdata())
    return {
        "nonblack_pixels": nonblack,
        "unique_colors": colors,
        "populated": nonblack >= 512 and colors >= 20,
    }


def find_body_rotation_for_yaw(out, name, yaw, max_chunks=36,
                               frames_per_chunk=6):
    from check_weapon_pose_spaces import set_head

    probes = []
    found = False
    frustum_control("enable")
    try:
        for chunk in range(max_chunks + 1):
            set_head(yaw_mdeg=yaw)
            native.frames(5)
            images, files = pair(
                out / f"{name}-probe-{chunk:02d}",
                require_populated=False,
            )
            probe = {
                "chunk": chunk,
                "body_rotation": native.players()[0]["rotation"],
                "images": files,
                "eyes": [
                    world_region_populated(image) for image in images
                ],
            }
            probes.append(probe)
            if all(eye["populated"] for eye in probe["eyes"]):
                found = True
                break
            if chunk == max_chunks:
                break
            command("set_input", buttons=65535, lx=0)
            native.frames(frames_per_chunk)
            command("set_input", buttons=65535, lx=128)
            native.frames(6)
    finally:
        command("set_input", buttons=65535, lx=128, ly=0)
        frustum_control("disable")
        set_head()
        native.frames(5)
    if not found:
        native.save(out / f"{name}-positioning-failure.json", {
            "yaw_mdeg": yaw,
            "probes": probes,
        })
        raise RuntimeError(
            f"no bounded body heading populated {name} world view"
        )
    return {
        "yaw_mdeg": yaw,
        "body_rotation": native.players()[0]["rotation"],
        "guest_frames_per_chunk": frames_per_chunk,
        "input": "native left analog lx toward 0 while stationary",
        "probes": probes,
    }


def write_visibility_sheet(out, rows):
    pictures = []
    for row in rows:
        path = Path(row["images"]["on_left_path"])
        image = Image.open(path).convert("RGB")
        tile = Image.new("RGB", (image.width, image.height + 18), (20, 22, 27))
        tile.paste(image, (0, 18))
        ImageDraw.Draw(tile).text(
            (6, 3), f"{row['case']}  frustum ON", fill=(255, 255, 255)
        )
        pictures.append(tile)
    sheet = Image.new(
        "RGB", (pictures[0].width, sum(image.height for image in pictures)),
        (20, 22, 27),
    )
    y = 0
    for image in pictures:
        sheet.paste(image, (0, y))
        y += image.height
    proof = native.ROOT / "vr/proof/weapon-mp-visibility-controls.png"
    proof.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(proof)
    return proof


def run_visibility_controls(out, receipt):
    before_players = native.players()
    if (before_players[0]["weapon_slot"], before_players[0]["weapon_id"]) != (0, 0):
        raise RuntimeError("W2.3 fixture is not P38 in slot 1")
    rows = [
        run_visibility_case(out, "zero", {"yaw_mdeg": 0}, "conservative")
    ]
    receipt["visibility_cases"] = rows
    native.save(out / "receipt.json", receipt)
    orientations = {}
    for name, yaw in (
        ("yaw-plus-90", 90000),
        ("yaw-minus-90", -90000),
    ):
        orientations[name] = find_body_rotation_for_yaw(out, name, yaw)
        pose = {"yaw_mdeg": yaw}
        rows.append(run_visibility_case(out, name, pose, "changed"))
        receipt["visibility_cases"] = rows
        native.save(out / "receipt.json", receipt)

    from check_weapon_pose_spaces import set_head
    set_head()
    native.frames(5)
    receipt["near_wall_reload"] = native.load(1)
    movement = move_until_near_wall(out)
    rows.append(run_visibility_case(
        out, "near-wall", {"yaw_mdeg": 0}, "conservative"
    ))
    proof = write_visibility_sheet(out, rows)
    after_players = native.players()
    if (after_players[0]["weapon_id"] != before_players[0]["weapon_id"] or
            after_players[0]["clip"] != before_players[0]["clip"] or
            after_players[0]["reserve"] != before_players[0]["reserve"] or
            after_players[1]["health_raw"] != before_players[1]["health_raw"]):
        raise RuntimeError("W2.3 controls changed weapon, ammo or P2 health")
    return {
        "cases": rows,
        "body_orientations": orientations,
        "near_wall_movement": movement,
        "players_before": before_players,
        "players_after": after_players,
        "proof_image": str(proof.relative_to(native.ROOT)),
        "proof_image_sha256": native.digest(proof),
    }


def finalize_visibility_evidence(out, receipt):
    raw = out / "receipt.json"
    compact = native.ROOT / "vr/proof/weapon-mp-visibility-receipt.json"
    controls = receipt["visibility_controls"]
    summary_cases = []
    for row in controls["cases"]:
        summary_cases.append({
            "case": row["case"],
            "pose": row["pose"],
            "selector": row["selector"],
            "off_world": row["off_world"],
            "on_world": row["on_world"],
            "images": row["images"],
            "off_vs_on_image": row["off_vs_on_image"],
            "frustum_off": {
                "stereo_pairs": row["frustum_off"]["stereo"]["pairs"],
                "rollback": row["frustum_off"]["rollback"],
                "counter_delta": {
                    key: value for key, value in
                    row["frustum_off"]["counter_delta"].items()
                    if key.startswith("mohu.vr.mp.frustum.")
                },
            },
            "frustum_on": {
                "stereo_pairs": row["frustum_on"]["stereo"]["pairs"],
                "rollback": row["frustum_on"]["rollback"],
                "counter_delta": {
                    key: value for key, value in
                    row["frustum_on"]["counter_delta"].items()
                    if key.startswith("mohu.vr.mp.frustum.")
                },
            },
        })
    native.save(compact, {
        "schema": 1,
        "date": "2026-10-26",
        "kind": "W2.3 multiplayer head visibility controls",
        "complete": True,
        "fixture": "copied root MP slot 1, P38 ID 0, no switching or firing",
        "executable_sha256": receipt["executable_sha256"],
        "source_hashes": receipt["sources"],
        "raw_receipt": str(raw.relative_to(native.ROOT)),
        "raw_receipt_sha256": native.digest(raw),
        "controls": summary_cases,
        "body_orientations": {
            name: {
                "yaw_mdeg": value["yaw_mdeg"],
                "body_rotation": value["body_rotation"],
                "guest_frames_per_chunk": value["guest_frames_per_chunk"],
                "input": value["input"],
                "selected_chunk": len(value["probes"]) - 1,
            }
            for name, value in controls["body_orientations"].items()
        },
        "near_wall_movement": controls["near_wall_movement"],
        "proof_image": controls["proof_image"],
        "proof_image_sha256": controls["proof_image_sha256"],
        "source_saves_unchanged": receipt["source_saves_unchanged"],
        "preferences_unchanged": receipt["preferences_unchanged"],
        "remaining_game_pids": receipt["remaining_game_pids"],
        "limits": [
            "Desktop synthetic head controls, not physical headset acceptance.",
            "The selector uses its measured 540x120 bounds; replay images are 512x120.",
            "No weapon switch or firing occurred.",
        ],
    })
    receipt["compact_receipt"] = str(compact.relative_to(native.ROOT))
    receipt["compact_receipt_sha256"] = native.digest(compact)
def pair(directory, require_populated=True):
    directory.mkdir()
    settle_stereo()
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
    if any(
        im.size != (512, 120) or
        (
            require_populated and
            (len(set(im.getdata())) < 100 or
             sum(ImageStat.Stat(im).mean) < 10)
        )
        for im in images
    ):
        raise RuntimeError("Empty or incorrectly sized MP view")
    return images, {p.name: native.digest(p) for p in (left[0], right[0])}


def finalize_gun_only_evidence(out, receipt):
    unique = {}
    cases = 0
    masks = {"left": 0, "right": 0}
    for row in receipt["weapons"]:
        unique.setdefault(row["id"], row)
        for case in row["cases"]:
            cases += 1
            delta = case["counter_delta"]
            for eye in ("left", "right"):
                count = delta.get("mohu.vr.weapon.gun_only." + eye, 0)
                if not count:
                    raise RuntimeError(
                        f"Missing gun-only mask for ID {row['id']} "
                        f"{case['case']} {eye}"
                    )
                masks[eye] += count
            rollback = case["rollback"]
            if not rollback["verify_checks"] or any(
                rollback[key] for key in
                ("verify_mismatch", "vram_leaks", "watchdog", "nesting_repairs")
            ):
                raise RuntimeError("Gun-only rollback verification failed")
    if set(unique) != set(native.WEAPONS):
        raise RuntimeError("Gun-only control did not cover all 13 IDs")

    panel_width, panel_height = 262, 30
    scale = 2
    label_width = 170
    columns = ("native", "translated", "yawed")
    sheet = Image.new(
        "RGB",
        (label_width + panel_width * scale * len(columns),
         panel_height * scale * len(unique)),
        (20, 20, 20),
    )
    draw = ImageDraw.Draw(sheet)
    for row_index, weapon_id in enumerate(sorted(unique)):
        row = unique[weapon_id]
        draw.text(
            (6, row_index * panel_height * scale + 17),
            f"{weapon_id:02} {native.WEAPONS[weapon_id]}",
            fill=(235, 235, 235),
        )
        for column, label in enumerate(columns):
            case = next(
                case for case in row["cases"] if case["case"] == label
            )
            case_dir = out / (
                f"slot-{row['slot']:02}-weapon-{row['switches']}-{label}"
            )
            filename = sorted(case["images"])[0]
            image = Image.open(case_dir / filename).convert("RGB")
            crop = image.crop((250, 90, 512, 120))
            crop = crop.resize(
                (panel_width * scale, panel_height * scale),
                Image.Resampling.NEAREST,
            )
            x = label_width + column * panel_width * scale
            y = row_index * panel_height * scale
            sheet.paste(crop, (x, y))
            draw.rectangle(
                (x, y, x + panel_width * scale - 1,
                 y + panel_height * scale - 1),
                outline=(70, 70, 70),
            )

    proof_image = native.ROOT / "vr/proof/weapon-complete-gun-controls.png"
    sheet.save(proof_image, optimize=True)
    compact_path = (
        native.ROOT / "vr/proof/weapon-complete-gun-controls-receipt.json"
    )
    compact = {
        "schema": 1,
        "kind": "W3.4 all-ID complete-gun desktop controls",
        "headset_used": False,
        "complete": True,
        "source_receipt": str((out / "receipt.json").relative_to(native.ROOT)),
        "source_receipt_sha256": native.digest(out / "receipt.json"),
        "executable_sha256": receipt["executable_sha256"],
        "sources": receipt["sources"],
        "source_saves": receipt["source_saves"],
        "preferences": receipt["preferences"],
        "unique_weapon_ids": sorted(unique),
        "captured_slot_rows": len(receipt["weapons"]),
        "cases": cases,
        "eye_mask_applications": masks,
        "cycles_closed": receipt["cycles"],
        "weapons": [
            {
                "id": row["id"],
                "slot": row["slot"],
                "switches": row["switches"],
                "cases": [case["case"] for case in row["cases"]],
                "image_hashes": [case["images"] for case in row["cases"]],
                "rollback_checks": sum(
                    case["rollback"]["verify_checks"]
                    for case in row["cases"]
                ),
                "mask_counts": {
                    eye: sum(
                        case["counter_delta"].get(
                            "mohu.vr.weapon.gun_only." + eye, 0
                        )
                        for case in row["cases"]
                    )
                    for eye in ("left", "right")
                },
            }
            for row in receipt["weapons"]
        ],
        "proof_image": str(proof_image.relative_to(native.ROOT)),
        "proof_image_sha256": native.digest(proof_image),
        "source_saves_unchanged": receipt["source_saves_unchanged"],
        "preferences_unchanged": receipt["preferences_unchanged"],
        "remaining_game_pids": receipt["remaining_game_pids"],
        "limits": [
            "Desktop synthetic pose controls, not physical acceptance.",
            "Gun-only mask and native-pose integrity, not grip/scale acceptance.",
            "No firing, NPC/SP override, special-animation or hardware claim.",
        ],
    }
    native.save(compact_path, compact)
    receipt["compact_receipt"] = str(compact_path.relative_to(native.ROOT))
    receipt["compact_receipt_sha256"] = native.digest(compact_path)
    native.save(out / "receipt.json", receipt)
    print(
        f"PASS: 13 complete-gun IDs, {cases} desktop cases, "
        f"{masks['left'] + masks['right']} eye masks",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--all-weapons", action="store_true")
    parser.add_argument("--eye-offset", type=int, default=0)
    parser.add_argument("--native-projection", action="store_true")
    parser.add_argument("--production-config", action="store_true")
    parser.add_argument("--require-native", action="store_true")
    parser.add_argument("--native-warm-seconds", type=int, default=0)
    parser.add_argument("--reject-recover", action="store_true")
    parser.add_argument("--fire-pistol", action="store_true")
    parser.add_argument("--frustum", action="store_true")
    parser.add_argument("--gun-only", action="store_true",
                        help="Enable measured complete-gun masks for every ID")
    parser.add_argument("--calibrated-all", action="store_true",
                        help="Enable provisional measured calibration for every ID")
    parser.add_argument(
        "--visibility-controls", action="store_true",
        help="Run W2.3 zero, +/-90-degree and near-wall selector controls",
    )
    args = parser.parse_args()
    if args.all_weapons and args.fire_pistol:
        parser.error('--fire-pistol is a separate focused slot-1 control; omit --all-weapons')
    effective_gun_only = args.gun_only or args.calibrated_all
    if args.visibility_controls and any((
        args.all_weapons, args.native_projection, args.reject_recover,
        args.fire_pistol, args.frustum, args.eye_offset, args.calibrated_all,
    )):
        parser.error("--visibility-controls cannot be combined with other modes")
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
            source = native.ROOT / f"analysis/fixtures/mp/openbios/state_8001F844_slot{slot:02}.{suffix}"
            shutil.copyfile(source, copies / source.name)
            sources.append(source)
    hashes = {str(p): native.digest(p) for p in sources}
    preferences = [native.ROOT / "build-release/settings.toml",
                   native.ROOT / "build-release/keybinds.ini",
                   Path("C:/Program Files (x86)/Steam/config/steamvr.vrsettings")]
    preference_hashes = {str(p): native.digest(p) for p in preferences if p.exists()}
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PSX_", "MOHU_VR_"))}
    env.update(PSX_DEV_INPUT="0", PSX_VSYNC="0", PSX_OPENXR_ENABLE="0",
               PSX_INTERNAL_RESOLUTION="native",
               PSX_STEREO_SHED="0", PSX_RENDER_PASS_VERIFY="1",
               MOHU_VR_MP_CONTROL="1", MOHU_VR_STEREO_PROOF="1",
               MOHU_VR_EYE_RENDER_VIEW="0" if args.native_projection else "1",
               MOHU_VR_EYE_GUEST_SUBMIT="1",
               MOHU_VR_EYE_OFFSET=str(args.eye_offset), PSX_VR_WEAPON_POSE="1",
               MOHU_VR_WEAPON_SYNTHETIC_X="1",
               MOHU_VR_WEAPON_GUN_ONLY="1" if effective_gun_only else "0",
               MOHU_VR_WEAPON_CALIBRATED="1" if args.calibrated_all else "0",
               MOHU_VR_MP_FRUSTUM="1" if args.frustum else "0")
    # A nonzero synthetic pose selects the diagnostic tracking source. Identity
    # controls are selected through the command after loading the fixture.
    exe = native.ROOT / "build-release/Medal_of_Honor_Underground_Recompiled.exe"
    receipt = {"complete": False, "eye_offset": args.eye_offset,
               "mp_frustum": args.frustum, "gun_only": effective_gun_only,
               "calibrated_all": args.calibrated_all,
               "production_config": args.production_config,
               "require_native": args.require_native,
               "executable_sha256": native.digest(exe), "source_saves": hashes,
               "preferences": preference_hashes, "weapons": [], "cycles": {},
               "sources": {str(p.relative_to(native.ROOT)): native.digest(p) for p in
                           (native.ROOT / "vr/underground/vr_diagnostic.c",
                            native.ROOT / "vr/underground/mp_view.h",
                            native.ROOT / "vr/underground/frustum.h",
                            native.ROOT / "vr/tools/check_mp_view.py",
                            native.ROOT / "vr/tools/check_weapon_pose_spaces.py",
                            native.ROOT / "vr/tests/test_mp_view.c",
                            native.ROOT / "psxrecomp/runtime/src/vr_geometry_math.c",
                            native.ROOT / "psxrecomp/runtime/include/vr_geometry_math.h")}}
    game_config = native.ROOT / (
        "game.toml" if args.production_config
        else "analysis/vr-baseline/game-interp.toml"
    )
    receipt["sources"][str(game_config.relative_to(native.ROOT))] = native.digest(
        game_config
    )
    with (out / "stdout.log").open("w") as stdout, (out / "stderr.log").open("w") as stderr:
        process = subprocess.Popen([str(exe), "--headless-opengl", "--no-launcher",
            "--game", str(game_config),
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
                if args.native_warm_seconds:
                    if not args.require_native:
                        parser.error("--native-warm-seconds requires --require-native")
                    time.sleep(args.native_warm_seconds)
                    native.frames(30)
                native_before = None
                if args.require_native:
                    native_before = overlay_native_summary(
                        command("overlay_native_ring")
                    )
                if args.visibility_controls:
                    receipt["visibility_controls"] = run_visibility_controls(
                        out, receipt
                    )
                    receipt["complete"] = True
                    native.save(out / "receipt.json", receipt)
                    continue
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
                            if effective_gun_only:
                                if not delta.get(
                                        "mohu.vr.weapon.gun_only." + eye, 0):
                                    raise RuntimeError(
                                        "Complete-gun mask did not run in one eye")
                            elif any(value for key, value in delta.items()
                                     if key.startswith(
                                         "mohu.vr.weapon.gun_only.")):
                                raise RuntimeError(
                                    "Complete-gun mask ran with its guard disabled")
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
            if args.require_native:
                native_after = overlay_native_summary(
                    command("overlay_native_ring")
                )
                receipt["overlay_native"] = {
                    "before": native_before,
                    "after": native_after,
                }
                if (not native_before["native_exec"] or
                        not native_after["native_exec"] or
                        native_after["calls_total"] <= native_before["calls_total"]):
                    raise RuntimeError("MP control did not execute native overlays")
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
    if args.visibility_controls and receipt.get("complete"):
        finalize_visibility_evidence(out, receipt)
    if effective_gun_only and args.all_weapons and receipt.get("complete"):
        finalize_gun_only_evidence(out, receipt)
    if not (receipt["source_saves_unchanged"] and receipt["preferences_unchanged"]
            and not receipt["remaining_game_pids"] and receipt["exit_code"] == 0):
        raise RuntimeError("MP control cleanup failed")


if __name__ == "__main__":
    main()
