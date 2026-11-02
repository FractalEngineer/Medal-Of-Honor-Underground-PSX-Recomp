import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import probe_weapon_death as death


def fixture():
    players = [{"actor": "0x80146cc0", "input": "0x801470c0",
                "weapon_slot": 0, "weapon_id": 0, "clip": 7, "reserve": 21,
                "health_raw": 2097152, "position": [0, 0, 0]},
               {"actor": "0x80144100"}]
    before = {"players": players, "marker": {
        "valid": 1, "sequence": 10, "expected_generation": 1,
        "shot_cycle": 100}}
    dead = copy.deepcopy(before)
    dead["players"][0]["health_raw"] = 0
    dead["marker"].update(valid=0, shot_cycle=200)
    respawn = copy.deepcopy(before)
    respawn["players"][0]["position"] = [1000, 0, 1000]
    respawn["marker"].update(sequence=11, shot_cycle=300)
    return {
        "name": death.CASE, "before": before, "dead": dead,
        "respawn": respawn,
        "attack_shots": [{"owner": 0x80144100, "weapon": 1,
                          "type": 0x13F7, "code_valid": 1,
                          "family_eligible": 0, "aimed": 0,
                          "aimed_position": [0, 0, 0], "shot": 0x8012EB00}],
        "lethal_damage": [{"addr": "0x00146dc8", "pc": "0x8004eb80",
                           "old": "0x00200000", "new": "0x00000000",
                           "s1": "0x8012eb00", "a2": "0x8012eb00",
                           "seq": 1, "frame": 100}],
        "respawn_trigger_shots": [],
        "recovered": {
            "shot_count": 1, "shot_types": [0x13F6],
            "ammo_delta": {"clip": 1, "reserve": 0},
            "converted": [{"native_fallback": False,
                           "origin_error_world_units": 0,
                           "first_motion_origin_error_world_units": 0,
                           "axis_cosine": 1.0,
                           "marker": {"cycle": 350},
                           "marker_generation": 1}],
        },
    }


class DeathTransitionTests(unittest.TestCase):
    def rejects(self, row, text):
        problems = death.validate_transition(row, "tracked")
        self.assertTrue(any(text in value for value in problems), problems)

    def test_native_death_respawn_and_fresh_shot(self):
        self.assertEqual(death.validate_transition(fixture(), "tracked"), [])

    def test_final_health_alone_is_not_linked_death(self):
        row = fixture()
        row["lethal_damage"] = []
        self.rejects(row, "exact linked")

    def test_other_victim_and_other_shot_are_not_accepted(self):
        for field, value in (("addr", "0x00144208"),
                             ("s1", "0x8012eb10")):
            row = fixture()
            row["lethal_damage"][0][field] = value
            self.rejects(row, "exact linked")

    def test_p2_candidate_write_is_rejected(self):
        row = fixture()
        row["attack_shots"][0]["aimed"] = 1
        self.rejects(row, "overridden")

    def test_negative_lethal_health_requires_exact_native_clamp(self):
        row = fixture()
        hit = row["lethal_damage"][0]
        hit.update(old="0x0000ccd2", new="0xfffe666c")
        self.rejects(row, "exact linked")
        clamp = dict(hit, pc="0x8004ec44", old=hit["new"],
                     new="0x00000000", seq=2)
        row["lethal_damage"].append(clamp)
        self.assertEqual(death.validate_transition(row, "tracked"), [])
        clamp["frame"] = 101
        self.rejects(row, "exact linked")

    def test_respawn_trigger_must_not_construct_a_shot(self):
        row = fixture()
        row["respawn_trigger_shots"] = [row["attack_shots"][0]]
        self.rejects(row, "extra P1 shot")

    def test_health_restore_without_relocation_is_not_respawn(self):
        row = fixture()
        row["respawn"]["players"][0]["position"] = [0, 0, 0]
        self.rejects(row, "relocate")

    def test_save_load_cannot_substitute_for_respawn(self):
        row = fixture()
        row["respawn"]["marker"]["expected_generation"] = 2
        self.rejects(row, "save load")

    def test_dead_marker_and_old_recovered_marker_are_rejected(self):
        row = fixture()
        row["dead"]["marker"]["valid"] = 1
        self.rejects(row, "validity")
        row = fixture()
        row["recovered"]["converted"][0]["marker"]["cycle"] = 100
        self.rejects(row, "fresh converted")

    def test_no_extra_ammo_or_native_fallback_on_recovery(self):
        row = fixture()
        row["respawn"]["players"][0]["clip"] = 6
        self.rejects(row, "ammunition")
        row = fixture()
        row["recovered"]["converted"][0]["native_fallback"] = True
        self.rejects(row, "fresh converted")

    def test_nonfinite_conversion_cannot_pass(self):
        row = fixture()
        row["recovered"]["converted"][0]["axis_cosine"] = float("nan")
        self.rejects(row, "fresh converted")


if __name__ == "__main__":
    unittest.main()
