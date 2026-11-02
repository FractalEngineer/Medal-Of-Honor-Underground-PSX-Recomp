import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'vr/tools'))
import build_packet_kernel as packet
import summarize_preflight as summary
import test_preflight as oracle


class CallerToolsTest(unittest.TestCase):
    def test_capture_rejects_truncated_or_foreign_contract(self):
        for data in (b'', struct.pack('<4I', 0, summary.RECORD_SIZE, 48, 1),
                     struct.pack('<4I', 0x50464831, summary.RECORD_SIZE, 48, 1)):
            with self.assertRaises(ValueError):
                summary.summarize(data)

    def test_capture_detects_real_result_difference(self):
        data = bytearray(struct.pack('<4I', 0x50464831, summary.RECORD_SIZE, 48, 1))
        data += bytes(summary.RECORD_SIZE)
        self.assertEqual(summary.summarize(data)['failed'], 0)
        data[16+16+summary.RESULT_SIZE+8] = 1
        self.assertEqual(summary.summarize(data)['mismatch_records'], [0])

    def test_oracle_uses_original_body_without_instrumentation_edits(self):
        text = (ROOT/'generated/SLUS_012.70_full_00.c').read_text()
        result = oracle.oracle_source(text)
        self.assertIn('void oracle_preflight(CPUState* cpu)', result)
        self.assertIn('PGXP_COP2(0x48880000u', result)
        self.assertIn('psx_cyc_step(cpu', result)
        with self.assertRaises(ValueError):
            oracle.oracle_source('void missing() {}')

    def test_packet_derivation_preserves_every_original_operation(self):
        text = (ROOT/'generated/SLUS_012.70_full_00.c').read_text()
        start = text.index('\nvoid func_80010CF0(CPUState* cpu)\n{')
        end = text.index('\nvoid ', start+1)
        original = text[start:end]
        result = packet.kernel(text)
        self.assertTrue(result.endswith(original.replace('void func_80010CF0(', 'void mohu_packet(', 1)))
        self.assertIn('#undef PSX_ENABLE_BLOCK_CYCLES', result)
        self.assertIn('#define gte_execute psx_hle_gte_execute', result)


if __name__ == '__main__':
    unittest.main()
