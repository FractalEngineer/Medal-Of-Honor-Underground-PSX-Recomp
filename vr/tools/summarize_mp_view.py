"""Retain the MP eye matrix, lateral control and native-fire recovery proof."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from inspect_weapon_sets import WEAPONS, digest, p2_damage_in_trace, save


def inventory(directory):
    path = directory / "receipt.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if (not value["complete"] or value.get("error") or value["exit_code"] or
            not value["source_saves_unchanged"] or not value["preferences_unchanged"]
            or value["remaining_game_pids"]):
        raise RuntimeError(f"Incomplete/unclean control: {path}")
    return value


def image_pair(directory, row, case):
    folder = directory / f"slot-{row['slot']:02}-weapon-{row['switches']}-{case['case']}"
    paths = [folder / next(name for name in case["images"] if name.endswith("_" + eye + ".png"))
             for eye in ("left", "right")]
    for path in paths:
        if digest(path) != case["images"][path.name]:
            raise RuntimeError("Eye image hash changed")
    return [Image.open(path).convert("RGB") for path in paths]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("lateral", type=Path)
    parser.add_argument("recovery", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    matrix, lateral, recovery = [inventory(p) for p in (args.matrix, args.lateral, args.recovery)]
    if set(matrix["cycles"]) != {"1", "2", "3", "4"} or not all(matrix["cycles"].values()):
        raise RuntimeError("Missing closed native MP cycles")
    rows, pictures = [], {}
    projective_draws = 0
    for row in matrix["weapons"]:
        cases, images = [], {}
        for case in row["cases"]:
            pair = image_pair(args.matrix, row, case)
            if ImageChops.difference(*pair).getbbox():
                raise RuntimeError("Zero eyes differ")
            stats, checks = case["stereo"], case["rollback"]
            projective_draws = max(projective_draws, next((c["count"] for c in
                case["counters"]["counters"] if c["name"] == "vr.projective.draw"), 0))
            if (stats["failed"] or stats["eye_cycles"][0] != stats["eye_cycles"][1]
                    or stats["eye_hashes"][0] != stats["eye_hashes"][1]
                    or not checks["verify_checks"] or any(checks[k] for k in
                    ("verify_mismatch", "vram_leaks", "watchdog", "nesting_repairs"))):
                raise RuntimeError("MP eye transaction failed")
            images[case["case"]] = pair[0]
            cases.append({"case": case["case"], "image_hashes": case["images"],
                          "checkpoint_pairs": stats["pairs"], "eye_cycles": stats["eye_cycles"],
                          "eye_hashes": stats["eye_hashes"], "verify_checks": checks["verify_checks"],
                          "counter_delta": {k: v for k, v in case["counter_delta"].items()
                                            if k.startswith("mohu.vr.")},
                          "sampled_world_difference": case["sampled_world_difference"],
                          "weapon_difference": case["weapon_difference"]})
        if set(images) != {"native", "translated", "yawed", "lost"}:
            raise RuntimeError("Incomplete pose matrix")
        pictures.setdefault(row["id"], images)
        rows.append({"slot": row["slot"], "id": row["id"], "name": WEAPONS[row["id"]], "cases": cases})
    if set(pictures) != set(WEAPONS):
        raise RuntimeError("Missing measured weapon ID")
    lateral_pair = image_pair(args.lateral, lateral["weapons"][0], lateral["weapons"][0]["cases"][0])
    lateral_changes = sum(p != (0, 0, 0) for p in ImageChops.difference(*lateral_pair).getdata())
    if lateral["eye_offset"] != 24 or not lateral_changes:
        raise RuntimeError("No lateral MP parallax")
    fire = recovery["pistol_fire"]
    if not p2_damage_in_trace(fire["native_health_trace"], fire["before"][1]):
        raise RuntimeError("Missing native P2 damage during eye replay")
    recover = recovery["reject_recover"]
    if (recover["refused"]["refused"] <= recover["before"]["refused"] or
            recover["recovered"]["pairs"] <= recover["refused"]["pairs"] or
            recover["recovered"]["failed"] != recover["refused"]["failed"] or
            recover["fresh_image_pair_id"] <= recover["recovered"]["last_failed_attempt"]):
        raise RuntimeError("Rejected draws did not recover to fresh pairs")
    sheet = Image.new("RGB", (1536, 32 + 145 * len(pictures)), (22, 24, 29))
    draw = ImageDraw.Draw(sheet)
    for i, label in enumerate(("P1 native eye", "P1 translation +24", "P1 yaw +12 degrees")):
        draw.text((i * 512 + 8, 10), label, fill="white")
    for i, weapon_id in enumerate(sorted(pictures)):
        y = 32 + i * 145
        draw.text((8, y), f"ID {weapon_id}: {WEAPONS[weapon_id]}", fill="white")
        for column, label in enumerate(("native", "translated", "yawed")):
            sheet.paste(pictures[weapon_id][label], (column * 512, y + 20))
    sheet.save(args.image)
    receipt = {
        "date": "2026-10-25", "kind": "guarded P1-only multiplayer eye replay",
        "executable_sha256": matrix["executable_sha256"], "sources": matrix["sources"],
        "controls": {str(p): digest(p / "receipt.json") for p in (args.matrix, args.lateral, args.recovery)},
        "contract": {"context": "0x800A0B08", "native_frame": "0x80054BC4",
                     "native_caller": "0x80063CF8", "camera_selector": "0x80054E68",
                     "scene_draw": "0x8006E9D8", "player_root": "0x800A3604",
                     "camera_root": "0x800A35B0", "scene_root": "0x800A35CC",
                     "current_player": "0x800A35C4", "eye_size": [512, 120],
                     "world_h": 400, "weapon_h": 133, "weapon_projection_h_ref": 400},
        "code_guards": [
            {"address": "0x80054BC4", "bytes": 512, "fnv32": "6CDFBB75"},
            {"address": "0x80054E68", "bytes": 332, "fnv32": "2BE15194"},
            {"address": "0x8006E9D8", "bytes": 384, "fnv32": "04C21F46"},
            {"address": "0x80082598", "bytes": 580, "fnv32": "8B9E349D"}],
        "unique_ids": sorted(pictures), "native_cycles_closed": matrix["cycles"], "rows": rows,
        "lateral_changed_pixels": lateral_changes,
        "projective_draws": projective_draws,
        "pistol_native_fire": fire,
        "reject_recovery": {key: {name: value[name] for name in
                                  ("pairs", "failed", "refused", "retained_pair_id", "stale_frames",
                                   "last_pair_id", "last_failed_attempt")}
                            for key, value in recover.items() if key in ("before", "refused", "recovered")},
        "recovered_image_pair_id": recover["fresh_image_pair_id"],
        "recovered_image_hashes": recover["fresh_image_hashes"],
        "proof_image_sha256": digest(args.image), "source_saves_unchanged": True,
        "preferences_unchanged": True, "remaining_owned_game_processes": [],
        "limits": ["Desktop synthetic controls, not physical headset acceptance.",
                   "Native 512x120 P1 view; native MP visibility selection remains in use.",
                   "Grip pivot/scale, independent head/hand calibration and tracked shots remain open.",
                   "MP eye bench omits the native split HUD and does not yet draw the laser.",
                   "Image pairs and checkpoint counters are separate bounded live snapshots."],
    }
    save(args.receipt, receipt)


if __name__ == "__main__":
    main()
