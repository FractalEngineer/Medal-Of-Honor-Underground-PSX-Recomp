# VR Port Handoff

Last updated: 2026-10-24

This is the canonical current-state handoff for the Underground VR port. Update
it before ending every implementation session.

## Repository state

| Item | Value |
| --- | --- |
| Target branch | `feature/vr-port` |
| Last implementation commit | pending this checkpoint |
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

The engine map is in `vr/underground/engine_map.c`. Sixteen mappings are recorded
with function SHA-256 and FNV-1a guards:

| Role | Reference | Underground | Evidence |
| --- | --- | --- | --- |
| Entity transform | `0x80084718` | `0x80093830` | 41/41 opcodes; live execution |
| Entity node transformer | `0x80013AE4` | `0x80013B40` | 221/221 opcodes; live function ring |
| GTE RT/TR loader | `0x80013E58` | `0x80013EB4` | Byte-identical; live function ring |
| Level vertex transformer | `0x8008B3E8` | `0x80099960` | 710/710 opcodes; 12 RTPS; live execution |
| Gameplay render wait | `0x80090B80` | `0x8009D828` | 110/110 opcodes; live execution |
| Scene draw bridge | undiscovered | `0x80090760` | 669 instructions; live caller chain |
| Scene draw dispatcher | undiscovered | `0x80091854` | 840 bytes; live execution |
| Entity render entry | `0x800824D0` | `0x800913A0` | 1,204 bytes; live execution |
| Render-list wrapper | undiscovered | `0x80079AF8` | 180 bytes; live execution |
| Actor render entry | undiscovered | `0x80076A50` | 472 bytes; live execution |
| Player render entry | undiscovered | `0x8008AB84` | 352 bytes; live execution |
| Actor update dispatcher | undiscovered | `0x80078E08` | object vtable dispatch; live execution |
| Frame render | undiscovered | `0x80053BB4` | 240 bytes; live execution |
| Frame driver | undiscovered | `0x8006D66C` | 1,496 bytes; replay execution |
| DrawOTag | `0x800172D8` | `0x80018B50` | 26 instructions; live submission |
| Post-render update | undiscovered | `0x8004356C` | 1,588 bytes; live execution |

The live-confirmed entity transform calls `0x80013B40`, not the near-identical
duplicate at `0x80014184`. The node transformer calls `0x80013EB4`, not
`0x800144F8`.

The opt-in diagnostic plugin is:

- Source: `vr/underground/vr_diagnostic.c`
- Package: `vr/preloaded/packages/mohu.vr.diagnostic/0.1.0/manifest.toml`
- Plugin ID: `mohu.vr.diagnostic`
- Behavior: function-entry logging after exact function-byte verification, plus
  environment-gated replay experiments. Canonical execution is unchanged unless
  `MOHU_VR_STEREO_PROOF=1`.

The diagnostic target reports sixteen active bindings and thirteen overlay hooks.
The isolated slot-0 scene verifies the render chain through the frame driver.

The single-player scene roots are measured:

| Root | Global | Live value at slot 0 |
| --- | --- | --- |
| Scene pointer | `0x800AA174` | `0x800F2180` |
| Player pointer | `0x800AA17C` | `0x800F0BE0` |
| Player input | `player + 0x39C` | `0x800F0FDC` |

Read the pointer globals at use time; the heap addresses themselves are not
stable across level loads. A right-stick camera turn changed GTE RT and the
rendered world while GTE TR stayed zero and the player pointer stayed fixed.

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
- The level transformer consumes the camera's rotation in GTE RT and projects
  camera-relative coordinates with TR zero.
- The stable scene/player pointer globals are mapped (see above). The frame
  render chain is mapped, but the high-level actor/camera update that originates
  camera motion remains unresolved.
- `0x80090760` is a render bridge, not the camera updater. It saves GTE state,
  calls `0x80093830`, projects three RTPS groups, builds packets, and restores
  state.
- The render call chain is
  `0x80053BB4 -> 0x80078E08 -> object+0x384 -> 0x8008AB84 -> ... ->
  0x80090760`.
- `0x80053BB4` is followed by the verified wait helper `0x80053CFC`, which calls
  `0x8009D828`.

See `CAMERA_EVIDENCE.md` for measurements.

## Transform probe

`MOHU_VR_DIAGNOSTICS=ON` now includes a diagnostic-only offset at the level
transformer. Setting `MOHU_VR_LEVEL_OFFSET_X=N` adds N to GTE TRX once per draw
span and restores the original TRX at the verified gameplay render-wait boundary:

```powershell
$env:MOHU_VR_LEVEL_OFFSET_X = '200'
```

The probe is inert without the environment variable. It verifies both boundary
functions before touching or restoring GTE state. It is not part of the flat
build and does not yet provide two-eye replay or OpenXR.

The current A/B receipt uses the same slot-0 scene:

| Probe | Result |
| --- | --- |
| `TRX = 0` | [Control](../../vr/proof/level-probe-control.png) |
| `TRX = 20` | [Depth-dependent world shift](../../vr/proof/level-probe-offset20.png) |
| `TRX = 200` | [Large world shift](../../vr/proof/level-probe-offset200.png) |

At `TRX + 20`, far rows aligned at +2 px, mid rows at +5 px, and near rows at
+6 px. The HUD and first-person weapon remained fixed. This establishes true
world-space parallax for the future eye-replay path.

## Stereo replay probe

The diagnostic build contains an environment-gated stereo experiment:

```powershell
$env:MOHU_VR_STEREO_PROOF = '1'
$env:MOHU_VR_EYE_OFFSET = '24'
$env:MOHU_VR_REPLAY_FRAME_DRIVER = '1'
```

The replay path:

1. Starts from `0x8006D66C` in a rollback-safe `psx_mod_render_stereo`
   transaction.
2. Applies signed `TRX` offsets at the verified level transformer.
3. Finishes `0x8009D828` early inside the transaction so the emulated wait cannot
   block replay.
4. Skips the post-render timer update at `0x8004356C`, which otherwise reads
   uncheckpointed device `0x1F801C0C`.
5. Submits the ordering table through guarded `DrawOTag` at `0x80018B50`.

Measured result:

- Zero-offset frame-render replay published pairs successfully.
- Full-driver replay published 180 pairs in the sampled run with four
  level-transformer entries per eye and no watchdog abort.
- `DrawOTag` submission produced roughly 1,000 GPU primitives per eye.
- The resulting left and right PNGs were still byte-identical.

Conclusion: rollback, wait bypass, submission, and per-eye CPU/GTE balance work,
but the visible level ordering table is generated before `0x8006D66C`. This
replay is diagnostic only and remains off by default. It is **not** parallax
proof and is not an OpenXR path.

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
- Interpreter-only diagnostic captures confirmed the camera roots and the
  `TRX` world-space probe.
- Hidden-window OpenGL replay confirmed the runtime stereo transaction can
  publish complete pairs with balanced eye cycles.

Last checks:

- Nine Python tests pass.
- Engine-map and diagnostic-plugin C files compile with
  `-Wall -Wextra -Werror`.
- All VR documentation links resolve.
- The diagnostic target builds and activates sixteen guarded bindings.
- TRX 0/20/200 A/B captures produce the expected depth-dependent world motion.
- Frame-driver replay completes and balances both eyes, but is rejected as image
  evidence because the eyes are identical.
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
mohu-vr-diag: active bindings=16 overlay_hooks=13 read_only=1 level_offset_x=0 stereo_proof=0 eye_offset=0 replay_driver=0
mohu-vr-diag: single_player_scene=0x800AA174 player=0x800AA17C player_input_offset=0x39C
```

## Open gates

1. Find the geometry-generation boundary before `0x8006D66C` that builds the
   visible level ordering table.
2. Replay from that boundary with the verified `TRX` eye offset and prove a
   non-identical pair with depth-dependent motion.
3. Keep the wait bypass and post-render timer skip scoped strictly to eye replay.
4. Label the actor/camera update function and separate camera motion from player
   translation over controlled inputs.
5. Complete interactive flat boot/menu/gameplay validation.
6. Implement the minimal OpenXR/native-screen startup path without modifying
   defaults used by `RunFlat` or the existing flat executable.
7. Only after a true parallax pair, connect the verified pair to OpenXR
   presentation and headset pose.

Do not treat the current frame-driver replay as working stereo. The rollback
transaction is proven; the visible geometry is still outside it.
