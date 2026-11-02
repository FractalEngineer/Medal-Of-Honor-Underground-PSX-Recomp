import sys
import unittest
from unittest.mock import patch, call
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "vr/tools"))
import probe_p38_headset as tool


def hands(*, synthetic=0, focused=1, origin=1, active=1, flags=15):
    pose = {
        "active": active,
        "flags": flags,
        "position_m": [0.0, 0.0, 0.0],
        "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
    }
    return {
        "synthetic": synthetic,
        "focused": focused,
        "origin_valid": origin,
        "pose": [[pose.copy(), pose.copy()], [pose.copy(), pose.copy()]],
    }


def sample(index):
    return {
        "hands": hands(),
        "input": {
            "stick": [[0.0, 0.0], [0.0, 0.0]],
            "trigger_active": [0, 0],
            "buttons_active": [0, 0],
        },
    }


class P38HeadsetTests(unittest.TestCase):
    def test_loaded_pad_does_not_mask_xr_actions(self):
        with patch.object(tool.native, "command") as command:
            tool.release_load_override()
        self.assertEqual(command.call_args_list, [
            call("clear_input"),
            call("set_input", layer="host", buttons=65535),
        ])

    def test_comparison_disables_dithering(self):
        for mode in tool.MODES:
            self.assertEqual(tool.environment(mode, True)["PSX_DITHERING"], "0")

    def test_mp_smoke_enables_the_measured_mp_frustum(self):
        for mode in tool.MODES:
            self.assertEqual(tool.environment(mode, True)["MOHU_VR_MP_FRUSTUM"], "1")

    def test_mp_frustum_checks_report_real_selector_counters(self):
        checks = tool.mp_frustum_checks({
            "mohu.vr.mp.frustum.override.left": 42,
            "mohu.vr.mp.frustum.override.right": 41,
            "mohu.vr.mp.frustum.fallback.left": 0,
            "mohu.vr.mp.frustum.fallback.right": 1,
            "mohu.vr.mp.guard_fail": 0,
        })
        self.assertEqual(checks["override_left"], 42)
        self.assertEqual(checks["override_right"], 41)
        self.assertEqual(checks["fallback_left"], 0)
        self.assertEqual(checks["fallback_right"], 1)

    def test_hand_fixed_smoke_explicitly_selects_current_aim(self):
        env = tool.environment("tracked", True, hand_fixed=True)
        self.assertEqual(env["MOHU_VR_WEAPON_AIM"], "1")
        self.assertEqual(env["MOHU_VR_WEAPON_CALIBRATED"], "1")
        self.assertEqual(env["MOHU_VR_WEAPON_GUN_ONLY"], "1")
        self.assertEqual(env["MOHU_VR_P38_AIM"], "0")
        native = tool.environment("native", True, hand_fixed=True)
        self.assertEqual(native.get("MOHU_VR_WEAPON_AIM", "0"), "0")

    def test_hand_fixed_runtime_requires_capture_off_and_camera_aim(self):
        camera = {"valid": 1, "owner": 0x801483D0, "cycle": 100}
        counters = {
            "mohu.vr.shot.camera.native": 2,
            "mohu.vr.shot.p1.eligible": 1,
            "mohu.vr.shot.weapon.aimed": 1,
            "mohu.vr.shot.weapon.tracking_fallback": 0,
            "mohu.vr.shot.p38.aimed": 0,
        }
        result = tool.hand_fixed_checks(
            camera,
            [{**camera, "cycle": 200}],
            {**camera, "cycle": 300},
            [{"capture": 0, "count": 0}],
            counters,
            camera["owner"],
        )
        self.assertEqual(result["problems"], [])
        self.assertEqual(result["camera_cycle_advance"], 200)
        self.assertFalse(result["capture_armed"])

    def test_hand_fixed_runtime_rejects_recording_and_fallback(self):
        camera = {"valid": 1, "owner": 0x801483D0, "cycle": 100}
        result = tool.hand_fixed_checks(
            camera,
            [],
            camera,
            [{"capture": 1, "count": 1}],
            {"mohu.vr.shot.weapon.tracking_fallback": 1},
            camera["owner"],
        )
        self.assertIn("shot capture was armed", result["problems"])
        self.assertIn("shot samples were recorded", result["problems"])
        self.assertIn(
            "canonical camera did not refresh", result["problems"]
        )
        self.assertIn(
            "hand-fixed aim used a tracking fallback",
            result["problems"],
        )

    def test_desktop_camera_check_does_not_require_a_shot(self):
        camera = {"valid": 1, "owner": 0x801483D0, "cycle": 100}
        result = tool.hand_fixed_checks(
            camera,
            [],
            {**camera, "cycle": 200},
            [{"capture": 0, "count": 0}],
            {"mohu.vr.shot.camera.native": 1},
            camera["owner"],
            require_aim=False,
        )
        self.assertEqual(result["problems"], [])

    def test_tracked_comparison_explicitly_selects_calibrated_combat_candidate(self):
        for mode in tool.MODES:
            env = tool.environment(mode, True)
            expected = str(int(mode == "tracked"))
            self.assertEqual(env["MOHU_VR_P38_CALIBRATED"], expected)
            self.assertEqual(env["MOHU_VR_P38_AIM"], expected)

    def test_compare_runs_native_before_tracked(self):
        self.assertEqual(tool.comparison_modes("compare"), ("native", "tracked"))
        self.assertEqual(tool.comparison_modes("tracked"), ("tracked",))

    def test_duration_is_bounded(self):
        self.assertEqual(tool.validate_seconds(30), 30)
        for value in (0, tool.MAX_SECONDS + 1):
            with self.assertRaises(ValueError):
                tool.validate_seconds(value)

    def test_live_hand_requires_focus_origin_and_flags(self):
        self.assertTrue(tool.hands_are_live(hands()))
        self.assertFalse(tool.hands_are_live(hands(synthetic=1)))
        self.assertFalse(tool.hands_are_live(hands(focused=0)))
        self.assertFalse(tool.hands_are_live(hands(origin=0)))
        self.assertFalse(tool.hands_are_live(hands(flags=1)))
        self.assertTrue(tool.hand_pose_ready(hands(synthetic=1)))

    def test_inherited_vr_flags_are_removed(self):
        cleaned = tool.clean_environment(
            {
                "PATH": "ok",
                "PSX_OPENXR_ENABLE": "1",
                "MOHU_VR_MP_CONTROL": "1",
                "XR_RUNTIME_JSON": "stale.json",
            }
        )
        self.assertEqual(cleaned, {"PATH": "ok"})

    def test_sample_summary_counts_live_and_movement(self):
        values = [sample(0), sample(1), sample(2)]
        values[1]["input"]["stick"][0][1] = 0.8
        summary = tool.summarize_samples(values)
        self.assertEqual(summary["live_hand_samples"], 3)
        self.assertEqual(summary["pose_ready_samples"], 3)
        self.assertEqual(summary["focused_samples"], 3)
        self.assertTrue(summary["user_input_observed"])

    def test_p38_identity_is_exact(self):
        model = {
            "magic": "0xe0007",
            "face_count": tool.P38_FACE_COUNT,
            "node_count": tool.P38_NODE_COUNT,
            "geometry_fnv32": "0x8544f8b9",
        }
        self.assertTrue(tool.p38_model_matches(model))
        model["node_count"] += 1
        self.assertFalse(tool.p38_model_matches(model))


if __name__ == "__main__":
    unittest.main()
