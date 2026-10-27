# Underground VR implementation handoff

Updated: 2026-10-28. This file is the execution contract for the next session.
[VR_PLAN.md](VR_PLAN.md) owns checkbox status. [WEAPON_MAPPING.md](WEAPON_MAPPING.md)
owns the detailed measured weapon layout. [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md)
owns history. [WEAPON_COMPLETE_PROFILES.md](WEAPON_COMPLETE_PROFILES.md)
owns the all-ID topology, provisional calibration and moving-marker result.
History is not a
queue of tasks to repeat.

[FRAMEWORK_UPSTREAM_TRACKER.md](FRAMEWORK_UPSTREAM_TRACKER.md) owns shared
framework branches and PR delivery. Develop generic changes on
`vr/shared-development`; fork master mirrors upstream. Both games retain tested
pin `555e1eab`. The earlier eight VR PRs are merged; the three later generic
commits await separate PR branches after implementation is complete. Do not
update either game to moving master or resubmit the old stack.

Read [REFERENCE_REUSE_AUDIT.md](REFERENCE_REUSE_AUDIT.md) before introducing
new code. It lists the first-game implementation and the local counterpart for
each task. Reuse their algorithms/tools and verify only Underground's bindings,
units and assets. Its corrected desktop-versus-hardware dependencies supersede
the earlier hardware-first sequence. Historical completed scopes stay closed
except the demonstrated SP regressions explicitly reopened in R1-R3.

## 1. Start here - SP repair before new features

**NEXT: R4 native-hook/performance integration, then R5 fog and R6 live SP
impact. Do these on desktop. W6.2 and another headset batch are deferred.**

Read [SP_PARITY_REPAIR.md](SP_PARITY_REPAIR.md) and
[sp-parity-repair-receipt.json](../../vr/proof/sp-parity-repair-receipt.json).
The operator rejected the earlier SP flash/visibility result. S1b's old counters
proved movement in one pose, not robust muzzle attachment or SP readiness.
The first game's post-animation transform, arm filtering and precision pattern
were reusable and should have been carried into the SP adapter together.

### What is fixed, and what remains open

- The native SP dispatcher `80091854`, caller `80091420`, owns the held draw.
  Apply at `80090954` after native animation and camera restoration. Read the
  projected muzzle and mask arms at `80090A78`, before triangle submission.
- Flash uses the exact projected animated tip vertices from that eye's draw.
  There is no independent fixed-400 projection. The same reader is used in MP.
  Native recoil moves the visible flash; the shot/laser ray stays fixed to hand.
  SP FT4 tags are `player+0x5FC` and `player+0x624`; their color words are
  `+0x600` and `+0x628`. Do not confuse a color-source address with a packet tag.
- P38 retains all 96 gun vertices (including the node-11 barrel), and masks
  142 arm vertices in each eye. Tracking loss keeps the native gun-only draw.
- Slot-3 disappearance reproduced at the native arena-full branch `8009086C`.
  When needed, use only a checked, unreferenced 32 KiB tail of the other native
  primitive bank for this held draw, restoring both arena words immediately.
  The same-binary OFF/ON control changes missing gun to 96 visible gun vertices.
  This is a bounded desktop fix; broader scene/weapon acceptance remains open.
- Existing source saves still load; repeated load and rollback controls pass.
  Do not add a persistent mod-memory allocation to solve this: it changes the
  memory-layout cookie and rejects the owner's existing states.
- SP P38 shot basis is already measured: `80048604 -> 80076C28`, return
  `8004860C`, type `13F6`. Do not rediscover it. W5.2 remains open for live NPC
  damage/isolation, broader SP families and physical impact, not missing P38 bindings.
- Production/debug performance is recorded separately in the repair receipt.
  No current result is headset-refresh-rate or whole-campaign acceptance.

### Exact next desktop work: R4

1. Keep one `build-release`, current framework pin `555e1eab`, and the existing
   shared-development/upstream tracker. Read its cache before running tools.
   Normal play uses `PSX_DEBUG_TOOLS=OFF`; TCP probes need ON. `run_vr.ps1 -Build`
   selects ON only with explicit `-DebugPort`; it builds with two jobs.
2. Read `REFERENCE_REUSE_AUDIT.md`'s new repair table and the reference
   `docs/reverse/VR_SLOT2_PERFORMANCE.md`. Detailed debug recording and VERIFY
   are excluded from throughput comparisons. Use the same copied analysis SP
   slot 3, resolution, scene and quiet window, and count unique stereo pairs
   separately from guest frames and XR submissions.
3. Fix the native overlay integration gap, before optimizing the renderer.
   `game.toml` has no `mod_function_entry_funcs`/`mod_instruction_sites` for
   the VR callbacks. Its current cached-native control produces ZERO stereo
   pairs; its higher flat FPS is invalid as a VR result. The launcher currently
   selects the interpreter analysis config so hooks execute. Record the resolved
   config; do not silently switch to native and claim a performance win.
4. Derive the required entry and instruction list from the existing registration
   block at the bottom of `vr/underground/vr_diagnostic.c` and the verified engine
   map. Reuse the framework's documented codegen instrumentation and the reference
   game's config pattern. Regenerate with the supported tool; never hand-edit
   generated C, inject guest code or disable correctness guards. No function/address
   rediscovery is needed. A diagnostic PSX_NATIVE_BLOCK control is retained as a
   localization experiment, not the shipping solution or a completed native path.
5. Instrumentation changes codegen identity. Preserve original saves. If a new
   compatible fixture is required, boot/create one in an isolated directory using
   native menu/input automation; do not patch personal state headers or weaken the
   loader. Validate real stereo pairs, the SP baseline/turned/close/lost controls,
   muzzle flashes, a focused MP regression and rollback before benchmarking.
6. Capture a quiet matched production comparison using the first-game reporting
   workflow, including `PSX_BENCH_WINDOW=300:900` for a common guest-frame window. Report pair cadence and stage costs. A faster run with zero pairs,
   missing weapons, lower resolution or disabled projective rendering fails R4.
   If native integration cannot be completed, retain the exact failed site and
   bounded trace rather than rerunning the full MP matrices or requesting a headset.

### Subsequent order

- **R5 / S3 fog:** identify the actual SP depth/fog producer. Compare fixed world
  points under head rotation against the reference implementation. The current
  explanation is unconfirmed; do not tune draw-distance/FOV constants blindly.
- **R6 / W5.2:** native-versus-tracked P38 firing against one real SP NPC with
  health tracing armed before firing. Record linked decreases and target ownership.
  MP P2 damage and a flash counter do not close this gate. Then expand SP families.
- **R7 physical:** one bounded operator batch after desktop quality/performance
  fixes, for hand attachment, scale, both-eye flash and target impact. No hardware
  acceptance is claimed by these desktop controls.
- **W6.2 later:** use the retained reader contract in section 6. A triangle laser
  and wrist HUD do not take priority over the reported SP defects.

### Repeatable changed-path controls

`python vr/tools/probe_sp_weapon.py <fresh-analysis-directory> --slot 3 --verify`
uses `analysis/vr-baseline/saves` by default: this is the SP fixture, not root MP
slot 3. Useful controls are `--head-yaw 60 --follow-head --eye-offset 8`,
`--hand-x-mm 300`, `--hand-z-mm -120`, `--tracking-loss`, and `--reload`.
`--no-spare-arena` is the causal disappearance control only. Use the receipt's
binary and request/environment; a completed transport is not visual acceptance.
The probe fires native input and never edits health/ammo or source saves.
Its `render.calibrated=0` is the legacy P38-only flag; the all-family
`MOHU_VR_WEAPON_CALIBRATED=1` / `weapon_aim=1` path is enabled. Do not turn
legacy aim on to "fix" that diagnostic label.
Enable debug tools only for these probes, then restore production OFF.

## 2. Current state - facts, not work to restart

| Item | Current observation |
| --- | --- |
| Repository | `C:/Users/titan/Desktop/Github_Projects/Mine/Medal-Of-Honor-Underground-PSX-Recomp` |
| Branch / current HEAD | `feature/vr-port`; read current HEAD during preflight. W1/W2.1 predecessor is `afda5082...` |
| Checkpoint scope | R1-R3 SP repair and R4a production overhead measured; NEXT R4b native hooks, then fog/live NPC; physical acceptance open |
| Framework gitlink | `555e1eabccc59b9b6ff0d9fca48aca783513dc86` |
| UI gitlink | `7c635c6b366a6e0d5d3c913a7fce6ec04dd9f256` |
| Title / version | `SLUS-01270` / `0.1.0` |
| One active build | `build-release`, Release/OpenGL/OpenXR/PGXP |
| Game executable | `build-release/Medal_of_Honor_Underground_Recompiled.exe`; `psx-runtime` is the CMake target, not the executable filename |
| Current debug tools | Production checkpoint uses `PSX_DEBUG_TOOLS=OFF`; explicitly build ON for TCP diagnostics, then restore OFF before play/performance |
| CMake VR option | `MOHU_VR_DIAGNOSTICS` defaults OFF; current `build-release` has it ON |
| Normal launcher | Native menus, `-Slot -1`; no implicit savestate load |
| Defaults | CMake VR option remains OFF for ordinary builds. The VR launcher explicitly enables calibrated gun-only SP/P38 aim. MP control/frustum remain a separate fixture opt-in. |
| PGXP save ABI | `131106`; base flavor ABI `34` is incompatible |
| Unrelated work | `.commandcode/` is unrelated; do not add, change or clean it |

Read current Git state at session start. These are observations, not instructions
to reset HEAD, switch to master, restore an old binary or force old gitlinks.
`BASELINE.md` records the 2026-10-23 starting tree, including old `31df2e1e`;
it is historical and must not override the current framework pin above.

Evidence at each receipt's recorded revision (not blanket current-binary acceptance):

| Scope | Receipt / practical limit |
| --- | --- |
| Flat first-person meshes | [weapon-viewmodel-receipt.json](../../vr/proof/weapon-viewmodel-receipt.json): all 13 IDs; visible pose controls; not physical calibration |
| P1-only MP eyes | [weapon-mp-eye-receipt.json](../../vr/proof/weapon-mp-eye-receipt.json): 1,215 pairs, 2,430 rollback checks, zero errors; both eyes and all 13 IDs |
| MP lateral / native fire | Same MP receipt: 52,136 differing pixels; pistol clip 8->7 and P2 health 32->31.25; not tracked-shot alignment |
| W1 P38 absolute spatial controls | [weapon-pose-space-receipt.json](../../vr/proof/weapon-pose-space-receipt.json): 29 cases, 10 head-only, five invalid; both eyes populated; no fire |
| W1 build / regressions | [weapon-pose-build-receipt.json](../../vr/proof/weapon-pose-build-receipt.json): source/binary hashes, 18 Python tests, strict fixtures, MP/flat/SP regressions, debug OFF |
| W2.1 native MP selector | [weapon-mp-level-selector-receipt.json](../../vr/proof/weapon-mp-level-selector-receipt.json) and [build receipt](../../vr/proof/weapon-mp-level-selector-build-receipt.json): five complete functions, both natural callers, 21-node flat queue/masks; no fire |
| W2.2 MP eye frustum | [frustum measurement](../../vr/proof/weapon-mp-frustum-measurement.json), [zero control](../../vr/proof/weapon-mp-frustum-controls.png) and [build receipt](../../vr/proof/weapon-mp-frustum-build-receipt.json): 21 live samples, guarded both-eye override, zero fallback/rollback errors |
| W2.3 MP head/near-wall visibility | [control receipt](../../vr/proof/weapon-mp-visibility-receipt.json), [control sheet](../../vr/proof/weapon-mp-visibility-controls.png) and [build regressions](../../vr/proof/weapon-mp-visibility-build-receipt.json): zero, +/-90-degree and near-wall; both eyes, per-eye selector comparison, populated top-screen world geometry, no fallback and clean rollback |
| W2.4 MP native input | [control receipt](../../vr/proof/weapon-mp-input-receipt.json) and [build regressions](../../vr/proof/weapon-mp-input-build-receipt.json): P1 actor/input/current ownership, live converter and table hashes, six synthetic controls, SP slot-2 regression, 23 Python tests and 33-case parity |
| W2.5 MP lifecycle / recovery | [control receipt](../../vr/proof/weapon-mp-lifecycle-receipt.json) and [build receipt](../../vr/proof/weapon-mp-lifecycle-build-receipt.json): 17 MP input/button cases, native Start pause/resume, zero render-time sampling, 13 SP cases, inherited-flag flat startup |
| S1 camera without recording | [proof](../../vr/proof/headset-s1-camera-receipt.json): 30 live samples, capture OFF, 13,524 camera callbacks, 20 eligible hand-fixed aim updates, zero fallbacks and linked P2 damage 32->14; shutdown still fails S5 |
| S1a native muzzle flash | [evidence](NATIVE_MUZZLE_FLASH_EVIDENCE.md) and [receipt](../../vr/proof/native-flash-alignment-receipt.json): existing 32x32 flash packet tracked in eye replay; baseline `(287,92)`, +150 mm hand X `(320,92)`, zero fallbacks; physical visibility open |
| Historical S1b SP binding / P38 aim (visual claim superseded by R2) | [SP receipt](../../vr/proof/sp-weapon-aim-flash-receipt.json): held-weapon dispatch active; flash `(355,225)` -> `(454,225)` after +150 mm hand X; 2/2 shots aimed in each control with zero shot/flash fallbacks and clean exit; physical acceptance open |
| S2 MP frustum desktop | [receipt](../../vr/proof/headset-s2-mp-frustum-receipt.json): 1,638 overrides per eye, zero fallbacks, 201 rollback checks, zero mismatches and clean exit; physical edges remain open |
| W3.1 P38 calibration | [calibration receipt](../../vr/proof/weapon-p38-calibration-receipt.json), [capture receipt](../../vr/proof/weapon-p38-calibration-capture-receipt.json) and [build receipt](../../vr/proof/weapon-p38-calibration-build-receipt.json): 69 atomic source/animated vertices, orthonormal axes, grip and muzzle markers, nominal-size scale, focused tests and 33-case parity |
| W3.2 P38 headset comparison | [headset comparison](../../vr/proof/weapon-p38-headset-receipt.json) and [complete build receipt](../../vr/proof/weapon-p38-headset-complete-build-receipt.json): 30 seconds native plus 30 seconds tracked, 30/30 live hand samples per mode, fresh VDXR submissions and stereo pairs, zero final failures; no operator acceptance claim |
| W3.4 all-ID profiles | [topology](../../vr/proof/weapon-complete-gun-topology-receipt.json), [animated capture](../../vr/proof/weapon-profile-captures-receipt.json), [provisional calibration](../../vr/proof/weapon-provisional-calibrations-receipt.json), [calibrated controls](../../vr/proof/weapon-complete-gun-controls-receipt.json) and [control sheet](../../vr/proof/weapon-complete-gun-controls.png): 13 unique IDs / 16 slot rows, 64 cases, 804 eye masks on its recorded binary, zero mixed gun/arm triangles and zero rollback errors |
| W3.4 moving marker | [moving-marker receipt](../../vr/proof/weapon-moving-muzzle-receipt.json) and [control sheet](../../vr/proof/weapon-moving-muzzle-controls.png): frozen all-vertex samples, 13 confirmed switches, nine recoil paths, seven confirmed reloads, three prop actions, scoped hidden-model states; all IDs require an animated marker recomputation |
| W5.3 shot families | [family receipt](../../vr/proof/weapon-shot-families-receipt.json) and [evidence](SHOT_FAMILY_EVIDENCE.md): historical read-only map of 13 IDs, common basis caller, types `13F1/13F3/13F6/13F7/13FA`, six shotgun pellets and native ammo/slot changes |
| W5.3 native lifecycle | [lifecycle receipt](../../vr/proof/weapon-shot-lifecycle-receipt.json), [evidence](SHOT_LIFECYCLE_EVIDENCE.md) and [tool validation](../../vr/proof/weapon-shot-lifecycle-validation-receipt.json): all 13 IDs, 22 lifetimes, 147 XYZ groups, 19 native damage writes, six distinct pellet directions and safe address reuse; no override enabled |
| W5.3c origin writers | [origin receipt](../../vr/proof/weapon-projectile-origin-writers-receipt.json): three actual objects, full object-address-filtered histories, last XYZ writers equal first-motion origins, live code windows; grenade has a second basis/init call after constructor |
| W5.3c canonical markers | [marker receipt](../../vr/proof/weapon-canonical-markers-receipt.json), [evidence](CANONICAL_MARKERS_EVIDENCE.md) and [build/regressions](../../vr/proof/weapon-canonical-markers-build-receipt.json): 13 IDs, 18 constructor events, three final-origin stages, independent vertex means, stale/load/recovery/P2/disabled controls; no new shot writes |
| W5.3d all-family conversion | [all-family receipt](../../vr/proof/weapon-aim-all-receipt.json): 13 IDs, 23 converted events, zero candidate fallbacks, six-pellet shotgun with 5.18-degree native spread, expected real damage, complete guarded projectile stages, stereo failure/recovery recorded |
| W5.3d build/regressions | [build receipt](../../vr/proof/weapon-aim-all-build-receipt.json): 81 Python tests, strict C/syntax, 64-case MP matrix, lateral/fire, flat pose, SP zero, 14 legacy P38 controls, 33-case parity and debug-off flat startup |
| W5.3e paired preservation/impact | [paired receipt](../../vr/proof/weapon-preservation-receipt.json) and [evidence](WEAPON_PRESERVATION_EVIDENCE.md): 13 IDs, common-prefix lifetimes/release/history/stages, exact shotgun RNG and six-pellet distribution, native damage plus animated-axis/target residuals, five P38 fallback controls |
| W5.3e build/regressions | [build receipt](../../vr/proof/weapon-preservation-build-receipt.json): 86 Python tests, affected C fixtures, strict diagnostic syntax, two-ID focused pair and the complete 13-ID pair |
| Earlier native damage | [WEAPON_SET_EVIDENCE.md](WEAPON_SET_EVIDENCE.md), [weapon-alignment-receipt.json](../../vr/proof/weapon-alignment-receipt.json): all 13 IDs, damage-only pose reachability |
| Current all-ID controls | [weapon-complete-gun-controls.png](../../vr/proof/weapon-complete-gun-controls.png) |
| SP world / visibility | [PGXP_RENDER_VIEW_EVIDENCE.md](PGXP_RENDER_VIEW_EVIDENCE.md), [HEAD_TURN_HUD_EVIDENCE.md](HEAD_TURN_HUD_EVIDENCE.md), [SKY_GHOST_EVIDENCE.md](SKY_GHOST_EVIDENCE.md) |
| Native input | [MOVEMENT_EVIDENCE.md](MOVEMENT_EVIDENCE.md): synthetic SP and MP controls; physical acceptance remains open |

The historical W5.3e Release/debug-on executable SHA-256 is
`8d0db60626bd516e91a342f648b22579e07b7ad3339ac104637774e1a71bc20d`.
The W5.3d historical tested executable remains
`4a17ce5cdc83533bb23f8c85ccdcd9834289ec7c8a32e45d162c291099c74d00`,
and its debug-off release was
`e2103a9ffb3696188b8cb405978bde587d17ea63cead196bddb007b029eb9fa1`.
See the historical [build receipt](../../vr/proof/weapon-aim-all-build-receipt.json)
for runtime source hashes, 81 Python tests, focused C/syntax/build checks, the
all-ID matrix and five native / 14 tracked legacy P38 regressions. The earlier
[lifecycle validation receipt](../../vr/proof/weapon-shot-lifecycle-validation-receipt.json)
records the preceding binary, trace-tool hashes, 72 Python tests and 33-case
parity for that earlier tooling/documentation pass. Historical receipts retain
their original hashes.
The last debug-off release executable was
`bae4f60f02f4bf70ce86ea85d201674df7157bafa4d6bea20c3086972f2ab71d`;
it is not the current working binary.
The tested W3.1 diagnostic executable SHA-256 is
`d59a6a2f02ccab4d4b9f14858e4a74c703a5075e78eea51bcb2a54eaec91df97`.
The OpenXR-off flat executable SHA-256 is
`18f4328bc9085f0a6a2322f940eea63516f07e93698010853cf3474cad94636c`.
They differ because debug tools differ. Earlier W1 and MP hashes remain
historical. Do not swap them or relabel a historical receipt. Source hashes are
in the current build receipt; a new implementation needs new provenance and
affected checks, not fabricated matching hashes.

## 3. Fixture selection - slot numbers alone are ambiguous

| Purpose | Source | Selection |
| --- | --- | --- |
| W1 P38 / stationary P2 | `saves/openbios/state_8001F844_slot01.pst` plus `.thumb` | MP slot 1, weapon ID 0, zero switches |
| Full MP matrix | Root `saves/openbios/`, slots 1-4 plus thumbnails | 13 unique IDs across four native cycles |
| SP regression only | `analysis/vr-baseline/saves/openbios/state_8001F844_slot02.pst` plus `.thumb` | Isolated SP slot 2 |
| Stale-identity control | Slot 1 in that isolated SP tree | Not the valid root MP slot 1; do not use as W1 fixture |

**Root slot 2 is MP; isolated slot 2 is SP. Never choose by slot number without
its save root.** A new empty analysis directory is not a new compatible save.

The existing tools copy the selected `.pst` and `.thumb` into a fresh output
subtree and pass its absolute `--memcard-dir`. Use that ownership/cleanup pattern.
Never save into, overwrite, migrate, patch or replace an operator source slot.
Do not change clip/reserve, health or enemy placement to make a test pass.
Do not chase a moving SP enemy for weapon-position work. Reload the MP copy.

Cycles: slot 1 = `0,1,17,10`; slot 2 = `8,16,4,15`;
slot 3 = `9,14,5,10`; slot 4 = `12,17,13,15`.
Unique IDs: `0,1,4,5,8,9,10,12,13,14,15,16,17`.

## 4. Locked native contracts - use these exact seams

| Meaning | Underground MP contract |
| --- | --- |
| P1 / P2 roots | `[800A3604]` / `[800A3608]`; read at use time |
| Input | `[actor+39C] == actor+400` |
| Slot / weapon ID | `input+92` / `input+93` (decimal offsets) |
| Current health | `actor+108` (hex offset); trace the exact P2 address |
| Native damage function | `8004EAB4`, 532 bytes, SHA-256 `5ee9683eb0646d46a39e0b552f214fe90be010d2d41cebbe45fadc2db2a1b9e5` |
| Native health subtract / store | `8004EB78` / `8004EB80`; damage evidence, not a shot-constructor seam |
| Real first-person object | `[actor+114] == input+9F0 == actor+DF0` (hex offsets) |
| Body object - rejected as viewmodel | `actor+4AC`, magic `00160024`, 22 nodes |
| First-person entry | `800892E8`, 0xA70 bytes, FNV32 `39E56A35` |
| Required first-person caller | Call `8008A53C`, return `8008A544` |
| Native animated vertex producer | `8008DB98`, 0xB4 bytes, FNV32 `FAE3646E` |
| Pose application | `800894DC`, after native animated vertices / RT/TR restoration |
| Shared epilogue / restore | `80089D30`; eight RT/TR words plus world render view |
| Native world / weapon focal | H=400 / H=133 |
| MP eye context | `800A0B08`, 512x120 P1 source view |
| Natural MP frame / caller | `80054BC4` / `80063CF8`; call word guarded at `80063CF0` |
| P1 camera / selected player / scene list roots | `800A35B0` / `800A35C4` / `800A35CC` |
| Native MP camera / scene calls | `80054E68(camera,0)` / `8006E9D8(context,list)` |
| Submission | `[context+2218]` OT, 512 buckets, guest DrawOTag `80018B48` |

Addresses in this table are hex guest addresses, usually shown without `0x`.
Offsets explicitly labeled decimal are decimal. Heap sample `801491C0` is not
an address to hardcode. Function hashes identify the overlay generation; the
same address in SP is not the same method. Full guards live in source.

Source ownership:

| File / function | Change here for |
| --- | --- |
| `vr/underground/weapon.c`: `mohu_vr_weapon_track_delta`, `mohu_vr_weapon_relative_delta`, `mohu_vr_weapon_compose_gte_control` | Pure pose math / captured per-ID profiles |
| `vr/underground/vr_diagnostic.c`: `vr_weapon_prepare_delta` | W1 P38 absolute placement; other real-hand IDs remain native until their calibration gates |
| Same file: `vr_weapon_fp_enter`, `vr_weapon_viewmodel_project`, `vr_weapon_viewmodel_restore` | Existing guarded model scope; keep native animation, caller/mesh guards and common restore |
| Same file: `vr_mp_snapshot`, `vr_mp_code_valid`, `vr_mp_frame_entry`, MP branch of `vr_stereo_eye_draw` | Existing MP replay; reuse, do not replace to fix a weapon pose |
| `vr/underground/mp_view.h`, `vr/tests/test_mp_view.c` | MP mode, ownership, input/pointer and 512x120/H=400 guard |
| `vr/underground/frustum.h`, `vr/tests/test_frustum.c` | Host AABB/tree fixture plus the W2.2 center/radius cube and render-view overflow guards |
| `vr/tools/check_mp_view.py` | Owned copied-save process, both-eye controls, native pistol fire, refusal/recovery |
| `vr/tools/probe_mp_level_selector.py` | W2.1 selector trace plus W2.2 live AABB/RT/TR/view measurement |
| `vr/tools/inspect_weapon_sets.py` | Native inventory, actual first-person mesh capture, exact native damage trace |
| `vr/underground/input.c` | Existing measured SP/MP mapper and converter/dispatcher adapters |
| `vr/underground/raycast.h` | Current visibility-node-extents pointer, not an exact triangle/barrel solution |

GTE TR uses integer camera units. The old affine helper packs translation in
Q12; `compose_gte_control` cancels that packing. Do not reintroduce `*4096` for
TR. RT coefficients are Q12; translation and rotation do not share units.

For the current authored mesh pose, temporarily use
`weapon_view.projection_h_ref=400`, preserving 133/400 of the world focal.
Restore the world view even for native/lost tracking. Absolute H=400 projection
or ref=133 without replacing the authored pose clipped the gun out of view.
Do not change this ratio independently of a measured new placement/projection
contract. A future calibrated placement may justify a different contract, but
requires a fresh same-run native/changed A/B with a visible gun and fixed world.

## 5. W1 - completed implementation and reproduction contract

This section records completed work. Reproduce it only for a changed execution
path or demonstrated regression; it is not the current work queue. Existing
helpers and the measured contract take precedence over the original prospective
wording below.

### W1.1: first bounded experiment - P38 space capture

1. Perform the read-only session preflight in section 7. Open these functions:
   `vr_weapon_prepare_delta`, `mohu_vr_weapon_track_delta`,
   `mohu_vr_weapon_relative_delta`, `vr_weapon_viewmodel_project`,
   `build_stereo_render_view`, and the native producer at `8008DB98`.
2. Use copied root MP slot 1, ID 0, zero switches. Keep P2 stationary; do not
   fire. Run a single-weapon MP control only if the preflight or new change
   needs a fresh baseline; an intact prior receipt is not a reason to rerun it.
3. Capture the native animated affine/vertex representation, GTE RT/TR,
   selected P1 camera and complete eye view at the already measured seam.
   Take samples before and after application and at restore. Record function
   bytes/caller/ID/object identity with the samples. Do not scan all RAM again
   for an alternative first-person object.
4. The W1 deliverable is `docs/vr/WEAPON_CALIBRATION.md`. It must:
   name model/animated-model, native base-camera, tracking-origin, hand and eye
   spaces. For every transform, specify source->destination, units, axis signs,
   handedness, matrix storage, authored root placement and native animation.
   Measure whether the native basis is scaled; use its full inverse if needed.
5. State the intended composed result in named spaces. The target relation is
   `point_eye = eye_from_origin * origin_from_hand * hand_from_model * point_animated`.
   Define all scale/conversion factors and where native authored placement is
   removed. Derive how this fits the existing guest GTE plus host eye transform;
   never apply the eye transform twice or assume it has already been removed.
   W1 may use explicitly labeled provisional test pivot/scale and analytic
   markers to validate spaces. Physical grip/size acceptance is W3; do not
   block W1 by trying to calibrate all 13 weapons or requiring a headset first.

**W1.1 exit:** a captured P38 contract sufficient to compute an expected point
and forward axis, with one explicit unit conversion at each boundary. If a
space or unit is unknown, capture that missing producer/consumer next; do not
"tune until it looks right" or move to another weapon.

### W1.2: add the missing independent pose harness

Harness: `vr/tools/check_weapon_pose_spaces.py`. It reuses
`check_mp_view.py` process/save/PNG/rollback code and must not create a new
build, save format, OpenXR backend or renderer.

- Feed genuine synthetic right grip and aim samples through the existing
  debug command `openxr_hands_override`. Set both poses, focus, activity and
  validity. Its positions are `px_mm/py_mm/pz_mm`; quaternion components
  `qx/qy/qz/qw` are integer millionths, not floats. Clear overrides afterward.
- Refresh samples during a valid control so age stays <=150 ms. Test staleness
  by deliberately stopping refresh using host time; guest frame count is not
  a host pose age. Record `openxr_hands` output with each case.
- Do not leave `MOHU_VR_WEAPON_SYNTHETIC_X/YAW_MDEG` or the flat-probe flag
  active: those select direct deltas and bypass the real hand-pose path.
  Existing `mohu.vr.weapon.pose x=/yaw=` controls prove only direct deltas.
- Independently vary the existing eye-view head pose with the implemented
  `mohu.vr.stereo.pose` command through `check_weapon_pose_spaces.set_head`.
  Yaw, pitch and translation already work; do not add another API. The current
  framework also includes synthetic-hand origin/age overrides (`b982e66e`).
  Reuse the implemented origin/stale cases in that harness rather than the old
  assumption that these controls still need to be written. Physical recenter
  remains a separate hardware test.
- Record effective units/metre for both hand conversion and eye view. The
  desktop view helper uses 1000 diagnostic units/metre; the hand converter
  currently uses `g_openxr_units_per_meter` (default `48/0.067`, and normally
  `238.806` with launcher WorldScale=3). Its environment override is parsed in
  the OpenXR activation branch, so setting that variable in a non-XR process
  does not prove it took effect. Make test units explicit and measured.
- `MOHU_VR_EYE_HEAD_*_MILLI` means milli-GTE camera units, not millimetres.
  Convert a requested physical pose using the declared unit scale; retain
  requested and effective values. Do not conflate diagnostic and headset scale.

Required independent cases, all with source slot 1 / P38:

| Case | What changes | Required invariant |
| --- | --- | --- |
| Absolute starts | Two different valid hand poses on fresh loads | First pose must affect placement; both must not silently become the same neutral/native placement |
| Hand only | +/-100 mm on each axis; +/-15-degree yaw/pitch/roll | Measured points/axis follow the composed transform; world ROI unchanged |
| Head only | Hand fixed in tracking-origin space; head +/-100 mm and +/-15-degree yaw/pitch | Reconstruct weapon anchor in origin space: it stays fixed; eye-space/screen motion agrees with head motion, not frozen pixels |
| Combined | Independently chosen head and hand changes | Same composed result, not the sum of two head transforms |
| Origin/recenter | Transform origin, head and hand consistently | Physical relation preserved; no retained stale neutral basis |
| Invalid/recovery | Unfocused, inactive, missing validity, stale and bad quaternion, then valid | Native fallback/no pose write on invalid samples; no jump from an old unintended anchor on recovery |

Use declared analytic points/axis in addition to images. Set tolerances before
judging output: float math <=1e-6 in its declared units, using recorded effective
inputs after SDK float conversion; final storage error no
more than one documented quantization step; zero-pose eyes identical; fixed
world ROI unchanged for hand-only cases. If the measured representation needs
a different tolerance, derive and record it before the run, not after a failure.
A clipped/disappearing gun is not a successful visible translation control.

### W1.3-W1.5: implement and close only this gate

Change the pure pose math and existing guarded geometry scope to meet the
captured contract. Preserve native animation/recoil/reload as input. Keep
unknown-ID, code/mesh/caller/ownership/focus/age failure paths native, and restore
RT/TR plus render view before another draw/eye. Do not hook firing or remove
arms as a shortcut. Per-weapon physical calibration comes later.

Save a compact pose-space receipt under `vr/proof/`, raw captures under a fresh
ignored analysis subtree, paired PNG IDs/hashes, effective parameters and
numeric expected/observed residuals. Run only the affected regression tier in
section 8. These checks passed and W1 is closed; do not reset NEXT to W2.1.

## 6. Later gates - dependencies and exact reuse entry points

| Task | Prerequisite / first action | Exit / allowed continuation |
| --- | --- | --- |
| W2 MP visibility/input | W2.1-W2.5 complete | Native/override visibility and desktop input/lifecycle controls are closed; physical acceptance remains in W3 |
| W3 desktop profiles | W1 and copied fixture; W3.1 P38 contract is measured; reuse reference profile/pose/batch validators with existing local 13-ID inventory | W3.2/W3.4 preparation does not wait for headset acceptance; retain provisional versus physically accepted values |
| W3 hardware | W2 usable visibility/input and prepared desktop candidate | Batch operator acceptance per weapon in W3.3/W3.5; do not certify physics from desktop images |
| W4 native shot binding | Complete for MP P38; read P38_NATIVE_AIM_EVIDENCE | Do not repeat the measured constructor, canonical global camera or linked damage trace |
| W5 diagnostic tracked aim | W4 plus W3.1 declared rendered-muzzle contract, with provisional physical calibration allowed | Adapt reference math/guards/streaming trace checks behind a new opt-in flag; keep normal defaults native until physical acceptance |
| W6 desktop exact laser | Declared rendered muzzle/axis plus verified target geometry readers | Port reference ray/triangle and beam/dot code/tests; W6.4 hardware acceptance remains open |
| H/Q HUD/coverage/performance/release | Relevant weapon gates pass | Reuse reference native HUD and reporting/package tools; these remain later priorities, not substitutes for the current task |

If hardware is unavailable, leave physical boxes open and continue the next
ready desktop task: W3 profile preparation, W4 native binding, then W5/W6
diagnostic candidates when their measured prerequisites hold. Desktop writes
must be explicitly opt-in, bounded and native on invalid input. Physical
acceptance gates normal enablement and accuracy claims, not developing those
candidates. Before switching from a blocked task, record its missing fact,
evidence and continuation. Do not silently jump to HUD/optimization or remap a
completed renderer.

For W4/W5, open the reference `vr/moh_vr_aim.c`, `test_moh_vr_aim.c`,
`check_weapon_aim.py` and `psx_vr_stereo.c` functions `vr_cache_camera`,
`vr_mp_level_entry`, `vr_shot_basis_entry` first. Reuse the conversion,
constructor-to-basis strategy, P1/camera freshness guards and streaming trace
logic. Locate Underground equivalents by instruction/call structure, then
verify the target fields before any write. The reference aim helper uses the
action-space aim origin; it is not proof of rendered-barrel alignment. Use one
declared mesh/muzzle frame for W5/W6. Local `vr_laser_capture_level` runs inside
eye replay and cannot supply the canonical simulation camera cache.

The original game's addresses, shot IDs, model profiles and 850/pivot/precision
values are target hypotheses, not reusable bindings. The reuse audit links
the exact sources for laser/HUD too; do not implement new triangle math,
capture APIs or OpenXR surface backends. Local `analysis/vr-baseline/weapon-shot-mapping/`
contains historical SP scripts with hardcoded slot 0/run names: read them as
leads, do not execute them unchanged for MP or adopt their fields as measured MP.
Keep native speed/spread/ammo/reload/collision/damage/throw behavior.

### Execute W6.2 before drawing a beam

1. Open the reference `vr/moh_vr_raycast.h` (`moh_vr_ray_tri`,
   `moh_vr_ray_tree_tris`), `vr/test_moh_vr_raycast.c` and the reference
   `vr_laser_draw` in `vr/psx_vr_stereo.c`. Reuse its triangle algorithm and
   fixture cases. Its 16-byte records / 8-byte vertices are a measured
   first-game lead, not an Underground layout or address contract. Test the
   origin-inside case explicitly; do not blindly inherit its leaf-skip shortcut.
2. Use copied root MP slot 1 and the existing owned-process/read-only tools.
   Read [MP_LEVEL_SELECTOR_EVIDENCE.md](MP_LEVEL_SELECTOR_EVIDENCE.md) and
   its saved complete callback disassembly first. The MP scene has 21 level
   nodes with callback `8006C61C`, scene `8006E9D8` and list `[800A35CC]`.
   Their center/radius fields are visibility bounds, not triangle records.
   The known SP projector `80099960` and SP tree do not establish MP geometry.
3. Follow the actual MP drawer/geometry reader from the measured callback,
   comparing its loads/calls with the reference record reader. Capture complete
   code units and hashes before trusting a binding. Record where the real vertex
   and triangle counts, bases, strides, indices and object-to-world transform
   come from. Reuse bounded code/trace snapshots; no broad RAM rediscovery,
   generated-C edits, actor/health/ammo writes or source-save changes.
4. Retain a bounded geometry snapshot and independently decode at least three
   spatially distinct drawn triangles from the real index/vertex tables. State
   their coordinate space and reconstruct their world positions. Validate counts,
   alignment, overflow and every index against measured bounds. A visibility-box
   hit or native damage alone is insufficient evidence for this reader.
5. Adapt reference ray/triangle fixtures for nearest hit, both windings, miss,
   range, parallel/degenerate triangles, edge hits, origin-inside bounds, malformed
   pointers/indices and traversal budgets. Keep broad-phase boxes separate from
   the final triangle test. Do not weaken bounds or substitute a different
   overlay when a guard fails. Run shared parity if shared math/wrappers change.
6. Close W6.2 only with the guarded reader, independent geometry reconstruction,
   pure fixtures and source/binary/fixture receipt. Then NEXT is W6.3: consume
   W6.1's current hand-fixed ray and per-eye view for beam/dot placement and nearest triangles.
   Before screen projection, also retain actual guest OFX/OFY/H; W6.1 currently
   records the affine and scoped view, not those extra projection registers.
   Reuse existing projection/clip/beam code; do not promote the old right-aim
   box pointer or borrow the reference's static pivot/muzzle/calibration.


## 7. Session preflight and bounded diagnostic commands

Read only, before editing:

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git submodule status
Get-Content vr/proof/weapon-rendered-muzzle-build-receipt.json -Encoding utf8
Get-FileHash -LiteralPath build-release/Medal_of_Honor_Underground_Recompiled.exe -Algorithm SHA256
Select-String -LiteralPath build-release/CMakeCache.txt -Pattern '^(PSX_DEBUG_TOOLS|MOHU_VR_DIAGNOSTICS|PSX_OPENXR):'
```

Compare the current source/build flags to that receipt. Differences require
inspecting the current diff, not resetting it. Do not create a branch/worktree,
change framework pins, regenerate C or launch a game merely to redo preflight.
All implementation/tools/tests remain under `vr/`; retained docs under
`docs/vr/`. Existing launcher/CMake integration may be narrowly edited when
required, with flat-mode checks. `game.toml`, `generated/`, framework/UI source
and original saves remain unchanged unless a separately justified task needs
it. Do not use broad `git add -A` with unrelated `.commandcode/` present.

Use the current CMake dependency cache; do not invent a new build directory.
Only when TCP/live diagnostics are needed:

```powershell
cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release -DMOHU_VR_DIAGNOSTICS=ON -DPSX_OPENXR=ON -DPSXRECOMP_REQUIRE_GAME_C=ON -DPSX_DEBUG_TOOLS=ON
if ($LASTEXITCODE -ne 0) { throw 'Diagnostic configure failed' }
cmake --build build-release --target psx-runtime --parallel 2
if ($LASTEXITCODE -ne 0) { throw 'Diagnostic build failed' }
$runRoot = Join-Path 'analysis/vr-baseline/weapon-mesh-mapping' ('resume-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $runRoot | Out-Null
```

The parent `$runRoot` may exist; **each tool's output child must not exist**.
Do not pre-create the child paths below. The tools own copying and cleanup.
Run one game at a time. Refuse occupied TCP 4372/existing games; do not attach
these controls to or terminate an operator's game. Configure/build before a
run, never while its process is alive. Explicit `-DebugPort` with `-Build`
selects debug ON; ordinary `-Build` selects production OFF.

Small existing zero-angle control, only when a changed path needs it:

```powershell
python vr/tools/check_mp_view.py (Join-Path $runRoot 'p38')
if ($LASTEXITCODE -ne 0) { throw 'P38 MP eye control failed' }
python vr/tools/check_mp_view.py (Join-Path $runRoot 'p38-frustum') --frustum
if ($LASTEXITCODE -ne 0) { throw 'P38 zero-angle frustum control failed' }
```

W3.4 topology/calibration reproduction after a changed profile path:

```powershell
python vr/tools/probe_weapon_profiles.py (Join-Path $runRoot 'profiles')
if ($LASTEXITCODE -ne 0) { throw 'All-ID profile capture failed' }
python vr/tools/derive_weapon_calibrations.py `
  (Join-Path $runRoot 'profiles/captures.json') `
  --proof vr/proof/<new-calibration-receipt>.json
if ($LASTEXITCODE -ne 0) { throw 'Calibration derivation failed' }
python vr/tools/check_mp_view.py (Join-Path $runRoot 'calibrated-all') `
  --all-weapons --calibrated-all
if ($LASTEXITCODE -ne 0) { throw 'All-ID calibrated MP controls failed' }
```

Use a new proof path for a new binary. The checked-in all-ID receipts remain
historical after source changes. `--calibrated-all` enables the provisional
profiles only for that child process; it does not alter normal defaults.

W3.4 moving-marker reproduction after an animation, profile or capture-path
change:

```powershell
python vr/tools/probe_weapon_animations.py `
  (Join-Path $runRoot 'moving-markers') `
  --proof vr/proof/<new-moving-marker-receipt>.json
```

The probe reloads the same copied slot before its independent switch control.
It uses native press frames long enough for the game to observe each action and
records clip/reserve/slot changes. `not-observed` fields are limits, not passes.

The existing `--frustum` flag enables the override; it does not add head-turn
or near-wall cases. The completed W2.3 command is:

```powershell
python vr/tools/check_mp_view.py (Join-Path $runRoot 'mp-visibility') --visibility-controls
```

It writes a compact receipt and control sheet under `vr/proof/`. For frustum
changes, run the affected MP regressions below with `--frustum` too; compare an
OFF control when needed.

W2.4/W2.5 input and lifecycle controls:

```powershell
python vr/tools/probe_mp_input.py (Join-Path $runRoot 'mp-lifecycle')
if ($LASTEXITCODE -ne 0) { throw 'MP input/lifecycle control failed' }
python vr/tools/check_movement.py (Join-Path $runRoot 'sp-fallback') --slot 2
if ($LASTEXITCODE -ne 0) { throw 'SP fallback control failed' }
python vr/tools/check_flat_fallback.py (Join-Path $runRoot 'flat-fallback')
if ($LASTEXITCODE -ne 0) { throw 'Flat fallback control failed' }
```

`check_movement.py` temporarily uses the existing restore-protected SteamVR
null-HMD setup; account for the Steam `Program Files` settings write permission.
The MP probe rejects an MP->SP savestate swap as an invalid fixture because the
resident overlay does not change. SP belongs in its own normal-launch run.
`check_flat_fallback.py` expects the existing `build-flat-check` target and
intentionally terminates only its own flat process after startup.

The prepared W3.2 comparison uses a fresh output directory for each attempt:

```powershell
python vr/tools/probe_p38_headset.py `
  analysis/vr-baseline/weapon-mesh-mapping/<fresh-w32-directory> `
  --mode compare --seconds 30
```

It copies root MP slot 1 for each mode, requires P38 ID 0 and the measured
14-node/354-face model, enables movement and the MP controller path, verifies
fresh OpenXR submissions, and leaves `headset_acceptance=false`. Use
`--desktop` only for the synthetic transport check.

### Headset execution context - mandatory

Codex shell commands run as `fractal-power\codexsandboxoffline` by default. That
account cannot use the interactive user's OpenXR HMD even when:

- Virtual Desktop Streamer and Server are running;
- the headset is connected and displaying the desktop;
- `RunVR-VDXR.bat` works when launched by the operator;
- the sandbox-launched process creates an OpenGL context and plays audio.

The observed sandbox-only failure is:

```text
mohu-vr-diag: OpenXR begin failed; flat native surface remains active
OpenXR begin failed at stage=system result=-35
XR_ERROR_FORM_FACTOR_UNAVAILABLE
```

The same launcher and game under the interactive `fractal-power\titan` account
successfully initialized `VirtualDesktopXR`, submitted stereo frames, and passed
the W3.2 comparison. Therefore:

1. Before headset work, verify `whoami` reports the interactive user, not
   `codexsandboxoffline`.
2. Run the headset probe only from the interactive account or an explicitly
   unsandboxed execution context. `--desktop` may remain sandboxed.
3. Pass the VDXR manifest with `XR_RUNTIME_JSON`; the working probe defaults to
   `C:\Program Files\Virtual Desktop Streamer\OpenXR\virtualdesktop-openxr.json`.
4. Never ask the operator to reconnect a working headset solely because a
   sandbox launch returned `stage=system result=-35`.
5. Preserve the execution account in new W3 receipts so launcher context remains
   auditable.

W5.3d/e all-family candidate controls after a marker, affine or family-stage change:

```powershell
python -X utf8 vr/tools/probe_weapon_aim.py `
  (Join-Path $runRoot 'weapon-aim') `
  --proof vr/proof/<new-all-family-receipt>.json
if ($LASTEXITCODE -ne 0) { throw 'All-family animated-marker candidate failed' }
python -X utf8 vr/tools/probe_weapon_aim.py `
  (Join-Path $runRoot 'weapon-aim-focused') --ids 0 1 4
if ($LASTEXITCODE -ne 0) { throw 'Focused P38/MP40/shotgun control failed' }
```

The full run requires a fresh child path and all 13 IDs for `--proof`. It
computes each synthetic hand pose from that profile's declared animated axis,
checks the per-shot marker copy against the shot fields, requires native ammo
and linked damage where the native baseline has damage, and preserves six-pellet
shotgun spread/speed variation. A petrol-bomb eye-discard burst can occur; accept
it only when a newer pair publishes after the last failure with zero rollback
mismatches, and retain the recovery numbers.

Full affected-path regression, once after a meaningful pose/replay change:

```powershell
python vr/tools/check_mp_view.py (Join-Path $runRoot 'mp-matrix') --all-weapons
if ($LASTEXITCODE -ne 0) { throw 'MP matrix failed' }
python vr/tools/check_mp_view.py (Join-Path $runRoot 'mp-lateral') --eye-offset 24
if ($LASTEXITCODE -ne 0) { throw 'MP lateral control failed' }
python vr/tools/check_mp_view.py (Join-Path $runRoot 'mp-fire') --fire-pistol --reject-recover
if ($LASTEXITCODE -ne 0) { throw 'MP native fire/recovery failed' }
python vr/tools/inspect_weapon_sets.py (Join-Path $runRoot 'flat-poses') --cycle --first-person-models --pose-controls
if ($LASTEXITCODE -ne 0) { throw 'Flat pose regression failed' }
python vr/tools/sky_ghost_control.py (Join-Path $runRoot 'sp-zero') --case zero
if ($LASTEXITCODE -ne 0) { throw 'SP regression failed' }
```

The old tool's `--native-projection` is an A/B discovery control; do not use it
as accepted projected/headset evidence. The W1 harness exercises the real hand
path separately from these existing direct-delta controls.

## 8. Verification, exit codes, recovery and session close

| Change | Required checks |
| --- | --- |
| Documentation only | Link/checkbox/task-ID consistency, source/receipt facts, diff whitespace; no game/build required |
| Pure weapon math / new spaces | Weapon fixture + new analytic space tests, P38 independent both-eye cases; then full affected pose/MP/flat/SP suite before accepting the implementation |
| MP mode/view/projection code | MP guard fixture, full MP matrix/lateral/fire/recovery, flat pose and SP zero regression |
| Shot state writes | New native/redirected shot traces + negative ownership/focus/ID cases, native damage suite, frame-state rollback and native fire/animation regressions |
| Launcher/input changes | Launcher tests, inherited-flag flat startup, relevant native input/boot/menu controls |

Existing focused commands (run once when affected):

```powershell
python -m unittest discover -s vr/tests -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Python tests failed' }
$cc = ((Select-String -LiteralPath build-release/CMakeCache.txt -Pattern '^CMAKE_C_COMPILER:.*=').Line -split '=',2)[1]
& $cc -std=c11 -Wall -Wextra -Werror -Ivr/underground vr/tests/test_mp_view.c -o (Join-Path $runRoot 'test_mp_view.exe')
if ($LASTEXITCODE -ne 0) { throw 'MP guard compile failed' }
& (Join-Path $runRoot 'test_mp_view.exe')
if ($LASTEXITCODE -ne 0) { throw 'MP guard fixture failed' }
& $cc -std=c11 -Wall -Wextra -Werror -Ivr/underground -Ipsxrecomp/runtime/include vr/tests/test_weapon.c vr/underground/weapon.c psxrecomp/runtime/src/vr_pose_math.c -o (Join-Path $runRoot 'test_weapon.exe')
if ($LASTEXITCODE -ne 0) { throw 'Weapon fixture compile failed' }
& (Join-Path $runRoot 'test_weapon.exe')
if ($LASTEXITCODE -ne 0) { throw 'Weapon fixture failed' }
& $cc -std=c11 -Wall -Wextra -Werror -fsyntax-only -Ivr/underground -Ipsxrecomp/runtime/include vr/underground/vr_diagnostic.c
if ($LASTEXITCODE -ne 0) { throw 'Diagnostic syntax failed' }
```

Interpret results correctly:

- MP/flat weapon inventories need `complete=true`, exit 0, unchanged sources/
  preferences and no remaining owned game. A receipt written during failure
  is not accepted just because some early cases passed.
- Both zero eye images must finish decoding, be populated and have identical
  hashes. Counters without a visible weapon do not prove a model seam.
- Native damage means a decrease in the complete trace at the exact current
  P2 health address. A kill can respawn to 32; final health alone is insufficient.
- A live counter read may catch one apply between restore calls. Verify exact
  equality after loss/drain; do not weaken the no-persistent-leak gate.
- Backend admission refusal increments `refused`; an interrupted eye may also
  increment `failed`. Retained/stale/last-failure fields are historical. For an
  intentional refusal control, require newer published/captured pair IDs after
  the last failed attempt, no new failures after recovery and zero state errors.
  Do not erase counters or accept a frozen retained picture as recovery.
- The established SP `sky_ghost_control.py` intentionally terminates its hidden
  child and may record child exit 1 with `intentional_termination=true`; its own
  command exits 0 when accepted. This exception does not excuse a crashed MP
  matrix or a save-load failure. The production flat startup smoke is also an
  explicit intentional termination, not interactive gameplay acceptance.

Failure handling is deterministic:

| Observation | Next action / stop condition |
| --- | --- |
| Debug port absent | Check build has debug tools ON, exact exe path, startup stderr and port 4372; no second game/build directory |
| `last_ok=0`, `state_load_failed`, ABI/identity mismatch | Stop dependent gameplay; ask operator for a fresh compatible PGXP source slot. Never patch ABI/identity or create a replacement save yourself |
| Occupied port / existing game | Recover/close it only if this session has a recorded ownership chain. Otherwise leave it alone; ask the operator only when it blocks dependent work, and continue independent code/docs |
| `emu busy or frozen` | Existing MP helper retries bounded busy responses; inspect advancing frames/logs after the bound. Do not invent pause/step/continue/run-to: removed APIs |
| Guard mismatch | Record actual bytes/contract and stay native. Do not weaken guards or reinterpret another overlay as the same function |
| Gun missing but apply counters rise | Compare the known native-projection control and focal/pose/near clipping at the same seam; do not reopen body-object discovery |
| World changes in hand-only control | Inspect eye/view restoration, transform order and double application; do not fix it with world offsets or widened FOV |
| Shutdown hangs | Stop admitting new eye transactions before TCP quit, as current MP helper does. Use bounded wait, then terminate only the recorded owned child; record forced cleanup as a limitation/failure, not exit 0 |
| Same hypothesis fails twice | Record both parameter sets and evidence; do not rerun it unchanged. Identify the missing fact or change one measured hypothesis; remain on this task |
| Hardware absent | Leave physical boxes open; finish ready desktop W3/W4 work and opt-in W5/W6 candidates under section 6, preserving native normal defaults |

Before ending an implementation session:

- [ ] Keep `PSX_DEBUG_TOOLS=ON` in the active desktop build by current operator
  direction. Only for a requested public/release checkpoint, configure the same
  build with debug OFF and build successfully:

```powershell
cmake -S . -B build-release -DPSX_DEBUG_TOOLS=OFF
if ($LASTEXITCODE -ne 0) { throw 'Release configure failed' }
cmake --build build-release --target psx-runtime --parallel 2
if ($LASTEXITCODE -ne 0) { throw 'Release build failed' }
```

- [ ] For that release checkpoint, if runtime/launcher changed, check hidden flat startup through RunFlat with
  inherited VR/weapon/MP flags; require pose/probe/stereo/OpenXR inactive and
  no MP frame replay. Do not require TCP from this debug-off smoke.
- [ ] Recheck source-save/thumbnail, settings/keybind and SteamVR hashes against
  this session's recorded baseline. Clear synthetic overrides and close only
  owned processes. No headset/runtime settings should silently remain changed.
- [ ] Keep bulk RAM/assets/images in ignored `analysis/`; retain compact receipts
  and selected proof under `vr/proof/`, with actual source/binary hashes.
- [ ] Check `git diff --check` and affected doc links. Review the diff; preserve
  unrelated work. No commit/push is implied unless the user requests it.
- [ ] Update checkbox IDs in VR_PLAN and the continuation record below; do not
  change earlier receipts to claim a new binary was tested.

## 9. Dead ends - do not repeat without new contrary evidence

| Rejected path / mistaken claim | Use instead / evidence needed to reopen |
| --- | --- |
| `actor+4AC` / shared 22-node table as first-person mesh | Measured `[actor+114] == input+9F0`; old candidate moved another panel |
| `80088C08` as the top-view weapon | Existing `800892E8` from `8008A544`; new viewport-specific evidence required to reopen |
| `8008DB98` is always the wrong function | It is the real native vertex producer when owned by the measured first-person caller; the old wrong body ownership was the error |
| `800892E8` as a simulation/player-update hook | This MP generation is animated model geometry; use measured mode-specific contracts |
| Generic frame-driver replay / all-span TRX experiments | Accepted SP frame-render slice and separate MP P1 reconstruction; black pairs were rejected |
| Manual GP0 OT walk as PGXP proof | Guest DrawOTag preserves packet source addresses |
| Following native y=240 flip for eye scratch | Accepted rollback-protected y=0 buffer; alternating black pairs were measured |
| Affine `*4096` applied to GTE TR | Integer TR helper and Q12 RT are deliberately different |
| Reference `ref=133`, pivot `(80,150,100)` or scale 850 copied as calibration | Existing authored pose uses ref=400; measure Underground spaces/mesh before changing placement |
| Native P2 hits prove tracked aim | Native shots are still native; require construction, trajectory and shared hand-ray/impact evidence |
| SP converter/table addresses applied to MP | W2.4 measured the MP converter `800799E4` and relocated tables; only the shared visibility selector helper is common |
| Current right-aim/node-box laser called exact barrel/triangle laser | W6 rendered affine/muzzle plus independently mapped exact triangles |
| New build folder or patched state header repairs a save | Ordinary PGXP checks and operator-provided compatible slot only |
| Historical run-11 SP script executed for MP | Read it as a lead; use root MP copied slot 1 and current ownership/layout |
| Old plan says create branch, align `31df2e1e`, scaffold VR | Completed; current branch/pins/receipts above are authoritative |

## 10. Continuation record

The current checkpoint and next actions are section 1, R1-R7 in VR_PLAN, and
SP_PARITY_REPAIR.md. Do not resume an older NEXT pointer from an evidence log.

Completed MP inventory, calibration, shot/lifecycle and W6.1 math receipts retain
their original scope and binary hashes. SP quality was reopened by a demonstrated
regression and operator rejection; this does not erase those historical results.
S1b's old movement/projection evidence is superseded for current SP visual claims.

Do not repeat full 13-ID combat matrices for a launcher/config change. Recheck
changed render/arm/arena paths and native integration, then profile production.
Keep W3.3/W3.5/W5.4d and live NPC/SP acceptance open until their actual controls
pass. Never convert transport counters or the 96-vertex result into a headset claim.
