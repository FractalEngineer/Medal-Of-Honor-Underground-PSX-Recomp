"""Bounded copied-fixture SP visual/quiet-cadence control; no headset."""
import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'vr/tools'))
import inspect_weapon_sets as n
import probe_p38_headset as p

def overlay_native_summary(response):
    ring = response.get('ring', {}) if isinstance(response, dict) else {}
    return {
        'native_exec': int(ring.get('native_exec', 0)),
        'calls_total': int(ring.get('calls_total', 0)),
        'would_run': int(ring.get('would_run', 0)),
        'in_progress': ring.get('in_progress'),
        'recent_addresses': [x.get('addr') for x in ring.get('recent', [])[:32]],
    }

def main():
    a = argparse.ArgumentParser()
    a.add_argument('out', type=Path)
    a.add_argument('--source', type=Path, default=ROOT/'analysis/vr-baseline/saves')
    a.add_argument('--slot', type=int, default=3)
    a.add_argument('--native', action='store_true')
    a.add_argument('--verify', action='store_true')
    a.add_argument('--seconds', type=int, default=8)
    a.add_argument('--reload', action='store_true')
    a.add_argument('--resolution', default='1080p')
    a.add_argument('--production-config', action='store_true')
    a.add_argument('--require-native', action='store_true')
    a.add_argument('--native-adapter', action='store_true')
    a.add_argument('--head-yaw', type=int, default=0)
    a.add_argument('--hand-z-mm', type=int, default=-400)
    a.add_argument('--hand-x-mm', type=int, default=150)
    a.add_argument('--eye-offset', type=int, default=0)
    a.add_argument('--tracking-loss', action='store_true')
    a.add_argument('--no-spare-arena', action='store_true')
    a.add_argument('--expect-out-of-view', action='store_true')
    a.add_argument('--follow-head', action='store_true')
    args = a.parse_args()
    if n.game_pids():
        raise RuntimeError('Close the existing game before this owned probe')
    if not 1 <= args.seconds <= 60:
        raise ValueError('seconds must be 1..60')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture = out/'saves/openbios'
    fixture.mkdir(parents=True)
    sources = list((args.source/'openbios').glob(f'*slot{args.slot:02}.*'))
    assert len(sources) == 2, sources
    hashes = {str(f): n.digest(f) for f in sources}
    prefs = p.hash_existing(p.preference_paths())
    for f in sources:
        shutil.copyfile(f, fixture/f.name)
    env = p.environment('native' if args.native else 'tracked', True, hand_fixed=True)
    for k in ('MOHU_VR_MP_CONTROL', 'MOHU_VR_MP_FRUSTUM'):
        env.pop(k, None)
    env.update(PSX_RENDER_PASS_VERIFY=str(int(args.verify)),
               PSX_RUNTIME_PERF_DIAG='1', PSX_RUNTIME_PERF_DIAG_MS='1000',
               PSX_FRAME_REPORT_MS='1000', PSX_INTERNAL_RESOLUTION=args.resolution,
               MOHU_VR_UNITS_PER_METER='238.80597014925373',
               MOHU_VR_WEAPON_TRACE='0',
               MOHU_VR_EYE_YAW_MDEG=str(args.head_yaw*1000),
               MOHU_VR_EYE_OFFSET=str(args.eye_offset),
               MOHU_VR_WEAPON_FORCE_TRACKING_LOSS=str(int(args.tracking_loss)),
               MOHU_VR_SP_WEAPON_SPARE_ARENA=str(int(not args.no_spare_arena)))
    if args.native_adapter:
        import re
        hooks=re.findall(r'\.target_address = (0x[0-9A-Fa-f]+)u', (ROOT/'vr/underground/engine_map.c').read_text())
        hooks += ['0x80076C28', '0x80090760']
        env['PSX_NATIVE_BLOCK'] = ','.join(hooks)
    exe = ROOT/'build-release/Medal_of_Honor_Underground_Recompiled.exe'
    r = dict(schema=1, kind='SP weapon visual/quiet-cadence control',
             headset_acceptance=False,
             request={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
             binary_sha256=n.digest(exe), source_hashes=hashes,
             environment={k:v for k,v in env.items() if k.startswith(('PSX_', 'MOHU_'))},
             build=p.build_configuration(ROOT/'build-release/CMakeCache.txt'),
             native=args.native, verify=args.verify, complete=False)
    def save():
        (out/'receipt.json').write_text(json.dumps(r, indent=2)+'\n')
    def word(addr):
        return struct.unpack('<I', n.read(addr, 4))[0]
    def snapshot(label):
        actor = word(0x800AA17C)
        assert 0x800B0000 <= actor <= 0x801FC000, hex(actor)
        inp, obj = word(actor+0x39c), word(actor+0x114)
        if inp != actor + 0x3FC or obj != inp + 0x330:
            raise RuntimeError('Fixture is not the measured SP held-weapon layout')
        if n.read(inp+93, 1)[0] != 0:
            raise RuntimeError('This focused SP control requires the P38 fixture')
        model = dict(actor=hex(actor), input=hex(inp), object=hex(obj),
                     weapon_id=n.read(inp+93, 1)[0],
                     object_bytes=n.read(obj, 0xc0).hex(),
                     registers=n.command('get_registers'))
        for off in (0x7c, 0x80):
            header=word(obj+off)
            model[hex(off)] = dict(header=hex(header), words=n.read(header, 32).hex())
        r[label]=model
        n.command('screenshot_hires', path=str(out/f'{label}.png'))
        return model
    with (out/'stdout.log').open('w') as so, (out/'stderr.log').open('w') as se:
        proc = subprocess.Popen([str(exe), '--headless-opengl', '--no-launcher',
            '--game', str(ROOT/('game.toml' if args.production_config else 'analysis/vr-baseline/game-interp.toml')),
            '--memcard-dir', str(out/'saves'), '--debug-port', '4372'],
            cwd=out, env=env, stdout=so, stderr=se,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            p.wait_for_ping(proc)
            n.load(args.slot)
            p.release_load_override()
            p.set_desktop_hands()
            if args.hand_z_mm != -400 or args.hand_x_mm != 150:
                for pose in ('grip', 'aim'):
                    n.command('openxr_hands_override', hand='right', pose=pose,
                              px_mm=args.hand_x_mm, py_mm=-150,
                              pz_mm=args.hand_z_mm, qx=0, qy=0, qz=0,
                              qw=1000000, flags=15, active=1, age_ms=0)
            if args.follow_head:
                import math
                import check_weapon_pose_spaces as poses
                angle=math.radians(args.head_yaw)
                grip=(0.15*math.cos(angle)-0.4*math.sin(angle), -0.15,
                      -0.15*math.sin(angle)-0.4*math.cos(angle))
                q=(0,math.sin(angle/2),0,math.cos(angle/2))
                poses.set_hand_pair(grip=grip, aim=grip, aim_q=q)
            n.frames(12)
            snapshot('before')
            r['overlay_status_before']=n.command('overlay_loader_status')
            r['overlay_native_before']=overlay_native_summary(
                n.command('overlay_native_ring'))
            (out/'ram.bin').write_bytes(n.read(0x80000000, 0x200000))
            # Quiet window excludes readbacks and verification when measuring performance.
            r['start_frame']=n.command('frame')
            r['start_counters']=p.counter_values()
            r['start_stereo']=n.command('stereo_stats')
            t=time.perf_counter()
            time.sleep(args.seconds)
            r['end_frame']=n.command('frame')
            r['elapsed_seconds']=time.perf_counter()-t
            r['end_counters']=p.counter_values()
            r['quiet_stereo']=n.command('stereo_stats')
            r['quiet_restoration']=n.command('render_pass_stats')
            r['guest_frame_rate']=(r['end_frame']['frame']-r['start_frame']['frame'])/r['elapsed_seconds']
            eyes=out/'eyes'
            eyes.mkdir()
            n.command('stereo_dump', path=eyes.as_posix(), count=6)
            n.command('set_input', buttons='0xbfff')
            n.frames(10)
            snapshot('firing')
            n.command('set_input', buttons='0xffff')
            n.frames(12)
            r['final_counters']=p.counter_values()
            r['overlay_status_after']=n.command('overlay_loader_status')
            r['overlay_native_after']=overlay_native_summary(
                n.command('overlay_native_ring'))
            r['render']=p.shot_command('render')
            r['stereo']=n.command('stereo_stats')
            r['restoration']=n.command('render_pass_stats')
            r['checks'] = {
                'fresh_stereo': r['quiet_stereo']['pairs'] > r['start_stereo']['pairs'],
                'no_eye_failures': r['stereo']['failed'] == 0,
                'rollback': not args.verify or (
                    r['restoration']['verify_checks'] > 0
                    and r['restoration']['verify_mismatch'] == 0),
            }
            if args.require_native:
                before=r['overlay_native_before']
                after=r['overlay_native_after']
                r['checks']['native_exec'] = bool(before.get('native_exec'))
                r['checks']['native_calls_advance'] = (
                    int(after.get('calls_total', 0)) >
                    int(before.get('calls_total', 0)))
            if not args.native:
                missing_control = args.no_spare_arena and abs(args.head_yaw) >= 60
                r['checks']['expected_gun'] = r['render']['visible_gun_vertices'] == (
                    [0, 0] if missing_control or args.expect_out_of_view else [96, 96])
                r['checks']['expected_arm_mask'] = r['render']['masked_arm_vertices'] == (
                    [0, 0] if missing_control else [142, 142])
                r['checks']['native_arena_failure_control'] = (
                    not missing_control or
                    r['final_counters'].get('mohu.vr.weapon.sp.arena_full', 0) > 0)
                r['checks']['shot_policy'] = (
                    r['final_counters'].get('mohu.vr.shot.sp.aimed', 0) == 0
                    if args.tracking_loss else
                    r['final_counters'].get('mohu.vr.shot.sp.aimed', 0) > 0)
                if args.expect_out_of_view:
                    r['checks']['hidden_owned_flash'] = (
                        r['end_counters'].get('mohu.vr.flash.hidden', 0) >
                        r['start_counters'].get('mohu.vr.flash.hidden', 0))
            if args.reload:
                r['reload_status']=n.load(args.slot)
                p.release_load_override()
                p.set_desktop_hands()
                n.frames(6)
                r['reload_render']=p.shot_command('render')
            r['complete']=True
        finally:
            try:
                n.command('render_pass_refuse', on=1)
                n.frames(6)
                n.command('quit')
            except (OSError, RuntimeError): pass
            try: proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                r['forced_cleanup']=True
                proc.terminate()
                proc.wait(timeout=8)
            r['exit_code']=proc.returncode
            r['remaining_game_pids']=n.game_pids()
            r['source_saves_unchanged']=all(n.digest(Path(f))==h for f,h in hashes.items())
            r['preferences_unchanged']=p.hash_existing(p.preference_paths())==prefs
            r['complete'] = bool(r['complete'] and r['exit_code'] == 0
                and not r.get('forced_cleanup') and not r['remaining_game_pids']
                and r['source_saves_unchanged'] and r['preferences_unchanged'])
            r['control_passed'] = bool(r['complete'] and r.get('checks')
                                       and all(r['checks'].values()))
            save()
    print(json.dumps({k:r.get(k) for k in ('complete','exit_code','guest_frame_rate','render')}))
    if not r['control_passed']:
        raise RuntimeError('SP control failed its declared checks; inspect receipt')


if __name__ == '__main__':
    main()
