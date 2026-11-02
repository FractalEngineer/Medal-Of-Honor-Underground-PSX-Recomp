import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import check_p38_mesh as mesh


def triangle(vertices):
    result=bytearray(28)
    for index,(node,vertex) in enumerate(vertices):
        result[22+index*2:24+index*2]=bytes((vertex,node))
    return result


class P38MeshTests(unittest.TestCase):
    def test_barrel_survives_arm_filter(self):
        self.assertTrue(all(mesh.gun_vertex(11,v) for v in range(6,33)))
        self.assertFalse(mesh.gun_vertex(11,5))
        self.assertFalse(mesh.gun_vertex(11,33))
        self.assertFalse(mesh.gun_vertex(9,0))

    def test_native_strip_extension_and_new_triangle(self):
        first=[(11,6),(11,7),(11,8)]
        data=triangle(first)+struct.pack("<HHI",(9<<8)|11,0,0)
        data+=struct.pack("<I",0x1FFF)+triangle([(13,0),(13,1),(13,2)])+struct.pack("<I",0x1FFF)
        triangles,consumed=mesh.decode_triangles(data,3,mesh.COUNTS)
        self.assertEqual(triangles,[tuple(first),((11,7),(11,8),(11,9)),((13,0),(13,1),(13,2))])
        self.assertEqual(consumed,len(data))

    def test_native_strip_reuses_first_edge_when_flagged(self):
        data=triangle([(11,6),(11,7),(11,8)])+struct.pack("<HHI",(9<<8)|0x80|11,0,0)+struct.pack("<I",0x1FFF)
        triangles,_=mesh.decode_triangles(data,2,mesh.COUNTS)
        self.assertEqual(triangles[-1],((11,8),(11,7),(11,9)))

    def test_truncation_and_bad_vertex_are_refused(self):
        for data,count in [(b"",1),(triangle([(13,0),(13,1),(13,69)]),1),
                           (triangle([(13,0),(13,1),(13,2)]),2)]:
            with self.assertRaises(ValueError):mesh.decode_triangles(data,count,mesh.COUNTS)


if __name__ == "__main__":unittest.main()
