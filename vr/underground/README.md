# Underground VR Adapter

This directory owns title-specific engine bindings for Medal of Honor:
Underground. It is intentionally not compiled into the current flat
`psx-runtime` target.

`engine_map.c` contains mappings that have both:

- matching normalized instruction shape across the source and target functions;
- a specific target overlay capture hash;
- observed execution in the loaded Underground gameplay capture.

The map does not register hooks. A later adapter must verify the game ID,
overlay hash, function bytes, and caller contract before activation. The flat
launcher and existing executable must continue to work without any VR state.

Current confirmed mappings:

| Role | Reference | Underground | Evidence |
| --- | --- | --- | --- |
| Entity transform | `0x80084718` | `0x80093830` | 41/41 opcodes, live execution |
| Entity node transformer | `0x80013AE4` | `0x80013B40` | 221/221 opcodes, live call ring |
| GTE RT/TR loader | `0x80013E58` | `0x80013EB4` | Byte-identical, live call ring |
| Level vertex transformer | `0x8008B3E8` | `0x80099960` | 710/710 opcodes, 12 RTPS, live execution |
| Gameplay render wait | `0x80090B80` | `0x8009D828` | 110/110 opcodes, live execution |

Executable/overlay and function SHA-256 values are recorded in `engine_map.c`
so future hooks can fail closed instead of trusting an address alone.
