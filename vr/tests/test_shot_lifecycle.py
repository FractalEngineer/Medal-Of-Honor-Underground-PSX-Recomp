"""Reject ambiguous shot lifetimes and false shotgun spread evidence."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import probe_shot_families as family


class Collector:
    def __init__(self, rows):
        self.rows = rows

    def entries(self, key):
        return self.rows.get(key, [])


def fixture():
    address = 0x80110000
    sample = {"shot": address, "type": 0x13F7,
              "position": [0,0,0], "angles": [0,0,0]}
    constructor = [{"s0": hex(address), "pc": "0x80048790",
                    "new": "0x13F7", "frame": 10, "seq": 1}]
    constructor += [{"s0": hex(address), "pc": hex(pc), "new": "0", "frame": 10,
                     "seq": axis+2}
                    for axis,pc in enumerate((0x800488EC,0x800488F0,0x800488F4))]
    motion = [{"s0": hex(address), "pc": hex(pc), "old": "0",
               "addr": hex(address+0x220+axis*4),
               "new": hex(value), "frame": 11, "seq": axis+5}
              for axis,(pc,value) in enumerate(zip(family.shot.MOTION_PCS, (0,0,65536)))]
    return sample, Collector({"constructor": constructor, "motion": motion})


class ShotLifecycleTests(unittest.TestCase):
    def test_complete_lifetime(self):
        sample, collector = fixture()
        result = family.trace_lifecycle([sample], collector)[0]
        self.assertEqual(result["birth_frame"], 10)
        self.assertEqual(result["motion_steps"], 1)
        self.assertEqual(result["first_motion"]["direction"], [0,0,1])

    def test_recycled_address_requires_each_constructor(self):
        sample, collector = fixture()
        with self.assertRaisesRegex(RuntimeError, "construction count"):
            family.trace_lifecycle([sample,sample], collector)

    def test_recycled_address_split_by_write_sequence(self):
        sample, collector = fixture()
        for key in ("constructor","motion"):
            collector.rows[key] += [dict(row,seq=row["seq"]+7,frame=row["frame"]+2)
                                    for row in collector.rows[key]]
        rows = family.trace_lifecycle([sample,sample],collector)
        self.assertEqual([row["motion_steps"] for row in rows],[1,1])
        self.assertEqual(rows[0]["next_birth_sequence"], rows[1]["birth_sequence"])

    def test_multiple_constructor_lifetimes_rejected(self):
        sample, collector = fixture()
        collector.rows["constructor"].append(collector.rows["constructor"][0])
        with self.assertRaisesRegex(RuntimeError, "ambiguous"):
            family.trace_lifecycle([sample], collector)

    def test_truncated_xyz_rejected(self):
        sample, collector = fixture()
        collector.rows["motion"].pop()
        with self.assertRaises(RuntimeError):
            family.trace_lifecycle([sample], collector)

    def test_later_truncated_xyz_rejected(self):
        sample, collector = fixture()
        collector.rows["motion"].append(dict(collector.rows["motion"][0], frame=12))
        with self.assertRaisesRegex(RuntimeError, "incomplete later"):
            family.trace_lifecycle([sample], collector)

    def test_wrong_motion_field_rejected(self):
        sample, collector = fixture()
        collector.rows["motion"][1]["addr"] = hex(sample["shot"]+0x240)
        with self.assertRaisesRegex(RuntimeError, "another field"):
            family.trace_lifecycle([sample], collector)

    def test_duplicate_history_axis_rejected(self):
        sample, collector = fixture()
        collector.rows["constructor"][2] = collector.rows["constructor"][1]
        with self.assertRaisesRegex(RuntimeError, "position history"):
            family.trace_lifecycle([sample], collector)

    def test_final_raw_hash_is_not_self_referential(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            sealed = family.seal_receipt(path, {"complete": True,
                                               "raw_receipt_sha256": "old"})
            self.assertEqual(sealed["raw_receipt_sha256"],family.native.digest(path))
            self.assertNotIn("raw_receipt_sha256",path.read_text(encoding="utf-8"))

    def test_same_basis_angles_can_have_spread(self):
        lifetimes = [{"basis_angles": [0,0,0], "first_motion": {
            "direction": [i*.01, 0, (1-(i*.01)**2)**.5]}} for i in range(6)]
        result = family.spread_summary(lifetimes,4)
        self.assertEqual(result["basis_angle_variants"], 1)
        self.assertEqual(result["motion_direction_variants"], 6)
        self.assertGreater(result["maximum_pair_angle_degrees"], 2)

    def test_six_identical_trajectories_not_spread(self):
        rows = [{"basis_angles": [i,0,0], "first_motion": {
            "direction": [0,0,1]}} for i in range(6)]
        with self.assertRaisesRegex(RuntimeError, "spread"):
            family.spread_summary(rows,4)


if __name__ == "__main__":
    unittest.main()
