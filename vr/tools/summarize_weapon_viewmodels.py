"""Check viewport-specific MP weapon controls and retain a compact receipt.

The fixed rectangles are explicit measurements of the stationary split-screen
fixture. They do not prove whole-image equality, physical calibration, or aim.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from inspect_weapon_sets import WEAPONS, digest, p2_damage_in_trace, save

REGIONS = {
    "top_world": (110, 30, 190, 65),
    "bottom_world": (20, 170, 150, 215),
    "top_ammo": (380, 0, 512, 45),
    "bottom_ammo": (380, 123, 512, 168),
    "other_weapon": (260, 218, 512, 240),
}


def changed(a, b):
    return sum(pixel != (0, 0, 0) for pixel in ImageChops.difference(a, b).getdata())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("--combat", type=Path)
    parser.add_argument("--stereo", type=Path)
    args = parser.parse_args()
    inventory = json.loads((args.directory / "inventory.json").read_text())
    if not (inventory["complete"] and inventory["exit_code"] == 0 and
            inventory["source_saves_unchanged"] and inventory["preferences_unchanged"]
            and not inventory["remaining_game_pids"]):
        raise RuntimeError("Incomplete or unclean inventory")
    rows = []
    pictures = {}
    for slot in inventory["slots"]:
        if not slot.get("cycle_closed"):
            raise RuntimeError("Inventory cycle did not close")
        for capture in slot["captures"]:
            if not capture.get("pose_controls"):
                continue
            weapon_id = capture["players"][0]["weapon_id"]
            controls = {c["case"]: c for c in capture["pose_controls"]}
            if set(controls) != {"native", "translated", "yawed", "lost", "restored"}:
                raise RuntimeError("Incomplete pose controls")
            if not capture.get("pose_scope_drained"):
                raise RuntimeError("Missing drained apply/restore check")
            images = {}
            for case, control in controls.items():
                path = args.directory / control["image"]
                if digest(path) != control["sha256"]:
                    raise RuntimeError("Capture hash changed")
                images[case] = Image.open(path).convert("RGB")
            cases = {}
            for case in ("translated", "yawed", "lost", "restored"):
                region_changes = {
                    name: changed(images["native"].crop(rect), images[case].crop(rect))
                    for name, rect in REGIONS.items()
                }
                if any(region_changes.values()):
                    raise RuntimeError(f"ID {weapon_id}: {case} changed fixed controls: {region_changes}")
                # This rectangle includes the top gun and the idle target.
                # Nonzero differences locate motion; inspect the proof sheet
                # to distinguish the gun from native actor/animation changes.
                top_changes = changed(images["native"].crop((0, 65, 512, 120)),
                                      images[case].crop((0, 65, 512, 120)))
                if case in ("translated", "yawed") and not top_changes:
                    raise RuntimeError(f"ID {weapon_id}: no top-view change")
                cases[case] = {"fixed_region_changed_pixels": region_changes,
                               "top_lower_region_changed_pixels": top_changes,
                               **controls[case]}
            rows.append({"slot": slot["slot"], "weapon_id": weapon_id,
                         "name": WEAPONS[weapon_id], "mesh": capture["first_person_model"],
                         "scope_drained": True, "cases": cases})
            pictures.setdefault(weapon_id, images)
    if set(pictures) != set(WEAPONS):
        raise RuntimeError("Missing measured weapon ID")
    sheet = Image.new("RGB", (3 * 512, 32 + 145 * len(pictures)), (22, 24, 29))
    draw = ImageDraw.Draw(sheet)
    for column, label in enumerate(("Native", "Translation +24", "Yaw +12 degrees")):
        draw.text((column * 512 + 8, 10), label, fill="white")
    for row, weapon_id in enumerate(sorted(pictures)):
        y = 32 + row * 145
        draw.text((8, y), f"ID {weapon_id}: {WEAPONS[weapon_id]}", fill="white")
        for column, case in enumerate(("native", "translated", "yawed")):
            sheet.paste(pictures[weapon_id][case].crop((0, 0, 512, 120)),
                        (column * 512, y + 20))
    sheet.save(args.image)
    receipt = {
        "date": "2026-10-25", "kind": "multiplayer first-person geometry mapping",
        "inventory": str(args.directory / "inventory.json"),
        "inventory_sha256": digest(args.directory / "inventory.json"),
        "executable_sha256": inventory["executable_sha256"],
        "revision": inventory["revision"], "vr_sources": inventory.get("vr_sources", {}),
        "source_saves": inventory["source_saves"],
        "fixed_regions_xyxy": REGIONS,
        "proof_image_sha256": digest(args.image), "rows": rows,
        "unique_ids": sorted(pictures),
        "source_saves_unchanged": True, "preferences_unchanged": True,
        "remaining_owned_processes": [],
        "limits": ["Fixed regions cover selected world/HUD/other-weapon pixels only.",
                   "Idle actors and native weapon animation continue between captures.",
                   "This is a flat MP geometry control; multiplayer stereo is not accepted.",
                   "Grip/pivot/scale, physical tracking, shot alignment and barrel laser remain open."],
    }
    if args.combat:
        combat_path = args.combat / "inventory.json"
        combat = json.loads(combat_path.read_text())
        if not (combat["complete"] and combat["exit_code"] == 0 and
                combat["source_saves_unchanged"] and combat["preferences_unchanged"]
                and not combat["remaining_game_pids"] and
                set(combat["p2_damaged_ids"]) == set(WEAPONS)):
            raise RuntimeError("Incomplete combat matrix")
        hits = []
        for slot in combat["slots"]:
            for capture in slot["captures"]:
                if not capture.get("fire"):
                    continue
                attempts = capture["fire"]["attempts"]
                valid = [a for a in attempts if p2_damage_in_trace(a["health_trace"], a["before"][1])]
                if not valid:
                    raise RuntimeError("No native P2 health-address decrease")
                hit = valid[0]
                hits.append({"slot": slot["slot"], "weapon_id": capture["players"][0]["weapon_id"],
                             "p2_health_before": hit["before"][1]["health"],
                             "p2_health_after": hit["after"][1]["health"],
                             "native_trace_entries": hit["health_trace"]["emitted"],
                             "native_p2_decrease": True})
        receipt["combat"] = {"inventory": str(combat_path), "sha256": digest(combat_path),
                             "executable_sha256": combat["executable_sha256"],
                             "controls": combat["controls"], "hits": hits,
                             "source_saves_unchanged": True, "preferences_unchanged": True}
    if args.stereo:
        stereo_path = args.stereo / "receipt.json"
        stereo = json.loads(stereo_path.read_text())
        passes = stereo["after"]["render_pass_stats"]
        stats = stereo["after"]["stereo_stats"]
        if (stereo.get("error") or not stereo["settings_restored"] or stereo["remaining_game_pids"]
                or not passes["verify_checks"] or any(passes[k] for k in
                ("verify_mismatch", "vram_leaks", "watchdog", "nesting_repairs"))
                or not stats["pairs"] or stats["failed"]
                or stats["eye_hashes"][0] != stats["eye_hashes"][1]
                or stats["eye_cycles"][0] != stats["eye_cycles"][1]):
            raise RuntimeError("SP stereo regression failed")
        receipt["sp_stereo_regression"] = {
            "receipt": str(stereo_path), "sha256": digest(stereo_path),
            "pairs": stats["pairs"], "eye_hashes": stats["eye_hashes"],
            "eye_cycles": stats["eye_cycles"],
            **{k: passes[k] for k in ("verify_checks", "verify_mismatch", "vram_leaks",
                                      "watchdog", "nesting_repairs")},
            "mp_weapon_stereo_accepted": False,
        }
    save(args.receipt, receipt)


if __name__ == "__main__":
    main()
