"""Validate pointer-free caller captures and summarize exact comparison coverage."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

SHADOW_SIZE = 48
RESULT_SIZE = 131*4 + 1024 + 322*SHADOW_SIZE
RECORD_SIZE = 16 + 3*RESULT_SIZE


def summarize(data):
    if len(data) < 16:
        raise ValueError('Truncated caller capture header')
    magic, size, shadow, count = struct.unpack_from('<4I', data)
    if (magic, size, shadow) != (0x50464831, RECORD_SIZE, SHADOW_SIZE) or not 1 <= count <= 4096:
        raise ValueError('Unsupported caller capture contract')
    if len(data) != 16+count*size:
        raise ValueError('Incomplete/trailing caller captures')
    results, winding, scopes, projection = Counter(), Counter(), Counter(), Counter()
    differences = []
    for i in range(count):
        offset = 16+i*size
        scope, flags, header, vertex = struct.unpack_from('<4I', data, offset)
        scopes[scope] += 1
        winding[(flags >> 13) & 7] += 1
        candidate = data[offset+16+RESULT_SIZE:offset+16+2*RESULT_SIZE]
        reference = data[offset+16+2*RESULT_SIZE:offset+16+3*RESULT_SIZE]
        if candidate != reference:
            differences.append(i)
        results[struct.unpack_from('<I', reference, 8)[0]] += 1
        for v in range(3):
            # Input homogeneous SXY provenance, not merely integer positions.
            base = offset+16+131*4+1024+(46+v)*SHADOW_SIZE
            projection[struct.unpack_from('<I', data, base+28)[0]] += 1
    return dict(checks=count, failed=len(differences), mismatch_records=differences,
                results=dict(sorted(results.items())), winding=dict(sorted(winding.items())),
                scopes=dict(scopes), input_projection_valid=dict(projection),
                capture_sha256=hashlib.sha256(data).hexdigest(),
                full_frame_performance=False, physical_acceptance=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = summarize(args.capture.read_bytes())
    text = json.dumps(result, indent=2)+'\n'
    if args.out:
        args.out.write_text(text)
    print(text)
    if result['failed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
