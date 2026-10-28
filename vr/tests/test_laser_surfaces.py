import math
from pathlib import Path
import struct
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from probe_laser_surfaces import decode_strip,nearest
from weapon_defaults import calibrations


class LaserSurfaceTests(unittest.TestCase):
    def test_native_sp_mp_strip_schemas_and_flags(self):
        for stride in (8,16):
            base=struct.pack('<3H',0x2000,1,2)+bytes(stride-6)
            for flag,expected in ((0,[1,2,3]),(0x8000,[2,1,3])):
                data=base+struct.pack('<I',flag|3)+struct.pack('<I',0x1fff)
                rows,used=decode_strip(data,2,4,stride)
                self.assertEqual(rows,[[0,1,2],expected])
                self.assertEqual(used,len(data))
                with self.assertRaises(ValueError):decode_strip(data[:-4],2,4,stride)
                with self.assertRaisesRegex(ValueError,'index'):decode_strip(data,2,3,stride)

    def test_independent_oracle_uses_surfaces_not_boxes(self):
        triangles=np.asarray([[[-10,-10,110],[10,-10,110],[-10,10,110]],
                              [[-10,-10,210],[10,-10,210],[-10,10,210]]],float)
        ray=np.asarray([0,0,1.])
        for mesh in (triangles,triangles[:,::-1],triangles[::-1]):
            self.assertEqual(nearest(mesh,np.asarray([-5,-5,0.]),ray,1000)['distance'],110)
            self.assertEqual(nearest(mesh,np.asarray([-5,-5,105.]),ray,1000)['distance'],5)
            self.assertIsNone(nearest(mesh,np.asarray([5,5,0.]),ray,1000))
            self.assertIsNone(nearest(mesh,np.asarray([-5,-5,0.]),ray,100))

    def test_pose_solver_uses_current_authored_calibration(self):
        rows=calibrations()
        self.assertEqual(len(rows),13)
        for weapon,row in rows.items():
            self.assertEqual(row['forward'],[0,0,1])
            self.assertEqual(row['up'],[0,-1,0])
            self.assertTrue(all(math.isfinite(x) for x in row['grip_pivot']))
            if weapon in (10,15):
                self.assertLess(row['muzzle'][1],row['grip_pivot'][1]-90)
            else:self.assertEqual(row['model_units_per_metre'],850)


if __name__=='__main__':unittest.main()
