# Verified Baseline

Recorded 2026-10-23 before VR implementation changes.

## Repository identity

| Item | Reference | Underground target |
| --- | --- | --- |
| Branch | `master` | `feature/vr-port` from `master` |
| Tree commit | `b33a7d96d596214233d3aef5ecacbf3736ad29e3` | `7fcb0ca35af683ac38c4c501347d59916a924aa4` |
| `psxrecomp` gitlink | `31df2e1e0e0a6525733e68ff70e72ecbef84bb09` | `31df2e1e0e0a6525733e68ff70e72ecbef84bb09` |
| `recomp-ui` gitlink | `7c635c6b366a6e0d5d3c913a7fce6ec04dd9f256` | `7c635c6b366a6e0d5d3c913a7fce6ec04dd9f256` |
| Version | `0.1.6` | `0.1.0` |
| Game ID | `SLUS-00974` | `SLUS-01270` |
| Main executable | `disc/SLUS_009.74` | `disc/SLUS_012.70` |

The source repository contains an unrelated untracked `.commandcode/` entry.
It was not modified.

`framework_pins.txt` in the reference is stale and lists older scaffold values.
The parent repository gitlinks and `git submodule status` output are
authoritative and match on both games.

## Main executable headers

| Field | Reference | Underground |
| --- | --- | --- |
| PS-X EXE payload length | `0x2A000` | `0x2B800` |
| Load address | `0x80010000` | `0x80010000` |
| Initial PC | `0x8001DFD4` | `0x8001F844` |
| Stack top | `0x801FFFF0` | `0x801FFFF0` |
| Seed inventory | 297 function addresses | 302 function addresses |

Only four seed addresses coincide exactly across the two games. That is not
evidence of function equivalence. Engine landmarks must be matched from
instruction structure, GTE use, call relationships, and live execution.

## Current target build

The existing `build-release/` executable was configured as:

| Setting | Value |
| --- | --- |
| Build type | `Release` |
| Committed game C required | `PSXRECOMP_REQUIRE_GAME_C=ON` |
| Debug tools | `PSX_DEBUG_TOOLS=OFF` |
| OpenXR | `PSX_OPENXR=OFF` |

The default target does not pass the framework `PGXP` option, add VR sources, or
stage the VR diagnostic package. The existing binary is therefore a flat-build
candidate, not a VR baseline. `MOHU_VR_DIAGNOSTICS` can opt a separate build
into the Underground diagnostic plugin, but that path remains OpenXR-off and
does not change the default product.

### Build and startup check

The Release target recompiled successfully with the pinned framework. The
resulting executable was regenerated on 2026-10-23.

The prior run report exposed a stale overlay toolchain: the staged codegen hash
was `0x1b6950cb`, while the runtime expected `0x115b1739`, so all overlays would
have remained interpreted. The framework's
`stage_overlay_toolchain_for_product` helper restaged the bundle from the current
checkout. Both hashes now read `0x115b1739`.

A bounded headless startup smoke test loaded `game.toml`, identified
`SLUS-01270`, loaded OpenBIOS, selected the software renderer, and printed:

```text
overlay autocompile enabled (gcc)
```

The process was then stopped by its owner before gameplay validation. This is
startup evidence only. Boot, menus, FMVs, first playable scene, and flat rendering
remain to be validated.

### Isolated slot-0 diagnostic

A separate Release diagnostic build was created at `build-vr-diagnostic/` with
`PSX_DEBUG_TOOLS=ON` and OpenXR off. It uses an isolated copy of the save tree at
`analysis/vr-baseline/saves/`.

Slot 0 loaded successfully:

| Field | Result |
| --- | --- |
| Savestate generation | `1` |
| Last operation | `load` |
| Slot | `0` |
| Observed frame | `890` |
| Overlay capture entries | `21` at dump time |

The gameplay capture contains the Underground render wait, level vertex
transformer, entity transform, and both RTPS-heavy geometry regions. There was
no observed crash or state-compatibility refusal during the loaded session.

The first startup smoke used the default save directory before the isolated copy
was created, and refreshed the two memory-card timestamps. Subsequent diagnostic
runs use only the copied directory. Existing savestate files retained their
original timestamps and sizes.

## Reference behavior to preserve

The reference source identifies v0.1.6 as its playable VR baseline:

- Release, OpenGL, OpenXR.
- PGXP and projective replay enabled.
- Debug tools disabled.
- LLE batching.
- Stereo shedding disabled by default.
- Atomic complete eye pairs from one guest checkpoint.
- Exact host eye rotation and translation with scoped provenance, signed
  facing, and near-plane clipping.
- Native menus, briefings, and movies on a flat OpenXR surface.

These are source observations only. They do not transfer to Underground until
the target implements and measures the equivalent paths.

## Gate status

| Gate | Status | Evidence or blocker |
| --- | --- | --- |
| G0 pins and identity | Partial | Exact revisions, headers, and submodule gitlinks recorded. |
| G0 target flat build | Partial | Release compile, corrected overlay autocompile, and isolated slot-0 gameplay boot pass. Interactive flat rendering/audio still need validation. |
| G0 isolated saves | Pass for diagnostics | Slot-0 tests use `analysis/vr-baseline/saves/`; original personal states were not written. |
| G1 engine landmarks | Partial | Render wait, level vertex transformer, entity transform, node transform, and RT/TR loading are mapped and observed executing. A named camera source and player roots remain open. |
| G2 plugin activation | Partial | Opt-in diagnostic package activates and verifies three overlay functions. OpenXR/native-screen launch is not implemented. |

The flat Release executable was also started after the VR files were added. It
loaded the game config, initialized overlay autocompile, entered OpenBIOS, and
began guest execution without a headset. `CMakeLists.txt` and `game.toml` remain
unchanged, so no VR source is linked into that target.

## Reproduction commands

```powershell
git branch --show-current
git rev-parse HEAD
git submodule status
Get-Content VERSION
Get-Content build-release\CMakeCache.txt |
  Select-String 'CMAKE_BUILD_TYPE|PSX_OPENXR|PSX_DEBUG_TOOLS|PSXRECOMP_REQUIRE_GAME_C'
Get-Content build-release\overlay_toolchain\include\overlay_codegen_hash.h
```

For the adjacent reference repository, use an explicit safe-directory override
instead of changing global Git configuration:

```powershell
$ref = 'C:\Users\titan\Desktop\Github_Projects\Mine\Medal-Of-Honor-PSX-Recomp'
git -c safe.directory=$ref -C $ref branch --show-current
git -c safe.directory=$ref -C $ref rev-parse HEAD
git -c safe.directory=$ref -C $ref submodule status
```
