"""Copied-save native HUD capture/fire/reload/pause/load checks; no XR runtime.

Launch outside the sandbox. Dual-matte/native-art checks follow the reference
verify_native_hud.py; actual surface upload/fallback is checked by test_hud.c.
"""
import argparse
import json
from pathlib import Path
import shutil
import socket
import subprocess
import time

import numpy as np
from PIL import Image
import inspect_weapon_sets as n
import probe_p38_headset as p

ROOT=Path(__file__).resolve().parents[2]
REGIONS=((8,8,112,112),(368,8,136,40))

def hud(args='status'):
    r=n.command('mod_cmd',name='mohu.vr.hud',args=args)
    if r['result']!=1:raise RuntimeError(r)
    return json.loads(r['reply'])

def verify(directory):
    black=np.frombuffer((directory/'hud-black.rgba').read_bytes(),np.uint8).reshape(240,512,4)[:,:,:3].astype(int)
    white=np.frombuffer((directory/'hud-white.rgba').read_bytes(),np.uint8).reshape(240,512,4)[:,:,:3].astype(int)
    results=[];union=np.zeros((240,512),bool)
    for name,(x,y,w,h) in zip(('left','right'),REGIONS):
        rgba=np.frombuffer((directory/f'hud-{name}.rgba').read_bytes(),np.uint8).reshape(h,w,4)[::-1].astype(int)
        union[y:y+h,x:x+w]=True;a=rgba[:,:,3:4]
        on_black=(rgba[:,:,:3]*a+127)//255
        on_white=(rgba[:,:,:3]*a+int(white[0,0,0])*(255-a)+127)//255
        error=max(int(abs(on_black-black[y:y+h,x:x+w]).max()),int(abs(on_white-white[y:y+h,x:x+w]).max()))
        covered=int((a>128).sum());transparent=int((a==0).sum())
        Image.fromarray(rgba.astype(np.uint8)).save(directory/f'hud-{name}.png')
        if error>2 or covered<(5 if name=='right' else 50) or not transparent:
            raise RuntimeError(dict(side=name,error=error,covered=covered,transparent=transparent))
        results.append(dict(side=name,covered=covered,transparent=transparent,error=error))
    for name,data in (('black',black),('white',white)):
        Image.fromarray(data.astype(np.uint8)).save(directory/f'hud-{name}.png')
    alpha=255*(1-(white-black).mean(axis=2)/int(white[0,0,0]))
    outside=int(np.count_nonzero((alpha>2)&~union))
    if outside:raise RuntimeError(f'Unowned captured content: {outside} pixels')
    return dict(panels=results,outside_pixels=outside)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('out',type=Path)
    ap.add_argument('--mode',choices=('sp','mp'),default='sp')
    ap.add_argument('--headless-xr',action='store_true',help='Restore-protected SteamVR null HMD; never a physical headset')
    args=ap.parse_args();mp=args.mode=='mp';slot=1 if mp else 3
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    if n.game_pids():raise RuntimeError('Close existing game before owned HUD probe')
    with socket.socket() as sock:sock.bind(('127.0.0.1',4372))
    src=ROOT/('analysis/fixtures/mp/openbios' if mp else 'analysis/fixtures/sp/openbios');dst=out/'saves/openbios';dst.mkdir(parents=True)
    paths=list(src.glob(f'*slot{slot:02}.*'));assert len(paths)==2
    hashes={str(f):n.digest(f) for f in paths}
    for f in paths:shutil.copyfile(f,dst/f.name)
    prefs=p.hash_existing(p.preference_paths());exe=ROOT/'build-release/Medal_of_Honor_Underground_Recompiled.exe'
    env=p.environment('tracked',True,hand_fixed=True)
    env.update(PSX_RENDER_PASS_VERIFY='1',PSX_INTERNAL_RESOLUTION='native',
               PSX_VR_WRIST_HUD='1',MOHU_VR_MP_CONTROL=str(int(mp)),MOHU_VR_MP_FRUSTUM=str(int(mp)),SDL_AUDIODRIVER='dummy',MOHU_VR_UNITS_PER_METER='238.80597014925373')
    r=dict(schema=1,mode=args.mode,headless_xr=args.headless_xr,complete=False,headset_acceptance=False,binary_sha256=n.digest(exe),source_hashes=hashes,build=p.build_configuration(ROOT/'build-release/CMakeCache.txt'),environment={k:v for k,v in env.items() if k.startswith(('MOHU_','PSX_'))})
    def state():
        actor=int.from_bytes(n.read(0x800A3604 if mp else 0x800AA17C,4),'little');inp=int.from_bytes(n.read(actor+0x39c,4),'little')
        assert inp==actor+(0x400 if mp else 0x3fc)
        return dict(actor=actor,input=inp,weapon=n.read(inp+93,1)[0],
                    clip=n.read(inp+(0x720 if mp else 0x110),4).split(b'\0')[0].decode('ascii'),
                    reserve=n.read(inp+(0x724 if mp else 0x114),4).split(b'\0')[0].decode('ascii'))
    def capture(name):
        d=out/name;d.mkdir();n.frames(4);r[name]=dict(state=state(),status=hud())
        hud('dump='+d.as_posix());r[name]['art']=verify(d)
        assert r[name]['status']['ready']==3,r[name]
        assert r[name]['status']['replacement']==(3 if args.headless_xr else 0)
        if args.headless_xr:
            r[name]['xr']=n.command('openxr_stats')
            assert r[name]['xr']['submitted_surfaces']==2,r[name]['xr']
        n.command('screenshot_hires',path=str(d/'native.png'))
        return r[name]['state']
    def press(**values):
        n.command('openxr_input_override',**values);n.frames(6)
        n.command('openxr_input_override',clear=1);n.frames(4)
    with (out/'stdout.log').open('w') as so,(out/'stderr.log').open('w') as se:
        launch=[str(exe),'--headless-opengl','--no-launcher','--game',str(ROOT/'game.toml'),'--memcard-dir',str(out/'saves'),'--debug-port','4372']
        if args.headless_xr:
            env.pop('XR_RUNTIME_JSON',None)
            launch=['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'vr/run_vr.ps1'),'-Headless','-Slot',str(slot),'-GameConfig',str(ROOT/'game.toml'),'-MemcardDirectory',str(out/'saves'),'-DebugPort','4372','-LogDirectory',str(out),'-InternalResolution','native','-NoLaser','-Seconds','60']
        proc=subprocess.Popen(launch,cwd=out,env=env,stdout=so,stderr=se,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            p.wait_for_ping(proc)
            if args.headless_xr:
                deadline=time.monotonic()+45
                while not (out/'openxr-smoke.json').exists():
                    if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Null-HMD startup failed')
                    time.sleep(.2)
                r['startup']=json.loads((out/'startup.json').read_text(encoding='utf-8-sig'))
            n.load(slot);p.release_load_override();p.set_desktop_hands()
            if args.headless_xr:n.command('openxr_hands_override',hand='left',pose='grip',active=1,flags=15,px_mm=-180,py_mm=-180,pz_mm=-450,qw=1000000)
            n.frames(8)
            before=capture('loaded');n.command('set_input',buttons='0xbfff');n.frames(3)
            n.command('set_input',buttons='0xffff');n.frames(14);fired=capture('fired')
            assert int(fired['clip'])<int(before['clip']),(before,fired)
            n.command('set_input',buttons='0x7fff');n.frames(3);n.command('set_input',buttons='0xffff');n.frames(60)
            reloaded=capture('reloaded');assert int(reloaded['clip'])>int(fired['clip']),(fired,reloaded)
            p.release_load_override()
            press(left_buttons=4);n.frames(25)
            r['paused']=hud();assert r['paused']['ready']==r['paused']['replacement']==0
            press(right_buttons=1);n.frames(20)
            capture('resumed');n.load(slot);p.release_load_override();n.frames(8)
            restored=capture('save-reloaded');assert restored==before,(before,restored)
            if args.headless_xr:
                for hand,expected in (('left',2),('right',0)):
                    n.command('openxr_hands_override',hand=hand,pose='grip',active=0);n.frames(6)
                    r[hand+'-lost']=hud();assert r[hand+'-lost']['replacement']==expected
                for hand,x in (('left',-180),('right',180)):
                    n.command('openxr_hands_override',hand=hand,pose='grip',active=1,flags=15,px_mm=x,py_mm=-180,pz_mm=-450,qw=1000000)
                n.frames(6);r['recovered']=hud();assert r['recovered']['replacement']==3
                n.command('openxr_hands_override',hand='left',pose='grip',focused=0);n.frames(6)
                r['focus-lost']=hud();assert r['focus-lost']['replacement']==0
                n.command('openxr_hands_override',hand='left',pose='grip',focused=1);n.frames(6)
            r['restoration']=n.command('render_pass_stats');r['stereo']=n.command('stereo_stats')
            assert r['restoration']['verify_checks']>0 and r['restoration']['verify_mismatch']==0
            assert r['stereo']['pairs']>0 and r['stereo']['failed']==0
            r['complete']=True
        except Exception as e:r['error']=str(e);raise
        finally:
            try:n.command('set_input',buttons='0xffff');n.command('render_pass_refuse',on=1);n.frames(3);n.command('quit')
            except Exception as e:r['quit_error']=str(e)
            try:proc.wait(timeout=40 if args.headless_xr else 15)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait();r['forced']=True
            r.update(exit_code=proc.returncode,sources_unchanged=all(n.digest(Path(f))==h for f,h in hashes.items()),preferences_unchanged=p.hash_existing(p.preference_paths())==prefs)
            (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print({k:r[k] for k in ('complete','exit_code','sources_unchanged','preferences_unchanged')})

if __name__=='__main__':main()
