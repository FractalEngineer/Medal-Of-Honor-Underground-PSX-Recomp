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

The same-checkpoint stereo control supports a complete per-eye render view:

```powershell
$env:MOHU_VR_STEREO_PROOF = '1'
$env:MOHU_VR_EYE_RENDER_VIEW = '1'
$env:MOHU_VR_EYE_GUEST_SUBMIT = '1'
$env:MOHU_VR_EYE_OFFSET = '24'
```

It replays the guarded frame render at `0x80053BB4`, builds a full
`PSXModRenderView` from the guest projection, and submits the regenerated list
through guarded guest `DrawOTag`. Guest TR registers are not modified. With
`MOHU_VR_EYE_OFFSET=0` and the same seam enabled, the pair is byte-identical.

`MOHU_VR_EYE_YAW_MDEG`, `MOHU_VR_EYE_PITCH_MDEG`, and
`MOHU_VR_EYE_HEAD_{X,Y,Z}_MILLI` add diagnostic head rotation and sub-unit
translation. The manual GP0 walker loses packet provenance and is not valid for
PGXP projective validation. `MOHU_VR_EYE_OFFSET_ALL_SPANS=1` selects the
rejected direct-TRX experiment; that variant produced a black pair.

PGXP diagnostic states use ABI `131106`; base-flavor states use `34`. Never
patch a save header. If the PGXP runtime rejects the fixture, ask the operator
for a fresh PGXP slot and copy its `.pst` and `.thumb` into the isolated tree.

The default build keeps `MOHU_VR_DIAGNOSTICS=OFF`, uses the existing
`mods/preloaded` catalog, and does not compile these sources.
