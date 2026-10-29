# Complete MP weapon calibration/control parity in SP

2026-10-29 operator priority: **port all existing MP weapon calibrations and
tracked control paths to SP first**. This is G7 in VR_PLAN and supersedes the
earlier G5/G6-first and performance-first orders. This runbook records the
verified source bindings and the remaining acceptance work.

Status 2026-10-29: **G7a is complete.** Natural frozen SP fixture coverage is
IDs 0, 13, 15 and 16 only. The guarded Panzerfaust basis candidate now follows
desktop hand rotation and tracking-loss fallback; petrol throw construction and
the other nine live-ID rows remain open. See the measured checkpoint below.

The operator reports that petrol bomb and Panzerfaust “seem to have fixed
aiming.” Record this as apparent fixed/native-direction aiming instead of hand
aiming, pending reproduction. Do not interpret “fixed” as a successful repair.
No affected save slot, exact runtime, captured trajectory or root cause was
provided. [Report receipt](../../vr/proof/sp-weapon-parity-report.json).

## Reuse the current MP implementation; do not restart calibration

This is a full **SP integration/parity** task, not an MP feature campaign or a
new calibration UI. MP is the existing calibration reference. Current authored
grip/orientation, scale/offset, complete gun-only masks, fixed muzzle/forward
basis, animation handling and shot-family logic already exist. Reuse them from:

- `vr/underground/weapon.c`, `weapon.h`, `weapon_markers.h` and the existing
  calibration/profile data used by `mohu_vr_weapon_calibration_find`.
- `vr/underground/vr_diagnostic.c`: shared model/control transforms, SP held
  draw adapters, canonical camera, firearm basis hook and MP final-origin paths.
- `vr/underground/shot.h`: exact ID/type guards and recorded native families.
- [WEAPON_MAPPING](WEAPON_MAPPING.md), [WEAPON_COMPLETE_PROFILES](WEAPON_COMPLETE_PROFILES.md),
  [SHOT_FAMILY_EVIDENCE](SHOT_FAMILY_EVIDENCE.md),
  [SHOT_LIFECYCLE_EVIDENCE](SHOT_LIFECYCLE_EVIDENCE.md) and the retained MP receipts.

Some profile data and render/control code are already shared with SP. Do not
create a second SP calibration table or claim a new port just for copying data
already consumed there. The source currently routes SP single/repeating/bolt
firearms through `80048604 → 80076C28`, return `8004860C`, and explicitly leaves
thrown/rocket families out of `mohu_vr_sp_firearm_type_valid`. That is a concrete
integration lead, **not proof of the reported live failure or permission to
remove its guards**. Correct model/laser rendering alone does not prove that
the final native projectile follows the same basis.

The known MP grenade/petrol/rocket final-stage addresses are leads only. Measure
the real SP caller, ownership/layout and final writer before binding them.
Retain the existing guarded SP petrol metadata variant; do not weaken mesh/code
checks or substitute MP actor/input offsets for SP offsets.

## Required 13-ID SP matrix

All rows have an existing MP calibration/profile. The table describes current
SP evidence and remaining coverage; it does not mark any new work accepted.

| Native ID | Weapon | SP status / required completion |
|---:|---|---|
| 0 | P38 | Scoped SP render/aim/fire/reload evidence exists; preserve it in the full parity regression |
| 1 | MP40 | Reuse profile; prove live SP render and final shot direction/origin |
| 4 | Shotgun | Reuse profile; prove all native pellets follow tracked basis with native spread preserved |
| 5 | Scoped rifle | Reuse profile; preserve native scope/model hiding and verify SP aiming/fallback |
| 8 | Colt .45 | Reuse profile; prove live SP render and final shot direction/origin |
| 9 | Silenced pistol | Reuse profile; retain complete suppressor/gun and prove SP shot control |
| 10 | Stick grenade | Prove SP held orientation, throw final origin/initial direction, hand-fixed ray and restoration |
| 12 | M1 Garand | Reuse profile; prove SP tracked fire plus native reload behavior |
| 13 | Panzerfaust | Guarded SP basis candidate turns native first motion with the hand and survives head-only/loss controls; exact calibrated final origin, speed/impact and lifecycle remain open |
| 14 | Crossbow | Reuse profile; prove native bolt follows SP hand basis and preserves native flight |
| 15 | Petrol bomb | Model/laser and ammo are present, but no native SP throw constructor was observed; direction/final origin remain open |
| 16 | Sten | Scoped SP native-motion and operator aim pass exists; preserve it in the full parity regression |
| 17 | StG44 | Reuse current hand-removal/profile data; prove gun-only SP model and tracked fire |

Map each ID to its actual SP held object/native type before claiming coverage.
If an ID cannot be reached in genuine SP, record the exact missing case or
game limitation; continue the other rows. Do not fabricate inventory or label
an MP run SP evidence. Full parity remains open until required coverage exists
or the operator explicitly accepts a documented scope exception.

## Measured SP inventory checkpoint (2026-10-29)

G7a is complete for the frozen fixture library and the current shared source.
This does not imply live SP coverage for profiles that are absent from those
fixtures. The checkpoint binary is debug-ON
`5DCE6B94C8DC3366029E3193267C37E1401A85CF90DD81F70851BFC0380B2CDE`.
All listed runs used one owned process, copied fixtures, ordinary switching and
the current `game.toml`; source saves and preferences were unchanged.

| Native ID | Shared SP model path | Natural frozen fixture | Measured native construction/motion | Remaining SP gap |
| ---: | --- | --- | --- | --- |
| 0 P38 | calibrated profile and gun-only mask | slots 3, 4, 5 | basis `80048604 -> 80076C28`; origin `80048608`; motion `800793E4/80079400/8007941C` | broader lifecycle and real NPC impact |
| 1 MP40 | calibrated profile and complete mask | none | MP only | live SP model, basis, origin and motion |
| 4 Shotgun | calibrated profile and complete mask | none | MP only | live SP model plus six-pellet direction/origin |
| 5 Scoped rifle | calibrated profile, complete mask and scope path | none | MP only | live SP scope/model and shot controls |
| 8 Colt .45 | calibrated profile and complete mask | none | MP only | live SP model, basis, origin and motion |
| 9 Silenced pistol | calibrated profile, complete mask and suppressor | none | MP only | live SP model, basis, origin and motion |
| 10 Stick grenade | calibrated profile and complete mask | none | MP final-origin adapters only | native SP throw construction and release path |
| 12 M1 Garand | calibrated profile and complete mask | none | MP only | live SP model, reload and shot controls |
| 13 Panzerfaust | calibrated profile and complete mask | slot 2, switch 2 | basis `80048604 -> 80076C28`; final native origin `8004874C/80048774/8004879C`; motion `800793E4/80079400/8007941C` | exact calibrated final origin, native speed/impact and broader lifecycle |
| 14 Crossbow | calibrated profile and complete mask | none | MP only | live SP bolt construction and first motion |
| 15 Petrol bomb | calibrated SP geometry variant and complete mask | slots 3, 4, 5 | model/laser only; no native throw constructor observed | SP throw input/context and final origin/velocity |
| 16 Sten | calibrated profile and complete mask | slots 1, 4, 5 | basis `80048604 -> 80076C28`; origin `80048608`; motion `800793E4/80079400/8007941C` | broader lifecycle and real NPC impact |
| 17 StG44 | calibrated profile and semantic hand mask | none | MP only | live SP gun-only model and shot controls |

The shared model guard and post-animation adapter already resolve all 13
profiles through `mohu_vr_weapon_profile_find` and
`mohu_vr_weapon_calibration_find`; no second SP calibration table was added.
The live inventory is in
[the compact checkpoint receipt](../../vr/proof/sp-weapon-parity-checkpoint-receipt.json)
and its ignored raw runs.

The current candidate now admits the measured rocket type through a separate
`mohu_vr_sp_tracked_type_valid` predicate. Thrown types remain excluded. With a
30-degree synthetic hand rotation, native first motion rotated by:

| ID | Baseline clip | Rotated-hand clip | Tracked shots | Measured direction change |
| ---: | ---: | ---: | ---: | ---: |
| 0 P38 | 8 -> 7 | 8 -> 7 | 1 per run | `29.970469°` |
| 16 Sten | 32 -> 30 | 32 -> 30 | 2-3 per run | `29.953052°` |
| 13 Panzerfaust | 1 -> 0 | 1 -> 0 | 1 per run | `29.874661°` |

A 30-degree head-only control left the Panzerfaust world direction byte-for-byte
unchanged in the sampled first motion. Unfocused tracking produced zero tracked
shots, one native tracking fallback, and preserved native motion. These are
desktop synthetic controls, not physical headset acceptance.

Petrol is not blocked by ammo or model identity: the tested fixture reported
one loaded bomb and three reserve, with 397 faces and the expected SP geometry
hash. No projectile constructor appeared after the tested fire/use/aim button
set or ordinary switching in slots 3, 4 and 5. Do not infer that the current
adapter fixed its throw; retain G7c as open and obtain a naturally compatible SP
throw context before changing that family.

Reproduce the inventory and the passing controls with:

```powershell
python vr/tools/probe_sp_weapon_inventory.py analysis/runtime/g7-inventory --slots 1 2 3 4 5
python vr/tools/probe_sp_shot_origins.py analysis/runtime/g7-origin --ids 0 16 13
python vr/tools/probe_sp_shot_origins.py analysis/runtime/g7-yaw --ids 0 16 13 --hand-yaw 30
python vr/tools/probe_sp_shot_origins.py analysis/runtime/g7-head --ids 13 --head-yaw 30
python vr/tools/probe_sp_shot_origins.py analysis/runtime/g7-loss --ids 13 --tracking-loss
```

The origin probe defaults to IDs 0, 16 and 13 because those controls construct
native projectiles in the frozen fixtures. Pass `--ids 15` to reproduce the
currently missing petrol construction rather than treating it as a pass.

## Ordered implementation and acceptance — G7a through G7f

1. **G7a: inventory existing SP consumption and gaps (COMPLETE).** Build one per-ID/family
   table naming shared calibration/mask/control code, live SP binding, available
   frozen fixture and missing evidence. Distinguish model pose, hand-fixed ray,
   native construction, final origin and first motion. Read the actual current
   MP implementation instead of replaying old discovery/PCA matrices.
2. **G7b: complete shared profile/render integration and firearm coverage.**
   Carry the current authored calibration through the real SP post-animation
   draw path. Preserve complete gun-only models, scale/grip, native recoil and
   reload, and scoped exceptions. Reuse the common firearm adapter with exact
   ID/type/owner/code/freshness guards; preserve P38/Sten rather than remapping
   their known basis. A tracked model is not a passed shot-control row.
3. **G7c: complete SP thrown-family adapters, petrol first, then grenade.**
   Trace natural SP switching/throwing to the final origin/velocity writers.
   Adapt the existing MP family algorithm to verified SP bindings, including
   canonical timing after any native overwrite. Compare rotated/translated
   hands, head/body independence and release/loss recovery. Preserve native
   throw speed, spread, gravity, fuse/impact and ammo behavior. The laser stays
   a straight hand-fixed aiming ray, not a promised ballistic landing arc.
4. **G7d: complete the SP rocket adapter for Panzerfaust.** Prove the actual
   projectile starts at the calibrated origin and its first native motion
   follows the hand orientation, including after final native writes. Preserve
   native rocket speed, effects, ammo consumption and ownership. Moving the
   displayed model/laser or changing a constructor value that is later overwritten
   is not a repair. Do not copy MP hook addresses unchecked into SP.
5. **G7e: finish the whole 13-ID SP control matrix.** For each reachable row,
   capture model/profile identity, baseline and rotated/translated hand controls,
   independent head movement, native first motion and final origin, appropriate
   firing/throwing/impact behavior, and laser agreement. Include native spread
   and ballistic-family semantics rather than requiring a grenade to fly in a
   straight line. Verify gun-only geometry and grip/scale through animations,
   switching, scope, tracking loss/stale camera, pause/load and render refusal.
   No writes from eye replay may retarget canonical gameplay; require zero
   unexplained rollback/VRAM failures. Run affected MP preservation controls
   only when shared behavior changes; no new broad MP feature matrix.
6. **G7f: record acceptance honestly and restore normal play.** Keep per-ID
   desktop evidence, unavailable cases and failures separate from physical
   acceptance and real live-NPC damage. Preserve meaningful native impacts/
   damage controls where fixtures support them; do not imply all-SP NPC damage
   from an MP target or a direction vector. Restore production/debug OFF with
   native timers/IPO OFF, unchanged personal saves/settings and no owned process
   left running. Update handoff with one exact remaining task.

Use the existing SP fixture library and disposable per-run copies. Normal
personal saves remain root `saves`; slot references throughout mean internal
indices, with no renumbering. If an additional naturally obtained SP weapon
fixture is needed, snapshot it deliberately and record provenance; do not add
alternate personal save stores, executable aliases or a new maintained build.

Every actual game launch is outside the sandbox, one game at a time. Two compile
jobs. Keep the previous game's existing algorithms/reference where relevant;
no framework pin update or new renderer/editor is part of this port.

## Priority after the port

G5 slot-1 missing-world and G6 slot-2 severe performance stay open. They are not
explained or repaired by weapon parity. If a rendering failure blocks a specific
G7 control, capture that prerequisite failure and use a valid visible SP case
for independent parity work; do not close G7 based on invisible world/targets.
Do not turn this exception into a general performance-first detour.

After G7's scoped desktop parity/known exceptions are recorded: reproduce/fix
slot 1, baseline/profile slot 2, then execute the measured performance target
and independent fresh-view work. No new general headset smoke is requested
until the independent fixes are ready. This turn is **document and push only**.
