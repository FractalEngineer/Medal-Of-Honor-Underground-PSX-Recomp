"""Verify native SP/MP pause state, menu routing and stereo resume in copied saves.

Desktop defaults to no XR. --xr uses the selected installed runtime and records
fresh native-source quad submissions; neither mode claims operator acceptance.
"""
import argparse
import json
from pathlib import Path
import shutil
import socket
import subprocess
import time

import inspect_weapon_sets as n
import probe_p38_headset as p
from run_headset_batch import close_owned_window

ROOT = Path(__file__).resolve().parents[2]


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('out', type=Path)
    a.add_argument('--mode', choices=('sp', 'mp'), required=True)
    a.add_argument('--xr', action='store_true')
    a.add_argument('--headless-xr', action='store_true',
                   help='Use the existing restore-protected SteamVR null-HMD launcher')
    a.add_argument('--runtime-manifest', type=Path)
    args = a.parse_args()
    if args.headless_xr:
        args.xr = True
    if n.game_pids():
        raise RuntimeError('Close the existing game before this owned probe')
    with socket.socket() as endpoint:
        endpoint.bind(('127.0.0.1', 4372))
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    slot = 3 if args.mode == 'sp' else 1
    state = 0x800A70F0 if args.mode == 'sp' else 0x800A0A84
    source = ROOT / ('analysis/vr-baseline/saves' if args.mode == 'sp' else 'saves') / 'openbios'
    target = out / 'saves/openbios'
    target.mkdir(parents=True)
    sources = list(source.glob(f'*slot{slot:02}.*'))
    if sorted(f.suffix for f in sources) != ['.pst', '.thumb']:
        raise RuntimeError('Expected one PST and thumbnail')
    hashes = {str(f): n.digest(f) for f in sources}
    for f in sources:
        shutil.copyfile(f, target / f.name)
    prefs = p.hash_existing(p.preference_paths())
    manifest = args.runtime_manifest or (p.resolve_vdxr_manifest() if args.xr else None)
    env = p.environment('tracked', not args.xr, runtime_manifest=manifest, hand_fixed=True)
    env.update(PSX_RENDER_PASS_VERIFY='1', PSX_INTERNAL_RESOLUTION='native',
               MOHU_VR_UNITS_PER_METER='238.80597014925373', SDL_AUDIODRIVER='dummy')
    if args.mode == 'sp':
        env.update(MOHU_VR_MP_CONTROL='0', MOHU_VR_MP_FRUSTUM='0')
    exe = ROOT / 'build-release/Medal_of_Honor_Underground_Recompiled.exe'
    r = dict(mode=args.mode, xr=args.xr, physical_acceptance=False, complete=False,
             headless_xr=args.headless_xr,
             exit_code_scope='launcher' if args.headless_xr else 'game',
             binary_sha256=n.digest(exe), source_hashes=hashes,
             environment={k: v for k, v in env.items() if k.startswith(('PSX_', 'MOHU_', 'XR_'))},
             pause_address=hex(state), cycles=[])

    def save():
        (out / 'receipt.json').write_text(json.dumps(r, indent=2) + '\n', encoding='utf-8')

    def flag():
        return int.from_bytes(n.read(state, 4), 'little')

    def stats():
        result = dict(pause=flag(), frame=n.command('frame')['frame'],
                      stereo=n.command('stereo_stats'),
                      restoration=n.command('render_pass_stats'),
                      counters={x['name']: x['count'] for x in n.command('mod_counters')['counters']})
        if args.xr:
            result['xr'] = n.command('openxr_stats')
        return result

    def press(**values):
        n.command('openxr_input_override', **values)
        n.frames(6)
        pad = n.command('pad_status')['slot0']
        n.command('openxr_input_override', clear=1)
        n.frames(4)
        return pad

    def screenshot(name):
        n.command('screenshot_hires', path=str(out / f'{name}.png'))

    with (out / 'stdout.log').open('w') as so, (out / 'stderr.log').open('w') as se:
        command = [str(exe), '--no-launcher', '--game', str(ROOT / 'game.toml'),
                   '--memcard-dir', str(out / 'saves'), '--debug-port', '4372']
        if args.headless_xr:
            env.pop('XR_RUNTIME_JSON', None)
            command = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                       str(ROOT / 'vr/run_vr.ps1'), '-Headless', '-Slot', str(slot),
                       '-GameConfig', str(ROOT / 'game.toml'),
                       '-MemcardDirectory', str(out / 'saves'), '-DebugPort', '4372',
                       '-LogDirectory', str(out), '-Seconds', '60']
        if not args.xr:
            command.append('--headless-opengl')
        proc = subprocess.Popen(command, cwd=out, env=env, stdout=so, stderr=se,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            p.wait_for_ping(proc)
            if args.headless_xr:
                deadline = time.monotonic() + 45
                while not (out / 'openxr-smoke.json').exists():
                    if proc.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('Null-HMD startup failed; inspect launcher logs')
                    time.sleep(.2)
                r['startup'] = json.loads((out / 'startup.json').read_text(encoding='utf-8-sig'))
                r['runtime_selection'] = 'restore-protected SteamVR null HMD; launcher owns XR_RUNTIME_JSON'
            n.load(slot)
            p.release_load_override()
            n.frames(20)
            assert flag() == 0
            screenshot('gameplay')
            for i in range(2):
                row = dict(before=stats())
                r['cycles'].append(row)
                n.command('wtrace_range', lo=hex(state), hi=hex(state + 4))
                n.command('wtrace_clear')
                row['start_pad'] = press(left_buttons=4)
                n.frames(10)
                assert flag() == 1
                row['paused'] = stats()
                row['enter_writes'] = n.command('wtrace_dump', count=64)
                screenshot(f'paused-{i}')
                row['navigate_right_pad'] = press(lx=1000, rx=1000)
                assert row['navigate_right_pad']['sticks'] == [128] * 4
                assert row['navigate_right_pad']['buttons'] == '0xFFDF'
                screenshot(f'paused-right-{i}')
                row['navigate_left_pad'] = press(lx=-1000)
                assert row['navigate_left_pad']['buttons'] == '0xFF7F'
                row['focus_lost_pad'] = press(focused=0, right_trigger=1000, ly=1000)
                assert row['focus_lost_pad']['buttons'] == '0xFFFF'
                assert row['focus_lost_pad']['sticks'] == [128] * 4
                row['paused_after'] = stats()
                assert row['paused_after']['pause'] == 1
                assert row['paused_after']['stereo']['pairs'] == row['paused']['stereo']['pairs']
                if args.xr:
                    assert row['paused_after']['xr']['native_submitted'] > row['paused']['xr']['native_submitted']
                    assert row['paused_after']['xr']['submitted_source'] == 2
                    assert row['paused_after']['xr']['submitted_layer'] == 2
                n.command('wtrace_clear')
                # First test native Start resume, then native Cross/Continue.
                row['resume_pad'] = press(**({'left_buttons': 4} if i == 0 else {'right_buttons': 1}))
                n.frames(20)
                row['resumed'] = stats()
                row['resume_writes'] = n.command('wtrace_dump', count=64)
                assert flag() == 0
                assert row['resumed']['stereo']['pairs'] > row['before']['stereo']['pairs']
                assert row['resumed']['restoration']['verify_mismatch'] == 0
                assert row['resumed']['stereo']['failed'] == 0
                assert row['resumed']['restoration']['verify_checks'] > 0
                screenshot(f'resumed-{i}')
            press(left_buttons=4)
            assert flag() == 1
            r['load_while_paused_before'] = stats()
            r['reload'] = n.load(slot)
            p.release_load_override()
            n.frames(20)
            r['load_while_paused_after'] = stats()
            assert flag() == 0
            assert r['load_while_paused_after']['stereo']['pairs'] > r['load_while_paused_before']['stereo']['pairs']
            r['control_passed'] = True
        except BaseException as error:
            r['error'] = str(error)
            raise
        finally:
            try:
                n.command('wtrace_range', lo='0', hi='0')
                n.command('openxr_input_override', clear=1)
            except (OSError, RuntimeError):
                pass
            if proc.poll() is None:
                try:
                    n.command('render_pass_refuse', on=1)
                    n.frames(4)
                    n.command('quit')
                except (OSError, RuntimeError):
                    close_owned_window(proc)
                try:
                    proc.wait(timeout=40 if args.headless_xr else 20)
                except subprocess.TimeoutExpired:
                    r['forced_cleanup'] = True
                    proc.terminate()
                    proc.wait(timeout=10)
            r.update(exit_code=proc.returncode,
                     source_saves_unchanged=all(n.digest(Path(k)) == v for k, v in hashes.items()),
                     preferences_unchanged=p.hash_existing(p.preference_paths()) == prefs)
            r['complete'] = bool(r.get('control_passed') and proc.returncode == 0
                                 and not r.get('forced_cleanup')
                                 and r['source_saves_unchanged'] and r['preferences_unchanged'])
            save()
    print(json.dumps({k: r.get(k) for k in ('mode', 'xr', 'control_passed', 'complete', 'exit_code')}))
    if not r['complete']:
        raise RuntimeError('Pause control incomplete; inspect receipt and exit scope')


if __name__ == '__main__':
    main()
