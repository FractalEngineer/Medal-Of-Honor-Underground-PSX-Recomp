"""Measure matched production/debug stereo cadence without a headset.

Reuses framework stereo proof counters and the first-game quiet-window workflow.
This no-XR, native-hand-fallback control measures build overhead, not physical
tracked performance. Captures no screenshots and never enables VERIFY.
"""
import argparse
import sys,json,subprocess,time,threading,re,ctypes,shutil,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'vr/tools'))
import inspect_weapon_sets as n
import probe_p38_headset as p


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('out',type=Path)
    a.add_argument('--source',type=Path,default=ROOT/'analysis/fixtures/sp')
    a.add_argument('--slot',type=int,default=3)
    a.add_argument('--seconds',type=int,default=32)
    a.add_argument('--config',type=Path,default=ROOT/'analysis/vr-baseline/game-interp.toml')
    a.add_argument('--bench-window',default='300:900')
    a.add_argument('--require-native',action='store_true')
    a.add_argument('--canonical-only',action='store_true',
                   help='Disable stereo/hand paths: measure native canonical cadence only')
    args=a.parse_args()
    if not 25<=args.seconds<=60:raise ValueError('seconds must be 25..60')
    config=args.config.resolve()
    if not config.is_file():raise ValueError(f'game config not found: {config}')
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    saves=out/'saves/openbios';saves.mkdir(parents=True)
    source=list((args.source/'openbios').glob(f'*slot{args.slot:02}.*'))
    assert len(source)==2,source
    hashes={str(x):n.digest(x) for x in source}
    for x in source:shutil.copyfile(x,saves/x.name)
    prefs=p.hash_existing(p.preference_paths())
    assert not n.game_pids()
    env=p.environment('tracked',False,runtime_manifest=Path('unused'),hand_fixed=True)
    for key in ('MOHU_VR_MP_CONTROL','MOHU_VR_MP_FRUSTUM','XR_RUNTIME_JSON','MOHU_VR_OPENXR'):
     env.pop(key,None)
    if args.canonical_only:
     for key in ('MOHU_VR_STEREO_PROOF','MOHU_VR_EYE_RENDER_VIEW','MOHU_VR_EYE_GUEST_SUBMIT','MOHU_VR_EYE_OFFSET',
                 'MOHU_VR_WEAPON_POSE','MOHU_VR_WEAPON_CALIBRATED','MOHU_VR_WEAPON_AIM','MOHU_VR_WEAPON_GUN_ONLY',
                 'MOHU_VR_P38_CALIBRATED','MOHU_VR_P38_AIM','PSX_VR_MOVEMENT','PSX_VR_HEAD_FRUSTUM',
                 'PSX_VR_SUPPRESS_FLAT_HUD','PSX_VR_LASER','PSX_VR_WEAPON_POSE'):
      env.pop(key,None)
    env.update(PSX_OPENXR_ENABLE='0',PSX_LOAD_SLOT=str(args.slot),PSX_RENDER_PASS_VERIFY='0',PSX_RUNTIME_PERF_DIAG='1',PSX_RUNTIME_PERF_DIAG_MS='1000',PSX_FRAME_REPORT_MS='1000',PSX_INTERNAL_RESOLUTION='1080p',PSX_BENCH_WINDOW=args.bench_window,SDL_AUDIODRIVER='dummy')
    exe=ROOT/'build-release/Medal_of_Honor_Underground_Recompiled.exe'
    r=dict(schema=1,binary_sha256=n.digest(exe),config=str(config.relative_to(ROOT)),config_sha256=n.digest(config),build=p.build_configuration(ROOT/'build-release/CMakeCache.txt'),environment={k:v for k,v in env.items() if k.startswith(('MOHU','PSX','SDL_AUDIO'))},source_hashes=hashes,headset_acceptance=False,mode=('hidden SDL window, no XR, canonical native only; stereo/hand paths disabled' if args.canonical_only else 'hidden SDL window, no XR, native fallback hand; matched build-overhead control'),canonical_only=args.canonical_only,require_native=args.require_native,samples=[],cadence_samples=[])
    with (out/'stdout.log').open('w') as log,(out/'stderr.log').open('w') as err:
     start=time.monotonic()
     proc=subprocess.Popen([str(exe),'--hidden-window','--no-launcher','--game',str(config),'--memcard-dir',str(out/'saves')],cwd=out,env=env,stdout=subprocess.PIPE,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
     def reader():
      for raw in iter(proc.stdout.readline,b''):
       line=raw.decode('utf-8',errors='replace');log.write(line);log.flush()
       m=re.search(r'stereo_proof attempt=(\d+) pairs=(\d+) rendered=(\d+)',line)
       if m:r['samples'].append(dict(seconds=time.monotonic()-start,attempts=int(m[1]),pairs=int(m[2]),rendered=int(m[3])))
       m=re.search(r'\[BENCH\] window=(\d+):(\d+) frames=(\d+) wall_ms=([0-9.]+) guest_work_ms=([0-9.]+) pacer_ms=([0-9.]+) autocapture_main_ms=([0-9.]+) provider_poll_ms=([0-9.]+) dirty_insns=\+([0-9]+) dirty_dispatches=\+([0-9]+) overlay_native=\+([0-9]+) overlay_interp=\+([0-9]+) overlay_loads=\+([0-9]+)',line)
       if m:r['bench']=dict(window_start=int(m[1]),window_end=int(m[2]),frames=int(m[3]),wall_ms=float(m[4]),guest_work_ms=float(m[5]),pacer_ms=float(m[6]),autocapture_main_ms=float(m[7]),provider_poll_ms=float(m[8]),dirty_insns=int(m[9]),dirty_dispatches=int(m[10]),overlay_native=int(m[11]),overlay_interp=int(m[12]),overlay_loads=int(m[13]))
       m=re.search(r'runtime cadence: guest=([0-9.]+) Hz.*?cpu=([0-9.]+) tex=([0-9.]+) draw=([0-9.]+) ms/s; work guest=([0-9.]+) pacer=([0-9.]+) autocapture=([0-9.]+) provider_poll=([0-9.]+) ms/s, dirty=([0-9]+) insn/s ([0-9]+) dispatch/s; overlay native=\+([0-9]+) interp=\+([0-9]+).*?loads=\+([0-9]+)',line)
       if m:r['cadence_samples'].append(dict(seconds=time.monotonic()-start,guest_hz=float(m[1]),gl_cpu_ms_s=float(m[2]),gl_tex_ms_s=float(m[3]),gl_draw_ms_s=float(m[4]),guest_work_ms_s=float(m[5]),pacer_ms_s=float(m[6]),autocapture_ms_s=float(m[7]),provider_poll_ms_s=float(m[8]),dirty_insn_s=int(m[9]),dirty_dispatch_s=int(m[10]),overlay_native=int(m[11]),overlay_interp=int(m[12]),overlay_loads=int(m[13])))
     thread=threading.Thread(target=reader);thread.start()
     try:
      deadline=start+args.seconds
      while time.monotonic()<deadline and proc.poll() is None:time.sleep(.1)
     finally:
      user32=ctypes.windll.user32
      callback_type=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
      def close(hwnd,unused):
       pid=ctypes.c_ulong();user32.GetWindowThreadProcessId(ctypes.c_void_p(hwnd),ctypes.byref(pid))
       if pid.value==proc.pid:user32.PostMessageW(ctypes.c_void_p(hwnd),0x0010,0,0)
       return True
      cb=callback_type(close);user32.EnumWindows(cb,0)
      try:proc.wait(timeout=10)
      except subprocess.TimeoutExpired:r['forced_cleanup']=True;proc.terminate();proc.wait(timeout=8)
      thread.join(timeout=5)
      r['exit_code']=proc.returncode
      r['remaining_game_pids']=n.game_pids()
      quiet=[x for x in r['samples'] if 8<=x['seconds']<=args.seconds-2]
      r['quiet_samples']=quiet
      if len(quiet)>1:r['quiet_pairs_per_second']=(quiet[-1]['pairs']-quiet[0]['pairs'])/(quiet[-1]['seconds']-quiet[0]['seconds'])
      cadence=[x for x in r['cadence_samples'] if 8<=x['seconds']<=args.seconds-2]
      r['quiet_cadence']=dict(samples=len(cadence),
          guest_hz=statistics.mean(x['guest_hz'] for x in cadence) if cadence else None,
          guest_work_ms_s=statistics.mean(x['guest_work_ms_s'] for x in cadence) if cadence else None,
          pacer_ms_s=statistics.mean(x['pacer_ms_s'] for x in cadence) if cadence else None)
      r['overlay_native_calls']=sum(x['overlay_native'] for x in r['cadence_samples'])
      r['overlay_interp_calls']=sum(x['overlay_interp'] for x in r['cadence_samples'])
      r['overlay_loads']=sum(x['overlay_loads'] for x in r['cadence_samples'])
      r['source_saves_unchanged']=all(n.digest(Path(k))==v for k,v in hashes.items())
      r['preferences_unchanged']=p.hash_existing(p.preference_paths())==prefs
      native_ok=not args.require_native or (
          r['overlay_native_calls']>0 and
          bool(r.get('bench')) and r['bench']['overlay_native']>0)
      if args.canonical_only:
       r['complete']=bool(proc.returncode==0 and not r.get('forced_cleanup') and len(cadence)>1
           and bool(r.get('bench')) and not r['remaining_game_pids']
           and r['source_saves_unchanged'] and r['preferences_unchanged'])
      else:
       r['complete']=bool(proc.returncode==0 and not r.get('forced_cleanup') and len(quiet)>1 and bool(r.get('bench')) and not r['remaining_game_pids'] and r['source_saves_unchanged'] and r['preferences_unchanged'] and native_ok)
      (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r.get(k) for k in ('complete','exit_code','forced_cleanup','canonical_only','quiet_pairs_per_second','quiet_cadence')}))
    if not r['complete']:raise RuntimeError('Profile transport/cadence incomplete; inspect receipt')


if __name__ == '__main__':
    main()
