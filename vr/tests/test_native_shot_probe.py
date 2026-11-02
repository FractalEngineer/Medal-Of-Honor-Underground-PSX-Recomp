import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import probe_native_shot as probe


class NativeShotProbeTests(unittest.TestCase):
    def test_trace_loss_never_becomes_a_pass(self):
        collector=probe.TraceCollector()
        for trace in ({"total":100,"available":50,"emitted":0,"entries":[]},
                      {"total":100,"available":100,"emitted":2048,"entries":[]}):
            with patch.object(probe.native,"command",return_value=trace):
                with self.assertRaises(RuntimeError):collector.collect()

    def test_first_motion_requires_xyz_of_the_same_shot_and_frame(self):
        rows=[{"s0":"0x801103C0","pc":hex(pc),"frame":1,"old":"0x00000000","new":hex(v)}
              for pc,v in zip(probe.MOTION_PCS,(0,0,65536))]
        self.assertEqual(probe.first_motion(rows,0x801103C0)["direction"],[0,0,1])
        with self.assertRaises(RuntimeError):probe.first_motion(rows,0x80128430)
        rows[2]["frame"]=2
        with self.assertRaises(RuntimeError):probe.first_motion(rows,0x801103C0)


if __name__ == "__main__":unittest.main()
