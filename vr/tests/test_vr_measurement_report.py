import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import analyze_vr_measurement as measurement


def trace(count=20, interval_ms=16.666, guest_step=1, pair_us=8000,
          hud_us=2000, target_period_us=0, fresh=None, delta_us=0):
    rows = []
    for index in range(count):
        flags = 1
        row = {
            'seq': index + 1,
            'open_ms': round(index * interval_ms, 3),
            'guest_frame': 100 + index * guest_step,
            'guest_cycle': 0,
            'pair_id': index + 1,
            'pair_age_ms': 0,
            'source': 1,
            'eye_failed': -1,
            'shed': 0,
            'flags': flags,
            'xr_display_delta_us': delta_us,
            'xr_submit_fresh': 1 if fresh is None else int(fresh[index]),
            'stages_us': {'pair_total': pair_us, 'hud_capture': hud_us},
        }
        rows.append(row)
    return {'enabled': 1, 'capacity': 2048, 'count': count, 'dropped': 0,
            'missing': 0, 'runtime': 'test-runtime',
            'target_period_us': target_period_us, 'records': rows}


class MeasurementReportTest(unittest.TestCase):
    def test_healthy_desktop_control_is_not_a_headset_pass(self):
        report = measurement.analyze_trace(trace(), [], 60, 59.83)
        self.assertEqual(report['verdict'], 'within_contract')
        self.assertFalse(report['headset_acceptance'])
        self.assertFalse(report['scope']['xr_submission_present'])
        self.assertAlmostEqual(report['rates']['native_vblank_hz_from_trace'], 60.0, 2)
        self.assertTrue(any('desktop control' in item for item in report['findings']))

    def test_slow_native_vblanks_classify_simulation_slowdown(self):
        report = measurement.analyze_trace(
            trace(interval_ms=33.333), [], 60, 59.83)
        self.assertEqual(report['verdict'], 'simulation_slowdown')
        self.assertAlmostEqual(report['rates']['native_vblank_hz_from_trace'], 30.0, 2)

    def test_expensive_pair_classifies_presentation_overload(self):
        report = measurement.analyze_trace(trace(pair_us=20000), [], 60, 59.83)
        self.assertEqual(report['verdict'], 'presentation_overload')
        self.assertGreater(report['pair_plus_hud_ms']['p95'],
                           report['scope']['display_budget_ms'])

    def test_slow_simulation_and_heavy_presentation_are_both_reported(self):
        report = measurement.analyze_trace(
            trace(interval_ms=33.333, pair_us=20000), [], 60, 59.83)
        self.assertEqual(report['verdict'], 'both_simulation_and_presentation')

    def test_missed_periods_and_repeats_are_counted_from_xr_rows(self):
        fresh = [1, 0] * 10
        data = trace(count=20, target_period_us=16666, fresh=fresh, delta_us=33332)
        for index, row in enumerate(data['records']):
            if not fresh[index]:
                row['flags'] |= measurement.TRACE_FLAG['xr_repeat']
        report = measurement.analyze_trace(data, [], 60, 59.83)
        self.assertTrue(report['scope']['xr_submission_present'])
        self.assertEqual(report['rates']['repeated_submissions'], 10)
        self.assertAlmostEqual(report['rates']['missed_periods_per_frame'], 1.0, 3)
        self.assertEqual(report['verdict'], 'presentation_overload')

    def test_runtime_display_period_sets_the_target_rate(self):
        report = measurement.analyze_trace(
            trace(count=20, target_period_us=22222), [], 60, 59.83)
        self.assertAlmostEqual(report['rates']['target_hz'], 45.0, 2)
        self.assertAlmostEqual(report['scope']['display_budget_ms'], 22.222, 3)
        self.assertEqual(report['verdict'], 'within_contract')

    def test_hud_absence_is_reported_not_assumed(self):
        report = measurement.analyze_trace(trace(hud_us=0), [], 60, 59.83)
        self.assertFalse(report['pair_plus_hud_ms']['hud_capture_included'])
        self.assertTrue(any('HUD capture never ran' in item
                            for item in report['findings']))

    def test_invalid_evidence_is_refused(self):
        for data in ({}, {'records': []}, trace() | {'dropped': 4}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                measurement.analyze_trace(data, [], 60, 59.83)
        stalled = trace()
        for row in stalled['records']:
            row['open_ms'] = 0
        with self.assertRaises(ValueError):
            measurement.analyze_trace(stalled, [], 60, 59.83)

    def test_runtime_cadence_lines_are_parsed_without_claiming_exclusive_time(self):
        text = '\n'.join([
            'noise',
            'psxrecomp: runtime cadence: guest=59.90 Hz, spu=44.1 Hz, '
            'work guest=12.5 pacer=3.2 autocapture=0.0 provider_poll=0.0 ms/s, x',
            'psxrecomp: runtime cadence: guest=59.70 Hz, spu=44.1 Hz, '
            'work guest=12.9 pacer=3.0 autocapture=0.0 provider_poll=0.0 ms/s, x',
        ])
        samples = measurement.parse_runtime_cadence(text)
        self.assertEqual(len(samples), 2)
        self.assertAlmostEqual(samples[1]['pacer_ms_per_s'], 3.0)
        report = measurement.analyze_trace(trace(), samples, 60, 59.83)
        self.assertAlmostEqual(report['runtime_cadence']['guest_hz_mean'], 59.8, 2)
        self.assertTrue(report['runtime_cadence']
                        ['work_guest_is_inter_frame_interval_not_exclusive'])

    def test_text_summary_keeps_the_limitation(self):
        report = measurement.analyze_trace(trace(), [], 60, 59.83)
        text = measurement.render_text(report)
        self.assertIn('not a physical headset acceptance', text)
        self.assertIn(report['verdict'], text)

    def test_cli_writes_report_and_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'frame-trace.json'
            source.write_text(json.dumps(trace()))
            stdout = root / 'stdout.log'
            stdout.write_text('psxrecomp: runtime cadence: guest=59.9 Hz, '
                              'work guest=11.0 pacer=4.0 autocapture=0.0 '
                              'provider_poll=0.0 ms/s, x\n')
            out, text = root / 'report.json', root / 'report.txt'
            measurement.main([str(source), '--stdout', str(stdout),
                              '--out', str(out), '--text', str(text)])
            report = json.loads(out.read_text())
            self.assertEqual(report['runtime_cadence']['samples'], 1)
            self.assertTrue(text.is_file())


if __name__ == '__main__':
    unittest.main()
