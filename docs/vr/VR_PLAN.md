# Underground VR execution plan

Updated: 2026-10-25. Working branch: `feature/vr-port`.

This is the current checkbox plan, not the original proposal. Start with
[HANDOFF.md](HANDOFF.md) for exact instructions. Checked means the stated
scope has evidence; it never implies broader headset or gameplay acceptance.
Historical design and prior attempts belong in
[IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) and the evidence documents.

**NEXT IMPLEMENTATION TASK: W1.1 - capture the P38 coordinate-space contract.**
Do not restart engine discovery, rebuild the MP renderer, or implement shot
redirection first. Advance by task ID only when its exit gate passes.

## Rules for using these checkboxes

- Check an item only after naming its source/binary, fixture, control and receipt.
- Keep desktop, physical headset and release acceptance as separate items.
- A historical receipt remains historical after source changes. Do not replace
  its hashes to make it appear to validate a new binary.
- Reopen a checked item only for a reproducible regression, changed guarded
  function/asset, or changed code on that item's execution path. Record why.
- Rerun the affected checks once after a meaningful change. Do not rerun all
  completed work repeatedly while leaving W1 unchanged.
- Update the handoff's next task ID, last result and next experiment at session
  end. An incomplete task needs a precise continuation, not "continue mapping".

## Established foundation - preserve, do not rediscover

- [x] B1. Working branch, title ID, PGXP ABI and current framework/UI pins recorded.
  Current framework is `d9b0f382`, not the original `31df2e1e` baseline.
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
  alignment. The present neutral-relative visual delta does not prove these.

Evidence: [WEAPON_MAPPING.md](WEAPON_MAPPING.md),
[flat receipt](../../vr/proof/weapon-viewmodel-receipt.json),
[MP eye receipt](../../vr/proof/weapon-mp-eye-receipt.json),
[MP build receipt](../../vr/proof/weapon-mp-build-receipt.json).

## W1 - P38 absolute pose contract and independent synthetic controls (NEXT)

Dependency: M1-M11. First weapon: **ID 0, source slot 1, zero native switches**.
No firing changes, laser work, mesh filtering or MP renderer replacement here.

- [ ] W1.1. Capture named coordinate spaces, native affine/animated vertex
  samples, GTE RT/TR and eye view at the existing P38 seam. Record units,
  axes, handedness, authored placement and invertibility. See handoff Step W1.
- [ ] W1.2. Add a copied-fixture head/hand independence harness using real
  synthetic hand samples, not only `mohu.vr.weapon.pose x=/yaw=` deltas.
- [ ] W1.3. Implement the measured absolute grip/model placement while preserving
  native animation; account for the eye transform exactly once. Full inverse
  where required; do not assume native camera/weapon matrices are orthonormal.
- [ ] W1.4. Pass independent head-only, hand-only and combined pose controls;
  origin/recenter, loss/unfocused/inactive/stale/invalid recovery; both eyes;
  bounded numeric error and visible-mesh controls, with no world/simulation drift.
- [ ] W1.5. Retain a P38 coordinate-contract receipt, paired PNGs and repeatable
  test commands; rerun affected baseline checks and update next task to W2.

Exit gate: independently supplied poses predict the measured rendered P38 pose
in a declared coordinate space. Head motion must not apply twice or drag a
stationary world-space hand anchor. A gun that merely moves is not a pass.

## W2 - MP visibility and native input needed for usable hardware testing

Dependency: W1. Do not apply SP addresses to the MP overlay.

- [ ] W2.1. Trace the native MP level selector from the already measured MP
  scene callback; capture its complete code, tree/masks/queue and caller.
- [ ] W2.2. Add a separately guarded MP eye-frustum override only after measuring
  its actual layout; preserve native fallback on malformed/overflow input.
- [ ] W2.3. Pass zero, +/-90-degree head turns and near-wall controls with populated
  geometry, native selector comparison and zero rollback errors.
- [ ] W2.4. Verify MP controller converter/dispatcher and native action tables;
  reuse the existing input mapper only where its MP guards/contracts match.
- [ ] W2.5. Verify native movement/buttons, no render-time input sampling,
  focus release, pause/resume, and SP/flat fallback. Record remaining hardware gates.

Exit gate: MP head movement and native inputs can support the next bounded
physical test. SP visibility and SP movement receipts do not close this gate.

## W3 - Per-weapon calibration and physical acceptance

Dependencies: W1 and W2. Start with P38; expand only after its desktop controls.

- [ ] W3.1. Measure model-local grip pivot, axes, scale and muzzle/forward markers
  for P38. Save native asset identity and explicit units with the profile.
- [ ] W3.2. Prepare a movement-enabled bounded headset comparison with fresh copied
  slot 1; keep source saves/settings untouched. Do not invent a new user save.
- [ ] W3.3. Operator accepts P38 size/attachment, head/hand independence, recoil,
  reload/switch, wall proximity, recenter, focus/loss recovery and both eyes.
- [ ] W3.4. Expand captured profiles and desktop controls to all 13 IDs, including
  native gun subparts and special animations. Arms filtering is a separate
  asset decision, not a prerequisite for the existing full-model path.
- [ ] W3.5. Operator accepts each designated weapon; retain a per-ID result table.

Exit gate: per-weapon physical observations, not copied reference numbers or a
single global "all works" claim. If hardware is unavailable, finish test
preparation, leave physical boxes open, and report exactly what is needed.

## W4 - Native MP shot mapping, read-only before any override

Dependencies: W1-W2; read-only mapping may proceed while W3 awaits hardware.
No tracked-shot writes may be enabled until the visual calibration gate passes.

- [ ] W4.1. From fresh copied slot 1, trace native P38 idle/fire/turned-away cases.
  Identify projectile/hitscan constructor, P1 ownership, origin/direction fields,
  basis/history initialization, first motion/collision and native damage writer.
- [ ] W4.2. Record complete Underground MP function bytes, caller words, live
  arguments and field units in a new native-shot contract. Mark unknowns unknown.
- [ ] W4.3. Verify P2/NPC shots and render replay cannot enter a P1 shot override;
  validate current native camera producer and freshness separately from eye views.

Exit gate: a complete native construction-to-motion-to-hit chain for one P38
shot, including negative controls. Old SP scripts/first-game shot IDs are leads.

## W5 - Tracked native aim and all-weapon combat

Dependencies: W3 physical calibration and W4 measured shot contract.

- [ ] W5.1. Transform the same calibrated rendered weapon origin/forward axis to
  native world shot pose at the verified seam, outside eye replay only.
- [ ] W5.2. Pass P38 near/far, translated/rotated hand, head/body independence,
  loss/stale/unfocused/unknown-ID, P2/NPC isolation and real impact controls.
- [ ] W5.3. Expand measured constructor families to all 13 IDs; preserve shotgun
  spread/pellets, rocket collision and both native throw/release/flight paths.
- [ ] W5.4. Complete reload/empty/switch/scoped/recoil/death/load matrix and the
  13-ID native damage gate; operator confirms barrel-to-impact alignment.

Exit gate: real native trajectory/collision/damage agrees with the rendered
barrel within a stated tested tolerance. Native hits alone are insufficient.

## W6 - Mesh-derived exact-triangle laser

Dependencies: W3 calibration; shared aim contract with W5 must agree.

- [ ] W6.1. Capture the actual rendered weapon affine plus calibrated muzzle/axis.
- [ ] W6.2. Independently map Underground level triangle tables and bounded traversal.
- [ ] W6.3. Beam origin/direction agrees with the rendered mesh; first triangle hit
  gets the dot; native misses/range limit, weapon eligibility and rollback pass.
- [ ] W6.4. Operator accepts alignment in both eyes. Clearly distinguish this from
  the existing right-aim/visibility-node-extents pointer.

## Remaining port gates - after the weapon sequence, not alternate rabbit holes

- [ ] H1. Capture native HUD producers for wrist/hand surfaces; current suppression
  and native menu surface are not a completed wrist HUD.
- [ ] H2. Native HUD values/artwork/fallback and menu/briefing/movie transitions pass.
- [ ] Q1. Multiple scenes, near walls, streaming areas, death/load, runtime recenter,
  headset disconnect/focus, dynamic effects and long-session gameplay pass.
- [ ] Q2. Profile unique guest/world-pair cadence separately from XR refresh;
  record bottlenecks without sacrificing PGXP, rollback or image correctness.
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
