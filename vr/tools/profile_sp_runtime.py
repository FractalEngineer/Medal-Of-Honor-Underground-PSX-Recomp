"""Measure matched production/debug stereo cadence without a headset.

Reuses framework stereo proof counters and the first-game quiet-window workflow.
This no-XR, native-hand-fallback control measures build overhead, not physical
tracked performance. Captures no screenshots and never enables VERIFY.
"""
import argparse
import sys,json,subprocess,time,threading,re,ctypes,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'vr/tools'))
import inspect_weapon_sets as n
import probe_p38_headset as p


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('out',type=Path)
    a.add_argument('--source',type=Path,default=ROOT/'analysis/vr-baseline/saves')
    a.add_argument('--slot',type=int,default=3)
    a.add_argument('--seconds',type=int,default=32)
    args=a.parse_args()
    if not 25<=args.seconds<=60:raise ValueError('seconds must be 25..60')
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
    env.update(PSX_OPENXR_ENABLE='0',PSX_LOAD_SLOT=str(args.slot),PSX_RENDER_PASS_VERIFY='0',PSX_RUNTIME_PERF_DIAG='1',PSX_RUNTIME_PERF_DIAG_MS='1000',PSX_FRAME_REPORT_MS='1000',SDL_AUDIODRIVER='dummy')
    exe=ROOT/'build-release/Medal_of_Honor_Underground_Recompiled.exe'
    r=dict(schema=1,binary_sha256=n.digest(exe),build=p.build_configuration(ROOT/'build-release/CMakeCache.txt'),environment={k:v for k,v in env.items() if k.startswith(('MOHU','PSX','SDL_AUDIO'))},source_hashes=hashes,headset_acceptance=False,mode='hidden SDL window, no XR, native fallback hand; matched build-overhead control',samples=[])
    with (out/'stdout.log').open('w') as log,(out/'stderr.log').open('w') as err:
     start=time.monotonic()
     proc=subprocess.Popen([str(exe),'--hidden-window','--no-launcher','--game',str(ROOT/'analysis/vr-baseline/game-interp.toml'),'--memcard-dir',str(out/'saves')],cwd=out,env=env,stdout=subprocess.PIPE,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
     def reader():
      for raw in iter(proc.stdout.readline,b''):
       line=raw.decode('utf-8',errors='replace');log.write(line);log.flush()
       m=re.search(r'stereo_proof attempt=(\d+) pairs=(\d+) rendered=(\d+)',line)
       if m:r['samples'].append(dict(seconds=time.monotonic()-start,attempts=int(m[1]),pairs=int(m[2]),rendered=int(m[3])))
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
      r['source_saves_unchanged']=all(n.digest(Path(k))==v for k,v in hashes.items())
      r['preferences_unchanged']=p.hash_existing(p.preference_paths())==prefs
      r['complete']=bool(proc.returncode==0 and not r.get('forced_cleanup') and len(quiet)>1 and not r['remaining_game_pids'] and r['source_saves_unchanged'] and r['preferences_unchanged'])
      (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r.get(k) for k in ('complete','exit_code','forced_cleanup','quiet_pairs_per_second')}))
    if not r['complete']:raise RuntimeError('Profile transport/cadence incomplete; inspect receipt')


if __name__ == '__main__':
    main()
