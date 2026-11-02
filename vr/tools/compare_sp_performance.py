"""Compare preserved first-game/Underground SP evidence; never launch a game.

These are different scenes, historical builds and input conditions. The output
is workload attribution, not a matched benchmark or a predicted speedup.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[2]
STAGES = (
    'pair_total', 'game_traverse', 'game_select', 'game_submit', 'hud_capture',
    'hud_draw', 'hud_readback', 'xr_wait_frame', 'xr_copy', 'xr_end_frame',
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(
        ['git', '-C', str(root), *args], text=True).strip()


def percentile(values, q):
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower, upper = math.floor(index), math.ceil(index)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def summary(values, divisor=1):
    return {key: round(value / divisor, 6) for key, value in (
        ('mean', statistics.mean(values)), ('p50', statistics.median(values)),
        ('p95', percentile(values, .95)),
    )}


def trace(root, relative):
    path = root / relative
    data = json.loads(path.read_text())
    rows = data['records']
    if not rows or data.get('missing') or data.get('dropped'):
        raise ValueError(f'Missing/overwritten trace evidence: {path}')
    for row in rows:
        if (row['flags'] & 0x101 != 0x101 or not row['xr_submit_fresh'] or
                row['failure'] or row['shed'] or row['vram_leaks'] or
                row['eye_failed'] != -1):
            raise ValueError(f'Unpublished/failed/repeated pair in {path}')
    if any(b['pair_id'] <= a['pair_id'] for a, b in zip(rows, rows[1:])):
        raise ValueError(f'Non-increasing pair IDs in {path}')
    span = rows[-1]['open_ms'] - rows[0]['open_ms']
    return {
        'path': relative, 'sha256': sha(path),
        'exported_rows': len(rows), 'ring_count': data['count'],
        'first_seq': rows[0]['seq'], 'last_seq': rows[-1]['seq'],
        'runtime': data['runtime'], 'headset_acceptance': False,
        'pair_intervals_per_second_in_export': (len(rows)-1)*1000/span,
        'stages_ms': {key: summary([r['stages_us'][key] for r in rows], 1000)
                      for key in STAGES},
        'workload': {key: summary([r[key] for r in rows]) for key in
                     ('prims_l', 'prims_r', 'tex_prims_l', 'tex_prims_r',
                      'cycles_l', 'cycles_r', 'xr_display_delta_us')},
    }


def checkout(root, paths, binary):
    cache = root / 'build-release/CMakeCache.txt'
    options = {}
    for line in cache.read_text().splitlines():
        if ':' in line and '=' in line and not line.startswith('//'):
            key, value = line.split('=', 1)
            key = key.split(':')[0]
            if key in ('CMAKE_BUILD_TYPE', 'CMAKE_C_FLAGS_RELEASE',
                       'CMAKE_CXX_FLAGS_RELEASE', 'PSX_DEBUG_TOOLS',
                       'PSX_GL_BATCH_IMPL', 'MOH_PGXP', 'MOHU_VR_DIAGNOSTICS',
                       'PSX_OPENXR', 'PSX_EXECUTION_PROFILE'):
                options[key] = value
    return {
        'root': str(root), 'head': git(root, 'rev-parse', 'HEAD'),
        'framework': git(root / 'psxrecomp', 'rev-parse', 'HEAD'),
        'working_files_may_be_uncommitted': True,
        'sources_sha256': {p: sha(root / p) for p in paths},
        'current_build_options': options,
        'current_binary_sha256': sha(root / 'build-release' / binary),
        'current_binary_is_not_historical_trace_provenance': True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-root', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    ref = args.reference_root.resolve()
    common = ['game.toml', 'CMakeLists.txt', 'vr/run_vr.ps1',
              'psxrecomp/runtime/src/render_pass.c',
              'psxrecomp/runtime/src/gpu_gl_renderer.c',
              'psxrecomp/runtime/src/gte.cpp']
    first = trace(ref, 'analysis/vr-proof/20261023-slot2-accepted-base/trace.json')
    second = trace(ROOT, 'analysis/vr-baseline/operator-perf-20261028/'
                         'production-final/frame-trace.json')
    timing_path = ref / 'analysis/vr-proof/20261023-slot2-release-final/timing.json'
    timing = json.loads(timing_path.read_text())
    production_path = ROOT / ('analysis/vr-baseline/operator-perf-20261028/'
                              'production-final/receipt.json')
    production = json.loads(production_path.read_text())
    if (not all(production[k] for k in
                ('complete', 'source_saves_unchanged', 'preferences_unchanged')) or
            production['exit_code'] != 0 or production.get('forced_cleanup') or
            production['remaining_game_pids']):
        raise ValueError('Underground production receipt failed its controls')
    report = {
        'schema': 1, 'date': '2026-10-28', 'new_runtime_measurements': False,
        'matched_cross_game_benchmark': False,
        'analysis_script_sha256': sha(Path(__file__)),
        'operator_observation': 'First game plays about fine at 60 FPS; 90 preferred',
        'limits': [
            'First trace: historical debug-ON interpreter, slot-2 indoor/crates.',
            'Underground trace: debug-OFF native, slot-3 courtyard; no injected hands.',
            'Both traces use null HMD, not the operator physical VDXR session.',
            'Stage boundaries differ: Underground traversal includes the frame wrapper.',
            'Ring count is not the number of rows exported.',
            'Guest cycles and primitive counts are workload indicators, not host CPU time.',
        ],
        'reference_checkout': checkout(ref, common + [
            'vr/psx_vr_stereo.c', 'vr/moh_vr_hud.c', 'RunVR-VDXR.bat',
            'docs/reverse/VR_SLOT2_PERFORMANCE.md',
            'docs/reverse/VR_OPTIMIZATION_STATUS.md',
        ], 'Medal_of_Honor__Recompiled.exe'),
        'underground_checkout': checkout(ROOT, common + [
            'vr/underground/vr_diagnostic.c', 'vr/underground/hud.c',
            'vr/underground/engine_map.c',
        ], 'Medal_of_Honor_Underground_Recompiled.exe'),
        'reference_diagnostic_trace': first,
        'underground_production_trace': second,
        'reference_historical_production': {
            'path': str(timing_path.relative_to(ref)), 'sha256': sha(timing_path),
            'weighted_guest_vblanks_per_second': timing['native_fps_weighted'],
            'median_pair_ema_ms': timing['pair_ema_ms_median'],
            'fresh_stereo_fps_is_not_guest_vblank_rate': True,
        },
        'underground_production_receipt': {
            'path': str(production_path.relative_to(ROOT)),
            'sha256': sha(production_path),
            'binary_sha256': production['binary_sha256'],
            'build': production['build'], 'bounded_launcher_stop': True,
        },
        'descriptive_workload_ratios_not_speedup_predictions': {
            key: second['workload'][key]['p50'] / first['workload'][key]['p50']
            for key in ('prims_l', 'prims_r', 'cycles_l', 'cycles_r')
        },
    }
    partial = (second['stages_ms']['pair_total']['mean'] +
               second['stages_ms']['hud_capture']['mean'])
    report['partial_pair_plus_hud_budget'] = {
        'mean_ms': partial,
        'excludes_canonical_guest_work_and_remaining_xr_stages': True,
        'minimum_reduction_fraction_for_60': 1 - (1000/60)/partial,
        'minimum_reduction_fraction_for_90': 1 - (1000/90)/partial,
        'is_not_a_complete_frame_time_or_fps_prediction': True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({
        'out': str(args.out), 'new_runtime_measurements': False,
        'reference_rows': first['exported_rows'],
        'underground_rows': second['exported_rows'],
        'partial_pair_plus_hud_mean_ms': partial,
    }))


if __name__ == '__main__':
    main()
