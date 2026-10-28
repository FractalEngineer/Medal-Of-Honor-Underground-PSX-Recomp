"""Read-only raw-image audit for the SP streaming regression; emits metadata only."""
import argparse
import hashlib
import json
import mmap
from pathlib import Path
import struct


def audit(path):
    with path.open('rb') as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as data:
        if len(data) % 2352:
            raise ValueError('Expected complete MODE2/2352 sectors')
        def sector(lba):
            if not 0 <= lba < len(data)//2352:
                raise ValueError('ISO extent outside image')
            return data[lba*2352+24:lba*2352+24+2048]
        pvd=sector(16)
        if pvd[:7] != b'\x01CD001\x01':
            raise ValueError('Expected ISO9660 primary volume')
        root=pvd[156:190]
        todo=[('',struct.unpack_from('<I',root,2)[0],struct.unpack_from('<I',root,10)[0])]
        seen=set();files=[]
        while todo:
            name,lba,size=todo.pop()
            if lba in seen:
                continue
            seen.add(lba)
            if len(seen)>4096 or size>16*1024*1024:
                raise ValueError('Unbounded ISO directory')
            directory=b''.join(sector(lba+i) for i in range((size+2047)//2048))
            offset=0
            while offset<size:
                length=directory[offset]
                if not length:
                    offset=(offset//2048+1)*2048
                    continue
                entry=directory[offset:offset+length];offset+=length
                if len(entry)<34 or len(entry)<33+entry[32]:
                    raise ValueError('Invalid ISO directory record')
                identifier=entry[33:33+entry[32]]
                if identifier in (b'\0',b'\1'):
                    continue
                child=name+'/'+identifier.decode('ascii')
                start=struct.unpack_from('<I',entry,2)[0]
                length=struct.unpack_from('<I',entry,10)[0]
                if entry[25]&2:
                    todo.append((child,start,length))
                else:
                    files.append((child,start,length))
        empty=[lba for lba in range(len(data)//2352)
               if data[lba*2352:(lba+1)*2352]==bytes(2352)]
        return dict(path=str(path.resolve()),bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),md5=hashlib.md5(data).hexdigest(),
            files=len(files),wholly_zero_raw_sectors=[dict(lba=lba,
                allocated_files=[name for name,start,size in files
                                 if start<=lba<start+(size+2047)//2048]) for lba in empty],
            source_modified=False,payload_recovered=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('bin',type=Path)
    ap.add_argument('--out',required=True,type=Path)
    args=ap.parse_args()
    result=audit(args.bin)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('sha256','md5','files')}))
    print('Wholly zero raw sectors:',len(result['wholly_zero_raw_sectors']))


if __name__=='__main__':main()
