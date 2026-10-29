# Underground VR execution plan

Updated: 2026-10-29. Working branch: `feature/vr-port`.

**Release scope is SP. MP is only a quick all-weapon calibration fixture.
Historical MP evidence remains useful; new MP feature/acceptance work must not
gate or displace SP alpha playability.**

This is the current checkbox plan, not the original proposal. Start with
[HANDOFF.md](HANDOFF.md) for exact instructions. Checked means the stated
scope has evidence; it never implies broader headset or gameplay acceptance.
Historical design and prior attempts belong in
[IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) and the evidence documents.

**CURRENT CHECKPOINT (2026-10-29): G7a is complete. The frozen SP fixtures
naturally expose only IDs 0, 13, 15 and 16. P38, Sten and Panzerfaust native
first motion follows a 30-degree hand rotation within 0.13 degrees; the
Panzerfaust is now admitted by the guarded SP basis path and falls back to native
control on tracking loss. Petrol has a valid live model/ammo but no native throw
constructor was observed; thrown and nine absent firearm/crossbow/StG rows remain
open. New personal SP slot 1 has missing level rendering (G5); slot 2 has severe
performance problems (G6). Earlier slot-5/music, pause and Sten smoke acceptance
remains scoped historical evidence.**

**Next: G7b–G7f all-MP-to-SP weapon parity FIRST → G5b/G5c slot-1 correctness →
G6b/G6c slot-2 baseline/target selection →
P3c2–P3c6 implementation/qualification when justified → measured budget
decision (P3d / conditional P3e if needed) → P4/P5 fresh view cadence/recovery
→ P6 focused SP performance acceptance.** Execute
[SP_WEAPON_PARITY.md](SP_WEAPON_PARITY.md) first, then the G5/G6 triage and
[PERFORMANCE_NEXT_STEPS.md](PERFORMANCE_NEXT_STEPS.md), with one game, two
compile jobs and unsandboxed launches. Preserve earlier image/music/culling
evidence; investigate the new G5 visibility report rather than replaying old
studies. Do not restart Sten basis mapping, pause ports or unchanged MP matrices.
P3b is complete. P0b's remaining two-title/XR dataset must not delay P3c.

A7 now has SP physical smoke acceptance. H1/A5a HUD is implemented; detailed
transitions/readability, broader SP damage, clean-close and matching-fixture
fog scopes remain distinct. The optional A3 editor is not on the alpha critical
path. Finish desktop implementation before another targeted headset request.

The owner rejected SP muzzle placement, poor performance, slot-3 weapon loss
and visible arms. The prior "physical pass next" order was premature. See
[SP_PARITY_REPAIR.md](SP_PARITY_REPAIR.md). R1-R3 below reopen only the failed
SP render paths; earlier MP/combat/math evidence retains its historical scope.

Operator policy: the laser indicates the bullet's hand-fixed aim ray. Native
recoil/reload remains visual. The shot candidate and future laser use the same
fixed calibrated muzzle/forward reference; animated markers are diagnostic and
eligibility data. This supersedes older moving-barrel aim requirements below.
Current evidence: [RENDERED_MUZZLE_EVIDENCE.md](RENDERED_MUZZLE_EVIDENCE.md) and
`weapon-hand-fixed-preservation-receipt.json` (all 13 IDs).
W4 native P38 mapping and W5.1 opt-in rendered-muzzle shot conversion are now
complete. The corrected P38 candidate retains its barrel, follows the measured
grip, and passes native P2 damage/miss and tracking-fallback controls without a
headset. W3.4 now has all-ID moving-marker evidence: recoil, reload, switching,
scope hiding and prop special actions are exercised with native ammo/slot
changes. W5.3 now has a complete read-only all-ID family map, including six
shotgun pellets. The native lifecycle probe now follows construction through
motion and linked damage, providing the preservation baseline for conversion.
W5.3c now passes canonical animated marker acquisition and timing at all 13
initial constructors plus three final projectile-origin stages, with real
load/stale/recovery/P2 controls. W5.3d now converts all 13 IDs under an explicit
default-OFF candidate: P38, MP40 and six-pellet shotgun controls pass with native
motion and real damage; grenade, petrol and rocket use complete guarded final-
origin stages. W5.3e now passes paired preservation and P2 impact. W5.4 now
passes the reload-tail, empty-fire, switch-during-reload, scoped-fire,
recoil-follow-up and load-recovery desktop pair. Scoped fire remains a recorded
native fallback because the hidden model exposes no fresh candidate marker.
The death/respawn supplement now exercises P1 health 32->0->32, rejects P2
candidate ownership, restores fresh markers without a save load and fires one
converted post-respawn P38 shot. It runs with stereo inactive; it adds lifecycle
evidence, not a new eye-rollback result. W5.4d physical hand-aim/impact
confirmation stays open. W6.1 now passes ten per-eye rendered-muzzle snapshots,
native recoil/reload, ownership/load/tracking rejection and live pair refusal/
recovery with actual stereo verification. W6.2/W6.3 are now desktop complete;
the current authored-axis defaults supersede the historical PCA calibration.
SP P38 render/shot bindings are measured; W5.2 remains open for linked live-NPC
damage/isolation, broader SP families and physical impact. W3.3/W3.5 remain
physical acceptance gates. Current evidence and exact continuation:
[WEAPON_COMPLETE_PROFILES.md](WEAPON_COMPLETE_PROFILES.md),
[SHOT_FAMILY_EVIDENCE.md](SHOT_FAMILY_EVIDENCE.md),
[P38_NATIVE_AIM_EVIDENCE.md](P38_NATIVE_AIM_EVIDENCE.md),
[combat receipt](../../vr/proof/weapon-p38-aim-receipt.json),
[complete-gun controls](../../vr/proof/weapon-complete-gun-controls-receipt.json)
and [moving-marker controls](../../vr/proof/weapon-moving-muzzle-receipt.json).
C1-C4 and W1-W3.2 remain complete; their historical receipts are retained.

The [reference reuse audit](REFERENCE_REUSE_AUDIT.md) names existing first-game
code and local equivalents for every workstream. Port/adapt those implementations;
measure only the target-specific bindings and data. Desktop diagnostic candidates
do not require physical acceptance first. Hardware acceptance gates physical
claims and normal default enablement. The dependencies below override the earlier
strict W1->W6/hardware-first sequence.

## Rules for using these checkboxes

- Check an item only after naming its source/binary, fixture, control and receipt.
- Keep desktop, physical headset and release acceptance as separate items.
- A historical receipt remains historical after source changes. Do not replace
  its hashes to make it appear to validate a new binary.
- Reopen a checked item only for a reproducible regression, changed guarded
  function/asset, or changed code on that item's execution path. Record why.
- Rerun the affected checks once after a meaningful change. Do not rerun all
  completed work repeatedly while leaving the current task unchanged.
- Update the handoff's next task ID, last result and next experiment at session
  end. An incomplete task needs a precise continuation, not "continue mapping".

## P - SP performance blocker (operator priority, 2026-10-28)

Workspace prerequisite (2026-10-29): [layout and recovery map](WORKSPACE_LAYOUT.md),
[cleanup receipt](../../vr/proof/workspace-cleanup-receipt.json).

- [x] WS1. Flat/VR share the same active executable and absolute root user
  saves. Current VR slots/cards migrated; all old overlapping Flat/VR files
  preserved and hashes checked. No save headers/execution identities changed.
- [x] WS2. Retire benchmark/test executable clutter and stale flat-check build;
  primary executable unchanged, old files preserved under one recovery archive.
- [x] WS3. Freeze separate SP/MP regression sources; tools copy them to isolated
  outputs. Headless requires an explicit save copy, never personal saves.
- [x] WS4. Archive superseded task queues, repair relative links and make one
  active documentation index. No performance implementation during cleanup.

The operator's latest instruction puts G7 weapon parity before G5/G6 and the
performance rewrite. See [SP weapon parity](SP_WEAPON_PARITY.md). Earlier smoke
closed only scoped historical slot-5/music, pause and Sten checks. G5/G6 remain
open [current regressions](SP_CURRENT_REGRESSIONS.md). The stable IDs retain their exact
scopes; the [smoke receipt](../../vr/proof/clean-disc-headset-smoke-receipt.json)
records the human observations and unmeasured limits. Performance is next; old
damaged-image regressions remain scoped closed; new slot 1 is a separate open case.

- [ ] G7. Complete all existing MP weapon calibration/control parity in SP
  **first**, including the new apparent fixed-aim petrol/Panzerfaust reports.
  [Ordered runbook and 13-ID matrix](SP_WEAPON_PARITY.md); G7a is complete and
  the guarded Panzerfaust basis candidate has desktop direction/fallback
  evidence. Remaining live-ID and thrown-family coverage is open.
- [x] G7a. Inventory each current MP profile and its actual SP render/aim/final
  origin consumption. The shared 13-profile adapter is mapped by ID, natural
  live fixture reachability is recorded, and P38/Sten/Panzerfaust origin and
  first-motion seams are measured. Petrol construction and nine absent live IDs
  remain explicit gaps. [Receipt](../../vr/proof/sp-weapon-parity-checkpoint-receipt.json).
- [ ] G7b. Complete shared authored pose/scale/grip/mask integration and SP
  firearm coverage, preserving existing P38/Sten, scope and animation behavior.
  A tracked model/ray does not close native projectile control.
- [ ] G7c. Adapt and verify the real SP thrown-family final writers: petrol
  first, then grenade. Prove calibrated final origin/initial direction after
  native overwrites; retain speed/spread/gravity/fuse/impact/ammo and fixed ray.
- [ ] G7d. Adapt and verify the real SP Panzerfaust rocket final writer/basis,
  ownership and first motion under independent head/hand controls. MP hook
  addresses are leads, not SP bindings; keep exact code/layout guards. The
  guarded candidate now rotates first motion with the hand, stays independent
  of 30-degree head yaw and falls back on tracking loss. Native speed/impact,
  the constructor's calibrated-origin adjustment and broader lifecycle remain
  open, so this step is not checked.
- [ ] G7e. Pass the all-13-ID SP matrix: model completeness/gun-only grip/scale,
  animations, rotated/translated hand, final native origin/first motion/appropriate
  impact, fixed-ray agreement, scope, switch, loss/stale, pause/load/refusal and
  restoration. Record naturally unavailable SP cases rather than fabricating
  inventory or calling an MP test an SP pass. Check changed shared MP behavior only.
- [ ] G7f. Record per-ID accepted/failed/unavailable coverage and restore normal
  production/personal-save/runtime state. Keep synthetic, physical and real
  live-NPC damage acceptance distinct; then return to G5/G6 and performance.

- [ ] G5. Resolve missing world rendering in personal **SP internal slot 1**, file
  `slot01` / tool index 1. Do not confuse it with MP slots or historical SP slot 5.
- [x] G5a. Record the operator report and freeze byte-identical state/thumbnail
  in the existing SP fixture library, with source hashes and no personal writes.
  [Receipt](../../vr/proof/sp-current-regressions-receipt.json); no runtime diagnosis yet.
- [ ] G5b. Reproduce/classify copied slot 1: native Flat versus stereo with
  matched scene/camera, actual world-geometry evidence and selection/draw/load
  state. Probe completion/nonblank enemies/pair counters alone do not pass this.
- [ ] G5c. Fix the demonstrated cause and validate both eyes, relevant head poses,
  rollback, streaming/music, weapon/laser and pause/load recovery. If not
  reproduced, record the missing condition and keep the issue open.
- [ ] G6. Resolve severe performance in personal **SP internal slot 2**, file
  `slot02` / tool index 2. No numeric FPS was reported; do not reuse slot-5 numbers.
- [x] G6a. Record the report and freeze the byte-identical internal-slot-2 (`slot02`) pair in
  the existing SP library, preserving source hashes and all personal data.
- [ ] G6b. Verify world rendering, then obtain a current production slot-2
  baseline: pair work/fresh cadence/guest timing and relevant CPU/GPU stages.
  Diagnostic attribution and actual HUD/weapon/laser/XR scope are separate.
- [ ] G6c. Confirm the dominant implementation target from this workload and
  apply the ordered P3c correctness/A-B/full-path gates. Reuse preflight work if
  supported; otherwise update one next target with measured evidence.

- [x] G1. Repair slot-4 Sten/common firearm aiming. Rotated native first motion,
  native/loss fallback and P38 regression pass; operator confirms Sten in headset.
  Live all-ID SP damage remains R6.
- [x] G2. Restore slot-5 world loading: clean image replaces the damaged input.
  Desktop native load/both-eye/independent-hit proof plus operator headset
  confirmation: no more missing level. Historical recovery is disabled.
  This closes that historical fixture only; new personal slot-1 report is G5.
- [x] G3. Recover the stuck stream: operator confirms music is fixed on the clean
  image. Earlier payload/refill controls advance after a controlled hitch.
  Historical recovery alone did not recover the old image's zeroed payload.
  Both supplied replacements now pass all 318,028
  sector checks and contain the actual payload; executable/overlays match and
  a copied slot-5 smoke passes without recovery. The remaining clean image is
  now active and the old repair disabled. See [disc comparison](DISC_IMAGE_COMPARISON.md).
- [ ] G4. Enable the hand-fixed surface laser for grenade and petrol, validate
  both eyes and grip/loss controls; this is an aiming ray, not a ballistic arc.
  Implementation and full SP petrol surface/loss/release checks pass. Grenade
  rays match in MP calibration, but two runs fail VRAM restoration (2/3
  mismatches); SP grenade acceptance remains unproven. Preserve failed evidence.
- [x] G4a. Enable grenade/petrol hand-fixed surface rays in the shared path.
- [x] G4b. Validate SP petrol eight directions/both eyes/independent hits and
  grip release/tracking loss; zero VERIFY mismatches.
- [ ] G4c. Obtain/validate the native SP grenade case and preserve restoration;
  do this under G7's SP thrown-family parity first. An MP
  feature expansion is not an alpha prerequisite.

Current production desktop evidence and exact next steps are in
[SP_GAMEPLAY_REPAIRS.md](SP_GAMEPLAY_REPAIRS.md). Release/debug-OFF is restored.
The optional native-world copy skip passes fallback controls and three A/B
repeats but remains OFF; it saves native-frame work, not the 17.6-ms stereo
traversal budget. Resolution reduction does not remove that cost. These controls
exclude XR/hand-HUD work and do not complete P0b's two-title/full-XR comparison,
P3c's shipping optimization or P4's independent fresh-view cadence.

Read [SP_PERFORMANCE_AND_PETROL.md](archive/SP_PERFORMANCE_AND_PETROL.md) and the current
[first-game comparison](archive/SP_PERFORMANCE_COMPARISON.md). This order supersedes
older R6-first pointers. MP remains calibration only. The operator's first-game
60-FPS experience is the playability reference; 90 is preferred.

- [x] P0a. Compare current first-game/Underground sources, launch/build defaults
  and preserved traces. Same shared framework/checkpoint/readback implementation;
  Underground's tested scene draws 65–69% more primitives per eye. Different
  historical scenes/builds/backends prevent a matched FPS/speedup conclusion.
- [ ] P0b. Capture controlled current production baselines for both titles:
  fixed copied fixture per title, warm native calls, equal effective resolution,
  projection/runtime/HUD/weapon/laser options, fresh pairs and guest VBlanks.
  No physical headset. Preserve reference source/settings/saves; see comparison
  report for exact provenance, workload and cleanup requirements.
- [x] P0b1. Clean-image Underground default-config slot-5 desktop baseline/smoke:
  activation receipt, 120 valid exported records, normal close. No XR/hand-HUD
  cost, no matched two-title or fresh 60/90 acceptance implied. Refresh once
  when beginning the next candidate; do not repeat the image audit.
- [x] P1. Reproduce SP slot-3 petrol loss with one native switch. Accept its
  exact measured metadata variant; verify 99 visible / 97 masked vertices in
  both eyes, no new guard failure, P38 fire/reload/load and rollback regression.
- [x] P2. Fix RunVR default to production `game.toml`; explicit diagnostics only.
  Matched debug-OFF native overlays reduce guest work about 16.5%, but measured
  desktop fresh pair cadence remains about 30/s. No 60-FPS claim.
- [x] P3a. Port reference stage brackets; isolate traversal, submission, exact
  laser, visibility and HUD capture/readback. Persistent pre-null settings
  backup and sufficient cleanup timeout; production trace export without TCP.
- [x] P3b. Profile native replay using the first game's existing phase/host/
  guest-cycle tools and split the wrapper's child draw stages. Resolve native
  overlay DLL samples; measure full guard/hook cost outside the collection span.
  Name the top three host costs; do not substitute guest cycles for host time.
  Exact commands, nested trace shape, module caveats, attribution targets,
  exit criteria and failure handling: [runbook](PERFORMANCE_NEXT_STEPS.md).
  Completed: [native attribution](NATIVE_REPLAY_PROFILE.md). Exclusive packet /
  preflight / GPU-command segments cost 5.729 / 3.805 / 1.143 ms per pair;
  full visibility hook 0.068 ms, collector 0.043 ms. Cached DLLs are resolved
  with their own PE tables; system samples are not treated as waits.
- [ ] P3c. Implement a measured replay or HUD synchronization improvement and
  validate at least three alternating production baseline/candidate windows.
  Preserve native HUD/fallback, geometry/FOV, weapons, laser and guest timing.
  Generic changes need both-game checks before either pin changes. Completed
  first-game checkpoint/readback work is already shared; do not redo it.
  Next: the real `80011424` caller contract and a qualified preflight kernel.
  Three compiler-inlining experiments are rejected. Existing IPO improves
  desktop pair work about 4.3% but fails stable full-path qualification; OFF.
- [x] P3c1. Qualify bounded native-copy candidate controls and three diagnostic/
  production A/B repeats; it remains OFF. Small desktop cadence gain does not
  remove the approximately 17.6-ms pair cost or close P3c/P3/P4.
- [ ] P3c2. Capture the full real `80011424` caller contract, including live
  registers, scratchpad, GTE/PGXP and internal resume entries. Start a standalone
  caller harness and establish valid per-execution integration fixtures before
  changing execution identity. Existing probes need build/fixture selection
  support for new families; old sibling launch overrides are retired. Exact deliverables:
  [ordered runbook](PERFORMANCE_NEXT_STEPS.md#31-ordered-execution-checklist--start-at-p3c2)
  and [fixture rules](PERFORMANCE_NEXT_STEPS.md#32-execution-identity-and-fixture-handling--resolve-before-integration).
- [ ] P3c3. Implement the faster preflight helper through the real caller
  interface, selected at build time, with the original runnable REFERENCE.
  Pass paired caller-result tests for accept/reject, winding, clipping/depth
  and subdivision, including observable memory and precision effects.
- [ ] P3c4. Pass focused correctness/lifecycle controls separately from timing:
  world/FOV/PGXP, gun-only weapon/laser, native gameplay/audio timing, pause,
  tracking loss, render refusal/recovery and load. Use valid fixture equivalents;
  leave unavailable integration coverage open instead of bypassing identity.
- [ ] P3c5. Run three alternating production baseline/candidate desktop windows
  and the second SP workload. Record actual binary/execution/fixture/flags and
  require a useful consistent gain beyond run spread; retain failed controls.
- [ ] P3c6. Qualify the actual HUD/weapon/laser/XR path with matched repeated
  measurements and correctness, then record retained/rejected/deferred and one
  next task. No physical headset needed for this gate. Synthetic/null-HMD
  evidence has its own limits; a limited no-hand run is not complete coverage.
  A rejected candidate leaves P3c open. No 60/90 claim follows from cost alone.
- [ ] P3d. Decide whether parent packet-builder work is still needed after the
  preflight result. If over budget, optimize measured `80010CF0` through its
  caller using the same contract/correctness/A-B/full-path gates. Otherwise
  record why it is deferred. This is a conditional budget decision, not a
  requirement to rewrite the parent if the full budget already passes.
- [ ] P3e. Decide whether a remaining HUD synchronization stall needs work from
  current full-path evidence. Inspect existing local/shared change detection,
  checkpoint reuse and paired capture/readback first. Implement only a missing
  measured optimization, preserving native updates/fallback; otherwise record
  the reason to defer. Do not count old shared ports as new work.
- [ ] P3. Reduce measured production scene-replay/HUD cost to the complete
  16.67 ms/frame budget; 11.11 ms preferred. Keep weapon/laser/HUD and correct FOV.
- [ ] P4. Implement safe render-only cadence independent of native 30 Hz draw.
  Preserve simulation/audio/shot timing and rollback/save ABI. No turbo,
  native VBlank-rate change or stale-pair/reprojection FPS substitution.
  A cached-scene path is a larger conditional fallback if targeted replay cannot
  meet budget/cadence, not a concurrent task or mandatory alpha feature. Follow
  [the budget decision table](PERFORMANCE_NEXT_STEPS.md#33-what-follows-preflight--choose-by-measured-full-path-budget)
  and preserve visibility, moving entities, weapon animation and fresh poses.
- [ ] P5. Pass desktop/null-HMD freshness, pacing, rollback, pause/load/recovery
  and guest-timing controls; restore debug-OFF production build.
- [ ] P6. One bounded SP headset check: steady minimum 60 fresh application
  frames/s, preferred 90; record CPU/GPU frame times and compositor repeats.

## A - Alpha playability backlog after the performance blocker

G7 weapon parity is FIRST, including the SP family coverage referenced by A2.
After G7 and G5/G6 triage, P3c/P4/P5 take priority over the remaining backlog
unless a new SP regression blocks their controls. A7 is implemented and physically accepted for SP; do not
port it again. A2 defaults/masks, A4 exact ray and A5 native HUD retain the scoped
evidence linked below. Continue only their explicitly open parts; defer optional
editor/polish work until after performance.
The [original study](archive/ALPHA_PLAYABILITY_AND_CALIBRATION.md) supplies reuse leads,
not a fresh implementation order. Port working reference behavior where relevant;
do not invent a settings framework. A3's runtime editor remains optional. These
are stable scope IDs, not instructions to redo already accepted work or require MP.

- [ ] A1. Classify/fix active-play versus close-only process exits (S5/Q1).
- [x] A1a. Classify the six physical batch exit reports: all record
  `sdl_window_close` followed by `atexit`; no active-play exception is reported
  there. Nonzero final process codes still leave S5 open.
- [x] A7. Port explicit native pause-state + existing native quad presentation
  and menu-input routing. SP/MP each pass two navigation/resume cycles plus
  load-while-paused recovery, fresh native XR quads, stereo recovery, zero XR
  failures and zero rollback mismatches. [Evidence](PAUSE_MENU_PARITY.md).
- [x] A7a. Operator confirms SP native pause is OK in the headset (2026-10-29).
  This closes the SP functional smoke, not exhaustive comfort/menu edge cases.
  MP physical pause acceptance is not required for the SP alpha.
- [ ] A2. Correct grenade held orientation, StG gun-only mask, oversized defaults
  and shared shot/sight alignment; pass representative live SP NPC impact (R6).
- [x] A2a. Authored axes/upright props, reference firearm scale and semantic StG
  mask; all 13 IDs pass actual SDK affine checks, changed topology and focused
  native firing controls. [Evidence](ALPHA_WEAPON_REPAIRS.md).
- [ ] A2b. Real SP NPC health/damage ownership and isolation (R6). Broader SP
  calibration/shot-family parity is G7 FIRST, not gated on this damage study.
- [ ] A2c. Operator accepts the corrected scale, grip, sights and target impact.
- [ ] A3. Add effective per-ID calibration state, versioned persistence and a
  minimal controller-operated in-headset menu using existing UI/XR surfaces.
- [ ] A4. Share the shot ray and hit actual triangles for the laser (W6.2-W6.4),
  or omit it from alpha instead of presenting visibility-box hits as surfaces.
- [x] A4a. Exact SP/MP arena + supported MP prop readers, shared fixed muzzle
  ray, both-eye independent intersections, tracking/grip fallback and native
  projectile agreement. Physical W6.4 remains open.
- [ ] A5. Readable health/ammo/essential mission information with native fallback
  (H1/H2 minimum); wrist polish may follow alpha.
- [ ] A6. Focused SP route, recovery/death/load, measured cadence and bounded
  stability test, then debug-off alpha packaging (B9/B10/Q1-Q4).

## R - 2026-10-28 SP parity repair (retained scope IDs)

Current execution order is G7, then G5/G6, then measured performance. These IDs
retain their evidence/scope; their historical sequence does not override G7.

- [x] R1. Audit actual reference/current sources and correct stale plan/handoff
  readiness claims. Weapon-only rendering, post-animation placement, precision
  and production/debug separation are reusable. Target flash packets, strip data,
  SP ownership and arena limits require Underground bindings, not new architecture.
- [x] R2. Replace separate flash projection with the same-eye projected animated
  muzzle vertices, correct both 40-byte FT4 packet tags (`+0x5FC`/`+0x624`),
  and apply SP gun-only filtering after projection. Preserve
  all 96 P38 gun vertices and remove 142 arm vertices, including on tracking loss.
  Desktop baseline, displaced hand, head-follow, close and lateral-eye controls
  are recorded in `sp-parity-repair-receipt.json`; physical acceptance stays open.
- [x] R3. Reproduce slot-3 allocation failure and restore the gun with guarded
  spare native-buffer use. Same binary, pose and fixture: disabled path loses
  the gun; enabled path renders 96 vertices per eye. Preserve source data,
  reload compatibility, arena pointers and eye rollback. Broader scenes remain open.
- [x] R4. Complete production performance/native overlay integration. Separate
  measured debug overhead from the remaining interpreter cost. Native cached
  config now executes the VR callbacks with real stereo and weapon parity.
  Matched 300:900 window: 9.9435 s native versus 9.8978 s interpreted, with
  slot 3, 1080p, no XR, VERIFY OFF and a clean exit. Wall time is effectively
  unchanged (0.46% slower in this native sample); the native path finishes the
  same 600 guest frames with 18.2% less measured guest work. Evidence:
  [SP native hooks](SP_NATIVE_HOOK_EVIDENCE.md).
- [x] R4a. Remove detailed debug recording from the playable build, retain
  diagnostic ON only for TCP tools, and measure matched quiet SP controls.
  Final-source debug ON: 18.2 new pairs/s; OFF: 29.2 pairs/s (no XR, native-hand
  fallback, 1080p, VERIFY OFF). This is a build-overhead result, not headset FPS.
- [x] R4b. Instrumented 24 entry hooks and 11 guarded instruction sites from the
  registration block/engine map, regenerated with the supported emitter, and
  passed SP baseline/turned/close/lost/out-of-view plus focused P38 MP
  stereo/fire/rollback/recovery controls before comparing throughput.
  Native work used 2,807,918 calls in the final matched window; measured guest
  work fell 18.2% but wall time stayed effectively flat. The bounded result
  does not claim a uniform FPS gain. Evidence:
  [SP native hooks](SP_NATIVE_HOOK_EVIDENCE.md).
- [ ] R5. Resolve SP view-dependent fog from measured depth/transform ownership.
  Paused on fixture selection: the available analysis/root slot-0 captures show
  the courtyard but not the operator's street-wall/fog case. The earlier
  slot-2/3 sweeps are non-matching controls, not fog evidence. Request a fresh
  compatible PGXP SP state that reproduces the reported scene.
- [ ] R6. Pass real SP NPC P38 damage/isolation; reuse the already measured
  P38 shot basis and fixed hand ray. G7 owns complete SP calibration/family
  integration first; direction/first-motion checks alone do not close R6.
- [ ] R7. Obtain bounded physical gun-only, both-eye flash/impact and performance
  feedback after desktop fixes. This does not gate R4-R6 desktop work.
- [x] R7a. Complete the operator-requested visual tracking batch: all four MP
  sets / 13 unique IDs and SP slot-3 P38 smoke, including a laser-enabled restart,
  initially received "Looks good". Later detailed feedback reopens calibration,
  StG hand masking, high shots and laser endpoints; batch execution remains complete.
  See [headset batch](HEADSET_BATCH.md). Impact measurements,
  numeric performance, recenter/recovery and clean shutdown retain separate gates.

## S - follow up the 2026-10-27 physical smoke

Follow the ordered contract in HANDOFF; preserve prior receipts and fixture hashes.

- [x] S1. Validate the all-family camera refresh with shot recording OFF and
  legacy P38 aim OFF; recording must not hide the startup dependency. Capture
  current-binary evidence before calling the predicate fix runtime-validated.
  Evidence: `headset-s1-camera-receipt.json`; 20 eligible hand-fixed aim updates,
  zero fallbacks, capture count zero and linked P2 damage 32->14.
- [x] S1a. Isolate the centre-fixed native muzzle flash and move the same
  eye-replay packet to the projected animated muzzle on desktop. Evidence:
  [NATIVE_MUZZLE_FLASH_EVIDENCE.md](NATIVE_MUZZLE_FLASH_EVIDENCE.md) and
  `native-flash-alignment-receipt.json`. Physical visibility remains in S2.
- [x] S1b. Historical one-pose binding control (superseded by R2/R3 for visual
  readiness). Bind the actual SP held-weapon draw, guard the measured SP P38
  basis caller and translate both SP flash copies with the `H=400` weapon
  projection. Baseline flash `(355,225)` moved to `(454,225)` after +150 mm
  hand X; each control wrote 2/2 aimed P38 shots with zero shot/flash
  fallbacks and clean exit. Evidence:
  [SP receipt](../../vr/proof/sp-weapon-aim-flash-receipt.json). Physical
  gun/flash/impact acceptance remains open.
- [ ] S2. Retest physical MP FOV edges with the separate MP frustum opt-in ON
  and the explicit hand-fixed probe profile. Configuration fix alone is not
  proof of visual correction or complete weapon acceptance. The desktop control
  records 1,638 overrides per eye with zero fallbacks; physical edges and
  physical observations remain pending. MP remains the all-weapon tracking
  fixture; it is not the primary product target. Evidence:
  `headset-s2-mp-frustum-receipt.json`.
- [ ] S3. Measure the SP view-dependent fog/distance defect and its actual
  producer, reusing first-game fog/depth work before changing target bindings.
- [ ] S4. Capture SP guest/world-pair cadence and timing versus XR refresh for
  the operator-reported approximately 35 FPS and very poor resolution; measure
  the actual source/eye/swapchain path before changing scale. Feed measured
  bottlenecks into Q2. Direct/default launch now uses `1080p`; the measured SP
  path is 2560x1200, but this is not a performance or physical-quality claim.
- [ ] S5. Resolve/record bounded MP shutdown with a real clean child exit;
  nonzero exit or forced cleanup cannot produce complete acceptance.
  The 2026-10-28 physical batch adds repeated `0xC0000409` process exits in MP
  and SP and `3489660927` in MP2; source saves/preferences stayed unchanged.
  Investigate these exits separately from the accepted weapon visual smoke.

S1b records historical one-pose evidence. R2/R3 supersede its SP render and
flash implementation. Physical and non-P38 SP coverage remain open. A1-A6 now
controls priority; the completed smoke is historical, with specific failures reopened.

## C - cross-game consistency pass (complete; no feature rediscovery)

- [x] C1. Add host-only cross-game parity fixtures and a behavior/policy difference
  table for the helpers named in CONSISTENCY_HANDOFF. Preserve current outputs
  and capture intentional differences before extraction. Evidence:
  `vr/tests/reference_parity_vectors.c`, the two title adapters,
  `vr/tools/check_reference_parity.py`, and the 33-case baseline.
- [x] C2. Consolidate exactly the 3x3 inverse, conservative box visibility and
  slab ray/box math in a shared framework implementation consumed by both games.
  Retain title-specific wrappers, limits, native readers, hooks and calibration.
  Both framework copies use `vr_geometry_math.c` SHA-256
  `9e51708f0f05a16182e4d5893063a06f656d4fc723965f72cea9191632661a23`.
- [x] C3. Build both consumers and pass focused fixtures plus the affected
  pre/post runtime controls. New receipts identify both games and the shared
  core revision. One game's passing result does not close this gate. Both
  release builds and host fixtures pass. Underground zero, lateral, side/head,
  native-fire, refusal and recovery controls pass. Reference cold boot supplied
  a fresh slot 9; five world views produced unique per-eye crops with 1,546
  rollback checks and zero mismatches; eight weapon controls passed; a real
  tracked-weapon watchdog aborted one eye, retained pair 1065 and published
  later complete pairs. Both flat configurations link with OpenXR OFF. See the
  parity receipt.
- [x] C4. Document common ownership, retained differences and a repeatable parity
  check in both projects. The ownership rule, command, receipt, source hashes
  and intentional policy differences are recorded. At C4 close, NEXT was W2.3.

Exit gate: shared calculation for these three operations, explicit game adapters,
both consumers validated, no behavioral/default change concealed as cleanup.
Input response rules, GTE weapon hook/storage and MP selectors are valid title
differences. Projection/HUD/aim/triangle features stay outside this first batch.

## Established foundation - preserve, do not rediscover

- [x] B1. Working branch, title ID, PGXP ABI and current framework/UI pins recorded.
  Current framework is `555e1eab`; it retains the earlier `b982e66e` work and
  is not the original `31df2e1e` baseline.
- [x] B2. Optional Underground plugin, guarded engine map and one shared
  `build-release`; default CMake VR option remains OFF.
- [x] B3. SP frame-render replay, complete zero/lateral eyes and PGXP projective
  provenance measured. Guest DrawOTag preserves source packet addresses.
- [x] B4. SP near-plane and signed-NCLIP fixture controls retained.
- [x] B5. OpenXR/native menu surfaces and headless runtime controls implemented.
- [x] B6. Corrected SP world scale, y=0 replay buffer, flat HUD and sky ghost;
  operator acceptance recorded for scale/image/sky correction.
- [x] B7. SP head-turn visibility and 1080p launcher defaults implemented and
  measured in the existing scene.
- [x] B8. Native input response and reference button/movement routing measured
  with synthetic controls. Normal launch starts menus (`-Slot -1`).
- [ ] B9. Physical movement, pause/recenter/focus, transitions and broad SP/MP
  gameplay acceptance. Synthetic input is not hardware acceptance.
- [ ] B10. Broader scene/near-wall/streaming stability and performance coverage.

Evidence: [HANDOFF.md](HANDOFF.md), [MOVEMENT_EVIDENCE.md](MOVEMENT_EVIDENCE.md),
[PGXP_RENDER_VIEW_EVIDENCE.md](PGXP_RENDER_VIEW_EVIDENCE.md),
[HEAD_TURN_HUD_EVIDENCE.md](HEAD_TURN_HUD_EVIDENCE.md),
[SKY_GHOST_EVIDENCE.md](SKY_GHOST_EVIDENCE.md).

## Completed weapon foundation - locked unless a regression is demonstrated

- [x] M1. Operator-owned MP source slots 1-4; stationary P2; four closed native
  cycles; 13 unique weapon IDs. Source saves/preferences unchanged.
- [x] M2. Native P2 damage for all 13 IDs, including delayed damage/respawn cases.
  Damage gate is an exact P2 `actor+0x108` health-write decrease.
- [x] M3. Real first-person object located:
  `[actor+0x114] == input+0x9F0 == actor+0xDF0`.
  `actor+0x4AC` is the body, not this viewmodel.
- [x] M4. Per-ID first-person magic, node/face counts and source vertex hashes
  captured. Shared 22-node body layout is not a weapon profile.
- [x] M5. Guarded flat viewmodel pose seam: enter `800892E8` from `8008A544`,
  apply `800894DC`, restore `80089D30`; native animation remains the input.
- [x] M6. All 13 IDs have flat native/+24/yaw+12/lost/restored controls with
  unchanged sampled world/HUD/other-weapon pixels and drained restore counts.
- [x] M7. Guarded P1-only MP eye replay: context `800A0B08`, frame `80054BC4`,
  selector `80054E68`, scene `8006E9D8`, native source view 512x120.
- [x] M8. Both eyes exercise all 13 meshes; zero eyes match. Latest matrix:
  1,215 pairs / 2,430 rollback checks, zero errors, four closed cycles.
- [x] M9. Lateral +/-24 eyes populated; 52,136 changed pixels. Native pistol
  firing during eye replay consumes clip 8->7 and damages P2 32->31.25.
- [x] M10. Deliberate backend refusal recovers newly captured pairs. Current
  history counters are distinguished from current published image IDs.
- [x] M11. Existing flat-pose and SP stereo regressions pass after MP work;
  debug-off build restored and inherited-flag flat startup is inert.
- [ ] M12. Physical hand attachment, head/hand independence and barrel/shot
  alignment. W1 now proves synthetic independence, not physical acceptance.

Evidence: [WEAPON_MAPPING.md](WEAPON_MAPPING.md),
[flat receipt](../../vr/proof/weapon-viewmodel-receipt.json),
[MP eye receipt](../../vr/proof/weapon-mp-eye-receipt.json),
[MP build receipt](../../vr/proof/weapon-mp-build-receipt.json).

## W1 - P38 absolute pose contract and independent synthetic controls

Dependency: M1-M11. First weapon: **ID 0, source slot 1, zero native switches**.
No firing changes, laser work, mesh filtering or MP renderer replacement here.

- [x] W1.1. Capture named coordinate spaces, native affine/animated vertex
  samples, GTE RT/TR and eye view at the existing P38 seam. Record units,
  axes, handedness, authored placement and invertibility. See handoff Step W1.
- [x] W1.2. Add a copied-fixture head/hand independence harness using real
  synthetic hand samples, not only `mohu.vr.weapon.pose x=/yaw=` deltas.
- [x] W1.3. Implement the measured absolute grip/model placement while preserving
  native animation; account for the eye transform exactly once. Full inverse
  where required; do not assume native camera/weapon matrices are orthonormal.
- [x] W1.4. Pass independent head-only, hand-only and combined pose controls;
  origin/recenter, loss/unfocused/inactive/stale/invalid recovery; both eyes;
  bounded numeric error and visible-mesh controls, with no world/simulation drift.
- [x] W1.5. Retain a P38 coordinate-contract receipt, paired PNGs and repeatable
  test commands; rerun affected baseline checks and update next task to W2.

Exit gate: independently supplied poses predict the measured rendered P38 pose
in a declared coordinate space. Head motion must not apply twice or drag a
stationary world-space hand anchor. A gun that merely moves is not a pass.

Evidence: [WEAPON_CALIBRATION.md](WEAPON_CALIBRATION.md),
[pose-space receipt](../../vr/proof/weapon-pose-space-receipt.json),
[both-eye controls](../../vr/proof/weapon-pose-space-controls.png),
[build receipt](../../vr/proof/weapon-pose-build-receipt.json). The receipt
contains 29 cases, 10 independent head cases, five invalid controls, zero
RT/TR prediction error, `1e-4` recovered-hand rotation error, `0.493` unit
translation error and `1.0` origin-anchor error. W1 used no firing. Physical
grip/scale, MP head-turn visibility and tracked shots remain open in W2-W5.

## W2 - MP visibility and native input needed for usable hardware testing

Dependency: W1. Do not apply SP addresses to the MP overlay.

- [x] W2.1. Trace the native MP level selector from the already measured MP
  scene callback; capture its complete code, tree/masks/queue and caller.
- [x] W2.2. Add a separately guarded MP eye-frustum override only after measuring
  its actual layout; preserve native fallback on malformed/overflow input.
- [x] W2.3. Pass zero, +/-90-degree head turns and near-wall controls with populated
  geometry, native selector comparison and zero rollback errors. Evidence:
  [controls](../../vr/proof/weapon-mp-visibility-receipt.json),
  [control sheet](../../vr/proof/weapon-mp-visibility-controls.png) and
  [build regressions](../../vr/proof/weapon-mp-visibility-build-receipt.json).
  Each eye sampled all 21 level nodes. The zero and near-wall controls preserved
  the native visible subset; the 90-degree cases exercised justified changed
  sets and retained populated world pixels. The near-wall run measured two
  consecutive approaches at or below 200,000 raw position units.
- [x] W2.4. Verified the MP controller converter/dispatcher and native action
  tables, then added the measured mode adapter to the existing controller
  source and pure mapper. Evidence:
  [MP input controls](../../vr/proof/weapon-mp-input-receipt.json) and
  [build/regressions](../../vr/proof/weapon-mp-input-build-receipt.json).
  P1 ownership, converter `0x800799E4`, dispatcher `0x80079B28`, action row
  `0x800C0ED0`, axis records `0x800C0BF0` and curve `0x800A458C` are guarded by
  live hashes. Forward, strafe, turn, focus release and trigger delivery passed;
  the SP slot-2 regression and cross-game parity also passed.
- [x] W2.5. Verified native movement/buttons, no render-time input sampling,
  focus release, native Start pause/resume, and separate SP/flat fallback.
  Evidence: [MP lifecycle controls](../../vr/proof/weapon-mp-lifecycle-receipt.json)
  and [build/regressions](../../vr/proof/weapon-mp-lifecycle-build-receipt.json).
  The MP run delivered 17 exact pad samples, froze actor position while paused
  with forward held, resumed movement through native Start, recorded zero
  render-time input samples and zero guard fallbacks. The isolated SP launcher
  passed 13 controls and 298 rollback checks; the OpenXR-off flat build reached
  `main()` with inherited VR flags inert. Physical MP input remains open.

W2.1 evidence: [MP_LEVEL_SELECTOR_EVIDENCE.md](MP_LEVEL_SELECTOR_EVIDENCE.md)
and [selector receipt](../../vr/proof/weapon-mp-level-selector-receipt.json),
with the final debug-off binary in
[build receipt](../../vr/proof/weapon-mp-level-selector-build-receipt.json).
The native MP path is a flat 26-node scene list with 21 `8006C61C` level nodes,
not the SP PVS leaf queue. Complete function guards cover frame `80054BC4`,
scene `8006E9D8`, callback `8006C61C`, selector `80096EF4` and helper
`80096AC8`; both natural scene callers executed in the copied slot-1 fixture.
Visibility masks at node `+0x0C`, the ordered queue and all hashes are in the
receipt. No firing, override or physical acceptance is claimed.

W2.2 evidence: [MP_EYE_FRUSTUM_EVIDENCE.md](MP_EYE_FRUSTUM_EVIDENCE.md),
[measurement receipt](../../vr/proof/weapon-mp-frustum-measurement.json),
[zero-angle both-eye control](../../vr/proof/weapon-mp-frustum-controls.png) and
[build receipt](../../vr/proof/weapon-mp-frustum-build-receipt.json). The live
selector uses node center `+0x2F4..+0x2F8` and radius `+0x2FC`, current GTE
RT/TR, a heap view descriptor and a measured 540x120 screen rectangle.
`MOHU_VR_MP_FRUSTUM=1` covered every level node in each eye, left non-level
nodes native, had no fallback or rollback errors, and retained populated
matching zero-IPD eyes. W2.3 added zero, +/-90-degree and near-wall acceptance,
including per-eye native/override selector comparisons and a strict top-screen
world-coverage check that excludes the weapon/body region.

W2.4 evidence: [MP input controls](../../vr/proof/weapon-mp-input-receipt.json)
and [build/regressions](../../vr/proof/weapon-mp-input-build-receipt.json).
The multiplayer overlay relocates input from the SP converter
`0x80083C6C`/table `0x800C47C8`/curve `0x800AB12C` set to converter
`0x800799E4`, dispatcher `0x80079B28`, P1 actions `0x800C0ED0`, axis records
`0x800C0BF0` and curve `0x800A458C`. Both P1/P2 actor ownership plus the current
player and 512x120/H=400 context select MP; copied slot 1 emitted neutral,
forward, strafe-right, turn-right, focus-release and Cross samples. Mismatches
return neutral. This is desktop synthetic input evidence, not physical
acceptance.

W2.5 evidence: [MP lifecycle controls](../../vr/proof/weapon-mp-lifecycle-receipt.json)
and [build/regressions](../../vr/proof/weapon-mp-lifecycle-build-receipt.json).
The controller source now checks replay state before querying XR input and
records mode, focus and render-blocked counters without changing the pure
mapper. Every movement sign, seven button masks, focus loss/recovery and native
Start pause/resume passed. SP slot 2 passed through the normal launcher with
`sp=211`, no MP/menu samples and no render-time sampling. The flat build's
6-package configuration reached `main()` with no active input/MP/stereo marker.
`probe_mp_input.py` rejects an MP-to-SP savestate swap because the resident
overlay does not change; SP must use its own launch path.

Exit gate: MP head movement and native inputs can support the next bounded
physical test. SP visibility and SP movement receipts do not close this gate.

## W3 - Per-weapon calibration and physical acceptance

Desktop profile/calibration preparation needs W1 and a usable copied fixture;
movement-enabled hardware testing also needs W2. Start with P38; expand after
its desktop controls. W3.1/W3.2/W3.4 are preparation; W3.3/W3.5 are hardware
gates. Do not wait for W3.3 before preparing the remaining desktop profiles.

- [x] W3.1. Measured model-local grip pivot, axes, scale and muzzle/forward
  markers for P38. Native asset identity and explicit animated-model units are
  stored in the title profile; the 216 mm nominal-size scale remains
  provisional. Evidence: [calibration receipt](../../vr/proof/weapon-p38-calibration-receipt.json),
  [atomic capture](../../vr/proof/weapon-p38-calibration-capture-receipt.json)
  and [build/regressions](../../vr/proof/weapon-p38-calibration-build-receipt.json).
- [x] W3.2. Prepared and ran a movement-enabled bounded headset comparison
  from fresh copied slot 1 for native and tracked modes. Quest 3/VDXR supplied
  30/30 live focused hand samples in each mode, fresh stereo/XR submissions,
  0 final failures, unchanged source saves/settings and no remaining process.
  Evidence: [headset comparison](../../vr/proof/weapon-p38-headset-receipt.json)
  and [complete build receipt](../../vr/proof/weapon-p38-headset-complete-build-receipt.json).
- [ ] W3.3. Operator accepts P38 size/attachment, head/hand independence, recoil,
  reload/switch, wall proximity, recenter, focus/loss recovery and both eyes.
  Initial headset feedback failed the gate: no working controls, a noise filter
  remained active, and hand motion pivoted rather than tracking the controller.
  The 2026-10-28 MP1/SP operator smoke now accepts ordinary tracking/model/flash
  behavior after the fixes. Wall-proximity, recenter and focus/loss recovery were
  not explicitly confirmed in that batch; the full gate remains open.
- [x] W3.4. Expand captured profiles and desktop controls to all 13 IDs, including
  native gun subparts and special animations, using the existing inventory and
  reference profile/batch validators. Do not rediscover the measured meshes.
  Arms filtering is a separate asset decision, not a full-model prerequisite.
  Operator requirement is explicit: render the gun model alone with no attached
  arms. All 13 now have measured whole-node or explicit per-vertex masks, with
  zero mixed gun/arm triangles. The provisional all-ID calibration and 64-case
  calibrated MP control matrix pass. A frozen-frame moving-marker probe confirms
  all 13 IDs across native switching and their available recoil/reload/special
  states. The tested model markers are not rigid. They remain model-animation
  diagnostics; the operator-selected shot/laser ray is fixed to the hand. Sten reload and scoped-shot
  ammo are explicitly not observed, not inferred. Evidence:
  [moving-marker receipt](../../vr/proof/weapon-moving-muzzle-receipt.json),
  [control sheet](../../vr/proof/weapon-moving-muzzle-controls.png) and
  [build receipt](../../vr/proof/weapon-moving-muzzle-build-receipt.json).
- [ ] W3.5. Operator accepts each designated weapon after profile corrections.
  Reopened: initial positive batch answers were followed by reports of incorrect
  grenade orientation, oversized weapons and a hand remaining on StG44.
  High firing/laser reports also leave W5.4d/W6.4 open. The historical 13-ID
  table/receipt remain in [HEADSET_BATCH.md](HEADSET_BATCH.md). Validate changed
  profiles and named failures; do not repeat unchanged combat matrices.

The original W3.1 markers below describe the receiver alone. The current
candidate uses [complete-gun calibration](../../vr/proof/weapon-p38-complete-calibration-receipt.json)
with the node-11 barrel; its true tip, barrel axis and 760.489674616524 scale
supersede the original receiver-cap marker and 530.210564041902 scale.

W3.1 evidence: [P38 calibration](../../vr/proof/weapon-p38-calibration-receipt.json),
[atomic vertex capture](../../vr/proof/weapon-p38-calibration-capture-receipt.json)
and [build/regressions](../../vr/proof/weapon-p38-calibration-build-receipt.json).
The capture stores all 69 node-13 source and animated vertex records through the
existing W1 seam. The animated grip block centers at
`(76.555555555556,100.777777777778,287.888888888889)`, the muzzle cap at
`(76.2,109.8,396.8)`, and the measured forward span is
`114.525481833051` model units. The profile carries an orthonormal
right/up/forward basis and `530.210564041902` model units per metre using a
nominal 216 mm P38 reference. The scale and placement are deliberately
provisional; no headset size/attachment claim or renderer consumption is made.

All-ID desktop evidence: [topology](../../vr/proof/weapon-complete-gun-topology-receipt.json),
[animated profile captures](../../vr/proof/weapon-profile-captures-receipt.json),
[provisional calibrations](../../vr/proof/weapon-provisional-calibrations-receipt.json),
[64-case controls](../../vr/proof/weapon-complete-gun-controls-receipt.json) and
[control sheet](../../vr/proof/weapon-complete-gun-controls.png). The masks retain
complete gun islands, including mixed-node P38/silenced-pistol parts, while
removing arms. Calibration beyond P38 is provisional and does not imply W3.5.

Exit gate: per-weapon physical observations, not copied reference numbers or a
single global "all works" claim. If hardware is unavailable, finish test
preparation, leave physical boxes open, and report exactly what is needed.

## W4 - Native MP shot mapping, read-only before any override

Dependencies: existing native MP fixture/damage evidence and W1. Read-only
mapping does not require W2 input/visibility completion or a headset. If W2 is
blocked, record its exact continuation before using this independent workstream.

- [x] W4.1. From fresh copied slot 1, trace native P38 idle/fire/turned-away cases.
  Match the reference MP constructor-to-basis call-chain pattern first, then
  verify Underground's constructor type, P1 ownership, origin/direction fields,
  basis/history initialization, first motion/collision and native damage writer.
- [x] W4.2. Record complete Underground MP function bytes, caller words, live
  arguments and field units in a new native-shot contract. Mark unknowns unknown.
- [x] W4.3. Verify P2/NPC shots and render replay cannot enter a P1 shot override;
  adapt the reference ownership/freshness checks and streaming trace controls.
  Validate the canonical native camera separately from eye/render-only caches.

Evidence: [native-shot receipt](../../vr/proof/weapon-native-shot-receipt.json)
and [measured contract](P38_NATIVE_AIM_EVIDENCE.md). Complete code/callers,
P1/P2 ownership, 16.16 fields, canonical camera and linked P2 health writes are
recorded. NPC/replay rejection is fixture-tested; no live NPC/SP run is claimed.

Exit gate: a complete native construction-to-motion-to-hit chain for one P38
shot, including negative controls. Old SP scripts/first-game shot IDs are leads.

## W5 - Tracked native aim and all-weapon combat

Desktop dependencies: W4 measured shot contract and W3.1's declared mesh/muzzle
contract, which may still be physically provisional. Reuse reference aim math,
basis-hook guards and trace checks. Candidate writes require a separate opt-in
diagnostic flag and stay off in normal launches. Physical calibration/impact
acceptance is required for physical claims and normal default promotion.

- [x] W5.1. Transform the same calibrated rendered weapon origin/forward axis to
  native world shot pose at the verified seam, outside eye replay only. Adapt
  reference inverse/angle conversion; do not substitute aim-space origin for
  the declared rendered-muzzle contract.
- [ ] W5.2. Pass P38 near/far, translated/rotated hand, head/body independence,
  loss/stale/unfocused/unknown-ID, P2/NPC isolation and real impact controls.
  Fourteen desktop controls pass for P38/P2, including complete-gun images,
  near/far native hits, translated/rotated hands, independent head/body turns,
  MP40 rejection and invalid/recovered hands. Live NPC/SP isolation is still open;
  this box is not closed by the MP fixture or pure ownership tests.
- [x] W5.3. Expand measured constructor families to all 13 IDs; preserve shotgun
  spread/pellets, rocket collision and both native throw/release/flight paths.
  All 13 IDs and five native types are now mapped through shared caller
  `0x800488D8`; one trigger produced six shotgun constructions. Family-aware
  conversion and paired native/tracked preservation/impact pass on desktop.
- [ ] W5.4. Complete reload/empty/switch/scoped/recoil/death/load matrix and the
  13-ID native damage gate; use the shared hand-fixed shot/laser ray while
  native recoil animation plays; operator confirms hand-aim/impact alignment.
- [x] W5.4a. Pass the paired desktop state matrix for reload tail, empty fire,
  switch during reload, scoped fire on ID 5, recoil follow-up and load recovery.
  The scoped samples remain a recorded native fallback. Evidence:
  `weapon-combat-states-receipt.json`.
- [x] W5.4b. Bind the all-13 native type/damage gate to the accepted W5.3e
  receipt rather than repeating its conversion matrix.
- [x] W5.4c. Pass native/tracked P1 death, native respawn and a separate
  post-respawn shot. Require exact native health-write/shot linkage, no P1
  construction from respawn input, unchanged load generation, fresh tracked
  markers and one round consumed. Evidence: `weapon-death-respawn-receipt.json`
  and [DEATH_RESPAWN_EVIDENCE.md](DEATH_RESPAWN_EVIDENCE.md). This headless
  lifecycle control has stereo inactive.
- [ ] W5.4d. Obtain operator confirmation of physical hand-aim/impact alignment.
  This is independent of ready desktop W6 work. The 2026-10-27 report says
  impacts land slightly high; it is a failure observation, not acceptance.

W5.3 desktop substeps:

- [x] W5.3a. Map all 13 IDs, five types and the common basis caller. Retain the
  native six-pellet shotgun count and native ammo/slot changes.
- [x] W5.3b. Retain constructor-to-motion native baselines, pellet trajectories,
  linked damage and prop flight samples using copied MP fixtures. Split recycled
  shot objects by constructor write sequence. Do not infer a trajectory from
  basis angles alone. Evidence: `weapon-shot-lifecycle-receipt.json`.
- [x] W5.3c. Acquire fresh canonical animated marker data with owner, weapon,
  load/time and freshness guards. The origin writers are mapped for thrown/rocket
  families; grenade also rebuilds basis after the common constructor. Retain
  those family-specific seams/history contracts. Eye snapshots and idle
  calibration are not simulation caches. The completed sampler uses natural P1
  post-animation output, owns its vertex copies, rejects eye replay/P2 drawing,
  and guards source identity, load generation and guest-cycle freshness. All 13
  IDs / 18 constructor events / three final-origin stages and six controls pass.
- [x] W5.3d. Add opt-in family-aware conversion using the hand-fixed calibrated ray
  and preserves native pellet generation, speeds, gravity, release and collision.
  Compare first integration origin as well as basis pose; no blind 13-ID guard
  expansion or guessed compensation for native position changes. Normal firearms
  convert at the common basis; grenade/petrol/rocket convert at complete guarded
  final-origin stages. Evidence: `weapon-aim-all-receipt.json`.
- [x] W5.3e. Pass paired native/tracked per-family controls, including release,
  sustained fire/object reuse, shotgun spread, rocket/bolt/throw motion, native
  ammo/damage, tracking fallback, ownership and replay rejection. Evidence:
  `weapon-preservation-receipt.json`.

W5.1 evidence: [tracked combat receipt](../../vr/proof/weapon-p38-aim-receipt.json)
and [complete-gun controls](../../vr/proof/weapon-p38-aim-controls.png). The
candidate uses the corrected node-11 barrel tip and one quantized render/shot
affine. New flags are explicit and normal defaults remain native. The W3.1
node-13-only receiver marker/scale are historical, superseded for this candidate.

W5.3 family evidence:
[SHOT_FAMILY_EVIDENCE.md](SHOT_FAMILY_EVIDENCE.md),
[family receipt](../../vr/proof/weapon-shot-families-receipt.json) and
[build regressions](../../vr/proof/weapon-shot-families-build-receipt.json).
W5.3b native preservation baseline:
[lifecycle evidence](SHOT_LIFECYCLE_EVIDENCE.md),
[receipt](../../vr/proof/weapon-shot-lifecycle-receipt.json) and
[tool validation](../../vr/proof/weapon-shot-lifecycle-validation-receipt.json).
All 13 IDs passed, with 22 lifetimes, 147 complete XYZ groups and 19 linked
native damage writes. Six native pellet directions span about 5.25 degrees.
The [focused origin receipt](../../vr/proof/weapon-projectile-origin-writers-receipt.json)
resolves the thrown/rocket position writers and grenade's second basis call.
W5.3c is complete within the contract in
[CANONICAL_MARKERS_EVIDENCE.md](CANONICAL_MARKERS_EVIDENCE.md),
[marker receipt](../../vr/proof/weapon-canonical-markers-receipt.json) and
[build/regressions](../../vr/proof/weapon-canonical-markers-build-receipt.json).
Maximum sampled constructor age is 1,128,671 cycles, below the declared
2,257,920 limit.

W5.3d is complete for synthetic desktop controls:
[all-family receipt](../../vr/proof/weapon-aim-all-receipt.json) and
[build/regressions](../../vr/proof/weapon-aim-all-build-receipt.json). All 13
IDs converted 23 shot events with zero candidate fallbacks. P38, MP40 and all
expected firearm/bolt/rocket controls produced linked native P2 damage. The
shotgun retained six pellets, 5.1817 degrees maximum native spread and a
378.89 world-unit/frame speed range. Grenade, petrol and rocket passed through
their complete function-hash-guarded final-origin seams. The legacy P38 flag
still passed 14 controls when the all-family flag was absent. Moving-shot
alignment and matched MP impact are now closed by W5.3e; physical acceptance
remains open.

W5.3e is complete:
[paired receipt](../../vr/proof/weapon-preservation-receipt.json),
[evidence](WEAPON_PRESERVATION_EVIDENCE.md) and
[build/regressions](../../vr/proof/weapon-preservation-build-receipt.json).
All 13 IDs passed. The shotgun retained six pellets, 21 construction-scoped RNG
updates, 5.257088/5.259963 degree native/tracked maximum pair angles and a
1.00003 median speed ratio. Five P38 controls covered missing/stale markers,
unfocused hand, P2 ownership and recovery. Tracked P2 damage was tied to the
converted animated axis and target residual rather than claimed from native
hits alone.

Exit gate: real native trajectory/collision/damage agrees with the shared
hand-fixed aim ray within the stated tested tolerance. The W5.3e desktop exit gate is met
for the copied MP fixture; physical and NPC/SP gates remain explicit.

## W6 - Mesh-derived exact-triangle laser

Desktop dependencies: declared W3.1 rendered-muzzle contract and verified target
geometry layout. Reuse reference ray/triangle math, bounded traversal, beam/dot
projection and tests; port target data readers. Hardware acceptance is W6.4.
The hand-fixed ray is shared with W5; native recoil animation does not steer it. Physical testing need not block code.
W6.2/W6.3 are desktop complete under A4a. The handoff and
ALPHA_WEAPON_REPAIRS document the actual local arena/prop bindings and controls.
W6.4 remains physical; the optional settings editor does not block it.
Do not reopen the completed W5 matrices or call the old box pointer exact.

- [x] W6.1. Capture the hand-fixed aim ray, actual per-eye view/affine and optional
  animated-model diagnostics. Native recoil/reload must not steer the ray.
  Ten P38 snapshots / 20 eyes pass independent head/hand,
  recoil/reload, tracking/load/weapon context and live refusal/recovery controls.
  Source data is owned per draw and published only after both scopes restore
  and the stereo pair completes. Evidence: `weapon-rendered-muzzle-receipt.json`
  and [RENDERED_MUZZLE_EVIDENCE.md](RENDERED_MUZZLE_EVIDENCE.md). Other-ID
  draw capture and physical alignment are not claimed by this P38 gate.
- [x] W6.2. Verified local SP/MP arena and MP prop triangle readers, independent
  7,251/8,039-triangle reconstruction, strict pointer/index/strip/budget tests;
  no origin-inside leaf shortcut. [Evidence](ALPHA_WEAPON_REPAIRS.md).
- [x] W6.3. Shared fixed calibration ray, actual nearest surface, both-eye
  head/hand controls, range/miss fixtures, grip/tracking rejection, real MP shot
  agreement and zero rollback mismatches. Static surfaces/props only; no NPC
  hit-volume or ballistic-drop prediction is claimed.
- [ ] W6.4. Operator accepts hand-fixed laser/shot agreement in both eyes. Clearly distinguish this from
  the existing right-aim/visibility-node-extents pointer.

## Remaining port gates - after the weapon sequence, not alternate rabbit holes

- [x] H1. Reference native dual-matte HUD, measured Underground producers/regions,
  per-hand fallback and FACE_HEAD surfaces implemented. SP native values,
  fire/reload/pause/save load and real null-HMD uploads/loss/recovery pass.
  [Evidence](NATIVE_HAND_HUD.md); physical readability remains H2.
- [ ] H2. Native HUD values/artwork/fallback and menu/briefing/movie transitions pass.
- [ ] Q1. Multiple scenes, near walls, streaming areas, death/load, runtime recenter,
  headset disconnect/focus, dynamic effects and long-session gameplay pass.
- [ ] Q2. Profile unique guest/world-pair cadence separately from XR refresh;
  adapt reference trace/hitch-report tools and record target bottlenecks without
  sacrificing PGXP, rollback or image correctness. No new scheduler by default.
- [ ] Q3. Debug-off reproducible package, supported-runtime matrix, release
  provenance and regression receipts; no copyrighted disc/BIOS/save artifacts.
- [ ] Q4. Promote experimental defaults only after relevant physical and combat
  gates pass. No release/commit/push is implied by this documentation update.

## Acceptance record

For every newly checked item, add the receipt path, tested source/binary hashes,
fixture/mode/weapon IDs, expected versus observed result, negative controls,
rollback counts, image pair IDs/hashes, cleanup and limitations to
[IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md). Preserve earlier receipts.
The detailed next-action contract and stop/recovery rules are in
[HANDOFF.md](HANDOFF.md); the measured weapon map is in
[WEAPON_MAPPING.md](WEAPON_MAPPING.md).
