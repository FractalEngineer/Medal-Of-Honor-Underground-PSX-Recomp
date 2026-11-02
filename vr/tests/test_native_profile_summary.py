import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import summarize_native_profile as profile


def fixture():
    r=dict(start={'pairs':10},end={'pairs':20})
    for key,us,calls in (('native_profile_before',1000,10),('native_profile_after',3000,50)):
        r[key]=[dict(reply=json.dumps(dict(exclusive_cps_segments=True,rows=[
            dict(scope=s,address='0x80010CF0',us=us,calls=calls)]))) for s in range(3)]
    return r


class NativeProfileSummaryTest(unittest.TestCase):
    def test_excludes_canonical_from_stereo_and_sums_two_eyes(self):
        result=profile.segment_summary(fixture())
        self.assertAlmostEqual(result['stereo_totals'][0]['ms_per_pair'],.4)
        self.assertEqual([r['calls'] for r in result['rows']],[40]*3)

    def test_refuses_changed_scopes_and_regressing_counters(self):
        for field,value in (('scope',2),('address','different'),('us',0),('calls',0)):
            r=fixture()
            row=json.loads(r['native_profile_after'][0]['reply'])
            row['rows'][0][field]=value
            r['native_profile_after'][0]['reply']=json.dumps(row)
            with self.subTest(field=field),self.assertRaises(ValueError):
                profile.segment_summary(r)

    def test_refuses_missing_scope_or_no_fresh_pair(self):
        r=fixture()
        r['end']['pairs']=10
        with self.assertRaises(ValueError):profile.segment_summary(r)
        r=fixture()
        r['native_profile_after'].pop()
        with self.assertRaises(ValueError):profile.segment_summary(r)

    def test_external_module_is_named_without_calling_it_wait_time(self):
        r=dict(host_profile=dict(image_base='0x100000',top=[['0x1010',7],['0',2],['0x10000',1]],
            samples=10,unbinned=0),host_modules=[dict(base=0x101000,size=0x1000,path='system-driver.dll')])
        result=profile.resolve_samples(r,None)
        names={row['name']:row['samples'] for row in result['functions']}
        self.assertEqual(names,{'system-driver.dll':7,'(non-image pc)':2,'(unresolved module)':1})
        self.assertEqual(result['binned_samples'],10)

    def test_preserved_executable_requires_exact_receipt_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            exe=Path(directory)/'preserved.exe'
            exe.write_bytes(b'test symbol image')
            r=dict(binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                host_profile=dict(image_base='0x100000',top=[['0x1001',1]],samples=1,unbinned=0),
                host_modules=[dict(path=str(profile.ROOT/'build-release/original.exe'),base=0x101000,size=16)])
            with patch.object(profile.host_profile,'symbols',return_value=[(0,'func_80011424')]):
                result=profile.resolve_samples(r,'nm',exe)
                self.assertEqual(result['functions'][0]['name'],'original.exe:func_80011424')
                exe.write_bytes(b'changed')
                with self.assertRaises(ValueError):profile.resolve_samples(r,'nm',exe)


if __name__=='__main__':unittest.main()
