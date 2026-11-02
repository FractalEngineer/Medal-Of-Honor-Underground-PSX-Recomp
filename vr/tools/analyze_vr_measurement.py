"""M0 measurement contract: classify a VR run as simulation or presentation bound.

Consumes the existing production frame trace and the opt-in runtime cadence
lines. It never launches a game and never certifies a physical headset pass.

Stage times are the trace's own fields. Nested stages are reported separately
and are never summed with their parents; `pair_total` remains the authoritative
pair cost. `guest_sim` is the interval between traced frames, not exclusive
simulation time, and is labelled as such.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys

TRACE_FLAG = {
    'published': 1 << 0, 'stale': 1 << 1, 'shed': 1 << 2, 'failed': 1 << 3,
    'xr_empty': 1 << 4, 'scene': 1 << 5, 'io': 1 << 6,
    'no_telemetry': 1 << 7, 'baseline_reused': 1 << 8, 'xr_repeat': 1 << 9,
}
NOMINAL_NTSC_VBLANK_HZ = 5983 / 100.0
TOLERANCE = 0.99


def percentile(values, q):
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower, upper = math.floor(index), math.ceil(index)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def stage_summary_ms(values_us):
    if not values_us:
        return {'count': 0}
    return {
        'count': len(values_us),
        'mean': round(statistics.mean(values_us) / 1000, 6),
        'p50': round(percentile(values_us, .50) / 1000, 6),
        'p95': round(percentile(values_us, .95) / 1000, 6),
        'p99': round(percentile(values_us, .99) / 1000, 6),
        'max': round(max(values_us) / 1000, 6),
    }


def _search(pattern, text, cast):
    match = re.search(pattern, text)
    return cast(match.group(1)) if match else None


def parse_runtime_cadence(text):
    """Extract the runtime's per-interval cadence lines, one sample each."""
    samples = []
    for line in text.splitlines():
        if 'runtime cadence:' not in line:
            continue
        guest = _search(r'guest=([\d.]+) Hz', line, float)
        work = re.search(r'work guest=([\d.]+) pacer=([\d.]+)', line)
        canonical = _search(r'\bcanonical=([\d.]+)', line, float)
        sim = _search(r'\bsim=([\d.]+)', line, float)
        # `sim` is the guest-quantum interval, not exclusive CPU; pacer and
        # canonical present are measured in the present body after it.
        pairs = re.search(r'VR pairs=(\d+) shed=(\d+) empty=(\d+) failures=(\d+)'
                          r' avg_pair_ms=([\d.]+) last_pair_ms=([\d.]+)', line)
        sample = {
            'guest_hz': guest,
            'work_guest_ms_per_s': float(work.group(1)) if work else None,
            'pacer_ms_per_s': float(work.group(2)) if work else None,
            'canonical_ms_per_s': canonical,
            'sim_interval_ms_per_s': sim,
        }
        if pairs:
            sample.update(
                vr_pairs=int(pairs.group(1)), vr_shed=int(pairs.group(2)),
                vr_empty=int(pairs.group(3)), vr_failures=int(pairs.group(4)),
                avg_pair_ms=float(pairs.group(5)),
                last_pair_ms=float(pairs.group(6)))
        if any(v is not None for v in sample.values()):
            samples.append(sample)
    return samples


def _require_trace(data, path):
    if not isinstance(data, dict) or not data.get('records'):
        raise ValueError(f'No frame-trace records in {path}')
    if data.get('dropped'):
        raise ValueError(
            f'Trace ring overwrote {data["dropped"]} records in {path}; '
            'the measurement window is not reproducible')
    rows = data['records']
    if any('stages_us' not in row for row in rows):
        raise ValueError(f'Trace rows lack stage timings in {path}')
    return rows


def _fresh_and_repeat(rows, xr_active):
    published = [r for r in rows if r['flags'] & TRACE_FLAG['published']
                 and r['pair_id'] > 0]
    if xr_active:
        fresh = [r for r in published if r.get('xr_submit_fresh')]
        repeats = [r for r in rows if r['flags'] & TRACE_FLAG['xr_repeat']]
    else:
        fresh, repeats = published, []
    return published, fresh, repeats


def analyze_trace(data, cadence, target_hz, nominal_hz, path='<memory>'):
    rows = _require_trace(data, path)
    first, last = rows[0], rows[-1]
    span_ms = last['open_ms'] - first['open_ms']
    if span_ms <= 0:
        raise ValueError(f'Trace spans no wall time in {path}')

    stages = sorted({key for row in rows for key in row['stages_us']})
    summaries = {key: stage_summary_ms([r['stages_us'][key] for r in rows])
                 for key in stages}

    xr_active = bool(data.get('target_period_us')) or any(
        r['stages_us'].get('xr_wait_frame') or r['stages_us'].get('xr_end_frame')
        or r.get('xr_display_delta_us') for r in rows)
    published, fresh, repeats = _fresh_and_repeat(rows, xr_active)

    flags = Counter()
    for row in rows:
        for name, bit in TRACE_FLAG.items():
            if row['flags'] & bit:
                flags[name] += 1

    vblank_hz = ((last.get('guest_frame', 0) - first.get('guest_frame', 0))
                 * 1000 / span_ms)
    pair_hz = (len(published) - 1) * 1000 / span_ms if len(published) > 1 else 0.0
    fresh_hz = (len(fresh) - 1) * 1000 / span_ms if len(fresh) > 1 else 0.0

    period_us = data.get('target_period_us') or round(1e6 / target_hz)
    budget_ms = period_us / 1000
    effective_target_hz = 1e6 / period_us

    hud_measured = any(r['stages_us'].get('hud_capture') for r in rows)
    gpu_rows = [r for r in rows
                if r.get('gpu_scene_us') or r.get('gpu_present_us')]
    gpu = {
        'timer_samples': len(gpu_rows),
        'measured': bool(gpu_rows),
        'scene_ms_mean': (round(statistics.mean(
            r['gpu_scene_us'] for r in gpu_rows) / 1000, 6) if gpu_rows else None),
        'present_ms_mean': (round(statistics.mean(
            r['gpu_present_us'] for r in gpu_rows) / 1000, 6) if gpu_rows else None),
        'sample_age_frames_max': (max(r.get('gpu_sample_age_frames', 0)
                                      for r in gpu_rows) if gpu_rows else None),
        'retrieved_asynchronously': True,
        'added_to_cpu_stages': False,
    }
    expected_stages = ('snapshot_extract', 'snapshot_publish', 'xr_locate',
                       'host_prep', 'xr_wait_frame')
    absent_stages = [key for key in expected_stages
                     if not any(r['stages_us'].get(key) for r in rows)]
    pair_plus_hud_us = [r['stages_us'].get('pair_total', 0)
                        + r['stages_us'].get('hud_capture', 0) for r in rows]
    pair_plus_hud_p95_ms = percentile(pair_plus_hud_us, .95) / 1000

    missed = 0.0
    for row in rows:
        delta = row.get('xr_display_delta_us') or 0
        if delta > 0:
            missed += max(0.0, delta / period_us - 1.0)
    missed_per_frame = missed / len(rows) if rows else 0.0

    cadence_guest = [s['guest_hz'] for s in cadence if s.get('guest_hz')]
    work = [s['work_guest_ms_per_s'] for s in cadence
            if s.get('work_guest_ms_per_s') is not None]
    pacer = [s['pacer_ms_per_s'] for s in cadence
             if s.get('pacer_ms_per_s') is not None]
    canonical = [s['canonical_ms_per_s'] for s in cadence
                 if s.get('canonical_ms_per_s') is not None]
    sim = [s['sim_interval_ms_per_s'] for s in cadence
           if s.get('sim_interval_ms_per_s') is not None]

    measured_vblank_hz = (statistics.mean(cadence_guest) if cadence_guest
                          else vblank_hz)
    simulation_slow = measured_vblank_hz < nominal_hz * TOLERANCE
    presentation_overload = (
        pair_plus_hud_p95_ms > budget_ms
        or (xr_active and missed_per_frame > 0.01)
        or (xr_active and fresh_hz < effective_target_hz * TOLERANCE))

    if simulation_slow and presentation_overload:
        verdict = 'both_simulation_and_presentation'
    elif simulation_slow:
        verdict = 'simulation_slowdown'
    elif presentation_overload:
        verdict = 'presentation_overload'
    else:
        verdict = 'within_contract'

    findings = []
    if simulation_slow:
        findings.append(
            f'native VBlank progression {measured_vblank_hz:.2f} Hz is below '
            f'{nominal_hz * TOLERANCE:.2f} Hz; simulation is not real-time')
    if pair_plus_hud_p95_ms > budget_ms:
        findings.append(
            f'pair+hud p95 {pair_plus_hud_p95_ms:.3f} ms exceeds the '
            f'{budget_ms:.3f} ms display period')
    if xr_active and missed_per_frame > 0.01:
        findings.append(
            f'{missed_per_frame:.3f} missed display periods per traced frame')
    if xr_active and fresh_hz < effective_target_hz * TOLERANCE:
        findings.append(
            f'fresh-pose pairs {fresh_hz:.2f}/s is below the '
            f'{effective_target_hz:.2f} Hz runtime target')
    if not xr_active:
        findings.append(
            'no XR submission occurred; this is a desktop control and cannot '
            'certify headset cadence')
    if not hud_measured:
        findings.append('HUD capture never ran; its cost is unmeasured here')
    if not gpu_rows:
        findings.append('no asynchronous GPU timer sample; GPU work is '
                        'unmeasured here (not zero)')
    if absent_stages:
        findings.append('stages absent (not zero cost): '
                        + ', '.join(absent_stages))
    if repeats:
        findings.append(f'{len(repeats)} repeated submissions are counted separately')

    return {
        'schema': 1,
        'trace_path': str(path),
        'trace_sha256': (hashlib.sha256(Path(path).read_bytes()).hexdigest()
                         if path != '<memory>' and Path(path).is_file() else None),
        'headset_acceptance': False,
        'physical_headset_measured': False,
        'certification': 'Not a headset acceptance; offline measurement contract only',
        'scope': {
            'runtime': data.get('runtime', ''),
            'target_period_us': data.get('target_period_us', 0),
            'display_budget_ms': round(budget_ms, 6),
            'xr_submission_present': xr_active,
            'records': len(rows),
            'wall_ms': round(span_ms, 3),
            'stages_measured': stages,
            'absent_stages': absent_stages,
        },
        'gpu': gpu,
        'rates': {
            'native_vblank_hz_from_trace': round(vblank_hz, 4),
            'native_vblank_hz_from_cadence': (round(statistics.mean(cadence_guest), 4)
                                              if cadence_guest else None),
            'fresh_pairs_per_second': round(fresh_hz, 4),
            'published_pairs_per_second': round(pair_hz, 4),
            'target_hz': round(effective_target_hz, 4),
            'repeated_submissions': len(repeats),
            'missed_periods_per_frame': round(missed_per_frame, 6),
        },
        'stages_ms': summaries,
        'pair_plus_hud_ms': {
            'p50': round(percentile(pair_plus_hud_us, .50) / 1000, 6),
            'p95': round(pair_plus_hud_p95_ms, 6),
            'p99': round(percentile(pair_plus_hud_us, .99) / 1000, 6),
            'hud_capture_included': hud_measured,
            'excludes_nested_stages': True,
        },
        'counter_flags': dict(flags),
        'runtime_cadence': {
            'samples': len(cadence),
            'guest_hz_mean': (round(statistics.mean(cadence_guest), 4)
                              if cadence_guest else None),
            'work_guest_ms_per_s_mean': (round(statistics.mean(work), 4)
                                         if work else None),
            'pacer_ms_per_s_mean': (round(statistics.mean(pacer), 4)
                                    if pacer else None),
            'canonical_ms_per_s_mean': (round(statistics.mean(canonical), 4)
                                        if canonical else None),
            'sim_interval_ms_per_s_mean': (round(statistics.mean(sim), 4)
                                           if sim else None),
            'sim_is_guest_quantum_interval_not_exclusive_cpu': True,
            'work_guest_is_inter_frame_interval_not_exclusive': True,
        },
        'verdict': verdict,
        'findings': findings,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path, help='frame-trace.json')
    parser.add_argument('--stdout', type=Path,
                        help='captured stdout.log with runtime cadence lines')
    parser.add_argument('--target-hz', type=float, default=60.0,
                        help='Fallback target when the trace has no display period')
    parser.add_argument('--nominal-vblank-hz', type=float,
                        default=NOMINAL_NTSC_VBLANK_HZ)
    parser.add_argument('--out', type=Path, help='Write the JSON report here')
    parser.add_argument('--text', type=Path, help='Write a short text summary here')
    args = parser.parse_args(argv)

    data = json.loads(args.trace.read_text())
    cadence = parse_runtime_cadence(
        args.stdout.read_text(errors='replace')) if args.stdout else []
    report = analyze_trace(data, cadence, args.target_hz,
                           args.nominal_vblank_hz, args.trace)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + '\n')
    if args.text:
        args.text.parent.mkdir(parents=True, exist_ok=True)
        args.text.write_text(render_text(report) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'rates': report['rates'],
                      'pair_plus_hud_ms': report['pair_plus_hud_ms'],
                      'findings': report['findings']}))
    return 0


def render_text(report):
    rates = report['rates']
    budget = report['pair_plus_hud_ms']
    lines = [
        f"verdict: {report['verdict']}",
        f"scope: {report['scope']['records']} records, "
        f"{report['scope']['wall_ms']:.1f} ms, XR={report['scope']['xr_submission_present']}",
        f"native VBlank: {rates['native_vblank_hz_from_trace']:.2f} Hz",
        f"fresh pairs: {rates['fresh_pairs_per_second']:.2f}/s "
        f"(target {rates['target_hz']:.0f} Hz)",
        f"pair+hud p95: {budget['p95']:.3f} ms vs "
        f"{report['scope']['display_budget_ms']:.3f} ms budget",
        'interval split (ms/s): '
        f"work={report['runtime_cadence']['work_guest_ms_per_s_mean']} "
        f"pacer={report['runtime_cadence']['pacer_ms_per_s_mean']} "
        f"canonical={report['runtime_cadence']['canonical_ms_per_s_mean']} "
        f"sim_interval={report['runtime_cadence']['sim_interval_ms_per_s_mean']}",
        f"async GPU samples: {report['gpu']['timer_samples']} "
        f"(scene={report['gpu']['scene_ms_mean']} ms, "
        f"present={report['gpu']['present_ms_mean']} ms)",
        'findings:',
    ]
    lines += [f'  - {item}' for item in report['findings'] or ['none']]
    lines.append('limitation: offline analysis; not a physical headset acceptance')
    return '\n'.join(lines)


if __name__ == '__main__':
    sys.exit(main())
