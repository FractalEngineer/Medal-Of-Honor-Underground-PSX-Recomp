"""Quiet SP stage timings with copied saves and synthetic hands; no physical HMD.

Launch outside the sandbox. Debug timings localize cost, not production FPS.
--headless-xr uses run_vr.ps1's restore-protected SteamVR null HMD.
"""
import argparse
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import time

import inspect_weapon_sets as n
import probe_p38_headset as p

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out', type=Path)
    ap.add_argument('--hud', action='store_true')
    ap.add_argument('--laser', action='store_true')
    ap.add_argument('--headless-xr', action='store_true')
    ap.add_argument('--production-null', action='store_true',
                    help='Debug-OFF null-HMD timing via one opt-in file export; no synthetic hand injection')
    ap.add_argument('--resolution', default='1080p')
    ap.add_argument('--seconds', type=int, default=10)
    args = ap.parse_args()
    if not 5 <= args.seconds <= 20:
        ap.error('--seconds must be 5..20')
    if n.game_pids():
        raise RuntimeError('Close the current game before this owned probe')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    saves = out / 'saves/openbios'
    saves.mkdir(parents=True)
    source = list((ROOT/'analysis/vr-baseline/saves/openbios').glob('*slot03.*'))
    assert len(source) == 2, source
    hashes = {str(f): n.digest(f) for f in source}
    for f in source:
        shutil.copyfile(f, saves/f.name)
    prefs = p.hash_existing(p.preference_paths())
    exe = ROOT/'build-release/Medal_of_Honor_Underground_Recompiled.exe'
    env = p.environment('tracked', True, hand_fixed=True)
    env.update(MOHU_VR_MP_CONTROL='0', MOHU_VR_MP_FRUSTUM='0',
               PSX_RENDER_PASS_VERIFY='0', PSX_FRAME_TRACE='1',
               PSX_VR_WRIST_HUD=str(int(args.hud)), PSX_VR_LASER=str(int(args.laser)),
               PSX_RUNTIME_PERF_DIAG='1', PSX_RUNTIME_PERF_DIAG_MS='1000',
               PSX_FRAME_REPORT_MS='1000', PSX_INTERNAL_RESOLUTION=args.resolution,
               MOHU_VR_UNITS_PER_METER='238.80597014925373', SDL_AUDIODRIVER='dummy')
    r = dict(complete=False, headset_acceptance=False, source_hashes=hashes,
             build=p.build_configuration(ROOT/'build-release/CMakeCache.txt'),
             binary_sha256=n.digest(exe),
             request={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
             environment={k: v for k, v in env.items() if k.startswith(('PSX_', 'MOHU_'))})
    if args.production_null:
        if r['build'].get('PSX_DEBUG_TOOLS') != 'OFF' or args.laser:
            raise RuntimeError('Production control requires debug OFF and no --laser (no injected grip)')
        trace_file = out/'frame-trace.json'
        env['MOHU_VR_FRAME_TRACE_FILE'] = str(trace_file)
        r['environment']['MOHU_VR_FRAME_TRACE_FILE'] = str(trace_file)
        r['mode'] = 'Production null HMD; no injected hands; HUD capture cost only, not hand surface acceptance'
        r['bounded_launcher_stop'] = True
        with (out/'stdout.log').open('w') as so, (out/'stderr.log').open('w') as se:
            proc = subprocess.Popen(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                str(ROOT/'vr/run_vr.ps1'), '-Headless', '-Slot', '3', '-MemcardDirectory', str(out/'saves'),
                '-LogDirectory', str(out), '-InternalResolution', args.resolution, '-Seconds', str(args.seconds),
                '-NoLaser'], cwd=out, env=env, stdout=so, stderr=se, creationflags=subprocess.CREATE_NO_WINDOW)
            proc.wait()
        if trace_file.exists():
            r['trace'] = json.loads(trace_file.read_text())
            rows = r['trace']['records']
            r['trace_valid'] = bool(len(rows) == 120 and all(
                x['pair_id'] > 0 and not x['failure'] and not x['vram_leaks']
                and (x['flags'] & 1) and not (x['flags'] & (4 | 8 | 16)) for x in rows))
            r['mean_stages_ms'] = {k: statistics.mean(x['stages_us'][k] for x in rows)/1000
                                   for k in rows[0]['stages_us']}
            span = rows[-1]['open_ms']-rows[0]['open_ms']
            r['trace_pairs_per_second'] = (len(rows)-1)*1000/span if span else 0
        r.update(exit_code=proc.returncode, remaining_game_pids=n.game_pids(),
                 source_saves_unchanged=all(n.digest(Path(k)) == v for k, v in hashes.items()),
                 preferences_unchanged=p.hash_existing(p.preference_paths()) == prefs)
        r['complete'] = bool(proc.returncode == 0 and r.get('trace_valid') and not r['remaining_game_pids']
                             and r['source_saves_unchanged'] and r['preferences_unchanged'])
        (out/'receipt.json').write_text(json.dumps(r, indent=2)+'\n')
        print(json.dumps({k: r.get(k) for k in ('complete', 'trace_pairs_per_second', 'mean_stages_ms')}))
        if not r['complete']:
            raise RuntimeError('Production timing incomplete; inspect receipt and runtime backup')
        return
    launch = [str(exe), '--headless-opengl', '--no-launcher', '--game', str(ROOT/'game.toml'),
              '--memcard-dir', str(out/'saves'), '--debug-port', '4372']
    if args.headless_xr:
        launch = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                  str(ROOT/'vr/run_vr.ps1'), '-Headless', '-Slot', '3',
                  '-MemcardDirectory', str(out/'saves'), '-DebugPort', '4372',
                  '-LogDirectory', str(out), '-InternalResolution', args.resolution, '-Seconds', '55']
        if not args.laser:
            launch.append('-NoLaser')
    with (out/'stdout.log').open('w') as so, (out/'stderr.log').open('w') as se:
        proc = subprocess.Popen(launch, cwd=out, env=env, stdout=so, stderr=se,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            p.wait_for_ping(proc)
            if args.headless_xr:
                deadline = time.monotonic()+40
                while not (out/'openxr-smoke.json').exists():
                    if proc.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('Null HMD did not start')
                    time.sleep(.2)
            n.load(3)
            p.release_load_override()
            p.set_desktop_hands()
            n.command('openxr_hands_override', hand='left', pose='grip', active=1,
                      flags=15, px_mm=-180, py_mm=-180, pz_mm=-450, qw=1000000)
            if args.laser:
                n.command('openxr_input_override', right_squeeze=1000)
            n.frames(20)
            start = n.command('stereo_stats')
            t0 = time.monotonic()
            time.sleep(args.seconds)  # no TCP, screenshots, or RAM reads in window
            elapsed = time.monotonic()-t0
            end = n.command('stereo_stats')
            r['quiet'] = dict(seconds=elapsed, before=start, after=end,
                             pairs_per_second=(end['pairs']-start['pairs'])/elapsed)
            r['trace'] = n.command('frame_trace', max=180)
            r['hud'] = n.command('mod_cmd', name='mohu.vr.hud', args='status')
            r['complete'] = end['pairs'] > start['pairs'] and end['failed'] == start['failed']
        finally:
            try:
                n.command('render_pass_refuse', on=1)
                n.frames(4)
                n.command('quit')
            except (OSError, RuntimeError):
                pass
            try:
                # Launcher may need 15 s to stop SteamVR and another 15 s to
                # restore settings after the game has already exited.
                proc.wait(timeout=45 if args.headless_xr else 15)
            except subprocess.TimeoutExpired:
                r['forced_cleanup'] = True
                proc.terminate()
                proc.wait(timeout=8)
            r.update(exit_code=proc.returncode, remaining_game_pids=n.game_pids(),
                     source_saves_unchanged=all(n.digest(Path(k)) == v for k, v in hashes.items()),
                     preferences_unchanged=p.hash_existing(p.preference_paths()) == prefs)
            r['complete'] = bool(r['complete'] and proc.returncode == 0 and not r.get('forced_cleanup')
                                 and not r['remaining_game_pids'] and r['source_saves_unchanged']
                                 and r['preferences_unchanged'])
            (out/'receipt.json').write_text(json.dumps(r, indent=2)+'\n')
    print(json.dumps(dict(complete=r['complete'], quiet=r.get('quiet'), hud=r.get('hud'))))
    if not r['complete']:
        raise RuntimeError('Performance control incomplete; inspect receipt')


if __name__ == '__main__':
    main()
