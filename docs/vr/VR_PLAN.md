# Underground VR execution plan

Updated: 2026-10-26. Working branch: `feature/vr-port`.

This is the current checkbox plan, not the original proposal. Start with
[HANDOFF.md](HANDOFF.md) for exact instructions. Checked means the stated
scope has evidence; it never implies broader headset or gameplay acceptance.
Historical design and prior attempts belong in
[IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) and the evidence documents.

**NEXT IMPLEMENTATION TASK: W2.3 - zero, +/-90-degree and near-wall MP
controls.** C1-C4 are complete. The reference runtime gate now uses a fresh
cold-boot gameplay slot captured by the diagnostic build and passes world
stability, weapon controls and watchdog recovery. See
[CONSISTENCY_HANDOFF.md](CONSISTENCY_HANDOFF.md) and
[the parity receipt](../../vr/proof/reference-parity-receipt.json).

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

## C - cross-game consistency pass (complete; no feature rediscovery)

- [x] C1. Add host-only cross-game parity fixtures and a behavior/policy difference
  table for the helpers named in CONSISTENCY_HANDOFF. Preserve current outputs
  and capture intentional differences before extraction. Evidence:
  `vr/tests/reference_parity_vectors.c`, the two title adapters,
  `vr/tools/check_reference_parity.py`, and the 32-case baseline.
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
  and intentional policy differences are recorded. NEXT is W2.3.

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
- [ ] W2.3. Pass zero, +/-90-degree head turns and near-wall controls with populated
  geometry, native selector comparison and zero rollback errors. Extend the
  existing MP/head-pose/eye-capture helpers; do not build another selector.
- [ ] W2.4. Verify MP controller converter/dispatcher and native action tables;
  add a measured MP binding to the existing controller source and pure mapper.
  Reuse the reference mode-adapter pattern, not its addresses/threshold math.
- [ ] W2.5. Verify native movement/buttons, no render-time input sampling,
  focus release, pause/resume, and SP/flat fallback. Record remaining hardware gates.

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
`MOHU_VR_MP_FRUSTUM=1` covered every level node in each eye in the zero-angle
P38 control, left non-level nodes native, had no fallback or rollback errors,
and retained populated matching zero-IPD eyes. Head turns and near walls remain
W2.3.

Exit gate: MP head movement and native inputs can support the next bounded
physical test. SP visibility and SP movement receipts do not close this gate.

## W3 - Per-weapon calibration and physical acceptance

Desktop profile/calibration preparation needs W1 and a usable copied fixture;
movement-enabled hardware testing also needs W2. Start with P38; expand after
its desktop controls. W3.1/W3.2/W3.4 are preparation; W3.3/W3.5 are hardware
gates. Do not wait for W3.3 before preparing the remaining desktop profiles.

- [ ] W3.1. Measure model-local grip pivot, axes, scale and muzzle/forward markers
  for P38. Save native asset identity and explicit units with the profile. Reuse
  reference calibration/profile tooling; label initial physical values provisional.
- [ ] W3.2. Prepare a movement-enabled bounded headset comparison with fresh copied
  slot 1; keep source saves/settings untouched. Do not invent a new user save.
- [ ] W3.3. Operator accepts P38 size/attachment, head/hand independence, recoil,
  reload/switch, wall proximity, recenter, focus/loss recovery and both eyes.
- [ ] W3.4. Expand captured profiles and desktop controls to all 13 IDs, including
  native gun subparts and special animations, using the existing inventory and
  reference profile/batch validators. Do not rediscover the measured meshes.
  Arms filtering is a separate asset decision, not a full-model prerequisite.
- [ ] W3.5. Operator accepts each designated weapon; retain a per-ID result table.

Exit gate: per-weapon physical observations, not copied reference numbers or a
single global "all works" claim. If hardware is unavailable, finish test
preparation, leave physical boxes open, and report exactly what is needed.

## W4 - Native MP shot mapping, read-only before any override

Dependencies: existing native MP fixture/damage evidence and W1. Read-only
mapping does not require W2 input/visibility completion or a headset. If W2 is
blocked, record its exact continuation before using this independent workstream.

- [ ] W4.1. From fresh copied slot 1, trace native P38 idle/fire/turned-away cases.
  Match the reference MP constructor-to-basis call-chain pattern first, then
  verify Underground's constructor type, P1 ownership, origin/direction fields,
  basis/history initialization, first motion/collision and native damage writer.
- [ ] W4.2. Record complete Underground MP function bytes, caller words, live
  arguments and field units in a new native-shot contract. Mark unknowns unknown.
- [ ] W4.3. Verify P2/NPC shots and render replay cannot enter a P1 shot override;
  adapt the reference ownership/freshness checks and streaming trace controls.
  Validate the canonical native camera separately from eye/render-only caches.

Exit gate: a complete native construction-to-motion-to-hit chain for one P38
shot, including negative controls. Old SP scripts/first-game shot IDs are leads.

## W5 - Tracked native aim and all-weapon combat

Desktop dependencies: W4 measured shot contract and W3.1's declared mesh/muzzle
contract, which may still be physically provisional. Reuse reference aim math,
basis-hook guards and trace checks. Candidate writes require a separate opt-in
diagnostic flag and stay off in normal launches. Physical calibration/impact
acceptance is required for physical claims and normal default promotion.

- [ ] W5.1. Transform the same calibrated rendered weapon origin/forward axis to
  native world shot pose at the verified seam, outside eye replay only. Adapt
  reference inverse/angle conversion; do not substitute aim-space origin for
  the declared rendered-muzzle contract.
- [ ] W5.2. Pass P38 near/far, translated/rotated hand, head/body independence,
  loss/stale/unfocused/unknown-ID, P2/NPC isolation and real impact controls.
- [ ] W5.3. Expand measured constructor families to all 13 IDs; preserve shotgun
  spread/pellets, rocket collision and both native throw/release/flight paths.
- [ ] W5.4. Complete reload/empty/switch/scoped/recoil/death/load matrix and the
  13-ID native damage gate; operator confirms barrel-to-impact alignment.

Exit gate: real native trajectory/collision/damage agrees with the rendered
barrel within a stated tested tolerance. Native hits alone are insufficient.

## W6 - Mesh-derived exact-triangle laser

Desktop dependencies: declared W3.1 rendered-muzzle contract and verified target
geometry layout. Reuse reference ray/triangle math, bounded traversal, beam/dot
projection and tests; port target data readers. Hardware acceptance is W6.4.
The shared aim contract with W5 must agree; physical testing need not block code.

- [ ] W6.1. Capture the actual rendered weapon affine plus calibrated muzzle/axis.
- [ ] W6.2. Locate and verify Underground triangle/vertex table bindings, comparing
  the reference drawer/record pattern first. Adapt its existing triangle raycast
  and fixtures; local MP scene bounds are not proof of SP triangle layout.
- [ ] W6.3. Beam origin/direction agrees with the rendered mesh; first triangle hit
  gets the dot; native misses/range limit, weapon eligibility and rollback pass.
- [ ] W6.4. Operator accepts alignment in both eyes. Clearly distinguish this from
  the existing right-aim/visibility-node-extents pointer.

## Remaining port gates - after the weapon sequence, not alternate rabbit holes

- [ ] H1. Capture native HUD producers for wrist/hand surfaces; current suppression
  and native menu surface are not a completed wrist HUD. Adapt reference native
  dual-matte capture, per-hand fallback and FACE_HEAD surface code through the
  already available framework APIs; measure target ownership/ROIs/mode support.
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
