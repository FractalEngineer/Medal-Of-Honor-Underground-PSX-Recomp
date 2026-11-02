"""Copied SP regression fixtures, shot/visibility/audio attribution; unsandboxed.

No inventory, health, ammo or source-save writes. No physical OpenXR session.
"""
import argparse
import ctypes
import json
import math
from pathlib import Path
import shutil
import subprocess
import time

import inspect_weapon_sets as n
import probe_p38_headset as p
import check_weapon_pose_spaces as poses

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out', type=Path)
    ap.add_argument('--slot', type=int, required=True)
    ap.add_argument('--seconds', type=int, default=8)
    ap.add_argument('--resolution', default='1080p')
    ap.add_argument('--frustum', type=int, choices=(0, 1, 2), default=1)
    ap.add_argument('--head-yaw', type=int, default=0)
    ap.add_argument('--hand-yaw', type=int, default=0)
    ap.add_argument('--fire', action='store_true')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--native', action='store_true')
    ap.add_argument('--flat', action='store_true', help='Native flat renderer; no stereo replay')
    ap.add_argument('--software', action='store_true')
    ap.add_argument('--audio', action='store_true', help='Hidden SDL, paced, dummy audio sink')
    ap.add_argument('--music-trace', action='store_true', help='Native CD driver write trace')
    ap.add_argument('--fallback-controls', action='store_true', help='Pause/refusal/reload recovery; also checks draw-filter counter when enabled')
    ap.add_argument('--tracking-loss', action='store_true')
    ap.add_argument('--hitch-ms', type=int, default=0)
    ap.add_argument('--hud', action='store_true')
    ap.add_argument('--laser', action='store_true')
    ap.add_argument('--geometry', action='store_true')
    ap.add_argument('--switch', type=int, default=0)
    ap.add_argument('--env-json', type=Path)
    ap.add_argument('--native-profile', action='store_true', help='Capture diagnostic CPS segment timers')
    ap.add_argument('--preflight-cases', type=int, default=0,
                    help='Arm isolated diagnostic native/host caller comparisons (maximum 4096)')
    ap.add_argument('--preflight-stride', type=int, default=127)
    ap.add_argument('--packet-cases', type=int, default=0)
    ap.add_argument('--fresh-60', action='store_true')
    ap.add_argument('--world-cache', action='store_true', help='Exact-pose world packet prototype; motion falls back')
    ap.add_argument('--build-dir', type=Path, default=ROOT/'build-release',
                    help='Complete isolated runtime build/assets directory')
    ap.add_argument('--fixtures', type=Path, default=ROOT/'analysis/fixtures/sp',
                    help='Validated per-execution fixture root containing openbios/')
    ap.add_argument('--disc', type=Path, help='Explicit disposable diagnostic disc override')
    args = ap.parse_args()
    if n.game_pids():
        raise RuntimeError('Close existing game before this owned probe')
    if not 2 <= args.seconds <= 30 or not 0 <= args.switch <= 3 or not 0 <= args.hitch_ms <= 2000:
        raise ValueError('seconds 2..30; switch 0..3')
    if not 0 <= args.preflight_cases <= 4096 or not 1 <= args.preflight_stride <= 4096:
        raise ValueError('preflight cases 0..4096; stride 1..4096')
    if not 0 <= args.packet_cases <= 4096:
        raise ValueError('packet cases 0..4096')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    saves = out/'saves/openbios'
    saves.mkdir(parents=True)
    sources = list((args.fixtures.resolve()/'openbios').glob(f'*slot{args.slot:02}.*'))
    if len(sources) != 2:
        raise RuntimeError('Expected state and thumbnail in analysis SP fixtures')
    hashes = {str(f): n.digest(f) for f in sources}
    for f in sources:
        shutil.copyfile(f, saves/f.name)
    pref_paths = list(dict.fromkeys([*p.preference_paths(),
        args.build_dir.resolve()/'settings.toml', args.build_dir.resolve()/'keybinds.ini']))
    prefs = p.hash_existing(pref_paths)
    env = p.environment('native' if args.native else 'tracked', True, hand_fixed=True)
    env.update(MOHU_VR_MP_CONTROL='0', MOHU_VR_MP_FRUSTUM='0',
               PSX_RENDER_PASS_VERIFY=str(int(args.verify)), PSX_FRAME_TRACE='1',
               PSX_VR_WRIST_HUD=str(int(args.hud)), PSX_VR_LASER=str(int(args.laser)),
               MOHU_VR_FRESH_60=str(int(args.fresh_60)),
               MOHU_VR_WORLD_CACHE=str(int(args.world_cache)),
               PSX_VR_HEAD_FRUSTUM=str(args.frustum), MOHU_VR_WEAPON_TRACE='1',
               MOHU_VR_EYE_YAW_MDEG=str(args.head_yaw*1000),
               PSX_INTERNAL_RESOLUTION=args.resolution,
               MOHU_VR_UNITS_PER_METER='238.80597014925373',
               PSX_RUNTIME_PERF_DIAG='1', PSX_RUNTIME_PERF_DIAG_MS='1000')
    if args.env_json:
        extra = json.loads(args.env_json.read_text())
        if any(not k.startswith(('PSX_', 'MOHU_')) or not isinstance(v, str)
               for k, v in extra.items()):
            raise ValueError('Diagnostic overrides must be string PSX_/MOHU_ flags')
        env.update(extra)
    if args.preflight_cases:
        env['MOHU_VR_PREFLIGHT_CAPTURE_FILE'] = str(out/'preflight-calls.bin')
    if args.flat:
        env.update(MOHU_VR_STEREO_PROOF='0', PSX_VR_WEAPON_POSE='0',
                   MOHU_VR_WEAPON_AIM='0', PSX_VR_LASER='0')
    if args.audio:
        env['SDL_AUDIODRIVER'] = 'dummy'
    build_dir = args.build_dir.resolve()
    exe = build_dir/'Medal_of_Honor_Underground_Recompiled.exe'
    config = build_dir/'game.toml'
    if not config.is_file() or not exe.with_suffix('.execution.json').is_file():
        raise RuntimeError('Requires a complete staged build/config/execution manifest')
    r = dict(complete=False, headset_acceptance=False,
             request={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
             source_hashes=hashes, binary_sha256=n.digest(exe),
             build=p.build_configuration(build_dir/'CMakeCache.txt'),
             build_directory=str(build_dir), fixture_root=str(args.fixtures.resolve()),
             execution_manifest=json.loads(exe.with_suffix('.execution.json').read_text()),
             environment={k: v for k, v in env.items() if k.startswith(('PSX_', 'MOHU_'))})

    def word(addr):
        return int.from_bytes(n.read(addr, 4), 'little')

    def snapshot(name):
        actor = word(0x800AA17C)
        if not 0x800B0000 <= actor <= 0x801FC000:
            raise RuntimeError('Not the SP player layout')
        inp = word(actor+0x39c)
        if inp != actor+0x3fc:
            raise RuntimeError('Not the SP input layout')
        state = dict(actor=actor, input=inp, weapon_id=n.read(inp+93, 1)[0],
                     object=word(actor+0x114), player_bytes=n.read(actor, 0x800).hex(),
                     render=p.shot_command('render'), counters=p.counter_values(),
                     stereo=n.command('stereo_stats'), cdrom=n.command('cdrom_state'),
                     audio=n.command('audio_stats'), voices=n.command('spu_voices'),
                     irq=n.command('irq_state'), camera=p.shot_command('sp-camera'),
                     cd_driver=n.read(0x80035c1c, 0x80).hex(),
                     cd_request=n.read(0x8002f6d8, 0x50).hex())
        if args.audio:
            music = b''.join(bytes.fromhex(n.command('spu_ram', addr=0x1010+offset,
                len=min(4096, 0xa000-offset))['hex']) for offset in range(0,0xa000,4096))
            music_path = out/f'{name}-music.adpcm'
            music_path.write_bytes(music)
            state['music_ram_sha256'] = n.digest(music_path)
        n.command('screenshot_file' if args.software else 'screenshot_hires',
                  path=str(out/f'{name}.png'))
        eyes = out/name
        eyes.mkdir()
        if not args.flat:
            n.command('stereo_dump', path=eyes.as_posix(), count=2)
        n.frames(4)
        return state

    with (out/'stdout.log').open('w') as so, (out/'stderr.log').open('w') as se:
        frontend = '--hidden-window' if args.audio else ('--headless' if args.software else '--headless-opengl')
        launch = [str(exe), frontend, '--no-launcher',
            '--game', str(config), '--memcard-dir', str(out/'saves'),
            '--debug-port', '4372']
        if args.disc:
            launch += ['--disc', str(args.disc.resolve())]
            r['disc_override_sha256'] = n.digest(args.disc.resolve())
        if args.software:
            launch += ['--renderer', 'software']
        proc = subprocess.Popen(launch, cwd=out, env=env, stdout=so, stderr=se,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            p.wait_for_ping(proc)
            r['load'] = n.load(args.slot)
            p.release_load_override()
            p.set_desktop_hands()
            q = (0, math.sin(math.radians(args.hand_yaw)/2), 0,
                 math.cos(math.radians(args.hand_yaw)/2))
            poses.set_hand_pair(grip=(.15, -.15, -.4), aim=(.15, -.15, -.4),
                                grip_q=q, aim_q=q, focused=0 if args.tracking_loss else 1)
            if args.laser:
                n.command('openxr_input_override', right_squeeze=1000)
            for _ in range(args.switch):
                n.switch()
            n.frames(10)
            r['before'] = snapshot('before')
            (out/'ram.bin').write_bytes(n.read(0x80000000, 0x200000))
            if args.preflight_cases:
                result = n.command('mod_cmd', name='mohu.vr.preflight-harness',
                    args=f'arm {args.preflight_cases} {args.preflight_stride}')
                deadline = time.monotonic()+30
                while json.loads(result['reply'])['remaining']:
                    if time.monotonic()>deadline:
                        raise TimeoutError('Preflight caller comparisons did not finish')
                    time.sleep(.1)
                    result = n.command('mod_cmd', name='mohu.vr.preflight-harness', args='status')
                r['preflight_harness'] = json.loads(result['reply'])
            if args.packet_cases:
                result = n.command('mod_cmd', name='mohu.vr.packet-harness',
                    args=f'arm {args.packet_cases} {args.preflight_stride}')
                deadline = time.monotonic()+30
                while json.loads(result['reply'])['remaining']:
                    if time.monotonic()>deadline:
                        raise TimeoutError('Packet caller comparisons did not finish')
                    time.sleep(.1)
                    result = n.command('mod_cmd', name='mohu.vr.packet-harness', args='status')
                r['packet_harness'] = json.loads(result['reply'])
            r['start'] = n.command('stereo_stats')
            r['start_frame'] = n.command('frame')
            if args.native_profile:
                r['native_profile_before'] = [n.command('mod_cmd', name='mohu.vr.native-profile', args=str(i)) for i in range(3)]
            n.command('cdrom_trace_clear')
            n.command('dma_trace_clear')
            if args.music_trace:
                n.command('wtrace_range', lo='0x8002f6d8', hi='0x80035ca0')
                n.command('wtrace_clear')
            if args.hitch_ms:
                # Stall only this owned child's main thread. SDL's audio thread
                # keeps draining, reproducing an emulation/driver hitch.
                tid = int(subprocess.check_output(['powershell', '-NoProfile', '-Command',
                    f'(Get-Process -Id {proc.pid}).Threads | Sort-Object StartTime | '
                    'Select-Object -First 1 -ExpandProperty Id'],
                    creationflags=subprocess.CREATE_NO_WINDOW, text=True).strip())
                k = ctypes.WinDLL('kernel32', use_last_error=True)
                k.OpenThread.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
                k.OpenThread.restype = ctypes.c_void_p
                k.SuspendThread.argtypes = k.ResumeThread.argtypes = [ctypes.c_void_p]
                k.SuspendThread.restype = k.ResumeThread.restype = ctypes.c_ulong
                k.CloseHandle.argtypes = [ctypes.c_void_p]
                handle = k.OpenThread(2, 0, tid)
                if not handle:
                    raise ctypes.WinError(ctypes.get_last_error())
                suspended = False
                try:
                    if k.SuspendThread(handle) == 0xffffffff:
                        raise ctypes.WinError(ctypes.get_last_error())
                    suspended = True
                    time.sleep(args.hitch_ms/1000)
                finally:
                    if suspended:
                        k.ResumeThread(handle)
                    k.CloseHandle(handle)
                r['injected_hitch'] = dict(thread_id=tid, milliseconds=args.hitch_ms)
            t0 = time.monotonic()
            time.sleep(args.seconds)
            r['elapsed'] = time.monotonic()-t0
            r['end'] = n.command('stereo_stats')
            r['end_frame'] = n.command('frame')
            if args.native_profile:
                r['native_profile_after'] = [n.command('mod_cmd', name='mohu.vr.native-profile', args=str(i)) for i in range(3)]
            r['fresh_pairs_s'] = (r['end']['pairs']-r['start']['pairs'])/r['elapsed']
            r['trace'] = n.command('frame_trace', max=180)
            r['host_profile'] = n.command('host_profile', top=400,
                frame_lo=r['start_frame']['frame'], frame_hi=r['end_frame']['frame'], **{'pass': 1})
            # Capture outside the quiet interval, while the owned process still
            # has its cached native DLLs loaded. Relative EXE addresses alone
            # cannot distinguish those functions from system-module work.
            module_script = (f'(Get-Process -Id {proc.pid}).Modules | ForEach-Object '
                '{ [pscustomobject]@{ path=$_.FileName; base=$_.BaseAddress.ToInt64(); '
                'size=$_.ModuleMemorySize } } | ConvertTo-Json -Compress')
            r['host_modules'] = json.loads(subprocess.check_output(
                ['powershell', '-NoProfile', '-Command', module_script], text=True,
                creationflags=subprocess.CREATE_NO_WINDOW))
            r['phase_profile'] = n.command('phase_profile', window=300)
            r['phase_hot_native'] = n.command('phase_hot', top=30)
            r['phase_hot_static'] = n.command('phase_hot', set='static', top=30)
            r['gcp'] = n.command('gcp_ring', path=str(out/'guest-cycles.csv'))
            if args.fire:
                n.command('wtrace_range', lo='0x800B0000', hi='0x801FF000')
                n.command('wtrace_clear')
                n.command('set_input', buttons='0xbfff')
                n.frames(12)
                n.command('set_input', buttons='0xffff')
                n.frames(8)
                n.command('wtrace_range', lo='0', hi='0')
                r['shot_writes'] = n.command('wtrace_dump', count=4096,
                                             pc_lo='0x80048000', pc_hi='0x80048b00')
                objects=sorted({int(e['s0'], 0) for e in r['shot_writes']['entries']
                    if int(e['pc'], 0) == 0x800484bc})
                r['shot_objects'] = [dict(address=address,
                    writes=n.command('wtrace_dump', count=2048,
                        addr_lo=hex(address), addr_hi=hex(address+0x400)))
                    for address in objects]
            r['after'] = snapshot('after')
            if args.music_trace:
                n.command('wtrace_range', lo='0', hi='0')
                r['music_writes'] = n.command('wtrace_dump', count=4096,
                    pc_lo='0x80023ca8', pc_hi='0x8002403c')
            r['spu_events'] = n.command('spu_events', count=256)
            r['cdrom_trace'] = n.command('cdrom_trace_dump', count=2048)
            if args.audio:
                r['dma_trace'] = n.command('dma_trace_dump', count=16384)
                r['cd_read_log'] = n.command('cd_read_log', tail=4096)
            if args.audio:
                r['audio_wav'] = [n.command('audio_wav', tap=tap,
                    path=str(out/f'audio-tap-{tap}.wav'),
                    start=str(max(0, r['after']['audio']['taps'][tap]['frames']-220500)),
                    count=220500)
                    for tap in (0, 1, 2) if r['after']['audio']['taps'][tap]['frames']]
            frame = n.command('frame')['frame']
            r['gpu_packets'] = [n.command('gpu_frame_dump', frame=f, count=8192)
                                for f in range(frame-2, frame+1)]
            r['gte'] = n.command('gte_state')
            if args.laser:
                r['laser'] = n.command('mod_cmd', name='mohu.vr.laser', args='eye=0')
            if args.geometry:
                import probe_laser_surfaces as surfaces
                r['level_geometry'] = [surfaces.command(f'level={i}') for i in range(8)]
                # The per-eye cache count is transiently zero during replay.
                # Read immutable native arena records instead of racing it.
                arena_count = word(0x800a5384)
                if not 1 <= arena_count <= 8:
                    raise RuntimeError('Invalid SP arena count')
                skip = word(0x800b749c)
                levels=[]
                for i in range(arena_count):
                    if i == skip:
                        continue
                    record=0x800a57dc+i*0xc4
                    levels.append(dict(root=word(word(record+8)+20),
                                       table=word(record+44), count=word(record+60)))
                r['native_levels'] = levels
                triangles = surfaces.geometry('sp', out, levels=levels)
                if not len(triangles):
                    raise RuntimeError('No decoded SP arena triangles')
                ray = surfaces.command('eye=0')
                r['independent_hit'] = surfaces.nearest(triangles,
                    surfaces.np.asarray(ray['origin']), surfaces.np.asarray(ray['direction']),
                    50*238.80597014925373)
            r['restore'] = n.command('render_pass_stats')
            r['overlay'] = n.command('overlay_native_ring')
            if args.fallback_controls:
                key='mohu.vr.world.native_copy_skipped'
                filter_enabled = env.get('MOHU_VR_SKIP_NATIVE_WORLD_COPY') == '1'
                def count():
                    return (p.counter_values().get(key,0) if filter_enabled
                            else n.command('stereo_stats')['pairs'])
                n.command('clear_input')
                def menu_button():
                    # Same controller route/window as probe_pause_menu.py.
                    n.command('openxr_input_override',left_buttons=4)
                    n.frames(6)
                    n.command('openxr_input_override',clear=1)
                    n.frames(10)
                menu_button()
                if word(0x800a70f0)!=1:raise RuntimeError('Pause input did not enter menu')
                paused=count();n.frames(8)
                paused_after=count()
                pause_counters=p.counter_values()
                menu_button();n.frames(8)
                if word(0x800a70f0)!=0:raise RuntimeError('Menu Back did not resume')
                resumed=count()
                n.command('render_pass_refuse',on=1);n.frames(8)
                refused=count();n.frames(8);refused_after=count()
                n.command('render_pass_refuse',on=0);n.frames(8)
                recovered=count()
                n.load(args.slot);p.release_load_override();n.frames(12)
                r['fallback_controls']=dict(paused=paused,paused_after=paused_after,
                    resumed=resumed,refused=refused,refused_after=refused_after,
                    recovered=recovered,reloaded=count(),camera=p.shot_command('sp-camera'),
                    pause_counters=pause_counters,
                    counter_scope=key if filter_enabled else 'stereo_pairs')
                if not (paused==paused_after and resumed>paused_after
                        and refused==refused_after and recovered>refused_after
                        and r['fallback_controls']['camera']['valid']):
                    raise RuntimeError('Native-copy filter fallback control failed')
                r['recovery'] = snapshot('recovery')
                r['restore'] = n.command('render_pass_stats')
            r['complete'] = ((args.flat and r['end_frame']['frame'] > r['start_frame']['frame']
                             or r['end']['pairs'] > r['start']['pairs']) and
                             r['end']['failed'] == r['start']['failed'] and
                             r['restore']['verify_mismatch'] == 0)
            if args.preflight_cases:
                r['complete'] = bool(r['complete'] and
                    r['preflight_harness']['checks'] == args.preflight_cases and
                    r['preflight_harness']['failed'] == 0 and
                    r['preflight_harness']['refused'] == 0)
            if args.packet_cases:
                r['complete'] = bool(r['complete'] and r['packet_harness']['checks'] == args.packet_cases
                    and r['packet_harness']['failed'] == 0 and r['packet_harness']['refused'] == 0)
        finally:
            try:
                n.command('set_input', buttons='0xffff')
                n.command('render_pass_refuse', on=1)
                n.frames(4)
                n.command('quit')
            except (OSError, RuntimeError):
                pass
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                r['forced_cleanup'] = True
                proc.terminate()
                proc.wait(timeout=8)
            r.update(exit_code=proc.returncode, remaining_game_pids=n.game_pids(),
                     source_saves_unchanged=all(n.digest(Path(k)) == v for k, v in hashes.items()),
                     preferences_unchanged=p.hash_existing(pref_paths) == prefs)
            r['complete'] = bool(r['complete'] and proc.returncode == 0 and not r.get('forced_cleanup')
                                 and not r['remaining_game_pids'] and r['source_saves_unchanged']
                                 and r['preferences_unchanged'])
            (out/'receipt.json').write_text(json.dumps(r, indent=2)+'\n')
    print(json.dumps({k: r.get(k) for k in ('complete', 'fresh_pairs_s', 'exit_code')}))
    if not r['complete']:
        raise RuntimeError('Probe incomplete; inspect receipt')


if __name__ == '__main__':
    main()
