"""Require an unbroken native-object origin history before naming its writer."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import probe_projectile_origins as origins


def fixture():
    address=0x80110000
    sample={"shot":address,"type":0x13F3,"position":[100,200,300]}
    def store(pc,offset,old,new,seq):
        return {"pc":hex(pc),"addr":hex(address+offset),"old":hex(old),
                "new":hex(new),"s0":hex(address),"frame":1,"seq":seq,"w":4}
    rows=[store(0x80048790,8,0,0x13F3,1)]
    final=[sample["position"][i]+value*65536 for i,value in enumerate((9,0,332))]
    rows += [store(0x80048100,0x220+i*4,0,value,i+2)
             for i,value in enumerate(sample["position"])]
    rows += [store(0x80049000+i*4,0x220+i*4,sample["position"][i],value,i+5)
             for i,value in enumerate(final)]
    rows += [store(pc,0x220+i*4,final[i],final[i]+65536,i+8)
             for i,pc in enumerate(origins.shot.MOTION_PCS)]
    return sample,rows


class ProjectileOriginTests(unittest.TestCase):
    def test_last_actual_writers_establish_motion_origin(self):
        sample,rows=fixture()
        result=origins.origin_writers(sample,rows)
        self.assertEqual(result["basis_to_motion_shift"],[9,0,332])
        self.assertEqual([int(row["pc"],0) for row in result["last_origin_writers"]],
                         [0x80049000,0x80049004,0x80049008])

    def test_birth_anchor_required(self):
        sample,rows=fixture()
        with self.assertRaisesRegex(RuntimeError,"birth anchor"):
            origins.origin_writers(sample,rows[1:])

    def test_missing_intervening_store_is_not_named_as_writer(self):
        sample,rows=fixture()
        rows.pop(4)
        with self.assertRaisesRegex(RuntimeError,"does not establish"):
            origins.origin_writers(sample,rows)

    def test_reused_object_is_ambiguous_in_single_origin_control(self):
        sample,rows=fixture()
        rows.append(dict(rows[0],seq=20))
        with self.assertRaisesRegex(RuntimeError,"birth anchor"):
            origins.origin_writers(sample,rows)


if __name__=="__main__":unittest.main()
