import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import probe_weapon_profiles as probe


def triangle(vertices):
    result = bytearray(28)
    for index, (node, vertex) in enumerate(vertices):
        result[22 + index * 2:24 + index * 2] = bytes((vertex, node))
    return result


class WeaponProfileProbeTests(unittest.TestCase):
    def test_cycles_cover_each_weapon_once(self):
        ids = [weapon for cycle in probe.CYCLES.values() for weapon in cycle]
        self.assertEqual(len(ids), 16)
        self.assertEqual(set(ids), {
            0, 1, 4, 5, 8, 9, 10, 12, 13, 14, 15, 16, 17,
        })

    def test_topology_validator_requires_a_complete_gun_split(self):
        profile = {
            "id": 99,
            "nodes": {1},
            "partial": None,
            "faces": 1,
            "vertices": 3,
        }
        model = {
            "face_count": 1,
            "nodes": [{"vertices": 0}, {"vertices": 3}],
        }
        nodes = {
            "1": {
                "count": 3,
                "local": [[0, 0, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0]],
            },
        }
        data = triangle([(1, 0), (1, 1), (1, 2)]) + struct.pack("<I", 0x1FFF)
        result = probe.validate_topology(profile, model, data, nodes)
        self.assertEqual(result["faces"], 1)
        self.assertEqual(result["vertices"], 3)
        self.assertEqual(result["mixed_triangles"], 0)


if __name__ == "__main__":
    unittest.main()
