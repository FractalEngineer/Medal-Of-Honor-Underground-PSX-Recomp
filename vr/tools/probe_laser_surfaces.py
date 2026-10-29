"""Owned SP/MP desktop laser checks against independently decoded real surfaces.

No headset, source-save edits or guest health/ammo writes. Reuses the pause
probe's launch/input ownership and first-game triangle strategy. Bulk geometry
is retained only under the fresh analysis directory.
"""
import argparse
import json
import math
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import time

import numpy as np
import inspect_weapon_sets as n
import probe_p38_headset as p
import check_weapon_pose_spaces as pose

ROOT=Path(__file__).resolve().parents[2]


def decode_strip(data,count,vertex_count,base_bytes=16):
    """Independent native SP 8 / MP 16-byte base + 4-byte strip decoder."""
    triangles=[];cursor=0;indices=None
    while len(triangles)<count:
        if indices is None:
            if cursor+base_bytes>len(data):raise ValueError('Truncated base triangle')
            indices=[x&8191 for x in struct.unpack_from('<3H',data,cursor)]
            cursor+=base_bytes
        else:
            if cursor+4>len(data):raise ValueError('Truncated strip')
            code=struct.unpack_from('<H',data,cursor)[0];cursor+=4
            if code==8191:indices=None;continue
            indices=([indices[2],indices[1],code&8191] if code&32768
                     else [indices[1],indices[2],code&8191])
        if max(indices)>=vertex_count:raise ValueError('Out-of-range level index')
        triangles.append(indices)
    if cursor+4>len(data) or struct.unpack_from('<H',data,cursor)[0]!=8191:
        raise ValueError('Missing final strip terminator')
    return triangles,cursor+4


def nearest(triangles,origin,direction,maximum):
    # Plane intersection and barycentric coordinates, independently of C's
    # Moller-Trumbore implementation. Test every decoded surface, no PVS boxes.
    a=triangles[:,0];u=triangles[:,1]-a;v=triangles[:,2]-a
    normals=np.cross(u,v);denom=normals@direction
    with np.errstate(divide='ignore',invalid='ignore'):
        t=np.einsum('ij,ij->i',normals,a-origin)/denom
        w=origin+t[:,None]*direction-a
        uu=np.einsum('ij,ij->i',u,u);vv=np.einsum('ij,ij->i',v,v)
        uv=np.einsum('ij,ij->i',u,v);wu=np.einsum('ij,ij->i',w,u);wv=np.einsum('ij,ij->i',w,v)
        det=uu*vv-uv*uv
        b=(vv*wu-uv*wv)/det;c=(uu*wv-uv*wu)/det
    valid=(abs(denom)>1e-9)&(t>1e-3)&(t<=maximum)&(b>=-1e-8)&(c>=-1e-8)&(b+c<=1+1e-8)
    if not valid.any():return None
    ids=np.nonzero(valid)[0];i=int(ids[np.argmin(t[valid])])
    return dict(index=i,distance=float(t[i]),vertices=triangles[i].tolist(),barycentric=[float(b[i]),float(c[i])])


def command(args):
    r=n.command('mod_cmd',name='mohu.vr.laser',args=args)
    if r['result']!=1:raise RuntimeError(r)
    return json.loads(r['reply'])


def valid_pair():
    # Queries run on the debug thread. A replay clears each working result
    # before drawing, so an in-flight read is not a published invalid ray.
    deadline=time.monotonic()+3
    while time.monotonic()<deadline:
        eyes=[command(f'eye={i}') for i in range(2)]
        if all(e['valid'] for e in eyes) and all(
            np.max(abs(np.asarray(eyes[0][key])-eyes[1][key]))<1e-6
            for key in ('origin','direction')):
            return eyes
        time.sleep(.01)
    raise RuntimeError('No coherent valid laser pair within three seconds')


def geometry(mode,out,levels=None):
    ram=n.read(0x80000000,0x200000)
    def read(a,size):
        offset=a&0x1fffffff
        if not 0<=offset<=len(ram)-size:raise ValueError('Mesh outside captured RAM')
        return ram[offset:offset+size]
    def word(a):return int.from_bytes(read(a,4),'little')
    result=[];chunks=[]
    def mesh(table,count,lists,matrix=None,translation=None,base_bytes=8):
        raw=read(table,count*8)
        xyz=np.frombuffer(raw,dtype='<i2').reshape(-1,4)[:,:3].astype(float)
        for address,faces in lists:
            data=read(address,faces*20)
            indices,used=decode_strip(data,faces,count,base_bytes)
            tris=xyz[np.asarray(indices)]
            if matrix is not None:tris=tris@matrix.T+translation
            chunks.append(dict(table=table,count=count,list=address,faces=faces,bytes=used,
                               indices=indices,vertices=xyz.tolist(),
                               base_bytes=base_bytes,matrix=matrix.tolist() if matrix is not None else None,
                               translation=translation.tolist() if matrix is not None else None))
            result.extend(tris)
    def level_mesh(g):
            stack=[g['root']];seen=set();lists=[]
            while stack:
                a=stack.pop()
                if a in seen:raise ValueError('Cyclic level tree')
                seen.add(a);assert len(seen)<8192
                data=read(a,36);count=struct.unpack_from('<i',data,12)[0]
                if count:lists.append((struct.unpack_from('<I',data,24)[0],count))
                else:stack.extend(x for x in struct.unpack_from('<3I',data,24) if x)
            mesh(g['table'],g['count'],lists)
    if mode=='sp':
        if levels is None:
            levels=[]
            count=word(0x800a5384)
            if not 1<=count<=8:raise ValueError('Invalid native SP arena count')
            skip=word(0x800b749c)
            for i in range(count):
                if i==skip:continue
                record=0x800a57dc+i*0xc4
                levels.append(dict(root=word(word(record+8)+20),
                                   table=word(record+44),count=word(record+60)))
        for g in levels:level_mesh(g)
    else:
        for i in range(word(0x8009ECE4)):
            st=0x8009F13C+i*196;sub=word(st+8)
            level_mesh(dict(root=word(sub+20),table=word(st+44),count=word(st+60)))
        a=word(0x800A35CC);seen=set()
        while a:
            assert a not in seen and len(seen)<64;seen.add(a)
            data=read(a,0x388)
            if struct.unpack_from('<I',data,0x384)[0]==0x8006C61C and not struct.unpack_from('<I',data,12)[0]&1:
                obj=struct.unpack_from('<I',data,0x114)[0];m=read(obj,0xb8)
                matrix=np.asarray(struct.unpack_from('<9h',data,0x354),float).reshape(3,3)/4096
                tr=np.asarray(struct.unpack_from('<3i',data,0x368),float)
                mesh(struct.unpack_from('<I',m,0x2c)[0],struct.unpack_from('<I',m,0x3c)[0],
                     [(struct.unpack_from('<I',m,0xb0)[0],struct.unpack_from('<H',m,0xb4)[0])],matrix,tr,16)
            a=struct.unpack_from('<I',data,4)[0]
    (out/'geometry.json').write_text(json.dumps(chunks)+'\n')
    return np.asarray(result)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('out',type=Path)
    ap.add_argument('--mode',choices=('sp','mp'),required=True)
    ap.add_argument('--switch',type=int,choices=range(4),default=0)
    ap.add_argument('--skip-shot',action='store_true')
    args=ap.parse_args()
    assert not n.game_pids(),'Close existing game first'
    with socket.socket() as s:s.bind(('127.0.0.1',4372))
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    slot=3 if args.mode=='sp' else 1
    source=ROOT/('analysis/fixtures/sp' if args.mode=='sp' else 'analysis/fixtures/mp')/'openbios'
    target=out/'saves/openbios';target.mkdir(parents=True)
    hashes={str(f):n.digest(f) for f in source.glob(f'*slot{slot:02}.*')}
    for f in hashes:shutil.copyfile(f,target/Path(f).name)
    prefs=p.hash_existing(p.preference_paths());exe=ROOT/'build-release/Medal_of_Honor_Underground_Recompiled.exe'
    env=p.environment('tracked',True,hand_fixed=True)
    env.update(PSX_RENDER_PASS_VERIFY='1',PSX_INTERNAL_RESOLUTION='native',PSX_VR_LASER='1',
               MOHU_VR_UNITS_PER_METER='238.80597014925373',SDL_AUDIODRIVER='dummy')
    if args.mode=='sp':env.update(MOHU_VR_MP_CONTROL='0',MOHU_VR_MP_FRUSTUM='0')
    r=dict(mode=args.mode,complete=False,headset_used=False,binary_sha256=n.digest(exe),cases=[])
    with (out/'stdout.log').open('w') as so,(out/'stderr.log').open('w') as se:
        proc=subprocess.Popen([str(exe),'--headless-opengl','--no-launcher','--game',str(ROOT/'game.toml'),
            '--memcard-dir',str(out/'saves'),'--debug-port','4372'],cwd=out,env=env,stdout=so,stderr=se,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            p.wait_for_ping(proc);n.load(slot);p.release_load_override();p.set_desktop_hands()
            for _ in range(args.switch):n.switch()
            n.command('openxr_input_override',right_squeeze=1000);n.frames(8)
            first=command('eye=0');r['first']=first
            assert first['valid'],first
            tris=geometry(args.mode,out);r['triangles']=len(tris)
            for yaw,pitch,head in ((0,0,0),(-30,0,0),(30,0,0),(0,0,45),
                                   (0,45,0),(-30,45,0),(30,45,0),(0,-75,0)):
                pose.set_head(yaw_mdeg=head*1000)
                sy,cy=math.sin(math.radians(yaw)/2),math.cos(math.radians(yaw)/2)
                sp,cp=math.sin(math.radians(pitch)/2),math.cos(math.radians(pitch)/2)
                pose.set_hand_pair(grip=(.15,-.15,-.4),aim=(.15,-.15,-.45),
                                   aim_q=(cy*sp,sy*cp,-sy*sp,cy*cp))
                n.command('openxr_input_override',right_squeeze=1000);n.frames(6)
                eyes=valid_pair()
                for eye in eyes:
                    assert eye['valid'],eye
                    hit=nearest(tris,np.asarray(eye['origin']),np.asarray(eye['direction']),50*238.80597014925373)
                    assert bool(hit)==bool(eye['hit']),(eye,hit)
                    if hit:assert abs(hit['distance']-eye['distance'])<1e-5,(eye,hit)
                    eye['independent']=hit
                assert np.max(abs(np.asarray(eyes[0]['origin'])-eyes[1]['origin']))<1e-6
                assert np.max(abs(np.asarray(eyes[0]['direction'])-eyes[1]['direction']))<1e-6
                r['cases'].append(dict(yaw=yaw,pitch=pitch,head=head,eyes=eyes))
                n.command('screenshot_hires',path=str(out/f'head-{head}-hand-{yaw}-{pitch}.png'))
            assert sum(c['eyes'][0]['hit'] for c in r['cases'])>=3
            # One native MP projectile must use precisely the previewed ray.
            # Recoil may move the visual flash/mesh, never this fixed affine.
            if args.mode=='mp' and not args.skip_shot:
                pose.set_head();p.set_desktop_hands()
                n.command('openxr_input_override',right_squeeze=1000);n.frames(6)
                before=command('eye=0');p.shot_command('start')
                n.command('openxr_input_override',right_squeeze=1000,right_trigger=1000)
                n.frames(10)
                n.command('openxr_input_override',right_squeeze=1000);n.frames(4)
                after=command('eye=0');status=p.shot_command('status')
                shots=[p.shot_command(f'read={i}') for i in range(status['count'])]
                aimed=[s for s in shots if s.get('aimed') and s.get('hand_fixed')]
                assert aimed,'No actual hand-fixed native projectile captured'
                for shot in aimed:
                    assert shot['weapon_control']==before['control']==after['control']
                    assert max(abs(np.asarray(shot['aimed_position'])/65536-np.asarray(before['origin'])))<2e-5
                    pitch,yaw,_=np.asarray(shot['aimed_angles'],float)/65536*2*np.pi/4096
                    direction=np.array([math.sin(yaw)*math.cos(pitch),-math.sin(pitch),math.cos(yaw)*math.cos(pitch)])
                    assert np.dot(direction,before['direction'])>.999999
                r['native_shot_shared_ray']=dict(before=before,after=after,shots=aimed)
                p.shot_command('stop')
            # Tracking loss and grip release must remove the laser immediately.
            pose.set_hand_pair(focused=0);n.frames(6);r['lost']=command('eye=0');assert not r['lost']['valid']
            p.set_desktop_hands();n.command('openxr_input_override',right_squeeze=0);n.frames(6)
            r['released']=command('eye=0');assert not r['released']['valid']
            r['stereo']=n.command('stereo_stats');r['restoration']=n.command('render_pass_stats')
            assert r['stereo']['failed']==0 and r['restoration']['verify_mismatch']==0
            r['complete']=True
        finally:
            try:n.command('render_pass_refuse',on=1);n.frames(4);n.command('quit')
            except (OSError,RuntimeError):pass
            try:proc.wait(timeout=15)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait();r['forced_cleanup']=True
            r.update(exit_code=proc.returncode,sources_unchanged=all(n.digest(Path(f))==h for f,h in hashes.items()),preferences_unchanged=p.hash_existing(p.preference_paths())==prefs)
            r['complete']=bool(r['complete'] and proc.returncode==0 and not r.get('forced_cleanup') and r['sources_unchanged'] and r['preferences_unchanged'])
            (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
    if not r['complete']:raise RuntimeError('Laser control failed')
    print(f"PASS: {args.mode} exact laser versus {len(tris)} independently decoded triangles")


if __name__=='__main__':main()
