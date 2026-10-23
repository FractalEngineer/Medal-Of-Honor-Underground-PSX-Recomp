# VR Port Handoff

Last updated: 2026-10-23

This is the canonical current-state handoff for the Underground VR port. Update
it before ending every implementation session.

## Repository state

| Item | Value |
| --- | --- |
| Target branch | `feature/vr-port` |
| Last implementation commit | `10b401d` |
| Target base | `7fcb0ca35af683ac38c4c501347d59916a924aa4` |
| Reference branch | `master` |
| Reference commit | `b33a7d96d596214233d3aef5ecacbf3736ad29e3` |
| `psxrecomp` gitlink | `31df2e1e0e0a6525733e68ff70e72ecbef84bb09` |
| `recomp-ui` gitlink | `7c635c6b366a6e0d5d3c913a7fce6ec04dd9f256` |
| Reference version | `0.1.6` |
| Underground version | `0.1.0` |
| Game ID | `SLUS-01270` |

The only unrelated untracked workspace entry is `.commandcode/`. Do not add or
modify it as part of VR work.

## Non-negotiable invariants

- All VR implementation, tools, tests, and integration files live under root
  `vr/`.
- All retained VR documentation lives under `docs/vr/`.
- The flat executable must launch without a headset, VR environment variable, or
  VR diagnostic package.
- `MOHU_VR_DIAGNOSTICS` defaults to `OFF`. With it off, the original
  `mods/preloaded` catalog is used and no VR source is compiled.
- `game.toml` and `generated/` remain unchanged by the current VR checkpoint.
- Never transplant a reference-game address without its Underground function
  signature, container identity, and call contract.
- Do not enable a state-changing hook before flat behavior and the relevant VR
  transaction tests have been rechecked.

## Current implementation

The engine map is in `vr/underground/engine_map.c`. Five mappings are recorded
with function SHA-256 and FNV-1a guards:

| Role | Reference | Underground | Evidence |
| --- | --- | --- | --- |
| Entity transform | `0x80084718` | `0x80093830` | 41/41 opcodes; live execution |
| Entity node transformer | `0x80013AE4` | `0x80013B40` | 221/221 opcodes; live function ring |
| GTE RT/TR loader | `0x80013E58` | `0x80013EB4` | Byte-identical; live function ring |
| Level vertex transformer | `0x8008B3E8` | `0x80099960` | 710/710 opcodes; 12 RTPS; live execution |
| Gameplay render wait | `0x80090B80` | `0x8009D828` | 110/110 opcodes; live execution |

The live-confirmed entity transform calls `0x80013B40`, not the near-identical
duplicate at `0x80014184`. The node transformer calls `0x80013EB4`, not
`0x800144F8`.

The opt-in diagnostic plugin is:

- Source: `vr/underground/vr_diagnostic.c`
- Package: `vr/preloaded/packages/mohu.vr.diagnostic/0.1.0/manifest.toml`
- Plugin ID: `mohu.vr.diagnostic`
- Behavior: read-only function-entry logging after exact function-byte
  verification

The diagnostic target reports five active bindings, three overlay hooks, and
successfully verifies the entity, level-transform, and render-wait functions in
the isolated slot-0 scene.

Whole overlay-window hashes change between diagnostic runs even when function
bytes remain identical. They are observations only. The stable runtime guard is
the function-byte hash.

## Camera findings

- Right-stick rotation changes GTE RT while TR remains zero.
- OFX/OFY/H were `256/120/400` in 16.16/integer form at the sampled gameplay
  point.
- Scratchpad matrix bytes around `0x1F800014` changed with camera rotation.
- Scratch writes were produced by overlay code near
  `0x80090B98..0x8009115C`, with return address `0x800908E4` at base
  `0x8008C000`.
- The named camera owner and stable player/scene roots are still unresolved.

See `CAMERA_EVIDENCE.md` for measurements.

## Build and test state

Flat build:

- Directory: `build-release/`
- Release, OpenGL, OpenXR off, debug tools off.
- `MOHU_VR_DIAGNOSTICS=OFF`.
- Six packages: framework-only.
- Builds and starts headless with the config, OpenBIOS, overlay autocompile, and
  guest execution all initialized.

VR diagnostic build:

- Directory: `build-vr-diagnostic/`
- Release, OpenXR off, debug tools on.
- `MOHU_VR_DIAGNOSTICS=ON`.
- Seven packages: one game-owned diagnostic plus six framework packages.
- Slot 0 loads from `analysis/vr-baseline/saves/`.
- A 512x240 screenshot confirmed the saved state is a playable courtyard scene.

Last checks:

- Nine Python tests pass.
- Engine-map and diagnostic-plugin C files compile with
  `-Wall -Wextra -Werror`.
- All VR documentation links resolve.
- No owned game process remains running.

The first startup smoke used the default memcard directory before isolation and
refreshed two card timestamps. All later diagnostics use the copied directory.
Existing savestate files retained their original sizes and timestamps.

## Reproduce the diagnostic checkpoint

The diagnostic build needs a local libwebp source because network fetches are
restricted:

```powershell
$env:PSX_LIBWEBP_SOURCE_DIR = (Resolve-Path 'build-release\_deps\psx_libwebp-src').Path
cmake -S . -B build-vr-diagnostic `
  -DPSX_DEBUG_TOOLS=ON `
  -DPSX_OPENXR=OFF `
  -DMOHU_VR_DIAGNOSTICS=ON
cmake --build build-vr-diagnostic --target psx-runtime
```

Run from an isolated save copy:

```powershell
$env:PSX_LOAD_SLOT = '0'
.\build-vr-diagnostic\Medal_of_Honor_Underground_Recompiled.exe `
  --headless --no-launcher --debug-port 4372 `
  --memcard-dir analysis\vr-baseline\saves
```

Expected startup:

```text
mohu-vr-diag: active bindings=5 overlay_hooks=3 read_only=1
```

## Open gates

1. Identify the stable camera matrix owner and player/scene roots.
2. Separate camera motion from player translation over controlled inputs.
3. Add guarded entry instrumentation for the main-EXE node/loader path only
   through the supported recompiler hook process if it becomes necessary.
4. Complete interactive flat boot/menu/gameplay validation.
5. Implement the minimal OpenXR/native-screen startup path without modifying
   defaults used by `RunFlat` or the existing flat executable.
6. Then proceed to checkpoint/no-op replay, zero-IPD stereo, and real parallax.

Do not begin state-changing stereo hooks before the camera and player ownership
is settled.
