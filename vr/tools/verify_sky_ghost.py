"""Verify the bounded courtyard controls; this is not a headset acceptance test."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def pixels(path):
    return np.asarray(Image.open(path).convert("RGB"))


def sky_pixels(rgb):
    height, width = rgb.shape[:2]
    return rgb[height // 10:height * 4 // 10, width * 45 // 100:width * 65 // 100]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--proof", type=Path, required=True)
    args = parser.parse_args()
    root = args.directory
    proof = args.proof
    summary = {"scope": "isolated PGXP slot 2, static courtyard, synthetic null-HMD look-up",
               "headset_acceptance": False, "runs": {}}
    names = ("verified-zero", "verified-sky", "verified-xr", "verified-regression-xr",
             "verified-yaw-positive", "verified-yaw-negative")
    for name in names:
        run = root / name
        receipt = json.loads((run / "receipt.json").read_text())
        assert "error" not in receipt, (name, receipt.get("error"))
        assert receipt["settings_restored"] and not receipt["remaining_game_pids"], name
        assert receipt["after"]["render_pass_stats"]["verify_checks"] > 0
        assert not any(receipt["after"]["render_pass_stats"][key] for key in
                       ("verify_mismatch", "watchdog", "vram_leaks", "nesting_repairs"))
        raw = receipt["raw"]
        assert len(raw) == 4 and all(x["size"] == [2560, 1200] for x in raw)
        if name == "verified-zero":
            assert all(raw[i]["sha256"] == raw[i + 2]["sha256"] for i in (0, 1))
        if "yaw-" in name:
            assert all(sum(x["mean"]) > 10 for x in raw)
            assert all(raw[i]["sha256"] != raw[i + 2]["sha256"] for i in (0, 1))
        log = run / ("vr-launch.stdout.log" if "xr" in name else "control.stdout.log")
        lines = log.read_text().splitlines()
        last = [line for line in lines if "stereo_proof attempt=" in line][-1]
        assert "fallback=0/0" in last
        summary["runs"][name] = {"executable_sha256": receipt["executable_sha256"],
                                  "controls": receipt["controls"],
                                  "raw": [{key: capture[key] for key in ("name", "sha256", "size")} for capture in raw],
                                  "proof_line": last,
                                  "verify_checks": receipt["after"]["render_pass_stats"]["verify_checks"],
                                  "settings_restored": True, "remaining_game_pids": []}
        if "xr" in name:
            xr = receipt["after"]["openxr_stats"]
            assert (xr["submitted_layer"], xr["submitted_source"]) == (1, 1)
            assert xr["empty"] == xr["failures"] == 0
            views = receipt["after"]["openxr_views"]
            assert views["submitted_pair_id"] > receipt["before"]["openxr_views"]["submitted_pair_id"]
            summary["runs"][name]["openxr"] = {key: xr[key] for key in (
                "submitted", "empty", "failures", "submitted_layer", "submitted_source",
                "quad_submitted", "native_submitted", "submitted_surfaces", "units_per_meter")}
            summary["runs"][name]["submitted_pair_id"] = views["submitted_pair_id"]
        if name in ("verified-sky", "verified-xr"):
            for capture in raw:
                image = pixels(run / "raw" / capture["name"])
                assert not sky_pixels(image).any(), (name, capture["name"], "sky ghost")
                # Measured ammo icon site for this fixture; not a general HUD classifier.
                assert int((image[80:150, 2070:2180].max(axis=2) > 140).sum()) == 0
        if name == "verified-xr":
            layer = pixels(run / "layers/application_layer.png")
            for eye in np.array_split(layer, 2, axis=1):
                assert not sky_pixels(eye).any(), "Application layer sky ghost"

    # The same executable must restore the full-scene ghost when the native
    # tail is re-enabled. That establishes causality beyond before/after shots.
    fixed = root / "verified-xr"
    bad = root / "verified-regression-xr"
    assert summary["runs"]["verified-xr"]["executable_sha256"] == summary["runs"]["verified-regression-xr"]["executable_sha256"]
    comparison = []
    for eye in ("left", "right"):
        a = pixels(sorted((fixed / "raw").glob(f"*_{eye}.png"))[0])
        b = pixels(sorted((bad / "raw").glob(f"*_{eye}.png"))[0])
        assert sky_pixels(b).any(), "Regression control did not restore ghost"
        # Exclude the dynamic lamp/weapon area; compare the static left building.
        mask = a[:, :800].max(axis=2) > 0
        agreement = float((a[:, :800][mask] == b[:, :800][mask]).all(axis=1).mean())
        assert agreement > .999, (eye, agreement)
        comparison.append({"eye": eye, "static_world_pixel_agreement": agreement,
                           "removed_background_pixels": int(((a.max(axis=2) == 0) & (b.max(axis=2) > 0)).sum())})
    summary["comparison"] = comparison
    production = root / "production"
    if production.exists():
        log = (production / "vr-launch.stdout.log").read_text()
        last = [line for line in log.splitlines() if "stereo_proof attempt=" in line][-1]
        assert "xr_begin_failures=0 xr_view_failures=0" in last
        assert "fallback=0/0" in last
        flat = (root / "flat/stdout.log").read_text()
        assert "stereo_proof=0" in flat and "openxr=0" in flat and "read_only=1" in flat
        repo = Path(__file__).resolve().parents[2]
        assert "PSX_DEBUG_TOOLS:BOOL=OFF" in (repo / "build-release/CMakeCache.txt").read_text()
        summary["production"] = {
            "debug_tools": False, "proof_line": last, "flat_plugin_inert": True,
            "executable_sha256": hashlib.sha256((repo / "build-release/Medal_of_Honor_Underground_Recompiled.exe").read_bytes()).hexdigest()}
    summary["passed"] = True
    proof.mkdir(parents=True, exist_ok=True)
    (proof / "sky-ghost-receipt.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")

    sheet = Image.new("RGB", (1280, 798), "#202020")
    draw = ImageDraw.Draw(sheet)
    for col, (run, label) in enumerate(((bad, "Control: native tail enabled"), (fixed, "Fix: one cleaned eye submission"))):
        for row, eye in enumerate(("left", "right", "application_layer")):
            path = run / "layers/application_layer.png" if row == 2 else sorted((run / "raw").glob(f"*_{eye}.png"))[0]
            draw.text((col * 640 + 8, row * 266 + 6), f"{label} / {eye}", fill="white")
            frame = Image.open(path).convert("RGB")
            frame.thumbnail((640, 240))
            sheet.paste(frame, (col * 640, row * 266 + 26))
    sheet.save(proof / "sky-ghost-fix.png")
    print(json.dumps({"passed": True, "comparison": comparison}))


if __name__ == "__main__":
    main()
