"""Captured per-face record -> CLUT/texpage mapping fixture (M1)."""
import json
import struct
import unittest
from pathlib import Path


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "world_material_records.json"


class WorldMaterialFixtureTest(unittest.TestCase):
    def test_record_words_map_to_material(self):
        data = json.loads(FIXTURE.read_text())
        self.assertEqual(data["mapping"]["record_size"], 12)
        self.assertEqual(data["mapping"]["word0"], "UV0 | CLUT << 16")
        self.assertEqual(data["mapping"]["word1"], "UV1 | texpage << 16")
        self.assertEqual(data["mapping"]["word2"], "UV2")

        packets = 0
        for record in data["records"]:
            raw = bytes.fromhex(record["record_hex"])
            self.assertEqual(len(raw), 12)
            halves = struct.unpack("<6H", raw)
            self.assertEqual(halves[1], record["clut"])
            self.assertEqual(halves[3], record["texpage"])
            self.assertEqual([halves[0], halves[2], halves[4]], record["uv"])
            self.assertEqual(halves[5], 0)
            if record["packet_material"]:
                packets += 1
                self.assertEqual(record["packet_material"]["clut"], record["clut"])
                self.assertEqual(record["packet_material"]["texpage"],
                                 record["texpage"])

        self.assertEqual(packets, 2)
        self.assertEqual(data["records"][0]["clut"], 0x7CC3)
        self.assertEqual(data["records"][0]["texpage"], 0x300E)


if __name__ == "__main__":
    unittest.main()

