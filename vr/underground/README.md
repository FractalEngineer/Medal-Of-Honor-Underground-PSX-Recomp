# Underground VR Adapter

This directory owns title-specific engine bindings for Medal of Honor:
Underground. It is intentionally not compiled into the current flat
`psx-runtime` target.

`engine_map.c` contains mappings that have both:

- matching normalized instruction shape across the source and target functions;
- a specific target overlay capture hash;
- observed execution in the loaded Underground gameplay capture.

The map itself does not register hooks. Its opt-in diagnostic consumer verifies
function bytes and logs entry registers. An additional transform probe is inert
unless `MOHU_VR_LEVEL_OFFSET_X` is set in the diagnostic build. The flat launcher
and existing executable must continue to work without any VR state.

Current confirmed mappings:

| Role | Reference | Underground | Evidence |
| --- | --- | --- | --- |
| Entity transform | `0x80084718` | `0x80093830` | 41/41 opcodes, live execution |
| Entity node transformer | `0x80013AE4` | `0x80013B40` | 221/221 opcodes, live call ring |
| GTE RT/TR loader | `0x80013E58` | `0x80013EB4` | Byte-identical, live call ring |
| Level vertex transformer | `0x8008B3E8` | `0x80099960` | 710/710 opcodes, 12 RTPS, live execution |
| Gameplay render wait | `0x80090B80` | `0x8009D828` | 110/110 opcodes, live execution |

Main-executable SHA-256 values and every function SHA-256/FNV-1a value are
recorded in `engine_map.c`. Whole overlay-capture hashes remain empty because
the capture windows change between sessions; function bytes are the stable
identity.

## Diagnostic build

The guard path is opt-in:

```powershell
cmake -S . -B build-vr-diagnostic `
  -DMOHU_VR_DIAGNOSTICS=ON `
  -DPSX_DEBUG_TOOLS=ON `
  -DPSX_OPENXR=OFF
```

`vr_diagnostic.c` registers function-entry hooks. On first entry it computes the
function's FNV-1a checksum in guest RAM and logs the entry registers only when
the checksum matches `engine_map.c`. A mismatch disables that binding.

The optional transform probe adds `MOHU_VR_LEVEL_OFFSET_X` to GTE TRX at the
level transformer once per draw span. It restores the saved TRX at the verified
gameplay render-wait entry. With the environment variable unset, the probe does
not alter GTE state.

The default build keeps `MOHU_VR_DIAGNOSTICS=OFF`, uses the existing
`mods/preloaded` catalog, and does not compile these sources.
