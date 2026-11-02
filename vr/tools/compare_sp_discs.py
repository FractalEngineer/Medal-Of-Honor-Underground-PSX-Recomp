"""Read-only raw-sector and ISO-file comparison of two MODE2/2352 images."""
import argparse
import hashlib
import json
import mmap
from pathlib import Path
import struct


def files(data):
    def sector(lba):
        if not 0 <= lba < len(data)//2352:
            raise ValueError('ISO extent outside image')
        return data[lba*2352+24:lba*2352+2072]
    pvd=sector(16)
    if pvd[:7]!=b'\x01CD001\x01':raise ValueError('Not an ISO9660 image')
    entry=pvd[156:190]
    todo=[('',struct.unpack_from('<I',entry,2)[0],struct.unpack_from('<I',entry,10)[0])]
    seen=set();result={}
    while todo:
        name,lba,size=todo.pop()
        if lba in seen:continue
        seen.add(lba)
        if size>16*1024*1024 or len(seen)>4096:raise ValueError('Unbounded directory')
        contents=b''.join(sector(lba+i) for i in range((size+2047)//2048))
        offset=0
        while offset<size:
            length=contents[offset]
            if not length:offset=(offset//2048+1)*2048;continue
            e=contents[offset:offset+length];offset+=length
            if len(e)<34 or len(e)<33+e[32]:raise ValueError('Invalid directory')
            ident=e[33:33+e[32]]
            if ident in (b'\0',b'\1'):continue
            child=name+'/'+ident.decode('ascii')
            start=struct.unpack_from('<I',e,2)[0];length=struct.unpack_from('<I',e,10)[0]
            if e[25]&2:todo.append((child,start,length))
            else:result[child]=dict(lba=start,bytes=length)
    return result


def file_hash(data,record):
    digest=hashlib.sha256();remaining=record['bytes']
    for lba in range(record['lba'],record['lba']+(remaining+2047)//2048):
        size=min(remaining,2048);offset=lba*2352+24
        if offset+size>len(data):raise ValueError('File outside image')
        digest.update(data[offset:offset+size]);remaining-=size
    return digest.hexdigest()


def compare(first,second):
    with first.open('rb') as fa,second.open('rb') as fb,\
        mmap.mmap(fa.fileno(),0,access=mmap.ACCESS_READ) as a,\
        mmap.mmap(fb.fileno(),0,access=mmap.ACCESS_READ) as b:
        if len(a)!=len(b) or len(a)%2352:raise ValueError('Expected equal-size raw images')
        af,bf=files(a),files(b)
        changes=[];counts={k:0 for k in ('header','subheader','payload','edc_or_ecc')}
        for lba in range(len(a)//2352):
            sa=a[lba*2352:(lba+1)*2352];sb=b[lba*2352:(lba+1)*2352]
            if sa==sb:continue
            end=2348 if sb[15]==2 and sb[18]&0x20 else 2072
            fields=dict(header=sa[:16]!=sb[:16],subheader=sa[16:24]!=sb[16:24],
                payload=sa[24:end]!=sb[24:end],edc_or_ecc=sa[end:]!=sb[end:])
            for k,value in fields.items():counts[k]+=int(value)
            changes.append(dict(lba=lba,old_entirely_zero=not any(sa),
                                changed_regions=[k for k,value in fields.items() if value]))
        layout_equal=af==bf;file_changes=[];critical=[]
        for name in sorted(set(af)&set(bf)):
            ah,bh=file_hash(a,af[name]),file_hash(b,bf[name])
            record=dict(path=name,old=af[name]|{'sha256':ah},new=bf[name]|{'sha256':bh})
            if ah!=bh:file_changes.append(record)
            if name in ('/SYSTEM.CNF;1','/SLUS_012.70;1','/LEVEL.BIN;1','/LEVEL2P.BIN;1','/SHELL.BIN;1'):
                critical.append(record|{'payload_identical':ah==bh})
        return dict(first=str(first.resolve()),second=str(second.resolve()),bytes=len(a),
            first_sha256=hashlib.sha256(a).hexdigest(),second_sha256=hashlib.sha256(b).hexdigest(),
            bytes_identical=not changes,iso_layout_identical=layout_equal,
            files_first=len(af),files_second=len(bf),
            added_files=sorted(set(bf)-set(af)),removed_files=sorted(set(af)-set(bf)),
            changed_sectors=len(changes),changed_sector_regions=counts,sectors=changes,
            changed_logical_files=file_changes,critical_files=critical,
            note='ISO logical-file hashes cover 2048 user bytes per sector; Form-2 full payload differences are separately included in sector regions.',
            source_images_modified=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('first',type=Path);ap.add_argument('second',type=Path)
    ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    result=compare(args.first,args.second)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('bytes_identical','iso_layout_identical','changed_sectors','changed_sector_regions')}))
    print('Changed ISO logical files:',len(result['changed_logical_files']))
    print('Critical files:',[(f['path'],f['payload_identical']) for f in result['critical_files']])


if __name__=='__main__':main()
