"""Production SP desktop stage control: no debug server or XR settings edits.

Uses copied saves and the existing opt-in one-shot trace export. Run unsandboxed.
This measures desktop stereo work, not physical headset FPS or hand surfaces.
Optional old-image recovery isolation restores exact mod-state bytes afterward.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import time
import tomllib

import inspect_weapon_sets as n
import probe_p38_headset as p
from run_headset_batch import close_owned_window

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out', type=Path)
    ap.add_argument('--slot', type=int, default=3)
    ap.add_argument('--exe', type=Path, help='Preserved production binary beside the normal build assets')
    ap.add_argument('--skip-native-world-copy', action='store_true')
    ap.add_argument('--resolution', default='1080p')
    ap.add_argument('--disc', type=Path, help='Temporary mounted image override; config is unchanged')
    ap.add_argument('--without-stream-recovery', action='store_true',
                    help='Temporarily disable the old-image recovery feature, then restore exact mod state')
    args = ap.parse_args()
    if not args.without_stream_recovery:
        return run(args)
    if not args.disc or n.game_pids():
        raise RuntimeError('Recovery isolation requires --disc and no running game')
    state=ROOT/'build-release/mods/state.toml'
    original=state.read_bytes()
    parsed=tomllib.loads(original.decode('utf-8-sig'))
    selected=[f for f in parsed.get('feature',[])
              if f.get('package_id')=='mohu.repair.music-sector' and f.get('id')=='sector-header']
    if selected:
        if len(selected)==1 and selected[0].get('enabled') is False:
            return run(args)
        raise RuntimeError('Recovery already has an explicit selection; preserve it and use a separate test state')
    modified=original+b'\n[[feature]]\npackage_id = "mohu.repair.music-sector"\nid = "sector-header"\nenabled = false\n'
    backup=args.out.resolve().with_name(args.out.name+'-mods-state-backup.toml')
    backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():raise RuntimeError('Refusing to replace an existing mod-state backup')
    backup.write_bytes(original)
    try:
        state.write_bytes(modified)
        return run(args)
    finally:
        state.write_bytes(original)
        restored=state.read_bytes()==original
        record=dict(original_sha256=hashlib.sha256(original).hexdigest(),
            isolated_sha256=hashlib.sha256(modified).hexdigest(),restored=restored,
            recovery_enabled_during_test=False)
        (backup.with_suffix('.json')).write_text(json.dumps(record,indent=2)+'\n')
        if not restored:raise RuntimeError('Original mod state not restored')


def run(args):
    if n.game_pids():
        raise RuntimeError('Close existing game before this owned probe')
    build = p.build_configuration(ROOT/'build-release/CMakeCache.txt')
    if build.get('PSX_DEBUG_TOOLS') != 'OFF' or build.get('configuration') != 'Release':
        raise RuntimeError('Requires production Release/debug OFF')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    target = out/'saves/openbios'
    target.mkdir(parents=True)
    sources = list((ROOT/'analysis/vr-baseline/saves/openbios').glob(f'*slot{args.slot:02}.*'))
    if len(sources) != 2:
        raise RuntimeError('Expected state and thumbnail')
    hashes = {str(f): n.digest(f) for f in sources}
    for f in sources:
        shutil.copyfile(f, target/f.name)
    prefs = p.hash_existing(p.preference_paths())
    exe = (args.exe.resolve() if args.exe else
           ROOT/'build-release/Medal_of_Honor_Underground_Recompiled.exe')
    if exe.parent != ROOT/'build-release' or not exe.is_file():
        raise RuntimeError('Production binary must be beside the existing build assets')
    trace = out/'frame-trace.json'
    env = p.environment('tracked', True, hand_fixed=True)
    env.update(PSX_LOAD_SLOT=str(args.slot), PSX_RENDER_PASS_VERIFY='0',
        PSX_INTERNAL_RESOLUTION=args.resolution, PSX_FRAME_TRACE='1',
        MOHU_VR_FRAME_TRACE_FILE=str(trace), MOHU_VR_WEAPON_TRACE='0',
        MOHU_VR_MP_CONTROL='0', MOHU_VR_MP_FRUSTUM='0', PSX_VR_WRIST_HUD='1',
        PSX_VR_LASER='1', MOHU_VR_UNITS_PER_METER='238.80597014925373',
        MOHU_VR_SKIP_NATIVE_WORLD_COPY=str(int(args.skip_native_world_copy)),
        SDL_AUDIODRIVER='dummy')
    r = dict(complete=False, headset_acceptance=False, injected_hands=False,
        build=build, binary_sha256=n.digest(exe), source_hashes=hashes,
        request={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
        environment={k: v for k, v in env.items() if k.startswith(('PSX_', 'MOHU_'))})
    launch=[str(exe), '--hidden-window', '--no-launcher',
            '--game', str(ROOT/'game.toml'), '--memcard-dir', str(out/'saves')]
    if args.disc:
        launch+=['--disc',str(args.disc.resolve())]
        r['disc_override']=dict(path=str(args.disc.resolve()),descriptor_sha256=n.digest(args.disc.resolve()))
    with (out/'stdout.log').open('w') as so, (out/'stderr.log').open('w') as se:
        proc = subprocess.Popen(launch,
            cwd=out, env=env, stdout=so, stderr=se, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic()+45
            while not trace.exists():
                if proc.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('No production stage export before deadline')
                time.sleep(.1)
            time.sleep(.15)  # Export is outside its measured window.
            data = json.loads(trace.read_text())
            rows = data['records']
            r['trace_valid'] = len(rows) == 120 and all(
                x['pair_id'] > 0 and not x['failure'] and not x['vram_leaks']
                and x['flags'] & 1 and not x['flags'] & (4 | 8 | 16) for x in rows)
            span = rows[-1]['open_ms']-rows[0]['open_ms']
            r['pairs_per_second'] = (len(rows)-1)*1000/span if span else 0
            r['mean_stages_ms'] = {k: statistics.mean(x['stages_us'][k] for x in rows)/1000
                                   for k in rows[0]['stages_us']}
        finally:
            if proc.poll() is None:
                close_owned_window(proc)
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                r['forced_cleanup'] = True
                proc.terminate()
                proc.wait(timeout=8)
            r.update(exit_code=proc.returncode, remaining_game_pids=n.game_pids(),
                source_saves_unchanged=all(n.digest(Path(k)) == v for k, v in hashes.items()),
                preferences_unchanged=p.hash_existing(p.preference_paths()) == prefs)
            r['complete'] = bool(r.get('trace_valid') and proc.returncode == 0
                and not r.get('forced_cleanup') and not r['remaining_game_pids']
                and r['source_saves_unchanged'] and r['preferences_unchanged'])
            (out/'receipt.json').write_text(json.dumps(r, indent=2)+'\n')
    print(json.dumps({k: r.get(k) for k in ('complete', 'pairs_per_second', 'mean_stages_ms')}))
    if not r['complete']:
        raise RuntimeError('Incomplete production control; inspect receipt')


if __name__ == '__main__':
    main()
