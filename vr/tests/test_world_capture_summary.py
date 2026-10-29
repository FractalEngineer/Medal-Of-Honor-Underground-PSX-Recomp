import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import summarize_world_capture as capture

HEADER = """MOHU-SP-WORLD-CAPTURE 1
draws=1 faces=1 draw_limit=1 face_limit=1
draw=0 ra=0x8009A51C begin=0x80100000 limit=0x80101000 a2=0x800A58A0 a3=0x800A82E0 sp=0x801FFE80 gp=0x8003739C level=0x800A58A0 sub=0x800A54A0 root=0x8010BA48 count=1444 table=0x8010FE4C
draw=0 scratch_len=4 scratch_hash=0x00000000 scratch=00000000
draw=0 range_len=4 range_hash=0x00000000 range=00000000
draw=0 record_base=0x80110000 record_entries=0 records=
face=0 draw=0 ra=0x80011008 s7=0x80120008 face=0x80120000 index=5 table_base=0x80110000 record_base=0x8011003C ok=1 flags=0x00D0812E gpr27=0x8015BB70 d8=0x0000000B dc=0x00000000
face=0 gpr=0000000000000000000000000000000000000000000000000000000000000000
face=0 face_bytes=00000000000005000000000000000000 record=11223344556677889900aabb table=
"""


class CaptureSummaryTest(unittest.TestCase):
    def write(self, text):
        handle = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False,
                                             encoding='utf-8')
        handle.write(text)
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return Path(handle.name)

    def test_summary_parses_proven_fields(self):
        report = capture.summarize(self.write(HEADER))
        self.assertEqual(report['faces'], 1)
        self.assertEqual(report['distinct_records'], 1)
        record = report['records'][0]
        self.assertEqual(record['indices'], [5])
        self.assertEqual(record['half_words'],
                         [0x2211, 0x4433, 0x6655, 0x8877, 0x0099, 0xBBAA])
        self.assertEqual([entry['field'] for entry in
                          report['face_record']['layout']],
                         ['half0', 'half1', 'half2', 'half3', 'half4',
                          'half5'])
        self.assertIsNone(report['material_fields']['texture_page'])
        self.assertIsNone(report['material_fields']['clut'])
        self.assertEqual(report['draws'][0]['root'], '0x8010BA48')
        self.assertEqual(report['draws'][0]['vertex_count'], 1444)

    def test_packet_evidence_is_checked(self):
        packet = bytes(range(0x60))
        text = HEADER + (
            f'face=0 packet_captured=1 packet_hash=0x'
            f'{capture.fnv1a(packet):08X} packet={packet.hex()}\n')
        report = capture.summarize(self.write(text))
        evidence = report['face_evidence'][0]
        self.assertTrue(evidence['packet_captured'])
        self.assertEqual(len(evidence['packet_words']), 24)
        self.assertEqual(evidence['packet_words'][0], '0x03020100')

        bad = text.replace(f'{capture.fnv1a(packet):08X}', '00000000')
        with self.assertRaises(ValueError):
            capture.summarize(self.write(bad))

    def test_native_compare_is_parsed(self):
        text = HEADER + (
            'draw=0 native_compare=1 native=12 overflow=0 unique=10 '
            'matched=9 missing=1 decoded_only=30 dup=2 multi=4 '
            'multi_count=11 triangles=40 status=0 first_missing=0x80123456 '
            'first_dup=0x80123400 first_multi=0x80120000 '
            'missing_in_range=1 missing_addrs=0x80123456,0x80123490\n')
        report = capture.summarize(self.write(text))
        compare = report['draws'][0]['native_compare']
        self.assertEqual(compare['native'], 12)
        self.assertEqual(compare['matched'], 9)
        self.assertEqual(compare['missing'], 1)
        self.assertEqual(compare['first_missing'], '0x80123456')
        self.assertEqual(compare['first_duplicate_call'], '0x80123400')
        self.assertEqual(compare['multi_source'], 4)
        self.assertEqual(compare['status'], 0)
        self.assertEqual(compare['missing_in_range'], 1)
        self.assertEqual(compare['missing_addrs'],
                         ['0x80123456', '0x80123490'])

    def test_entry_attribution_is_parsed(self):
        text = HEADER + (
            'entry=2 ra=0x8009A51C pc=0x00000000 level=0x800A5A28 '
            'sub=0x800A56C8 root=0x800E8D28 table=0x800ECE1C count=1471 '
            'faces=16 selected=1 overflow=0 compare=0 status=0 matched=0 '
            'missing=0 decoded_only=0 triangles=0 first_missing=0x00000000 '
            'visible=1 visible_overflow=0 '
            'visible_entries=800E9098:16:800EA91C\n')
        report = capture.summarize(self.write(text))
        entry = report['entries'][0]
        self.assertEqual(entry['index'], 2)
        self.assertEqual(entry['ra'], '0x8009A51C')
        self.assertTrue(entry['selected'])
        self.assertEqual(entry['faces'], 16)
        self.assertEqual(entry['visible_count'], 1)
        self.assertEqual(entry['visible'],
                         [{'entry': '0x800E9098', 'faces': 16,
                           'list': '0x800EA91C'}])

    def test_wrong_record_base_is_refused(self):
        text = HEADER.replace('record_base=0x8011003C',
                              'record_base=0x80110040')
        with self.assertRaises(ValueError):
            capture.summarize(self.write(text))

    def test_wrong_index_is_refused(self):
        text = HEADER.replace('index=5 table_base', 'index=6 table_base')
        with self.assertRaises(ValueError):
            capture.summarize(self.write(text))

    def test_missing_header_is_refused(self):
        with self.assertRaises(ValueError):
            capture.summarize(self.write('draws=1 faces=1\n'))


if __name__ == '__main__':
    unittest.main()
