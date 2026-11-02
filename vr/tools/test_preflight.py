"""Build/run the standalone native-body preflight oracle; never launches a game."""
import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def oracle_source(text):
    match = re.search(r'\nvoid func_80011424\(CPUState\* cpu\)\n\{', text)
    if match is None:
        raise ValueError('Missing original preflight body')
    end = text.index('\nvoid ', match.end())
    body = text[match.start():end]
    if 'Size: 668 bytes' not in body or 'psx_mod_function_entry' in body:
        raise ValueError('Unexpected native preflight contract')
    return '#include "SLUS_012.70_decls.h"\n' + body.replace(
        'void func_80011424(', 'void oracle_preflight(', 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--cc', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    oracle = out/'oracle.c'
    oracle.write_text(oracle_source((ROOT/'generated/SLUS_012.70_full_00.c').read_text()))
    exe = out/'test_preflight.exe'
    subprocess.run([str(args.cc), '-std=c23', '-O2', '-UNDEBUG', '-DPSX_NO_DEBUG_TOOLS=1',
                    '-DPSX_PGXP=1', '-Wall', '-Wextra', '-Werror',
                    '-Wno-tautological-compare', '-Wno-unused-label',
                    '-I'+str(ROOT/'generated'), '-I'+str(ROOT/'psxrecomp/runtime/include'),
                    '-I'+str(ROOT/'vr/underground'), str(oracle),
                    str(ROOT/'vr/underground/preflight.c'),
                    str(ROOT/'vr/tests/test_preflight.c'), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    main()
