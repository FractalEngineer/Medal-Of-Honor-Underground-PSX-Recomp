"""Offline host attribution for an owned SP diagnostic receipt.

DLL samples remain real work. System-module samples are labeled by module,
never called idle. Segment times exclude guest callees and dispatch overhead.
"""
import argparse
import bisect
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'psxrecomp/tools'))
import host_profile


def segment_summary(receipt):
    pairs = receipt['end']['pairs']-receipt['start']['pairs']
    if pairs <= 0:
        raise ValueError('No fresh pairs in the window')
    if any(len(receipt[k]) != 3 for k in ('native_profile_before','native_profile_after')):
        raise ValueError('Expected canonical and two eye scopes')
    rows = []
    for scope, (before, after) in enumerate(zip(
            receipt['native_profile_before'], receipt['native_profile_after'])):
        first, last = json.loads(before['reply']), json.loads(after['reply'])
        if not first.get('exclusive_cps_segments') or not last.get('exclusive_cps_segments'):
            raise ValueError('Expected exclusive CPS segment timing')
        if len(first['rows']) != len(last['rows']):
            raise ValueError('Segment set changed')
        for b, a in zip(first['rows'], last['rows']):
            if a['scope'] != scope or b['scope'] != scope or a['address'] != b['address']:
                raise ValueError('Segment scope/address changed')
            if a['us'] < b['us'] or a['calls'] < b['calls']:
                raise ValueError('Segment counters regressed')
            rows.append(dict(scope=scope, address=a['address'],
                calls=a['calls']-b['calls'], ms_per_pair=(a['us']-b['us'])/1000/pairs))
    addresses = sorted({r['address'] for r in rows})
    return dict(pairs=pairs, rows=rows, stereo_totals=sorted([
        dict(address=address, ms_per_pair=sum(r['ms_per_pair'] for r in rows
            if r['scope'] and r['address']==address)) for address in addresses
        ], key=lambda r: -r['ms_per_pair']),
        limitation='Diagnostic exclusive CPS segments, excluding dispatch; scope snapshots bracket the quiet window approximately')


def resolve_samples(receipt, nm, exe_override=None):
    profile = receipt['host_profile']
    modules = receipt['host_modules']
    base = int(profile['image_base'], 16)
    tables, totals = {}, {}
    for address, count in profile['top']:
        if int(address,16)==0:
            totals['(non-image pc)'] = totals.get('(non-image pc)',0)+count
            continue
        absolute = base+int(address,16)
        module = next((m for m in modules if m['base'] <= absolute < m['base']+m['size']), None)
        label = '(unresolved module)'
        if module:
            path = Path(module['path'])
            source = Path(exe_override) if exe_override and path.suffix.lower()=='.exe' else path
            label = path.name
            # Resolve game/runtime and cached native code only. System modules
            # retain their own names without pretending they are idle/waits.
            if path.is_relative_to(ROOT/'build-release') and source.is_file():
                if str(source) not in tables:
                    digest = hashlib.sha256(source.read_bytes()).hexdigest()
                    if path.suffix.lower()=='.exe' and digest != receipt['binary_sha256']:
                        raise ValueError('Executable changed since the sample window')
                    table = host_profile.symbols(nm, str(source))
                    tables[str(source)] = (table, [r[0] for r in table], digest)
                table, keys, _ = tables[str(source)]
                i = bisect.bisect_right(keys, absolute-module['base'])-1
                if i >= 0:
                    label += ':'+table[i][1]
        totals[label] = totals.get(label,0)+count
    return dict(samples=profile['samples'], binned_samples=sum(totals.values()),
        unbinned=profile['unbinned'],
        samples_outside_reported_top=profile['samples']-sum(totals.values()),
        modules=profile.get('modules',[]), functions=sorted([
            dict(name=name, samples=count, share=count/profile['samples'])
            for name,count in totals.items()], key=lambda r: -r['samples']),
        symbol_images={path: item[2] for path,item in tables.items()})


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('receipt', type=Path)
    ap.add_argument('--nm')
    ap.add_argument('--exe', type=Path, help='Preserved executable; must match the receipt SHA-256')
    ap.add_argument('--out', type=Path, required=True)
    args=ap.parse_args()
    receipt=json.loads(args.receipt.read_text())
    result={}
    if 'native_profile_before' in receipt:
        result['segments']=segment_summary(receipt)
    if 'host_modules' in receipt:
        result['host']=resolve_samples(receipt,host_profile.find_nm(args.nm),args.exe)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result.get('segments',{}).get('stereo_totals',[])))


if __name__=='__main__':
    main()
