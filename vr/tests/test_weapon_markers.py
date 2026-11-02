from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

from test_shared_geometry_policy import compiler

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"vr/tools"))
from probe_weapon_animations import marker_groups


class WeaponMarkerTests(unittest.TestCase):
    def test_marker_contract_and_measured_groups(self):
        with tempfile.TemporaryDirectory() as temporary:
            exe=Path(temporary)/("markers.exe" if os.name=="nt" else "markers")
            subprocess.run([compiler(),"-std=c11","-Wall","-Wextra","-Werror",
                f"-I{ROOT/'vr/underground'}",f"-I{ROOT/'psxrecomp/runtime/include'}",
                str(ROOT/"vr/tests/test_weapon_markers.c"),str(ROOT/"vr/underground/weapon.c"),
                str(ROOT/"psxrecomp/runtime/src/vr_pose_math.c"),"-lm","-o",str(exe)],check=True)
            output=subprocess.check_output([str(exe)],text=True)
        expected=marker_groups();seen=set()
        for line in output.splitlines():
            if not line.startswith("GROUP|"):continue
            _,weapon,counts,refs=line.split("|")
            weapon=int(weapon);seen.add(weapon)
            grip=expected[weapon]["grip"];tip=expected[weapon]["muzzle"]
            base=[[11,i] for i in range(11,18)] if weapon==0 else []
            self.assertEqual([int(v) for v in counts.split(",")],[len(grip),len(tip),len(base)])
            self.assertEqual([[int(v) for v in pair.split(":")] for pair in refs.split(",")],grip+tip+base)
        self.assertEqual(seen,set(expected))
        self.assertIn("PASS: canonical marker means",output)


if __name__=="__main__":unittest.main()
