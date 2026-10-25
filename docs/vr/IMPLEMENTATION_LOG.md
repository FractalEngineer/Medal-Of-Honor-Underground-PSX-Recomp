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

## 2026-10-24

### Frame caller and stereo view seam

- Identified the natural caller above the frame driver as `0x80070444`; the
  direct frame-driver call is at `0x800705E4`, returning to `0x800705EC`.
- Confirmed that replaying the frame driver still does not expose the visible
  geometry transaction.
- Added a diagnostic-only scoped view offset for frame-render replay. It uses
  `psx_mod_render_view_offset()` rather than guest GTE control writes.
- Confirmed `MOHU_VR_EYE_OFFSET=0` with
  `MOHU_VR_EYE_VIEW_OFFSET=1` publishes a complete, byte-identical pair
  (zero differing pixels out of 122,880).
- Confirmed signed `-24` / `+24` offsets publish a complete courtyard pair with
  94,282 differing pixels. Block matching measured about 5 px far-scene motion
  and 8 px near-floor motion, establishing depth-dependent parallax.
- Repeated the offset pair with `PSX_RENDER_PASS_VERIFY=1`: 3,542 checks, zero
  mismatches, equal per-eye guest cycles and equal per-eye state hashes.
- Added a separate `MOHU_VR_EYE_OFFSET_ALL_SPANS=1` negative control. Applying
  the TRX offset at every level-transformer entry produced a black pair and is
  rejected.
- Retained zero and offset image pairs under `vr/proof/` and recorded runtime
  pair IDs, equal eye cycles, and capture statistics in
  [STEREO_VIEW_EVIDENCE.md](STEREO_VIEW_EVIDENCE.md).

### Full render view and PGXP near-plane path

- Made the opt-in diagnostic target the framework PGXP hook flavor while
  leaving the flat target on its base flavor.
- Replaced the fixed integer eye offset with a complete `PSXModRenderView`
  built from guest `H`, `OFX`, and `OFY`, with precise translation and
  diagnostic yaw, pitch, and sub-unit head controls.
- Added guest `DrawOTag` submission for the regenerated eye list. The manual
  GP0 walker remains a submission control but loses source provenance and
  reports every packet as `vr.projective.miss0`.
- Confirmed the base savestate is not interchangeable with the PGXP build:
  `slot00` has ABI `34`, while PGXP expects `131106`. The header was not
  patched. The operator created a fresh PGXP save, and slot `1` was copied into
  the isolated save tree.
- Retained a byte-identical PGXP zero pair, a 93,376-pixel lateral pair, and a
  91,984-pixel forward/downward near-plane pair under `vr/proof/`.
- Measured 1.4M homogeneous projective draws in the accepted runs. The
  forward/downward pair completed 1,544 verified passes with zero mismatches,
  no watchdog, no VRAM leak, and equal per-eye state hashes.
- Added render-scoped signed-NCLIP counters at the homogeneous winding decision.
  They report total/precise/miss, final positive/negative/zero sign, and
  corrections without requiring widescreen `precise_nclip`.
- Recorded five 60-pair snapshots after the operator created fresh PGXP slot 2:
  zero, lateral, pitch, yaw-positive, and yaw-negative. Every snapshot had zero
  precise-projection misses, and corrections ranged from 14,950 to 18,396.
- Added unit coverage for the counter transitions in both GTE contract targets.
- Full receipt:
  [PGXP_RENDER_VIEW_EVIDENCE.md](PGXP_RENDER_VIEW_EVIDENCE.md).

### Single-build launcher workflow

- Matched the reference repository's single-build layout: `build-release/` is
  now the active Release, OpenXR, PGXP diagnostic target.
- Added root `RunFlat.bat`, `RunVR-VDXR.bat`, `RunVR-Oculus.bat`, and
  `RunVR-SteamVR.bat`. The VR wrappers call shared `vr/run_vr.ps1`, which pins
  the selected runtime, enables Underground's OpenXR mode, waits for a fresh
  headset submission receipt, and restores the parent environment.
- Flat mode clears VR environment variables and leaves the loaded diagnostic
  plugin inert.
- Confirmed that save failures came from ABI or runtime-identity invalidation,
  not from a reused build directory.
- Deleted `build-vr-diagnostic/`, `build-vr-pgxp/`, `build-vr-pose/`,
  `build-fw-tests/`, and `build-recompiler/`; only `build-release/` remains.

### OpenXR bootstrap

- Added opt-in `MOHU_VR_OPENXR=1` handling to the diagnostic plugin. It implies
  stereo proof, render-view, and guest-submit mode, and locates the two eye
  views from the headset frame.
- Added a native head-relative menu surface that remains active until the first
  guarded gameplay stereo frame, plus fail-closed begin/view handling.
- Reconfigured `build-release/` in place with `PSX_OPENXR=ON`; the framework
  built the OpenXR loader and runtime successfully without another directory.
- Verified PGXP slot `2` still loads after the rebuild. Without a headset,
  OpenXR fails at the system stage (`-35`) and the process remains alive on the
  flat fallback; no pair is submitted.
- Receipt: [OPENXR_EVIDENCE.md](OPENXR_EVIDENCE.md).

### Headless OpenXR acceptance

- Ported the reference repository's SteamVR null-HMD settings helper and
  `-Headless` launcher mode to Underground.
- Adopted the reference scale profile: 67 mm IPD calibration, `WorldScale=3`,
  and 238.806 effective game units per metre.
- Disabled the redundant desktop VSync wait while the OpenXR compositor owns
  pacing.
- Verified slot `2`, a sustained 57-pair sample over 2 seconds, zero empty
  startup frames, zero XR begin/view failures, and clean SteamVR settings
  restoration.
- The earlier physical-headset run used the unscaled profile and reported an
  oversized world plus black flashing.
- Reproduced the remaining flashing headlessly despite zero empty XR
  submissions. A 60-pair sequence showed every even pair was pure black.
- Proved with the OT-only control and non-empty alternating OT lists that
  replay regeneration was not the cause. The replay was following the native
  display origin to `y=240`, while eye packet coordinates were rooted at the
  rollback-protected `y=0` scratch surface.
- Changed both eye replays to use the `y=0` scratch buffer. The final 60-pair
  sequence had zero black left or right images, and a verification run reached
  241 pairs and 482 checks with zero mismatches or empty submissions.
- Added timed null-HMD compositor capture. Eight consecutive samples were
  nonblank in both the compositor and application layer.
- The operator confirmed the corrected image no longer flashes.

### Head-turn visibility, resolution, and flat HUD

- Changed the shared VR launcher from native 240-line rendering to the
  reference game's `1080p` default. The runtime now reports 5x internal scale;
  `-InternalResolution native` remains available as a control.
- Ported the reference per-eye level-tree selector to Underground's
  `0x80099960` transformer. It validates the complete 710-instruction function
  on every override, builds the full AABB/PVS queue before writing guest RAM,
  and falls back to the native selector on malformed trees or overflow.
- Recorded the Underground visibility-tree mapping: masks `0x800B7490` and
  `0x800B7494`, bypass `0x800B7498`, queue `0x800B74B8`, count
  `0x800B74B4`, and sentinel `0x800C8458`.
- Added a guard for the flat HUD text producer at `0x8006B64C`. It is skipped
  only during eye replay, using the full 692-byte FNV-1a guard.
- Traced the regenerated OT and removed the health/bar/compass packet block at
  `0x800B8C88..0x800BA4B0` plus the small HUD bar node at `0x800F109C`. This
  removes the stale fixed overlay that remained after suppressing text.
- Added `MOHU_VR_STEREO_DUMP_PAIRS` for bounded evidence captures and an
  opt-in `MOHU_VR_HUD_TRACE=1` OT trace for future packet mapping.
- Verified zero-offset left/right hashes are identical
  (`AEECA835133FAE5DADF3047D28D612AA0258FE087098BEE04EAFB46E3C23735B`), both
  90-degree side poses remain populated, and stereo differences remain large.
- A final null-HMD run completed 30 pairs with `frustum=120/120`,
  `fallback=0/0`, `hud_skips=30/30`, `hud_unlinked=525/525`, and zero XR
  begin/view failures. SteamVR settings matched the pre-run backup afterward.
- Evidence: [HEAD_TURN_HUD_EVIDENCE.md](HEAD_TURN_HUD_EVIDENCE.md) and
  [head-turn-hud-fix.png](../../vr/proof/head-turn-hud-fix.png).

### Sky-only ghost isolation and correction

- Started only after local HEAD and live `origin/feature/vr-port` both matched
  `4dbe4cd`. The reference port's explicit scene build/submit sequence omits
  the native wait/submission/display tail.
- Added bounded controls under `vr/`: raw eyes plus SteamVR application layer,
  clear-only black/magenta, native surfaces disabled, HUD/frustum opt-outs,
  and replay-only/final-clear controls. Uniform clear captures and zero native
  submission counters excluded retained native surfaces for the reproduced
  defect; replay-only still drew the flat courtyard.
- Isolated the native tail at `0x80053CFC`, called inside frame-render replay.
  Its native OT draw/display selection ran before our final projected submit.
  Added a full 80-byte guard and skipped it only inside the eye transaction.
- Corrected `DrawOTag` to the complete `0x80018B48` entry, including its initial
  library-state loads. A trial main-function hook recorded no callbacks in
  existing generated code and was rejected; the accepted filter is at the
  overlay tail. No generated source or game configuration changed.
- Traced the last gold ammo icon to two alternating 40-byte FT4 packets.
  The old single-buffer rule missed `0x800F10C4`. Both buffers now require
  exact captured payloads, covered by a strict C fixture.
- Same-binary synthetic look-up A/B restores the flat ghost with
  `MOHU_VR_KEEP_REPLAY_SUBMIT=1`. The fix removes 1,294,352/1,289,357 background
  pixels with 100% agreement in the measured static foreground in both eyes.
  Both raw eyes and both application-layer halves were inspected.
- Rechecked 13 Python tests, strict frustum/ammo C fixtures, diagnostic C,
  zero-offset hashes, +/-90-degree world coverage, and documentation links.
  The diagnostic XR run reached 180 logged pairs; the capture had 150 rollback
  checks, zero mismatches/leaks/watchdogs, fresh projection/source `1/1`, and
  zero empty submissions or XR failures.
- Rebuilt the same `build-release` with debug tools OFF. The normal null-HMD
  smoke reached 360 pairs with zero XR failures and frustum fallbacks. The flat
  launcher remained inert even with inherited VR activation variables.
- SteamVR settings restored byte-for-byte; no owned game/runtime process was
  left running. Slot 2 stayed valid; no save-slot migration was attempted or
  failed. A future invalid slot must result in asking the operator for a fresh
  PGXP slot, without header or identity changes.
- Rejected harness attempts and their cleanup are recorded in
  [SKY_GHOST_EVIDENCE.md](SKY_GHOST_EVIDENCE.md). Retained only a compact receipt
  and one [proof image](../../vr/proof/sky-ghost-fix.png); bulk captures are ignored.
- Physical-headset acceptance of this correction remains pending.

### Reference input mappings and operator save preparation

- The operator confirmed the sky ghost fixed and requested movement, then
  clarified that they will create the saves and want the previous game's maps.
  Started with local/live remote `627b31d` matching; no save was created,
  migrated, patched, or copied by the agent.
- Reused the reference input mapper and offline source/presentation seam.
  Left stick moves/strafes, right X turns, with the same combat/menu buttons
  and optional left-grip axis merge. Flat mode stays inert. Deadzone 0.2,
  turn gain 0.65; 1080p, 67 mm and WorldScale=3 remain unchanged.
- Mapped Underground converter `80083C6C`, dispatcher `80083DB0`, calibration
  `800C47C8`, actions `800C4AA8`, and curve `800AB12C` from native code and live
  pad controls. Full function guards and live records protect input routing.
  Adapted center +/-37/clamping and both measured DualShock table layouts;
  reusing reference guest addresses or threshold math would be incorrect.
- Synthetic XR actions verified native pad delivery and actor-field changes for
  forward/back, strafing, turning, partial/diagonal input, button/release and
  focus/inactivity controls. Rollback checks had zero errors; boot menu pad
  mappings worked without loading a slot. Multiplayer gameplay remains untested.
- Added `-NoMovement`, `-MoveDeadzone`, `-TurnGain`, and a working `-Slot -1`
  native-menu startup path. All process environment values restore on exit.
- Passed 13 Python tests, strict input/frustum/HUD C fixtures, diagnostic C,
  zero identity, populated +/-90-degree views and raw/app-layer clear-sky checks.
  Restored debug-off Release in the one `build-release`; the normal null-HMD
  smoke completed 360 logged pairs with zero XR failures. Flat inherited-flag
  startup was inert, SteamVR settings restored, and owned processes closed.
- Rejected registration/calibration harness runs and a missing relative save
  path are documented in [MOVEMENT_EVIDENCE.md](MOVEMENT_EVIDENCE.md). No save
  migration failed. Any future invalid slot means ask for a fresh PGXP slot.

### Flat P1 controller / P2 keyboard setup

- Operator reported Steam Controller input also moving P2 and requested a
  separate P2 layout on the keyboard. Existing device assignments were correct;
  both players shared default keyboard keys, always merged by the runtime.
- Backed up local `build-release/settings.toml` and `keybinds.ini`, cleared all
  P1 keyboard binds, preserved its Steam Controller/analog assignment, set P2
  keyboard/digital to IJKL, U/O, number-row buttons, P/M, and disabled multitap.
- `RunFlat.bat` now disables inherited diagnostic `PSX_DEV_INPUT`. TOML/INI
  parsing and exact assignments/bindings passed. No framework, generated code,
  game config or savestates were changed; no rebuild was needed.
- The operator stopped Steam UI inspection; no Steam settings changed. The
  physical-event source of controller-to-P2 input remains unconfirmed and the
  resulting physical separation awaits operator testing. Keys/backup paths:
  [FLAT_LOCAL_INPUT.md](FLAT_LOCAL_INPUT.md).

### Multiplayer weapon inventory and native damage

- Operator created source slots 1-4 with P1 facing P2 and authorized native
  weapon cycling/firing. Started from matching local/live origin `7f2632d`.
  All saves pass ordinary PGXP ABI/execution-identity checks. No migration,
  header patch, identity bypass, new save or ammo edit occurred.
- Adapted the reference copied-save/TCP/native-input inventory procedure in
  `vr/tools/inspect_weapon_sets.py`. All four cycles close after four switches;
  13 distinct IDs have inspected first-person images and native P2 damage.
- Measured Underground P1/P2 roots, input slot/ID, clip/reserve, and current
  health +108 independently. Guarded the complete 532-byte native damage
  function at `8004EAB4`; traced subtraction/store `8004EB78/8004EB80`.
- Idle and turned-away pistol controls record no damage. Longer scoped and
  grenade controls retain damage/death/respawn writes even when final health
  returns to 32. Stationary petrol bombs miss; a closer native movement control
  damages both players. No safe-distance or tracked-aim conclusion is made.
- Kept source saves separate from diagnostic copies and the existing isolated
  SP slot 2. Final inventory verifies unchanged save/thumbnail/controller and
  SteamVR hashes, exit 0 and no owned game. Restored the same `build-release`
  to debug OFF; 13 Python tests and all three strict C fixtures pass.
- Rejected discovery field/port/input-mask assumptions are documented in
  [WEAPON_SET_EVIDENCE.md](WEAPON_SET_EVIDENCE.md). Source-owned evidence is the
  [compact receipt](../../vr/proof/weapon-set-receipt.json); bulk stays ignored.
  No VR runtime source, framework, generated output, or game config changed.
- Debug-off flat startup was inert, but two hidden auto-load smokes staged slot
  4 without attempting the load before 30-second deadlines. Both owned games
  were closed; no invalid save was reported. Recorded this production-headless
  limitation separately from successful diagnostic save/combat evidence.

## 2026-10-25

### Multiplayer-first weapon mapping

- Changed the shared VR launcher default from slot `2` to `-Slot -1`. Normal
  VR launches now reach the native boot/menu path and clear an inherited
  `PSX_LOAD_SLOT`; loading a savestate requires an explicit `-Slot N`. Added a
  focused launcher-default regression test.
- Restored the native flat menu surface after stereo gameplay stops. The
  state now mirrors the reference game's four-VBlank scene-idle threshold, so
  pause menus return to the head-relative surface and the next gameplay frame
  resumes stereo. Added a strict helper fixture and retained an isolated
  null-HMD boot receipt.

- Mapped the multiplayer player update at `0x800892E8` (0xA70, FNV
  `0x39E56A35`) and the single-player update at `0x800892C8` (0xF20, FNV
  `0xF4D6C439`) as separate overlay generations. Every title hook must match the
  mode-specific function bytes and caller instruction word.
- The multiplayer fixtures provide one stationary P2 target, all 13 measured
  weapon IDs, closed native inventory cycles, and native damage writes. This is
  the working fixture for weapon-position and mesh-transform mapping.
- P1's measured 22-node player/model object is `actor+0x4AC`; it has magic
  `0x00160024` and a shared node table
  `9f8c7275b3e8a1d6c7765da25a02d78b23f0c3fa4b67483f28865191d2805e4f`.
  Object fields at `+0x5C/+0x64` change during cycling and are animation state,
  not a stable mesh identity. The object is not yet proven to own the top-view
  first-person weapon.
- Added `vr/tests/test_weapon.c`, covering the 13 unique ID table, exact node
  guard, stale/unfocused/bad-pose fallback, and render-view output.
- The current implementation target is the first-person model's affine/node
  transform or later vertex projection. The accepted path must preserve native
  animation, recoil, reload, ammo and fire behavior while leaving the world view
  unchanged.
- Restored the single `build-release` to Release/OpenGL/OpenXR/PGXP with debug
  tools OFF. The flat launch remained inert. The final null-HMD smoke completed
  360 pairs with zero XR failures, `frustum=1440/1440`, and zero weapon-pose
  applications because the production launcher leaves the experiment off.
- Added a top-view P1 native-hit matrix covering all 13 IDs at native, lateral
  (`x=96`), yawed (`12000` mdeg), and forced-tracking-loss poses. Damage is
  accepted from a decrease at the exact P2 health address in the native write
  trace, including targets that respawn before the final sample.
- The current `0x8008DB98` affine hook changes P1's world body in the other
  split view, not the visible top-view first-person mesh. It remains
  diagnostic-only and is not claimed as the accepted model seam.
- A later `0x80088C08` geometry/GTE-control experiment also passed local guards
  and recorded apply/restore operations, but a same-run `x=512` A/B moved the
  other split-panel weapon while the top P1 gun stayed unchanged. It is rejected
  for the requested viewmodel and remains uncommitted.
- Re-read the adjacent reference checkout's `VR_WEAPON_TRACKING.md`,
  `VR_WEAPON_AIM_PLAN.md`, and `VR_WEAPON_BATCH.md`. The reference game treats
  the first-person object separately from the third-person/held-body object,
  captures the rendered weapon affine, and uses exact level triangles for the
  laser. Its offsets are title-specific and must not be copied into Underground.
- Added `vr/underground/raycast.h` and a strict visibility-tree fixture for a
  default-on right-squeeze aim ray with beam and impact dot. `-NoLaser` and
  `PSX_VR_LASER=0` are explicit opt-outs. Runtime headset visual acceptance
  remains pending.
- Repeated the top-view P1 firing control with native pose disabled at
  `3cdbe826`. Fresh copied slots 1-4 produced native P2 health-write decreases
  for all 13 IDs, exit 0, unchanged source saves/preferences, and no owned game
  process. Evidence:
  `analysis/vr-baseline/weapon-mesh-mapping/p1-p2-top-20261025c/inventory.json`.
- Current scratch state is not release-ready: `vr/underground/vr_diagnostic.c`,
  `weapon.c`, and `weapon.h` are modified and uncommitted, and `build-release`
  is configured with `PSX_DEBUG_TOOLS=ON`.

### Real multiplayer first-person geometry seam

- Consulted the adjacent reference game's `VR_WEAPON_TRACKING.md`,
  `VR_WEAPON_AIM_PLAN.md` and `VR_WEAPON_BATCH.md`. Traced Underground's
  `[actor+114] == input+9F0` viewmodel independently of the `actor+4AC` body.
  Pistol is a 14-node object, not the shared 22-node body. The same native path
  supplies all 13 measured weapon IDs.
- Identified `8008A3DC -> 800892E8`, call `8008A53C` / return `8008A544`,
  H=133. The method transforms animated vertices via `8008DB98`, restores its
  native GTE RT/TR, then projects them. Scoped the delta at `800894DC`, with
  eight-word restoration at the common `80089D30` epilogue. Corrected the
  historical engine-map display label from player update to model geometry.
- Captured real per-ID magic, 14-32 node counts, 280-397 faces, and source
  vertex data hashes. Runtime hashes exclude heap pointers and match repeated
  IDs across source slots. Full function/caller/ownership/mesh/H/stack guards
  precede writes. Native animation, arms, recoil, reload, ammo and shots remain
  inputs; no shot direction or ammo state is edited.
- Corrected affine-Q12 versus integer-GTE-TR translation. The initial +8 test
  sent every gun offscreen because it inherited affine `*4096`; that receipt
  is rejected. Final +24 controls produce a visible top-panel shift.
- All 13 IDs pass native/+24/yaw+12/lost/restored controls. Fixed world, ammo
  HUD and other-panel-weapon rectangles remain byte-identical. Loss records
  native fallback and no pose applications. Every control drains to equal
  apply/restore counters. Captures preserve native target/weapon animation;
  this is not whole-image identity or physical calibration.
- Retained the [proof sheet](../../vr/proof/weapon-viewmodel-controls.png),
  [compact receipt](../../vr/proof/weapon-viewmodel-receipt.json), and reusable
  capture/summary tools. Final control inventory:
  `analysis/vr-baseline/weapon-mesh-mapping/fp-controls-final-20261025/inventory.json`.
- Removed dead wrong-panel runtime hook code/address selection. Kept the
  session-start scratch diff locally under the ignored analysis tree. The
  production launcher still leaves tracking off. The pivot is diagnostic;
  calibrated grip/scale, MP eye replay, native shot alignment and mesh-derived
  exact-triangle laser remain open.
- Rejected harness controls include a duplicate Python keyword argument,
  pre-VBlank command sampling, and treating a one-call in-flight counter skew
  as a persistent leak. Final controls wait for VBlank latching and require
  exact equality after tracking-loss drain. Every owned run closed with source
  saves and preferences unchanged. No invalid save or identity migration arose.
- Final +24 geometry build retains native P2 health-write decreases for all
  13 IDs; all four cycles close, exit 0, source saves/preferences unchanged,
  and no owned game remains. The same binary's SP zero-eye regression has
  18 complete pairs, equal eye cycles/hashes and 37 rollback checks with zero
  mismatches, leaks, watchdogs or repairs. This does not accept MP stereo.
- An ad-hoc SP probe with the weapon flag set reached 60 pairs but hit an
  `emu busy or frozen` debug snapshot/cleanup response before writing a
  receipt. It is rejected as acceptance; no owned process remained afterward.
  The accepted SP regression uses the established sky-ghost control tool.
- Hardened `RunFlat.bat` against inherited weapon-pose/flat-probe variables and
  added its isolation regression. Eighteen Python tests and all six strict C
  fixtures pass; the diagnostic source passes strict warning-as-error syntax
  checking. Production tracking remains off.
- Restored the one `build-release` to debug OFF and checked hidden flat startup
  with inherited weapon/stereo activation flags: weapon pose, flat probe,
  stereo and OpenXR remain disabled. Saves/preferences/SteamVR hashes still
  match, and no owned game remains. Its CIM parent lookup was denied during
  cleanup; the observed owned PID was closed directly and the empty inventory
  rechecked. The smoke intentionally terminates the hidden game, not a normal
  gameplay exit. [Final build receipt](../../vr/proof/weapon-viewmodel-build-receipt.json).
  `game.toml`, generated output, framework and UI trees are unchanged. Changes
  remain uncommitted; `.commandcode/` was not touched.

### P1-only multiplayer eye replay

- Updated the handoff before resuming from the 13-ID flat model checkpoint.
  Used the adjacent reference's native first-view reconstruction as a method,
  then independently traced Underground's frame/camera/scene calls from actual
  MP RAM. No reference address or mesh calibration was transplanted.
- Mapped context `800A0B08`, frame `80054BC4` from caller `80063CF8`, camera
  selector `80054E68`, scene draw `8006E9D8`, camera root `800A35B0`, current
  player `800A35C4` and list root `800A35CC`. Full frame/selector/scene/player
  callback byte hashes and a pure ownership/layout guard protect the bench.
- Added opt-in `MOHU_VR_MP_CONTROL=1` replay of P1 only at native 512x120.
  Canonical two-player simulation, second-view draw and waits remain outside
  the eye transaction. Each eye clears y=0, selects P1, regenerates one OT and
  submits once through guest DrawOTag. The split HUD is omitted; MP visibility
  still uses the native selector and the MP bench does not yet draw the laser.
- First render-view trials lost the gun. A no-render-view control isolated
  projection, not ownership. Absolute H=400 and weapon reference H=133 both
  clipped the authored placement. Scoped reference H=400 preserves native
  weapon/world focal ratio 133/400; native RT/TR and the world render view are
  restored at the shared epilogue, including forced loss. Those earlier images
  are rejected as complete-scene evidence.
- All 13 IDs pass native/+24/yaw+12/lost controls in both eyes across four
  closed native cycles. The last matrix snapshot has 1,215 pairs and 2,430
  rollback checks, zero mismatches/leaks/watchdogs/repairs, and equal eye
  cycles/hashes. Zero eye PNGs match exactly. Sampled world pixels stay fixed
  and the visible gun changes; source saves/preferences remain unchanged.
- The lateral +/-24 control has two populated eyes and 52,136 changed pixels.
  While MP replay and +24 model pose are active, native pistol fire reduces
  clip 8->7 and P2 health 32->31.25, with the exact native health-write trace.
  These are native shots, not tracked barrel/shot alignment.
- Deliberate backend refusal recovers fresh image pairs after clearing the
  switch. The accepted control has seven admission refusals and no failed eye.
  Earlier probes misread admission refusals as failed-eye counts, then treated
  cumulative retained/stale history as current output. A mid-right refusal
  control had one expected failed eye and recovered to a newer pair; its
  original harness verdict is retained as rejected, not silently relabeled.
- One earlier recovery probe needed forced process cleanup. The final harness
  stops admitting new transactions before TCP quit; the accepted matrix,
  lateral and fire/recovery controls all exit 0 and leave no owned game.
- The existing flat pose matrix passes all 13 IDs again. The SP zero-eye
  regression has 19 pairs and 38 rollback checks, zero errors. Its established
  harness intentionally terminates its hidden game. A strict MP ownership,
  pointer/mode/projection C fixture and diagnostic warning-as-error syntax check
  pass; all 18 Python tests pass.
- Retained [MP eye receipt](../../vr/proof/weapon-mp-eye-receipt.json) and
  [13-ID eye proof](../../vr/proof/weapon-mp-eyes.png). Restored the single
  build-release to debug OFF. Flat startup with inherited MP, weapon and stereo
  flags remains inert. Source-save and preference hashes match and no owned
  game remains. RunFlat clears the new MP bench variable as well.
- Desktop MP eye rendering is accepted at this fixture. Physical grip/scale,
  head/hand independence, native MP head-turn visibility, movement/menus and
  tracked shot alignment remain open. Production tracking/MP bench remain off;
  game config, generated output, framework and UI source remain unchanged.
  All changes remain uncommitted and unrelated .commandcode/ is untouched.

### Execution plan and handoff consolidation

- Replaced the stale pre-implementation VR plan with evidence-scoped checkboxes
  for completed foundation/mesh/MP eye work and remaining W1-W6/H/Q gates.
- Replaced the historical handoff backlog with one next task (W1.1), exact
  P38 fixture/seams/units and source entry points, a new independent-pose
  harness specification, ordered dependencies, acceptance gates, commands,
  bounded recovery, rejected-path table and session continuation record.
- Linked weapon mapping and the documentation index to the same task order.
  Clarified old baseline pins, SP/MP slot-root ambiguity, diagnostic versus
  release binary hashes, real hand samples versus direct deltas, removed debug
  APIs and cumulative refusal counters. Runtime/source/build/save state was
  not changed by this documentation-only session.
- Documentation checks passed: 54 unique task IDs, local links, whitespace and
  all six PowerShell command blocks parsed without execution. Receipt-listed
  source hashes and the release executable still match; debug tools remain OFF.

### W1 P38 absolute synthetic pose contract

- Captured W1.1 at the existing guarded first-person seam from a fresh copy of
  root MP slot 1: P38 ID 0, zero weapon switches, stationary P2 and no firing.
  The source record, native animated record, complete P38 mesh bounds, GTE
  RT/TR, native H/OFX/OFY and the complete P1 eye view were measured in one
  bounded run. The authored native basis is scaled and sheared, not
  orthonormal; its measured inverse is retained.
- Added [WEAPON_CALIBRATION.md](WEAPON_CALIBRATION.md) before implementing
  absolute placement. It names the XR-local, origin, hand, animated-model,
  native-camera and eye spaces; defines axes, handedness, matrix storage,
  source-to-destination transforms, authored placement, native animation and
  each unit boundary. W1's `(98,296,193)` pivot is explicitly provisional for
  synthetic-space validation, not physical grip calibration.
- Added absolute P38 composition that replaces the first-accepted neutral pose
  while preserving the native model-to-camera affine and animated vertices.
  Other real-hand weapon IDs remain native. The existing guarded mesh/caller/
  ownership/profile checks, RT/TR restoration and eye-view restoration remain
  in place. Invalid focus, activity, validity, age and quaternion paths fall
  back without retaining an unintended anchor.
- Extended the diagnostic hand override to carry measured host age and an
  explicit synthetic origin for this harness. The W1 hand path uses
  `48 / 0.067 = 716.4179104477612` game units/metre; the independent desktop
  head path uses 1000 diagnostic units/metre. Direct x/yaw and flat-probe
  controls were not used as hand-path evidence.
- Added `vr/tools/check_weapon_pose_spaces.py` and its fresh-process head worker.
  The retained receipt has 29 cases: two absolute fresh-load starts, hand-only
  translations and rotations, 10 head-only cases, a combined pose, origin
  change, invalid controls and valid recovery. GTE RT/TR expected-versus-
  observed error was zero; recovered-hand maxima were `6.185436e-05` rotation
  and `0.492537` translation. The origin anchor stayed within one integer GTE
  unit. Every non-zero hand case changed the visible weapon, the sampled world
  ROI stayed fixed, and both eye images were populated. Zero-IPD eyes matched.
- Retained [pose-space receipt](../../vr/proof/weapon-pose-space-receipt.json),
  [both-eye proof](../../vr/proof/weapon-pose-space-controls.png) and
  [build receipt](../../vr/proof/weapon-pose-build-receipt.json). The build
  receipt records the tested diagnostic SHA-256 `aa885d40...`, source hashes,
  unchanged source saves/preferences/SteamVR settings, 18 Python tests, strict
  C fixtures, MP matrix/lateral/refusal recovery, flat poses and SP zero stereo.
  The operator-requested W1 path did not fire.
- Restored the single `build-release` to debug OFF. Its current executable
  SHA-256 is `5916470b7058a13624fdd4393921629dea03ea1db209895c81c23e210a52dafb`;
  the inherited-flag flat smoke remained inert. No owned game or debug listener
  remains. This continuation rechecked the current source/save/preference
  hashes and reran 18 Python tests, the weapon and MP guard fixtures, diagnostic
  strict syntax, and the standalone hand-age fixture. The configured
  `openxr_input_test` target is not present in this build graph, so that fixture
  was compiled with the existing toolchain and its non-network code path.
- W1 is complete for synthetic spatial controls only. Physical grip/size,
  physical recenter, MP head-turn visibility and tracked shots remain open.
  Changes remain uncommitted; `.commandcode/` was not touched.

### W2.1 multiplayer level-selector trace

- Used a fresh copy of root MP slot 1 with P38, zero switches, stationary P2
  and no firing. The final natural two-player frame observed both scene callers:
  `80054CD4` and `80054D54` call `8006E9D8` with return addresses
  `80054CDC`/`80054D5C`. The PC probe counted 592 scene calls across 296
  frame-function hits.
- Captured complete live code for the frame `80054BC4` (`0x200`, FNV
  `6CDFBB75`), scene dispatch `8006E9D8` (`0x180`, `04C21F46`), callback
  `8006C61C` (`0x290`, `A2AAC71B`), selector `80096EF4` (`0x90`,
  `273C8059`) and selector helper `80096AC8` (`0x428`, `77C2060F`). The raw
  receipt retains all 690 decoded instructions and complete hashes.
- Measured the actual MP path as a flat scene list at `[800A35CC]`, not the SP
  PVS leaf queue. The final list had 26 nodes: two headers, 21 level nodes
  using callback `8006C61C`, one special callback and two player callbacks.
  Every level node had visibility mask `0x07020200` at `+0x0C`, render flags
  `0x00400211` at `+0x10` and auxiliary flags `0x08000001` at `+0x14`.
- The complete callback invokes `80096EF4` from `8006C664`/`8006C688`; the
  selector builds the object AABB and calls `80096AC8` from `80096F70`.
  Neither the SP selector `80099960` nor its `800B74B8` queue is
  resident/executed in this MP fixture. W2.2 must extend the measured flat
  list/object path and keep native fallback.
- Added `vr/tools/probe_mp_level_selector.py`. It owns the copied save and
  process, records both player snapshots, hashes sources/settings and writes a
  compact receipt plus ignored raw disassembly. The final run exits 0, leaves no
  game/debug listener, and confirms saves/preferences unchanged.
- Rejected attempts included a dirty-break probe that did not fire on this
  compiled overlay, then a PC-count gate that was too strict before the list
  could be read. A forced MP replay also returned no rendered pair because the
  weapon-pose seam was disabled. Those attempts were not repeated unchanged;
  the accepted run used the natural frame, direct roots and a settled PC probe.
- Retained [MP_LEVEL_SELECTOR_EVIDENCE.md](MP_LEVEL_SELECTOR_EVIDENCE.md) and
  [selector receipt](../../vr/proof/weapon-mp-level-selector-receipt.json).
  The final debug-off executable SHA-256 is
  `a32125b089d6bea881c40e09a6147f3b18c49727aae6069f63e6a266fc5f1418`;
  [build receipt](../../vr/proof/weapon-mp-level-selector-build-receipt.json)
  records the tested diagnostic hash, 18 Python tests, probe compilation,
  strict diagnostic syntax and cleanup. No MP frustum override, firing change,
  save edit or physical acceptance was made.

### W2.2 multiplayer eye-frustum measurement and guarded override

- Extended the W2.1 probe to capture the live selector inputs before changing
  selection. A fresh copied root MP slot 1, P38 ID 0, zero switches and no fire
  produced 21 unique level-node samples. Each sample retained signed-short
  center `+0x2F4..+0x2F8`, radius `+0x2FC`, GTE RT/TR, projection, screen
  bounds, camera/input/view pointers and the native selector result.
- Measured screen bounds `540x120`, H 400, OFX `256.0`, OFY `60.0`, and a heap
  view descriptor at `camera_input+0xC8`. The retained run selected three of the
  21 level nodes. The visible set is live; no node or heap address is treated as
  a static allowlist.
- Added `MOHU_VR_MP_FRUSTUM=1` as a separate guarded MP selector path. A
  function filter consumes only level-node calls from return addresses
  `8006C66C`/`8006C690` during valid P1 eye replay. It composes the measured
  center/radius cube with live RT/TR and the existing eye render view. Other
  callers and the P2 player node stay native. Complete function/callback
  hashes, P1 ownership, finite view values and non-wrapping short AABBs are
  required; failures execute the original selector.
- The first capture attempt hit a Python wrapper argument collision before
  sampling. A later capture was rejected only because one side of the node
  comparison retained `0x`; the third exposed the P2 player node as a
  legitimate non-level selector caller. Each failure identified and fixed one
  contract fact; none was repeated unchanged.
- Added `mohu_vr_mp_aabb_from_sphere`, overflow/view validation in
  `frustum.h`, and `--frustum` coverage in the existing copied-save MP harness.
  `RunFlat.bat` now clears `MOHU_VR_MP_FRUSTUM` and
  `MOHU_VR_MP_FRUSTUM_CAPTURE`.
- The final zero-angle P38 run applied 126-147 override decisions per eye across
  native/translated/yawed/lost weapon cases with zero fallback and zero
  rollback errors. Both eyes remained populated and byte-identical at zero IPD;
  pair 22 SHA-256 was
  `de83c69d0a08f5933805c07dc86ac27f2310df3ef8eb1e920b12d0608d9b3c9e`.
- Regressions against diagnostic SHA-256 `5fe5c4dd...` covered 13 IDs, 64 MP
  matrix cases, 1,282 final pairs, lateral eyes, native pistol clip 8->7 and
  P2 health decrease, six refusal/recovery, flat pose cycles and SP zero eyes.
  All saves/preferences stayed unchanged and all rollback counters were clean.
  The final release is debug OFF at
  `d13aa6496ea4a690e2018cf8ed5e44668ad4c47e4af9919342ea2ce9deca955a`;
  the inherited-flag flat smoke cleared both new variables and left no game or
  debug listener. Its hidden wrapper needed forced cleanup after the intentional
  game termination, recorded in the smoke receipt.
- Retained [MP_EYE_FRUSTUM_EVIDENCE.md](MP_EYE_FRUSTUM_EVIDENCE.md),
  [measurement receipt](../../vr/proof/weapon-mp-frustum-measurement.json),
  [both-eye control](../../vr/proof/weapon-mp-frustum-controls.png) and
  [build receipt](../../vr/proof/weapon-mp-frustum-build-receipt.json). W2.3
  zero/side/near-wall visibility and native/override equality remain open.

### Reference-game reuse audit (2026-10-26)

- Compared the current plan and feature documentation with the adjacent first
  game's documentation and implementation. The full findings and source/tool
  entry points are in [REFERENCE_REUSE_AUDIT.md](REFERENCE_REUSE_AUDIT.md).
- Confirmed framework pose math and the mod API header are byte-identical;
  input mapping, frustum math, headless ownership and copied-fixture controls
  are already partly ported. Identified reusable native-shot guards/trace
  analysis, triangle raycast, profile/batch checks and native dual-matte HUD
  extraction/surface submission. Target code/asset/layout validation remains.
- Removed the unnecessary physical-acceptance prerequisite for opt-in desktop
  tracked-aim/laser candidates and the XR-input prerequisite for read-only
  native-shot mapping. Physical accuracy and normal enablement remain gated.
- Kept all acceptance states and NEXT=W2.3. Corrected stale W1 API/preflight
  guidance and early equivalence-table status, and clarified that frustum
  plane crossing and turned native/override sets are not equality failures.
  This supersedes earlier prospective hardware-first dependency wording.
- Documentation-only review: no runtime source, framework pins, binaries,
  original saves, settings or historical receipts changed; no game/build ran.
- Validation: local and cross-repository links resolve; all 54 task IDs and
  acceptance states are unchanged; six PowerShell blocks parse without being
  executed. Latest receipt source hashes and release binary still match,
  debug tools remain OFF, and whitespace checks pass with CRLF recognized.

### Cross-game consistency handover (2026-10-26)

- Follow-up source comparison identified duplicate inverse/frustum/slab and
  laser projection/clipping calculations, with meaningful validation-policy
  differences. Input is an intentional reference port with native converter
  differences; the tested GTE weapon adapter must not be replaced just to
  match the reference's vertex-hook implementation.
- Added [CONSISTENCY_HANDOFF.md](CONSISTENCY_HANDOFF.md): C1 characterization,
  C2 extraction of exactly three pure operations, C3 both-consumer regression
  gates and C4 ownership/parity documentation. Projection/input/tooling remain
  characterized or deferred, not a mandate for a broad rewrite.
- NEXT becomes C1 for this requested pass; W2.3 stays the next feature after
  C4. Added four unchecked C items without changing any existing feature
  acceptance. No refactor, runtime test, source/build/save/settings change or
  edit to the first-game checkout was performed by this documentation turn.
- Handover checks passed: nine documentation files' links resolve, original
  54 task states are preserved, four C items are unchecked, current pointers
  agree on C1, and the six PowerShell blocks parse without execution. Latest
  runtime source and release-executable hashes still match the retained receipt.

## Next work

**C1: characterize cross-game helper parity.** Execute the bounded C1-C4 pass
in [CONSISTENCY_HANDOFF.md](CONSISTENCY_HANDOFF.md), then resume W2.3 visibility
validation without reopening completed engine/mesh/pose work. Use
[HANDOFF.md](HANDOFF.md) as the execution contract and
[VR_PLAN.md](VR_PLAN.md) as the only checkbox/status list. Prior log entries are
historical results and rejected attempts, not instructions to repeat them.
Consult the reuse audit before adding code; extend existing helpers and follow
the corrected desktop/hardware dependencies instead of rediscovering systems.
