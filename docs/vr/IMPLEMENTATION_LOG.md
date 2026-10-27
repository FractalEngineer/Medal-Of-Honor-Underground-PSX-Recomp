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

### Shared VR geometry extraction (2026-10-26)

- C1 added the file-local inverse seam, two distinctly named host adapters, one
  common numeric vector set and
  [check_reference_parity.py](../../vr/tools/check_reference_parity.py). The
  baseline exposed the expected inverse policy split and Underground's partial
  failure write, plus a non-finite ray-origin gap.
- C2 added `psxrecomp/runtime/include/vr_geometry_math.h` and
  `psxrecomp/runtime/src/vr_geometry_math.c`. Both game framework copies now
  contain the same source hash
  `9e51708f0f05a16182e4d5893063a06f656d4fc723965f72cea9191632661a23`.
  The shared framework commit is `555e1eab`.
  Inverse wrappers retain separate limits; MP expansion/view validation and all
  tree layouts, masks, hooks, projection, input and weapon behavior stayed local.
- The 33-case parity run passes after extraction. Inverse rejection now leaves
  the caller's output untouched in both consumers. The shared ray test rejects
  malformed inputs instead of inheriting either wrapper's weaker checks.
- C3 release builds pass in both checkouts. Underground's existing controls pass
  at zero/lateral/side head poses, with native/translated/yawed/lost weapon
  cases, native pistol fire, refusal and fresh-pair recovery. Reference host
  aim/frustum/raycast fixtures pass. A headless cold boot reached Mission 1 and
  captured a fresh slot 9 under the diagnostic execution identity, leaving all
  source `.pst` files unchanged. Five world-stability views had unique per-eye
  crops and 1,546 rollback checks with zero mismatches. All eight weapon-aim
  controls passed. A tracked-weapon watchdog aborted one right eye, retained
  pair 1065 and later published complete pair 1163; its run had one watchdog,
  one nesting repair, 2,328 verification checks and zero mismatches.
  Release builds with OpenXR OFF also link in both repositories.
- C4 added the same ownership rule to both game handoffs, a shared-policy test
  to both VR test workflows, and
  [reference-parity-receipt.json](../../vr/proof/reference-parity-receipt.json).
  Historical receipts and source saves were not changed. Both builds were
  restored to debug OFF; no game or VR process remains.

### W2.3 multiplayer head visibility and near-wall control

- Extended `check_mp_view.py` with one `--visibility-controls` mode rather than
  adding another renderer or selector framework. The diagnostic sampler now
  captures native and shared-frustum results for every level node in each eye,
  and local `enable`/`disable` actions keep OFF/ON controls in one owned process.
- Zero yaw retained every natively visible node and populated both 512x120
  eyes. The override selected 7 nodes versus 3 native nodes per eye.
- +90 and -90 degrees used separate measured native body rotations because the
  flat fixture exposes one side at a time. Both selected justified changed sets
  and retained real top-screen world geometry in both eyes.
- A fresh slot reload followed by a native forward approach measured two
  consecutive chunks at or below 200,000 raw position units. The near-wall
  pair retained 23,040 top-screen world pixels per eye.
- All four controls had matching zero-IPD eye hashes/cycles, zero frustum
  fallback and zero rollback mismatch, leak, watchdog or nesting repair.
- The final run passed 23 Python tests, strict frustum/MP fixtures and
  diagnostic syntax. Regressions passed the 64-case MP matrix across 13 weapon
  IDs, lateral eye offset, native pistol fire and refusal recovery, flat
  inventory and SP zero.
- Retained [W2.3 controls](../../vr/proof/weapon-mp-visibility-receipt.json),
  [control sheet](../../vr/proof/weapon-mp-visibility-controls.png) and
  [build/regression receipt](../../vr/proof/weapon-mp-visibility-build-receipt.json).
  Debug tools were restored OFF; source saves, preferences and historical
  receipts remain unchanged.

### W2.4 multiplayer input binding

- Traced the MP overlay independently from the SP input path. The copied slot
  uses converter `0x800799E4`, dispatcher `0x80079B28`, P1 actions
  `0x800C0ED0`, inversions `0x800C0F20`, axes `0x800C0BF0` and curve
  `0x800A458C`; the SP addresses contain unrelated MP overlay code/data.
- Added a mode adapter to the existing controller source. It identifies MP from
  both valid player actors, the current-player root and the native 512x120/H=400
  context, then guards the converter/dispatcher and all selected table hashes.
  Unsupported or stale layouts return neutral; rendering replay never samples
  input and the pure mapper remains the sole action-to-pad implementation.
- Added `vr/tools/probe_mp_input.py` for the copied slot-1 ownership/hash probe
  and six synthetic controls through the framework host-pad and XR override
  path. Neutral, forward, strafe-right, turn-right, focus loss and trigger/Cross
  passed; forward/strafe changed position and turn changed rotation.
- Extended `test_input.c` with the measured MP curve and selected 15360/8960/8960
  axis response, and extended `test_mp_view.c` with the outside-render MP input
  ownership guard. Corrected `check_movement.py` to explicitly load SP slot 2;
  its 13-case regression, 304 rollback checks and settings restoration pass.
- The final MP probe passed all six MP code/table hashes. The 23 Python tests,
  strict input/MP-view/frustum/raycast/HUD fixtures, diagnostic syntax, fresh
  33-case cross-game parity and final debug-off release build pass. A refresh of
  the unchanged flat build tree stalled in its mod-staging target; the existing
  diagnostics-off binary remains the recorded flat artifact and W2.5 still owns
  flat fallback acceptance.
- Retained [MP input controls](../../vr/proof/weapon-mp-input-receipt.json) and
  [build/regressions](../../vr/proof/weapon-mp-input-build-receipt.json).
  Source saves, preferences and historical receipts remain unchanged.

### W2.5 multiplayer input lifecycle and fallback

- Kept the accepted MP mapper and mode binding unchanged. Moved the eye-replay
  guard ahead of the XR input query and added invisible counters for callbacks,
  selected input mode, focus loss, render-blocked sampling and guard fallback.
  This makes the existing no-render-input policy testable without replacing the
  pure mapper.
- Extended `probe_mp_input.py` to 17 exact controls: neutral, both directions of
  forward/back, strafe and turn, focus loss/recovery, inactive sticks, Cross,
  Square, Circle, Triangle, L2, combined buttons and release. The native pad
  values, actor position/rotation changes and released state all pass.
- Native Start produced pad `0xFFF7`. While paused, holding forward still
  produced pad LY `1` but did not move P1; a second Start resumed forward motion.
  Across 630 controller callbacks, render-blocked sampling and guard fallback
  both remained zero.
- Kept SP validation as a cold normal-launch boundary: copied isolated slot 2
  passed 13 controls, 298 rollback checks, 211 SP samples and zero MP/menu
  samples. An attempted MP-savestate-to-SP-savestate swap was rejected because
  the resident MP overlay remained active and the strict converter guard
  correctly returned neutral.
- Rebuilt the OpenXR-off `build-flat-check` target. Its inherited-flag startup
  reached `main()` with six framework packages and no active input, MP or stereo
  marker. The run was intentionally terminated after 35 seconds; source saves
  stayed unchanged.
- Final checks passed 23 Python tests, all strict input/MP-view/menu/frustum/
  raycast/HUD/weapon fixtures, diagnostic syntax and the 33-case cross-game
  parity baseline. The diagnostic, debug-off release and flat executables are
  `3f45dbe...`, `02bd98ff...` and `18f4328...` respectively.
- Retained [W2.5 controls](../../vr/proof/weapon-mp-lifecycle-receipt.json) and
  [build/regressions](../../vr/proof/weapon-mp-lifecycle-build-receipt.json).
  Earlier receipts and source saves were not changed.

### W3.1 P38 model-local calibration

- Added a focused read-only probe that copies root MP slot 1, loads P38 ID 0,
  configures the existing synthetic hand and eye controls, and captures the
  selected node's complete source and animated vertex arrays at the W1 seam.
  The first implementation found that the animated output pointer is a
  per-frame buffer; the final probe stores both arrays atomically in the plugin
  and returns bounded chunks instead of rereading a moving guest address.
- All 69 node-13 vertices match the captured geometry identity. The animated
  grip block center is `(76.555555555556, 100.777777777778,
  287.888888888889)`, the muzzle cap center is `(76.2, 109.8, 396.8)`, the
  forward span is `114.525481833051` model units, and the three axes are
  orthonormal.
- Added inert P38 calibration metadata to `MohuVrWeaponProfile`. The scale is
  `530.210564041902` model units per metre using a nominal 216 mm P38 length
  and is explicitly provisional. The W1 camera-space pivot remains the active
  diagnostic rotation marker; the renderer, input, hooks, shot path and normal
  defaults did not change.
- Added `probe_weapon_calibration.py` and `check_weapon_calibration.py`, and
  extended the strict weapon fixture with marker, axis, scale and unsupported-ID
  checks. The final capture had matching zero-IPD eyes, 17 stereo pairs, zero
  failures and zero render-verification mismatches.
- Final checks passed 23 Python tests, strict weapon and MP-view fixtures,
  diagnostic syntax, and the fresh 33-case cross-game parity baseline. The
  release executable is `9eca8fa6...`; the tested diagnostic executable is
  `d59a6a2f...`. Source saves, preferences and historical receipts remain
  unchanged, and no owned game or debug listener remains.
- Retained [calibration](../../vr/proof/weapon-p38-calibration-receipt.json),
  [atomic capture](../../vr/proof/weapon-p38-calibration-capture-receipt.json)
  and [build/regressions](../../vr/proof/weapon-p38-calibration-build-receipt.json).

### W3.2 P38 headset comparison preparation

- Added `vr/tools/probe_p38_headset.py`, a bounded native/tracked P38 runner that
  copies root multiplayer slot 1 separately for each mode, enables movement and
  the accepted MP controller path, validates the 354-face/14-node P38 model,
  samples real hands and input, and keeps headset acceptance false.
- The two-second synthetic comparison passed both modes. The runner preserved
  source-save and settings hashes, sampled stereo pairs in both modes, and
  drained all owned processes. The local suite is now 29 passing Python tests.
- The first real-headset attempt loaded the copied P38 successfully but OpenXR
  did not begin stereo. The runtime recorded `OpenXR begin failed; flat native
  surface remains active`, and the probe recorded `OpenXR did not submit stereo
  frames`; this became evidence of the sandbox-account/runtime boundary, not a
  headset failure.
- Rerunning the probe under the interactive `titan` account with the VDXR
  manifest succeeded for separate 30-second native and tracked passes. Each
  mode produced 30/30 focused live-hand samples; stereo pairs advanced
  `21->522` and `19->515`, XR submissions advanced `18->525` and `15->518`,
  and the final sample reported zero failures.
- Kept `PSX_DEBUG_TOOLS=ON` during active W3.2/W3.3 work per operator direction.
  Retained the [successful headset proof](../../vr/proof/weapon-p38-headset-receipt.json)
  and [complete build receipt](../../vr/proof/weapon-p38-headset-complete-build-receipt.json).
  The synthetic dry run and blocked sandbox-account attempt remain historical.
- Operator review of the completed headset transport rejected W3.3: controls
  were absent, a noise filter was visible, hand motion rotated around a pivot
  instead of following the controller, and arms remained attached to the gun.
  The transport result remains valid, but acceptance stays open.

### W4 native P38 shot contract and W5.1 desktop combat

- Reviewed advancement through W3.2 and retained the failed W3.3 operator gate.
  The user's current direction is desktop progress without another headset run.
  Adapted the reference constructor-to-basis and streaming trace strategy,
  preserving shared inverse/pose math and title-specific guards.
- Fixed the comparison runner's absolute neutral load-time pad override; it now
  releases it and uses a neutral host layer. It also disables dithering. Native
  and tracked desktop fire now reach the guest through the XR controller source.
- Measured constructor 800486D0, basis 8006C8B0/caller 800488D8, 16.16 fields,
  history, first motion and the exact shot-linked P2 health writer. Five native
  idle/fire/away/P2/head cases pass. Callback-entry GTE was a previous-object
  matrix; the corrected cache samples the guarded canonical global 800A2CEC
  outside replay and inverts back to the native camera actor within tolerance.
- Added separately enabled P38 calibrated rendering and native-shot candidates.
  Both use the same quantized measured grip/model affine. The native constructor
  then builds basis/history and owns motion, collision, ammunition and damage.
  P2, unsupported IDs, replay, stale cameras and invalid tracking are guarded.
- The initial gun-only candidate wrongly retained node13 alone. Operator review
  found the missing barrel. Topology/atomic vertex inspection identified the
  disconnected node11 vertices6..32: 27 vertices and 37 barrel/sight triangles.
  The corrected complete gun retains 128 triangles/96 vertices and hides 142
  arm/hand vertices. Native triangle strips and animation data are preserved;
  full source geometry and the 4,320-byte stream, including final terminator,
  are hash-guarded. The old node13 muzzle was a receiver cap; the current true
  tip is (81.8,110.6,447.6), with barrel-ring axis and provisional complete-gun
  scale 760.489674616524 units/metre. Historical W3.1 receipts remain unchanged.
- The final 14-case desktop batch passes aim-toward/away, +100 mm hand
  translation, head/body turns, nearer/farther positions, P2, MP40, unfocused,
  inactive, partial, stale and recovered hands. Tracked hits reduce P2 health
  32->29 through native shot-linked damage; aim-away leaves health32. Invalid
  hands retain native P38 fire (32->31.25), and MP40/P2 remain native.
- Numerical checks match the rendered barrel tip to native first motion within
  one 16.16 origin step, with axis cosine >=.999995. Both eyes retain the barrel,
  hand translation changes gun pixels while the fixed world ROI is identical,
  and the final batch has 679 pairs / 1,358 rollback checks with zero mismatches.
- Validation: 38 Python tests, strict weapon/calibrated/shot C fixtures and
  diagnostic syntax; 33-case shared parity; unchanged W1 spatial controls;
  all 64 MP pose cases across13 IDs/four closed cycles; lateral eyes, native
  pistol clip8->7/P2 health32->31.25 and refused-pair recovery; SP zero stereo;
  rebuilt OpenXR-off flat startup with inherited candidate flags inert.
  The unsupported combined all-weapons/fire harness invocation was rerun as
  separate controls; no partial failure is promoted as a complete receipt.
- Source saves/preferences are unchanged, every owned game closed, framework
  pins unchanged, and active debug tools remain ON per operator direction.
  No headset/runtime was launched.
- Current evidence: [contract](P38_NATIVE_AIM_EVIDENCE.md),
  [native receipt](../../vr/proof/weapon-native-shot-receipt.json),
  [combat receipt](../../vr/proof/weapon-p38-aim-receipt.json),
  [complete calibration](../../vr/proof/weapon-p38-complete-calibration-receipt.json)
  and [build receipt](../../vr/proof/weapon-p38-native-aim-build-receipt.json).

### W3.4 all-ID complete-gun profiles and controls

- Added a data-driven complete-gun profile to `MohuVrWeaponProfile`. Long guns
  use measured whole-node masks; P38 and the silenced pistol use an explicit
  256-bit mask because their gun islands share node 11 with hand geometry.
- Extended the bounded native strip decoder into an all-ID topology validator.
  It recomputes the captured geometry identity, decodes every triangle, rejects
  mixed gun/arm triangles and checks exact selected face/vertex totals.
- Added a single-process profile probe over copied MP slots 1-4. Sixteen native
  slot appearances cover 13 unique IDs; source and animated vertices are
  captured for every non-empty node without firing.
- Derived provisional grip, orthonormal axes, forward span and nominal-size
  scale for the other 12 IDs while retaining P38's accepted values exactly. The
  fixed synthetic pose is explicitly not physical acceptance.
- Added `MOHU_VR_WEAPON_GUN_ONLY` and `MOHU_VR_WEAPON_CALIBRATED`; both default
  OFF. The P38-specific calibrated and aim flags remain separate. The flat
  launcher clears the new flags.
- The historical bootstrap-binary MP matrix passed 64 cases across all 16 slot
  appearances with both eyes, translated/yawed/lost controls, 876 per-eye gun
  masks and zero
  rollback/VRAM/watchdog/nesting failures. The control sheet shows complete gun
  crops without arms for all 13 IDs.
- Historical bootstrap validation: 47 Python tests; strict C weapon,
  calibrated-affine and
  diagnostic checks; default P38 eye replay; native fire/ammo/P2 damage and
  refusal recovery; 14-case tracked P38 aim/fallback; SP zero; rebuilt flat
  startup with inherited flags inert. Source saves/preferences are unchanged
  and no owned game remains.
- Evidence: [profiles](WEAPON_COMPLETE_PROFILES.md),
  [topology](../../vr/proof/weapon-complete-gun-topology-receipt.json),
  [animated capture](../../vr/proof/weapon-profile-captures-receipt.json),
  [provisional calibration](../../vr/proof/weapon-provisional-calibrations-receipt.json),
  [controls](../../vr/proof/weapon-complete-gun-controls-receipt.json) and
  [build receipt](../../vr/proof/weapon-all-id-profiles-build-receipt.json).

### W3.4 moving muzzle and native animation controls

- Added a latched all-vertex diagnostic snapshot at the existing animated-model
  seam. A request is filled once from the next complete model frame, then all
  marker chunks read that frozen sequence without crossing animation frames.
- Added a single-process copied-save animation probe over all 13 IDs. Native
  press windows drive recoil, reload, switching, scope and prop hold/release
  paths; every confirmed control records a clip, reserve or weapon-slot change.
- Recomputed grip and tip points from their measured vertex groups at each
  frozen frame. The predeclared limits are 1% of idle grip-to-tip span and two
  degrees. Every ID exceeds the limits somewhere in its confirmed states, so
  the stored idle point is not animation-safe. The crossbow launch sample alone
  remained rigid, but its switch sample did not.
- The matrix confirms 13 switches, nine recoil paths, seven reload paths, three
  prop special actions and the scoped hidden-model state. Sten reload and
  scoped-shot ammo were not observed and are recorded as limits, not passes.
- Validation: 52 Python tests; strict MP and weapon C fixtures; diagnostic
  syntax/build; 64 calibrated all-ID eye cases with 804 current-binary masks;
  P38 native fire/refusal recovery; 14-case tracked P38 aim/fallback. Source
  saves/preferences are unchanged and no owned game remains.
- Evidence: [moving-marker receipt](../../vr/proof/weapon-moving-muzzle-receipt.json),
  [control sheet](../../vr/proof/weapon-moving-muzzle-controls.png),
  [build receipt](../../vr/proof/weapon-moving-muzzle-build-receipt.json) and
  [profiles](WEAPON_COMPLETE_PROFILES.md).

### W5.3 multiplayer shot-family map

- Extended explicit shot capture so W5.3 can sample actor-valid basis calls
  without enabling writes. A `start-p1` mode filters to the live P1 owner, while
  the existing broad control retains P2/NPC evidence.
- The basis hook now requires valid shot/owner actors and `A0 == S0`. P38's
  override remains behind the prior type, caller, ownership, model and camera
  guards; all other IDs were sampled read-only.
- Copied MP slots 1-4 covered the first occurrence of all 13 IDs. Every ID used
  caller `0x800488D8`. Measured types are `13F1` Panzerfaust, `13F3` stick and
  petrol bombs, `13F6` P38/scoped rifle/Colt/silenced pistol/M1, `13F7`
  MP40/shotgun/Sten/StG44 and `13FA` crossbow.
- One shotgun trigger window constructed six pellets. Action windows changed
  clip for every firearm, reserve for the Panzerfaust, and slot/reserve for the
  thrown items and crossbow. The isolated scoped path is recorded by ordinary
  native fire because raw R2 plus fire did not construct a shot.
- Added `mohu_vr_shot_type()` / `mohu_vr_shot_family()` and strict fixture
  coverage. Unknown IDs return native.
- Validation: 57 Python tests; strict MP, shot and weapon C fixtures; diagnostic
  syntax/build; complete all-ID family capture; five-case native P38 and
  14-case tracked P38 aim. Source saves/preferences stayed unchanged, no owned
  game remained, and normal defaults stayed off.
- Evidence: [family evidence](SHOT_FAMILY_EVIDENCE.md),
  [receipt](../../vr/proof/weapon-shot-families-receipt.json) and
  [build receipt](../../vr/proof/weapon-shot-families-build-receipt.json).

## Next work

**W5.3d: opt-in family-aware shot conversion, without a headset.** Read the exact
experiment in [HANDOFF.md](HANDOFF.md). Native family/lifecycle and final-origin
mapping plus the canonical animated-marker contract are complete. Reuse the
existing producer and quantized-affine/inverse helpers; capture complete code
guards at the known family stages before new writes. W5.3e remains matched
tracked controls. W5.2 needs its compatible copied NPC/SP fixture and
independent SP bindings; W3.3/W3.5 remain physical. Preserve native gameplay,
source saves, defaults, historical receipts and unrelated `.commandcode/`.

## 2026-10-27 — framework delivery tracker and W5.3 native lifecycle

- Added [FRAMEWORK_UPSTREAM_TRACKER.md](FRAMEWORK_UPSTREAM_TRACKER.md): the three
  generic commits stay on `vr/shared-development` at `555e1eab`; fork master
  mirrors upstream `1a3fc0db`. Both games retain tested `555e1eab` gitlinks.
  Listed the future per-feature PR split without creating branches/PRs for it.
- Queried GitHub: the earlier VR stack #739-#746 is merged, including readiness
  commit `31df2e1e`. Its first-game PR draft is historical, not pending work.
  Documented the `.gitmodules` remote-master caveat and explicit pin policy.
- Reviewed current first-game aim/guards and the local plan. The shared inverse,
  visibility and slab math remains the source of truth; the 33-case host parity
  harness passed again. Corrected stale audit/consistency pointers without
  reopening C1-C4 or claiming another runtime/hardware acceptance.
- Extended the existing family probe with `--lifecycle` and optional collector
  filters. It streams native construction, position history, full motion/update
  context, complete XYZ groups and exactly linked native damage. Per-ID raw
  traces are saved before analysis, so failures can be inspected offline.
- Automatic fire demonstrated object reuse. Lifetimes now use ordered native
  constructor sequence bounds, not an address/frame-only identity. Added
  malformed-history/XYZ/field, reuse, spread and receipt-hash fixtures. Corrected
  the proof finalizer to hash final raw bytes without self-reference; historical
  family receipts remain unchanged.
- Final native matrix: 13 IDs, 22 lifetimes, 147 complete XYZ groups and 19
  linked native damage writes, including rocket and crossbow. No shot override
  was enabled. Six shotgun trajectories span `5.252537956386305` degrees despite
  identical basis angles. Both thrown items were constructed after release;
  no thrown explosion-damage or zoom-plus-fire acceptance is claimed.
- Measured basis-to-first-integration start differences: grenade `(9,0,332)`,
  petrol bomb `(8,0,149)`, Panzerfaust `(27,0,431)` world units. Other IDs had
  zero difference. A focused all-PC object-address query over the full retained
  ring then resolved grenade stores `80084CC0/CCC/CD8`, petrol stores
  `80084AF0/B18/B40`, and rocket constructor stores `80048A20/A48/A70`.
  Focused petrol/rocket Z differences were 150/432, proving those baseline
  shifts are not fixed compensation constants.
- The grenade release path calls basis again at `80084CD4`, RA `80084CDC`,
  then initialization `800517B4`. Here the shot is `A0 == S1` and S2 is P1
  input, so the existing constructor-only observer/override does not cover it.
  Retained live code windows show the actual stores and surrounding calls; full
  code guards and ownership policy still need validation before any new writes.
- Added `probe_projectile_origins.py` and four origin-history failure fixtures.
  The successful three-control probe uses the accepted eight-frame trigger
  window; an earlier four-frame grenade attempt did not construct a shot.
- Validation: 72 Python tests, 33 shared-math cases, final raw/proof/source and
  unchanged executable hashes. Runtime C/framework sources did not change, so
  no rebuild or unchanged P38/stereo matrix was required. Source saves and
  preferences stayed unchanged; owned processes closed; no headset/XR runtime
  launched. No commit/push requested in this pass.
- Evidence: [lifecycle](SHOT_LIFECYCLE_EVIDENCE.md),
  [compact receipt](../../vr/proof/weapon-shot-lifecycle-receipt.json),
  [origin writers](../../vr/proof/weapon-projectile-origin-writers-receipt.json),
  [validation receipt](../../vr/proof/weapon-shot-lifecycle-validation-receipt.json).
  W5.3a/b are checked; parent W5.3 and its moving-origin, conversion and tracked
  preservation substeps remain open.

## 2026-10-27 — W5.3c canonical animated-marker contract

- Committed/pushed the preceding framework tracker and native lifecycle work as
  `8fac00d` under the owner's commit/push/continue request.
- Added a default-disabled, read-only natural P1 producer at the existing
  post-animation `800894DC` seam. It checks the native entry/stack/caller/H=133,
  live source model and vertex hash, copies the measured marker vertices, and
  rejects eye replay/P2 drawing. No model, projection or shot field is written.
- Added immutable per-shot selected-vertex snapshots, pure mean/usability guards,
  a host load generation via the existing framework restore callback, and bounded
  diagnostic commands. Marker groups are the existing W3.4 selections; P38 uses
  barrel rings, while other grip-tip axes remain explicitly provisional.
- Three separate observers sample grenade after its second basis call, petrol
  after the optional clamp, and rocket after its constructor adjustment. The
  initial constructor ring remains unchanged. Observed instruction/register
  checks are not promoted to complete write guards.
- Final all-ID measurement passes 13 IDs / 18 initial shot events / three final
  origins. Maximum initial age is 1,128,671 cycles under a 2,257,920-cycle limit;
  maximum independent NumPy mean error is `4.2857095650106203e-10`. All three
  final stages use the same completed source sample as initial construction.
- Six controls pass: fresh, frozen/stale, recovered, frozen-cache load rejection,
  fresh P1 cache rejected for P2 fire, and disabled sampling. All fire through
  native ammo logic. Load rejection covers generation and real clock reversal.
- Validation: 77 Python tests including the strict C fixture and original group
  comparison; strict diagnostic syntax; Release rebuild; fresh 33-case parity;
  five native / 14 tracked P38 regressions with 901 pairs, 1,802 rollback checks
  and zero failed pairs or mismatches. No framework/generated/config changes.
- The all-ID sample reports 300 discarded eye attempts, isolated to the petrol
  fixture and reproduced with the sampler disabled. Both have zero rollback
  mismatches; a focused crossbow-death control has zero discards. Retained exact
  counts/controls prevent a false zero-discard stereo claim. No render guard was
  relaxed to hide that fixture behavior.
- Current executable: `cf399e543a90a8ec9c09eea62f9ab7fd838fde1229d33e23957d8b9ea1b47e68`.
  Debug/diagnostics remain ON for active work; sampler and candidate flags default
  OFF. Source saves/preferences are unchanged, owned processes closed, and no
  headset/XR runtime launched.
- Evidence: [canonical contract](CANONICAL_MARKERS_EVIDENCE.md),
  [marker receipt](../../vr/proof/weapon-canonical-markers-receipt.json),
  [build/affected regressions](../../vr/proof/weapon-canonical-markers-build-receipt.json).
  W5.3c is checked. Parent W5.3 and W5.3d/e remain open; no non-P38 override or
  moving barrel/impact acceptance is claimed.

## 2026-10-27 - W5.3d animated-marker family conversion

- Added `mohu_vr_weapon_animated_shot()` as the shared immutable-tip/declared-
  axis conversion. The historical P38 muzzle helper is now a compatibility
  wrapper, with degenerate-axis, nonfinite and atomic-output fixtures.
- Added default-OFF `MOHU_VR_WEAPON_AIM`, requiring `PSX_VR_WEAPON_POSE=1` and
  `MOHU_VR_WEAPON_CALIBRATED=1`. The existing natural P1 marker producer and
  quantized render affine are reused. When the new flag is absent, the old P38
  path and its MP40-negative/fallback behavior remain unchanged.
- Normal firearms and the crossbow write at the common basis entry. Grenade,
  petrol and rocket are deferred to `80084CDC`, `80084B74` and `80048AAC`,
  guarded by the complete 1,872-byte release-flow hash or the existing
  constructor hash plus exact stage words and live register/type/ownership
  checks. Native initialization, release, RNG, spread, speed, gravity,
  collision, ammo and damage continue.
- Added `probe_weapon_aim.py`, which solves each synthetic hand pose from that
  profile's animated axis, verifies the immutable per-shot marker conversion,
  traces first motion and linked P2 damage, and records shotgun spread/speed.
- All 13 IDs / 23 events passed with zero shot fallbacks. P38, MP40 and every
  expected firearm/bolt/rocket produced linked native damage. Shotgun retained
  six pellets, 5.1817 degrees maximum spread and 378.89 world-units/frame speed
  range. Grenade and petrol passed guarded stage/motion controls without damage
  claims. The long stereo run reproduced the petrol discard burst, then
  published pair 2,777 after failure 841 with zero rollback mismatches.
- Validation: 81 Python tests; strict C/syntax fixtures; 64-case MP matrix;
  lateral, native fire/recovery, flat pose and SP zero; 14 legacy P38 controls
  with 684 pairs and zero failures; 33-case shared parity; inherited-flag
  OpenXR-off flat startup. Debug tools were restored OFF after testing.
- Evidence: [all-family receipt](../../vr/proof/weapon-aim-all-receipt.json) and
  [build/regressions](../../vr/proof/weapon-aim-all-build-receipt.json). The
  tested executable is `4a17ce5c...`, and the final debug-off executable is
  `e2103a9f...`. W5.3d is checked. W5.3e paired preservation/impact, W5.2 NPC/SP
  and physical W3.3/W3.5 remain open.

## 2026-10-27 - W5.3e paired preservation and impact

- Extended the native lifecycle probe with the live LCG update at `80016DBC`,
  state `800C4E5C`, explicit trigger/release bounds and per-weapon RNG state
  sequences. The tracked probe now records the same constructor-to-motion
  lifetimes, family origin stages and target-ray residuals.
- Added `check_weapon_preservation.py` to join separately activated native and
  tracked receipts. It checks common-prefix shot types, release phases, history
  groups, family origin stages, per-shot ammo, object-reuse observation,
  shotgun construction RNG, six pellets, angle/speed distributions, rendered
  axis and real P2 damage. Native and tracked source saves and preferences must
  be identical between launches.
- The full pair passed 13 IDs. Native/tracked lifetimes were 22/21 and linked
  damage writes 18/16; the final StG44 lifetime at the release boundary is the
  one allowed frame-local difference. Automatic-fire displacement tolerances
  are separate from single-shot/bolt limits.
- The shotgun retained six pellets, exactly 21 construction-scoped RNG updates,
  5.257088/5.259963 degree maximum pair angles, 0.010589 degree median
  pair-angle delta and a 1.00003 median speed ratio. Missing/stale markers,
  unfocused hand and P2 fire stayed native; a focused recovered control became
  tracked again. The run recorded 379 replay-rejected and 94 P2-rejected marker
  updates.
- Validation: 86 Python tests, affected shot/calibrated-weapon C fixtures,
  strict diagnostic syntax, a focused P38/shotgun pair and the complete 13-ID
  pair. The Release/OpenXR/diagnostics/debug-tools build is
  `8d0db606...`; all candidate flags remain OFF by default.
- Evidence: [preservation evidence](WEAPON_PRESERVATION_EVIDENCE.md),
  [paired receipt](../../vr/proof/weapon-preservation-receipt.json) and
  [build/regressions](../../vr/proof/weapon-preservation-build-receipt.json).
  W5.3 and W5.3e are checked. At that checkpoint, W5.4 combat states, W5.2
  NPC/SP and physical W3.3/W3.5 remained open; the W5.4 desktop portion is
  recorded in the following entry.

## 2026-10-27 - W5.4 paired combat-state desktop matrix

- Added `probe_weapon_combat_states.py` and host fixtures. The probe runs native
  and tracked modes separately against the same copied MP fixtures, executable,
  source saves and preferences. It records shot types, ammunition, linked P2
  damage, marker sequences/generations/ages and first-motion origin errors.
- Reload tail records an early interlock with no shot/damage, then a post-tail
  P38 shot with one round consumed and linked damage. Empty fire captures the
  final round and requires the immediate second press to add no shot; the native
  auto-reload transition is recorded separately. Switch during reload produces
  zero shots/damage while changing slot. Load recovery advances tracked marker
  generation 6->7 and fires one linked-damage shot.
- Scoped ID 5 uses the measured 60-frame R2 plus 60-frame Cross+R2 control and
  two shots. It remains a recorded native fallback because the hidden-scope
  ordinary family guard has no fresh candidate marker. Recoil follow-up turns
  the native view away so the second shot exposes converted origin and first
  integration without merging into a P2 hit.
- The all-13 type/damage gate remains the accepted W5.3e receipt. W5.4 does not
  repeat its conversion matrix. Non-fallback tracked origins and first-motion
  origins were zero at recorded precision; normalized axis cosines were `1.0`.
- Validation: 92 Python tests; the W5.3e pair checker; proof/source/pair-receipt
  provenance; clean mode exit codes; unchanged source saves/preferences; no
  remaining owned game. The executable remains `8d0db606...`; no runtime C
  source changed, so no rebuild or new physical/headset claim is made.
- Evidence: [combat-state evidence](COMBAT_STATE_EVIDENCE.md),
  [paired receipt](../../vr/proof/weapon-combat-states-receipt.json) and
  [build/validations](../../vr/proof/weapon-combat-states-build-receipt.json).
  W5.4a/b are checked. Operator barrel-to-impact confirmation, the unexercised
  death transition, W5.2 live NPC/SP and physical W3.3/W3.5 remain open.

## 2026-10-27 - W5.4c P1 death, native respawn and fresh tracked shot

- Reviewed advancement against current receipts: W5.3d/e and W5.4a/b were
  already complete. The previous next-pointer combined physical alignment with
  a still-open desktop death test. Split W5.4c desktop lifecycle from W5.4d
  physical acceptance; NEXT is now W6.1 under a six-step capture contract.
- Added `probe_weapon_death.py`, reusing the combat runner's copied saves,
  process ownership, explicit environment and cleanup through an optional case
  registry. The accepted six-case matrix and its hashes are unchanged.
- The paired final control observed P1 health 32->0->32 through exact native
  P2 damage and native respawn. All 34 native / 29 tracked P2 attack shots
  remained candidate-ineligible. The respawn press constructed no P1 shot;
  a later P38 shot consumed one round in both modes. Tracked markers changed
  valid->invalid->valid without changing P1 actor/input or load generation.
- The recovered tracked sample used a new post-death marker: origin error
  `0.0000072954` world units, first-motion error `0`, normalized axis cosine
  `0.9999991904`. No post-respawn damage is claimed for the upward shot.
- Fixture corrections are retained in the evidence: fixed-turn crossbow and
  continuous-turn/salvo recipes were unreliable; short native turns/bursts
  measured useful aim. Observe restored health before calling a fire input a
  recovered shot. Signed lethal subtraction must be linked to its native zero
  clamp, rather than requiring zero at the subtract instruction.
- Validation: 103 Python tests, including signed-health/clamp, wrong-victim,
  P2 ownership, respawn extra-shot, load-substitution, stale-marker and nonfinite
  conversion rejection; independent proof/raw/source/binary hashes; clean mode
  exit codes; unchanged source saves/preferences; no remaining owned game or
  listener. Both modes had stereo inactive (zero verification checks), so no
  new rollback or stereo-death acceptance is claimed.
- Evidence: [death/respawn evidence](DEATH_RESPAWN_EVIDENCE.md),
  [paired proof](../../vr/proof/weapon-death-respawn-receipt.json) and
  [validation](../../vr/proof/weapon-death-respawn-validation-receipt.json).
  The executable remains `8d0db606...`; no runtime C or shared math changed, so
  no rebuild, repeated parity matrix or headset session was needed. Debug tools
  remain ON for active desktop work; candidate defaults remain OFF. No
  framework pin or reference checkout changed. `.commandcode/` was untouched.

## 2026-10-27 - Shared hand-fixed shot/laser ray and W6.1 capture

- Committed/pushed the prior death checkpoint as `69cda7c`. Continued W6.1 by
  extending the guarded existing projection capture with immutable per-eye
  controls/view/model diagnostics and complete-pair/restore ownership.
- The operator clarified the intended behavior: the laser points where the
  bullet goes, fixed to the hand; native recoil animation plays independently.
  Replaced the opt-in all-family shot reference with fixed profile muzzle and
  forward via the existing `mohu_vr_weapon_muzzle_shot` helper. The ray capture
  uses the same helper/affine. Animated markers remain diagnostics and guard
  data. Existing native animation and physics code is unchanged.
- Current P38 controls pass ten snapshots / 20 eyes. Native recoil/reload move
  the visible model while the hand-fixed ray remains identical. An actual shot
  matches the captured ray's recorded position/angles exactly. Tracking loss,
  weapon/load identity and live pair-refusal/recovery controls pass: 268 pairs,
  536 rollback checks, zero mismatches/failed eyes and six deliberate refusals.
- Revalidated the changed aim policy on all 13 families in a fresh native/
  tracked pair: 21/21 lifetimes, 22 linked tracked health decreases, six shotgun
  pellets and 21 matching construction RNG updates. All five fallback/recovery
  controls pass. Speed, history, release, ownership and impact checks pass.
- The redirected grenade/petrol now hit P2 where the native baseline misses.
  The checker records this explicitly and permits only added linked damage for
  hand-fixed mapped `0x13F3` throws; damage loss, other-family exceptions and
  physics changes still fail. Tests cover the policy difference. The tracked
  run reproduces the known 300 petrol eye discards and publishes pair 3296
  after failed attempt 1844 with zero rollback mismatches.
- Validation: 115 Python tests, strict C syntax and active build; current-binary
  P38 legacy recovery and MP40 native fallback. The earlier capture-only binary
  `fecd002a...` passed 19 P38 controls, the 64-case MP matrix, lateral/native
  fire/refusal recovery, all-ID flat poses and SP zero. Those regression
  receipts retain their actual binary and are not relabeled as current.
- Current executable: `4204a6f3...`, Release/OpenXR/diagnostics/debug tools ON.
  Normal experimental defaults stay OFF. No headset/XR runtime, framework pin,
  source save/preference or reference checkout change. Owned processes closed.
- Evidence: [hand-fixed contract](RENDERED_MUZZLE_EVIDENCE.md),
  `weapon-rendered-muzzle-receipt.json`, `weapon-hand-fixed-aim-receipt.json`,
  `weapon-hand-fixed-preservation-receipt.json` and
  `weapon-rendered-muzzle-build-receipt.json`. W6.1 is checked; W6.2 verified
  triangle/vertex bindings is NEXT. No exact-triangle beam or physical
  acceptance is claimed. Earlier moving-barrel aiming requirements are
  superseded by the operator policy in the current handoff/plan.

## 2026-10-27 - Physical MP/SP smoke and documentation-only checkpoint

- Ran bounded interactive VDXR MP P38 and isolated SP slot-2 headset smokes on
  committed `29f7157` / executable `4204a6f3...`. MP observed 59 live hand
  samples, 1,131 new submissions and 1,125 new pairs; zero failed eyes,
  verification OFF. Operator said gun looked okay but reported MP edge culling.
- The MP profile omitted `MOHU_VR_MP_FRUSTUM`. All-family camera refresh also
  depended on debug capture/legacy P38 aim. After the observer armed, 12 shots
  reported hand-fixed aim; P2 health was already 29 before recording, versus
  fixture 32. No linked damage occurred during these 12 shots. Do not conflate
  whole-run health change with verified tracked-shot damage.
- MP exit was 1 with `tcp_quit`/`atexit` report. Old runner's complete flag is
  not clean acceptance; forced cleanup was not recorded. Owned game closed.
- SP edges looked good to the operator; tracked weapon control is still W5.2.
  Operator reported about 35 FPS and view-dependent distant fog, with greater
  visibility at FOV edges than straight ahead. Neither an independently
  measured FPS benchmark nor a confirmed fog cause is claimed. Startup had
  27 fresh pairs / zero XR failures. Source saves/preferences unchanged.
- Before the stop request, changed camera predicate to include `g_weapon_aim`;
  MP probe now opts into MP frustum, offers explicit `--hand-fixed`, records
  account/forced cleanup and rejects nonzero/forced exit as complete acceptance.
  Strict C syntax, active Release build and 11 focused probe unit tests passed.
  New executable `924691b6...` is NOT runtime/headset retested.
- User requested only documentation and push because usage is low. No further
  implementation or runtime/headset tests at this checkpoint. Added S1-S5 and
  exact ordered continuation in HANDOFF, ahead of W6.2; physical gates stay open.
  Framework pins/defaults and reference checkout unchanged; `.commandcode/`
  remains untouched. Evidence: [headset smoke](HEADSET_SMOKE_EVIDENCE.md) and
  [checkpoint receipt](../../vr/proof/headset-smoke-20261027-receipt.json).

## 2026-10-27 - S1 retest, MP selector control and native flash alignment

- Extended `probe_p38_headset.py` so `--hand-fixed` samples canonical camera
  ownership/cycle and shot counters while capture remains OFF. It rejects armed
  capture, recorded samples, non-P1 cameras, missing eligible/aimed updates,
  tracking fallback and legacy P38 aim. MP selector overrides/fallbacks are
  recorded separately from the unrelated SP `level_hits` counter.
- Interactive VDXR S1 on copied root MP slot 1 and `924691b6...` produced 30
  live/focused samples, 13,524 canonical camera callbacks, 20 eligible
  hand-fixed aim updates, zero fallbacks, capture count zero and three linked
  P2 health writes (32->14). The process still exited 1 after forced cleanup,
  so S5 remains open. Evidence:
  [S1 proof](../../vr/proof/headset-s1-camera-receipt.json).
- Desktop `MOHU_VR_MP_FRUSTUM=1` control produced 1,638 overrides in each eye,
  zero fallback and clean exit. This proves the selector path but not physical
  edge appearance.
- Isolated the operator-reported centre-fixed flash. It is the native 32x32
  semi-transparent packet at `actor+0xCB8/+0xCBC`, not the calibrated shot or
  gun mesh. Added a guarded eye-replay translation that preserves packet colour,
  texture, size, ordering and timing while moving its four XY words to the
  projected animated muzzle. Shot position/angles remain unchanged.
- Synthetic copied-MP controls captured the same packet before and after a
  +150 mm hand X translation. Eye-replay flash centres moved from `(287,92)` to
  `(320,92)` in the 512x120 surface; the natural packet remained near
  `(293,106)`. Current-binary counters were 234/231 successful alignments, zero
  fallbacks, clean exits and unchanged copied saves/preferences.
- The operator additionally reported very poor resolution and impacts slightly
  high. Resolution is now explicit S4 measurement; high impact is an open
  W5.4d failure observation. No scale or aim-pitch constant was changed.
- Validation: 121 Python tests, strict weapon/MP/rendered-muzzle C fixtures,
  focused tracked P38 shot with linked P2 damage, strict diagnostic syntax and
  active Release build. Current executable `0dbdb244...`; defaults remain OFF.
- Evidence: [native flash evidence](NATIVE_MUZZLE_FLASH_EVIDENCE.md),
  [native flash receipt](../../vr/proof/native-flash-alignment-receipt.json),
  [headset smoke evidence](HEADSET_SMOKE_EVIDENCE.md) and the raw GP0 histories
  under `analysis/vr-baseline/p38-effect-flash-align-final-20261027a/` and `b/`.

## 2026-10-28 - SP tracked weapon, muzzle flash and P38 shot ray

- Bound the real SP held-weapon draw at `0x80091854` / caller `0x80091420`.
  The calibrated hand transform is scoped around that dispatcher and the native
  GTE state is restored immediately afterward. The SP player/weapon layout is
  `player+0x114`, input `player+0x39C`, weapon ID `input+93`.
- SP projects the held weapon with `H=400`, not MP's `H=133`. The flash target
  uses `OFX/OFY=256/120` produced by the dispatcher call and translates both
  guarded packet copies at `player+0x600` and `player+0x624`.
- Traced the SP P38 basis chain as `0x80048604 -> 0x80076C28`, return
  `0x8004860C`, shot type `0x13F6`. The guarded shot write supplies the shared
  calibrated muzzle/forward ray before native basis/history initialization.
- Final desktop controls on executable `0bc60df5...`: baseline flash
  `(355,225)` and +150 mm hand-X flash `(454,225)` in the 512x240 surface.
  Baseline recorded 332 weapon applications / 308 flash alignments; shifted
  recorded 378 / 354. Both wrote 2/2 aimed P38 shots with zero flash or shot
  fallbacks, clean exit, unchanged copied saves/preferences and no remaining
  game process. Raw receipts are hashed in
  [the SP receipt](../../vr/proof/sp-weapon-aim-flash-receipt.json). The final
  binary resets stale per-eye flash targets at eye entry; the controls were
  rerun against that exact build.
- `RunVR` now enables the tracked calibrated weapon/aim path and forces
  `1080p`; `game.toml` ships the same preset for direct launches. A user
  `settings.toml` preset still outranks `game.toml` on a direct launch.
- Validation: 121 Python tests, strict weapon and MP-guard C fixtures, focused
  MP tracked desktop passthrough control and active Release build.
- Limits: synthetic desktop input only. Physical gun/flash/impact alignment,
  non-P38 SP shot families, SP arm filtering and measured performance remain
  open. The high-impact report still requires a controlled target test.
