import unittest

from PIL import Image, ImageDraw

import check_mp_view


def sample(node, eye, native_result, override_result):
    return {
        "node": node,
        "eye": eye,
        "screen": [540, 120],
        "result_valid": 1,
        "override_valid": 1,
        "native_result": native_result,
        "override_result": override_result,
    }


class MpVisibilityTests(unittest.TestCase):
    def test_parse_reply(self):
        self.assertEqual(
            check_mp_view.parse_reply("capture=1 count=42"),
            {"capture": "1", "count": "42"},
        )
        with self.assertRaises(RuntimeError):
            check_mp_view.parse_reply("capture=1 malformed")

    def test_selector_difference_is_reported_per_eye(self):
        samples = [
            sample("80100000", 0, 1, 1),
            sample("80100010", 0, 1, 0),
            sample("80100000", 1, 0, 1),
            sample("80100010", 1, 0, 0),
        ]
        result = check_mp_view.compare_selector_samples(samples)
        self.assertEqual(
            result["0"]["changed_nodes"], ["80100010"]
        )
        self.assertEqual(
            result["1"]["changed_nodes"], ["80100000"]
        )

    def test_selector_rejects_missing_decision(self):
        samples = [
            sample("80100000", 0, 1, 1),
            sample("80100000", 1, 1, 1),
        ]
        samples[0]["override_valid"] = 0
        with self.assertRaises(RuntimeError):
            check_mp_view.compare_selector_samples(samples)

    def test_world_population_excludes_lower_body_region(self):
        image = Image.new("RGB", (512, 120), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((180, 50, 332, 110), fill=(180, 120, 80))
        self.assertFalse(check_mp_view.world_region_populated(image)["populated"])
        for x in range(20, 221):
            draw.line((x, 0, x, 45), fill=(x % 256, 100, 80))
        self.assertTrue(check_mp_view.world_region_populated(image)["populated"])


if __name__ == "__main__":
    unittest.main()
