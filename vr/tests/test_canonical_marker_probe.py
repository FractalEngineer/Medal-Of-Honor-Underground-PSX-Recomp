from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import probe_canonical_markers as probe


def snapshot():
    return {"valid":1,"id":0,"generation":1,"expected_generation":1,
            "shot_cycle":10000,"cycle":9999,"sequence":7,"vertex_count":30,
            "grip":[1,2,3],"tip":[1,2,3],"axis_base":[1,2,3]}


class CanonicalMarkerProbeTests(unittest.TestCase):
    def test_missing_marker_cannot_pass(self):
        with patch.object(probe,"marker",return_value={"valid":0}):
            with self.assertRaisesRegex(RuntimeError,"validity"):
                probe.verify_sample(0,0)

    def test_stale_marker_cannot_pass_as_fresh(self):
        sample=snapshot();sample["cycle"]=sample["shot_cycle"]-probe.MAX_AGE-1
        with patch.object(probe,"marker",return_value=sample):
            with self.assertRaisesRegex(RuntimeError,"freshness"):
                probe.verify_sample(0,0)

    def test_mean_is_checked_against_raw_selected_vertices(self):
        sample=snapshot();sample["tip"]=[2,2,3]
        def command(args):
            if args.startswith("shot="):return sample
            start=int(args.split(":")[1])
            return {"sequence":7,"start":start,"total":30,
                    "vertices":[[1,2,3]]*min(4,30-start)}
        with patch.object(probe,"marker",side_effect=command):
            with self.assertRaisesRegex(RuntimeError,"Marker mean"):
                probe.verify_sample(0,0)

    def test_page_sequence_change_cannot_pass(self):
        sample=snapshot()
        with patch.object(probe,"marker",side_effect=[sample,
                {"sequence":8,"start":0,"total":30,"vertices":[]} ]):
            with self.assertRaisesRegex(RuntimeError,"changed across pages"):
                probe.verify_sample(0,0)


if __name__=="__main__":unittest.main()
