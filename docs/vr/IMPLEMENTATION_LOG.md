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
  zero-offset hashes, ±90-degree world coverage, and documentation links.
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

- Operator created source slots 1–4 with P1 facing P2 and authorized native
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
- P1's first-person object is `actor+0x4AC`; it has magic `0x00160024` and a
  shared 22-node table
  `9f8c7275b3e8a1d6c7765da25a02d78b23f0c3fa4b67483f28865191d2805e4f`.
  Object fields at `+0x5C/+0x64` change during cycling and are animation state,
  not a stable mesh identity.
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
- Added `vr/underground/raycast.h` and a strict visibility-tree fixture for a
  default-on right-squeeze aim ray with beam and impact dot. `-NoLaser` and
  `PSX_VR_LASER=0` are explicit opt-outs. Runtime headset visual acceptance
  remains pending.

## Next work

1. Repeat the PGXP pose sweep in additional scenes and near-wall positions.
2. Rebuild the flat target and repeat interactive boot/menu/gameplay validation.
3. Locate the visible top-view first-person mesh seam; keep the completed
   13-ID native-hit matrix as the combat regression gate. Validate the
   right-grip laser visually in a headset.
4. Extend the pair-sequence and compositor checks to motion, wall proximity,
   menus, transitions, and additional levels.
