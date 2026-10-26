import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_weapon_meshes as meshes


class WeaponMeshTests(unittest.TestCase):
    def test_p38_keeps_barrel_and_rejects_hand_island(self):
        profile = meshes.PROFILES[0]
        self.assertTrue(meshes.selected(profile, 13, 68))
        self.assertTrue(meshes.selected(profile, 11, 6))
        self.assertTrue(meshes.selected(profile, 11, 32))
        self.assertFalse(meshes.selected(profile, 11, 5))
        self.assertFalse(meshes.selected(profile, 11, 33))
        self.assertFalse(meshes.selected(profile, 9, 0))

    def test_silenced_pistol_uses_noncontiguous_suppressor_mask(self):
        profile = meshes.PROFILES[9]
        self.assertTrue(meshes.selected(profile, 11, 17))
        self.assertFalse(meshes.selected(profile, 11, 18))
        self.assertFalse(meshes.selected(profile, 11, 25))
        self.assertTrue(meshes.selected(profile, 11, 26))
        self.assertFalse(meshes.selected(profile, 11, 32))

    def test_components_ignore_filtered_vertices(self):
        triangles = [
            ((11, 6), (11, 7), (11, 8)),
            ((11, 8), (11, 7), (11, 9)),
            ((11, 18), (11, 19), (11, 20)),
        ]
        vertices = {vertex for triangle in triangles for vertex in triangle}
        components = meshes.triangle_components(
            triangles, {(11, index) for index in range(6, 10)}
        )
        self.assertEqual(len(components), 1)
        self.assertEqual(components[0]["triangles"], 2)
        self.assertEqual(components[0]["vertices"], 4)
        self.assertEqual(len(vertices), 7)

    def test_every_profile_has_a_complete_component_selection(self):
        self.assertEqual(set(meshes.PROFILES), {
            0, 1, 4, 5, 8, 9, 10, 12, 13, 14, 15, 16, 17,
        })
        for profile in meshes.PROFILES.values():
            self.assertGreater(profile["faces"], 0)
            self.assertGreater(profile["vertices"], 0)
            self.assertTrue(profile["nodes"])


if __name__ == "__main__":
    unittest.main()
