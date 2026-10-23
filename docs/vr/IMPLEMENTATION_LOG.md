# VR Port Implementation Log

## 2026-10-23

### Baseline and organization

- Created `feature/vr-port` from Underground `master` at
  `7fcb0ca35af683ac38c4c501347d59916a924aa4`.
- Verified the adjacent reference repository at
  `b33a7d96d596214233d3aef5ecacbf3736ad29e3`.
- Verified matching framework/UI gitlinks on both repositories:
  `psxrecomp=31df2e1e...`, `recomp-ui=7c635c6b...`.
- Moved the VR plan into `docs/vr/` and established a documentation index.
- Recorded that the current target build is Release with debug tools off and
  OpenXR off; it is not yet a VR build.
- Rebuilt the flat Release target successfully.
- Found and corrected a stale staged overlay toolchain. Both the staged and
  runtime headers now name codegen hash `0x115b1739`.
- Ran a bounded headless startup smoke test: config, game ID, OpenBIOS,
  software renderer, and overlay autocompile all initialized. The process was
  stopped before gameplay; this is not a flat gameplay validation.

### Engine matching

- Added a dependency-free PS-X EXE and overlay-capture matcher under `vr/tools/`.
- Added landmark reporting with normalized MIPS opcode/token similarity, GTE
  profile matching, overlay identity, and an explicit "candidate only" label.
- No state-changing Underground hook has been promoted.
- Generated the current
  [candidate report](ENGINE_EQUIVALENCE_REPORT.md). Only the PsyQ `VSync`
  wrapper formed a near-identical static match (`0x800186A8`). Gameplay,
  geometry, weapon, and HUD functions remain low-similarity candidates.
- Unit tests for MIPS decoding, PS-X header parsing, function boundaries, and
  self-similarity pass.

### Gameplay capture and live confirmation

- Built `build-vr-diagnostic/` with debug tools enabled and OpenXR off.
- Loaded slot 0 from an isolated save copy; load generation 1 completed and the
  session advanced past frame 890.
- Captured Underground overlays at `0x80097000` and `0x8008C000`. Whole-window
  capture hashes changed between runs while function bytes stayed identical, so
  the function SHA-256 and FNV-1a values are treated as the stable guards.
- Confirmed live execution and address-only instruction differences for the
  entity transform, level vertex transformer, and gameplay render wait.
- Used the live function ring to select the active duplicate scene-transform
  branch: `0x80013B40` -> `0x80013EB4`. Both execute during the loaded slot-0
  scene; the alternate near-identical branch is not mapped.
- Rotated the camera with debug input: GTE RT changed while TR stayed zero and
  the scratchpad view matrix changed. The producer PCs are in overlay code near
  `0x80090B98..0x8009115C`; the matrix owner remains unresolved. See
  [CAMERA_EVIDENCE.md](CAMERA_EVIDENCE.md).
- Added the guarded mapping metadata in `vr/underground/engine_map.c`. The map
  itself registers no hooks.

### Opt-in diagnostic plugin

- Added `MOHU_VR_DIAGNOSTICS`, default `OFF`, plus the separate
  `vr/preloaded/packages/mohu.vr.diagnostic` catalog.
- Added read-only function-entry shadow hooks that verify each target function's
  FNV-1a bytes before logging registers.
- Built the diagnostic target with `MOHU_VR_DIAGNOSTICS=ON`. The package
  activated and verified the entity transform, level vertex transformer, and
  gameplay render wait in the isolated slot-0 scene.
- The diagnostic build staged seven packages (one VR diagnostic package plus six
  framework packages). The default build still stages only the original six and
  does not load the plugin.
- Captured a 512x240 screenshot of the loaded courtyard to confirm the save is
  an actual playable scene rather than a menu or paused placeholder.

### Camera roots and transform probe

- Mapped the reference scene/player globals to Underground's
  `0x800AA174`/`0x800AA17C` through the 710-instruction level-transformer
  equivalence and live pointer reads.
- Confirmed slot-0 `scene=0x800F2180`, `player=0x800F0BE0`, and
  `input=0x800F0FDC`; the player global remained stable through a right-stick
  camera turn while GTE RT changed and TR stayed zero.
- Added camera root constants under `vr/underground/camera_map.h`.
- Added a diagnostic-only, fail-closed level-transform TRX offset controlled by
  `MOHU_VR_LEVEL_OFFSET_X`; it is frame-span scoped by the verified render-wait
  boundary and is inert by default.
- A same-scene A/B at `TRX=0/20/200` changed 32.53% and 64.24% of the frame
  respectively. At `TRX=20`, far rows shifted +2 px, mid rows +5 px, and near
  rows +6 px, proving depth-dependent world parallax while HUD/weapon stayed
  fixed. Evidence is under `vr/proof/`.

### Flat-path preservation

- Kept every VR implementation file under root `vr/`.
- Added a default-off `MOHU_VR_DIAGNOSTICS` CMake option; the default catalog,
  generated game code, and runtime sources remain unchanged when it is off.
- Rebuilt the flat Release target successfully.
- Launched the flat executable headless with the isolated memcard directory;
  config load, OpenBIOS boot, overlay autocompile, and guest execution all
  started normally. The owned process was closed after the smoke check.
- The engine map compiles standalone with Clang using
  `-std=c11 -Wall -Wextra -Werror`.

### VR isolation invariant

- All VR implementation and diagnostic files are kept under the root `vr/`
  directory. VR documentation remains under `docs/vr/`.
- The flat Release target has not been changed to include VR sources or require
  a headset. Its launch path remains the existing executable and configuration.

## Next work

1. Rebuild the existing flat target and record a launch/boot/gameplay baseline
   with an isolated memcard path.
2. Capture Underground overlay generations for the first playable scene and
   identify stable fingerprints.
3. Capture the reference region for `0x8006591C`, which the retained overlay
   bundle does not contain.
4. Review the highest-ranked render-wait, level-projector, and camera candidates
   in disassembly and live traces.
5. Bootstrap only the opt-in plugin registration and native-screen OpenXR path
   after G1 produces safe, guarded target bindings.
