"""Materialize the original packet CPS math with operation-level render timing.

No source/disc patch. The build-selected caller may use this ONLY in a frozen
render transaction. Preserve every architectural/PGXP operation, resume label,
callee and packet writer. The original generated body remains runnable.
"""
import argparse
from pathlib import Path


def kernel(text):
    start = text.index('\nvoid func_80010CF0(CPUState* cpu)\n{')
    end = text.index('\nvoid ', start+1)
    body = text[start:end]
    if 'Size: 1840 bytes' not in body or '0x80011008u' not in body:
        raise ValueError('Unexpected packet-builder contract')
    prefix = '''/* Derived at build time from the retained original packet body. */
#include "SLUS_012.70_decls.h"
#include "hle_gte.h"
#undef PSX_ENABLE_BLOCK_CYCLES
#define psx_cyc_load_word(c,a,r,m) ((c)->read_word(a))
#define psx_cyc_load_half(c,a,r,m) ((c)->read_half(a))
#define psx_cyc_load_byte(c,a,r,m) ((c)->read_byte(a))
#define psx_check_interrupts_at(c,a) ((void)0)
#define gte_execute psx_hle_gte_execute
'''
    return prefix + body.replace('void func_80010CF0(', 'void mohu_packet(', 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    output = kernel(args.source.read_text())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if not args.out.exists() or args.out.read_text() != output:
        args.out.write_text(output)


if __name__ == '__main__':
    main()
