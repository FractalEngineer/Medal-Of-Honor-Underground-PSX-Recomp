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

### Scene draw bridge

- Identified the overlay function at `0x80090760` as the draw bridge containing
  the live entity-transform call site whose return address is `0x800908E4`.
  The function is bounded by the next prologue at `0x800911D4`.
- Recorded the exact 2,676-byte SHA-256 and FNV-1a guards. The function saves
  GTE control state, calls the entity transformer, loads GTE RT from the composed
  scratch matrix, and performs three RTPS operations per draw pass.
- Added a static-confirmed read-only diagnostic binding. It does not write guest
  state; the entry hook exists only to capture the caller contract.
- Live confirmation observed `0x80090760 <-- 0x80091854`; the bridge returned
  through the branch at `0x800919BC`. Added a second guarded, read-only binding
  for the 840-byte dispatcher at `0x80091854`.
- The dispatcher is live-confirmed from `0x800913A0` with return address
  `0x80091420`. Added a guarded binding for that 1,204-byte entity render entry;
  its alternate paths mean it is not yet a safe whole-scene replay callback.
- The entity render entry is called by a 180-byte wrapper at `0x80079AF8`
  (`$ra=0x80079B50`). Added a guarded binding for this wrapper; a second call
  site at `0x80079CD4` shows that the wrapper is not the frame root.
- The wrapper is live-confirmed from the 472-byte actor render entry at
  `0x80076A50` (`$ra=0x80076B90`). The parent branches on actor flags before
  calling it, so it is not yet a whole-frame callback.
- The actor render entry is live-confirmed from a 352-byte player-oriented entry
  at `0x8008AB84` (`$ra=0x8008AC60`). It reads the verified player input field
  at `+0x39C` before calling the actor path.
- The player entry is invoked indirectly through the object vtable at
  `object+0x384`; the return address `0x8008AC60` follows the `jalr` in
  `0x80078E08`. Added a guarded binding for that 436-byte actor update dispatcher.
- The actor dispatcher is live-confirmed from `0x80053BB4`. Disassembly shows a
  complete frame sequence: scene setup, two conditional world passes, render
  environment, display projection, actor traversal, player draw, and the wait
  helper. This is the first whole-frame draw candidate; replay must omit the
  embedded wait helper.
- Added an opt-in dual-eye replay proof at `0x80053BB4`. It reproduces the
  pre-wait frame calls twice under the runtime's rollback transaction. A zero
  offset published a pair; frame tracing then showed zero GPU primitives, so an
  unchanged pair was correctly rejected as evidence.
- Matched the reference `DrawOTag` at `0x800172D8` to Underground
  `0x80018B50` and added its exact byte guard to the replay. The submission call
  is required after the scene-building calls and before the omitted wait helper.
- The first frame-render replay submitted 1,002/1,004 primitives per eye but
  produced identical images because its ordering table was already built before
  entry. Added an environment-gated, guarded experiment that replays the full
  frame driver at `0x8006D66C` so geometry generation and submission share the
  same eye transaction.
- Completed the frame-driver replay by finishing the verified
  `0x8009D828` wait early and skipping the post-render timer update at
  `0x8004356C` inside the eye transaction. The run published 180 pairs with
  four level-transformer entries per eye and no watchdog aborts.
- The driver pair remained byte-identical. This proves the visible level
  ordering table is generated before `0x8006D66C`; the next search must move to
  that earlier geometry-generation boundary.
- Clarified that the write trace names renderer output, not the camera update
  that originally authored the camera motion.

### Frame entry and OT correction

- Corrected the natural frame driver entry from `0x8006D66C` to
  `0x8006D65C`. The first four instructions load the frame context and status
  globals before falling into the old prologue. Updated the guarded binding to
  1,512 bytes with SHA-256 `bc1f06d6...` and FNV-1a `0x7F07744E`.
- Added a guarded `PutDrawEnv` binding at `0x80018BB8` (192 bytes, 0.981
  structural match to reference `0x80017348`). `PutDispEnv` maps to
  `0x80018C78` at 0.984 similarity.
- Confirmed the live DRAWENV for the slot-0 scene is `x=0, y=240, 512x240`, and
  the context OT base is `[0x800A7138 + 0x2218]`.
- Added a measured GP0 state packet and an eye-rect fill. A clear-only control
  produced two pure-black images, proving the target and clear path.
- Added a bounded diagnostic OT walker that feeds the linked packet words to
  GP0 inside the rollback transaction. The OT-only control
  (`MOHU_VR_STEREO_OT_ONLY=1`, zero offset) rendered the complete courtyard,
  weapon, and HUD, with OT base `0x800A72E0` and head `0x800A7ADC`.
- The OT-only left/right PNGs were byte-identical as expected for zero offset.
  Retained both images and the side-by-side control under `vr/proof/`.
- Confirmed the driver toggles the OT base from `0x800A72E0` to
  `0x800A82E0`. A full-scene pair can be obtained from the prebuilt list, but
  this does not prove fresh eye geometry.
- Rejected two offset experiments: the host render-view seam left the full scene
  byte-identical, while direct per-eye `TRX` injection under the driver path
  produced a black pair at the post-driver OT base.
- Armed `wtrace` over `0x0013DFE0..0x0013E030`. The visible packet writes came
  from `0x80090D68..0x8009104C` (`ra=0x800908E4`, scene draw bridge) and
  `0x800110C4..0x80011334` (`ra=0x80011008`, packet command writer).
- Rechecked the flat Release target: six framework packages, no VR diagnostic
  plugin, and a successful headless start.

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
