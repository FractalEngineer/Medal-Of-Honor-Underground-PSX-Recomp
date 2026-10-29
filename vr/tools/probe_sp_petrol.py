"""Reproduce slot-3 SP petrol bomb visibility with one native weapon switch.

Copied fixture, synthetic hand, no firing or guest state edits. Launch unsandboxed.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time
import struct

import inspect_weapon_sets as n
import probe_p38_headset as p

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out', type=Path)
    ap.add_argument('--native', action='store_true', help='Unmodified native weapon pose control')
    args = ap.parse_args()
    if n.game_pids():
        raise RuntimeError('Close the current game before this owned probe')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    saves = out/'saves/openbios'
    saves.mkdir(parents=True)
    source = list((ROOT/'analysis/fixtures/sp/openbios').glob('*slot03.*'))
    assert len(source) == 2
    hashes = {str(f): n.digest(f) for f in source}
    for f in source:
        shutil.copyfile(f, saves/f.name)
    prefs = p.hash_existing(p.preference_paths())
    exe = ROOT/'build-release/Medal_of_Honor_Underground_Recompiled.exe'
    env = p.environment('native' if args.native else 'tracked', True, hand_fixed=True)
    env.update(MOHU_VR_MP_CONTROL='0', MOHU_VR_MP_FRUSTUM='0',
               PSX_INTERNAL_RESOLUTION='native', PSX_RENDER_PASS_VERIFY='1',
               MOHU_VR_UNITS_PER_METER='238.80597014925373')
    r = dict(complete=False, headset_acceptance=False, source_hashes=hashes,
             native=args.native, binary_sha256=n.digest(exe))
    def word(addr):
        return int.from_bytes(n.read(addr, 4), 'little')
    def capture(name):
        actor = word(0x800AA17C)
        assert 0x800B0000 <= actor <= 0x801FC000
        inp = word(actor+0x39c)
        assert inp == actor+0x3fc
        obj = word(actor+0x114)
        nodes_header = word(obj+0x80)
        count = word(nodes_header+4)
        assert count <= 32
        nodes = word(nodes_header)
        geometry = bytearray()
        node_rows = []
        for i in range(count):
            addr, vertices = struct.unpack('<2I', n.read(nodes+8*i, 8))
            assert vertices < 1024
            data = n.read(addr, vertices*8) if vertices else b''
            geometry.extend(struct.pack('<I', vertices)+data)
            node_rows.append(dict(address=addr, count=vertices))
        fnv = 2166136261
        for b in geometry:
            fnv = ((fnv ^ b)*16777619) & 0xffffffff
        r[name] = dict(actor=actor, input=inp, object=obj, id=n.read(inp+93, 1)[0],
                       magic=word(obj+0x70), faces=int.from_bytes(n.read(obj+0xb6, 2), 'little'),
                       geometry_fnv32=hex(fnv), nodes=node_rows, render=p.shot_command('render'),
                       counters=p.counter_values())
        n.command('screenshot_hires', path=str(out/f'{name}.png'))
        d = out/name
        d.mkdir()
        n.command('stereo_dump', path=d.as_posix(), count=2)
    with (out/'stdout.log').open('w') as so, (out/'stderr.log').open('w') as se:
        proc = subprocess.Popen([str(exe), '--headless-opengl', '--no-launcher', '--game', str(ROOT/'game.toml'),
            '--memcard-dir', str(out/'saves'), '--debug-port', '4372'], cwd=out, env=env,
            stdout=so, stderr=se, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            p.wait_for_ping(proc)
            n.load(3)
            p.release_load_override()
            p.set_desktop_hands()
            n.frames(8)
            capture('p38')
            n.switch()
            n.frames(8)
            capture('petrol')
            assert r['petrol']['id'] == 15, r['petrol']['id']
            if not args.native:
                r['visibility_passed'] = (
                    r['petrol']['render']['visible_gun_vertices'] == [99, 99]
                    and r['petrol']['render']['masked_arm_vertices'] == [97, 97]
                    and r['petrol']['counters'].get('mohu.vr.weapon.sp.project', 0)
                        > r['p38']['counters'].get('mohu.vr.weapon.sp.project', 0)
                    and r['petrol']['counters'].get('mohu.vr.weapon.sp.model_guard_fail', 0)
                        == r['p38']['counters'].get('mohu.vr.weapon.sp.model_guard_fail', 0))
            (out/'ram.bin').write_bytes(n.read(0x80000000, 0x200000))
            r['restoration'] = n.command('render_pass_stats')
            r['stereo'] = n.command('stereo_stats')
            r['complete'] = r['stereo']['failed'] == 0 and r['restoration']['verify_mismatch'] == 0
        finally:
            try:
                n.command('render_pass_refuse', on=1)
                n.frames(4)
                n.command('quit')
            except (OSError, RuntimeError):
                pass
            try:
                proc.wait(timeout=10)
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
    print(json.dumps({k: r.get(k) for k in ('complete', 'petrol')}))
    if not r['complete'] or (not args.native and not r['visibility_passed']):
        raise RuntimeError('Petrol visibility control incomplete; inspect receipt')


if __name__ == '__main__':
    main()
