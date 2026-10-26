# Complete viewmodel profiles

Updated: 2026-10-27. This is desktop evidence only. W3.3/W3.5 physical
acceptance remains open, and no headset was used for this pass.

## Result

All 13 native multiplayer weapon IDs have a measured complete-gun topology,
a source/animated vertex capture, a provisional model-space calibration, and
confirmed native-input animation samples. The moving-marker probe covers
recoil, reload, switching, scope hiding and the grenade, petrol-bomb and
Panzerfaust special actions. P38 continues to use its accepted complete-gun
calibration exactly; the other 12 profiles are explicitly provisional.

Normal defaults are unchanged. The new candidates require either
`MOHU_VR_WEAPON_GUN_ONLY=1` or `MOHU_VR_WEAPON_CALIBRATED=1`.
The older `MOHU_VR_P38_CALIBRATED=1` path remains P38-specific.

## Complete-gun topology

A triangle is retained only when every vertex is in the measured gun set. This
is stricter than hiding whole nodes: node 11 contains both the P38 barrel and
silenced-pistol suppressor as well as hand geometry. No triangle may cross the
gun/arm boundary.

| ID | Weapon | Native nodes/faces | Gun faces/vertices | Masked vertices | Gun selection |
| --- | --- | ---: | ---: | ---: | --- |
| 0 | P38 pistol | 14 / 354 | 128 / 96 | 142 | node 13; node 11 indices 6..32 |
| 1 | MP40 | 32 / 316 | 193 / 124 | 66 | nodes 26, 29, 31 |
| 4 | Shotgun | 21 / 306 | 182 / 137 | 62 | nodes 18, 20 |
| 5 | Scoped rifle | 26 / 383 | 199 / 159 | 78 | nodes 22, 25 |
| 8 | Colt .45 | 14 / 303 | 115 / 68 | 112 | node 13 |
| 9 | Silenced pistol | 14 / 310 | 94 / 75 | 124 | node 13; node 11 indices 6..17 and 26..31 |
| 10 | Stick grenade | 24 / 341 | 140 / 58 | 105 | node 23 |
| 12 | M1 Garand | 23 / 280 | 174 / 136 | 67 | node 22 |
| 13 | Panzerfaust | 31 / 333 | 168 / 116 | 87 | nodes 27, 28, 30 |
| 14 | Crossbow | 29 / 290 | 187 / 178 | 61 | nodes 14, 17, 18, 19, 21, 23, 25, 26, 28 |
| 15 | Petrol bomb | 28 / 397 | 198 / 99 | 97 | nodes 25, 26, 27 |
| 16 | Sten | 31 / 354 | 217 / 166 | 73 | nodes 26, 29, 30 |
| 17 | StG44 | 32 / 352 | 215 / 161 | 73 | nodes 27, 29, 31 |

The P38 and silenced-pistol masks are explicit 256-bit per-node selections in
the compiled profile. The apparent index gap on the silenced pistol is required:
indices 18..25 and 32+ belong to the arm-connected island even though they live
on the same animation node.

Evidence: [topology receipt](../../vr/proof/weapon-complete-gun-topology-receipt.json)
and [all-node capture receipt](../../vr/proof/weapon-profile-captures-receipt.json).
The capture contains 16 slot appearances because IDs 10, 15 and 17 occur in
more than one native cycle, but only 13 unique IDs.

## Provisional calibration

The accepted P38 grip, rendered muzzle, barrel axis and `760.489674616524`
units/metre values are unchanged. The other profiles use one repeatable recovery
rule over a fixed synthetic hand pose:

- grip: mean of the closest 20% of selected gun vertices to the arm island;
- forward: principal axis of the selected animated geometry, with camera-space
  forward resolved for normal firearms and grip-to-far-end direction for thrown
  props;
- muzzle: mean of the five most-forward selected vertices;
- scale: selected forward span divided by a nominal weapon length.

| ID | Weapon | Forward span | Nominal length | Provisional units/metre |
| --- | --- | ---: | ---: | ---: |
| 0 | P38 pistol | 164.266 | 0.216 m | 760.490 |
| 1 | MP40 | 470.610 | 0.833 m | 564.957 |
| 4 | Shotgun | 716.800 | 1.000 m | 716.800 |
| 5 | Scoped rifle | 723.766 | 1.110 m | 652.042 |
| 8 | Colt .45 | 161.338 | 0.216 m | 746.935 |
| 9 | Silenced pistol | 209.224 | 0.300 m | 697.414 |
| 10 | Stick grenade | 151.318 | 0.365 m | 414.570 |
| 12 | M1 Garand | 636.783 | 1.107 m | 575.233 |
| 13 | Panzerfaust | 516.805 | 1.000 m | 516.805 |
| 14 | Crossbow | 449.835 | 0.800 m | 562.294 |
| 15 | Petrol bomb | 170.675 | 0.300 m | 568.917 |
| 16 | Sten | 437.685 | 0.762 m | 574.390 |
| 17 | StG44 | 637.164 | 0.940 m | 677.834 |

Exact marker groups, axes and full-precision values are in the
[provisional calibration receipt](../../vr/proof/weapon-provisional-calibrations-receipt.json).
Nominal lengths are size references, not measured copies of the PSX assets.

## Desktop controls

`check_mp_view.py --all-weapons --calibrated-all` ran 64 cases: native,
translated, yawed and tracking-loss for all 16 slot appearances. The current
binary retained 804 per-eye gun-only mask applications, closed every four-weapon
cycle, and recorded zero render-pass mismatches, VRAM leaks, watchdog events,
nesting repairs or remaining owned processes. The historical 876 count belongs
to the previous binary.

The [control sheet](../../vr/proof/weapon-complete-gun-controls.png) shows the
native, translated and yawed weapon crop for each ID. The
[control receipt](../../vr/proof/weapon-complete-gun-controls-receipt.json)
contains per-ID image hashes, rollback check counts and mask counts.

Affected regressions also pass: default P38 eye replay, native P38 fire/ammo/P2
damage and refusal recovery, 14-case tracked P38 aim/fallback, 52 Python tests,
strict C fixtures and the calibrated all-ID matrix.

## Moving muzzle contract

The moving-marker probe latches every animated vertex from one
`0x8008DB98` output at a time. It recomputes the P38 grip/tip points and the
provisional grip/tip points from the captured marker-vertex groups. A marker is
called rigid only when its grip-to-tip distance stays within 1% of the idle span
and its direction stays within 2 degrees. Those tolerances were fixed before the
run.

| ID | Weapon | Confirmed animation controls | Result |
| --- | --- | --- | --- |
| 0 | P38 pistol | recoil, reload, switch | moving marker required |
| 1 | MP40 | recoil, reload, switch | moving marker required |
| 4 | Shotgun | recoil, reload, switch | moving marker required |
| 5 | Scoped rifle | scope model hidden, switch | moving marker required |
| 8 | Colt .45 | recoil, reload, switch | moving marker required |
| 9 | Silenced pistol | recoil, reload, switch | moving marker required |
| 10 | Stick grenade | hold/release, switch | moving marker required |
| 12 | M1 Garand | recoil, reload, switch | moving marker required |
| 13 | Panzerfaust | launch, switch | moving marker required |
| 14 | Crossbow | launch/auto-switch, switch | moving marker required |
| 15 | Petrol bomb | hold/release, switch | moving marker required |
| 16 | Sten | recoil, switch | moving marker required |
| 17 | StG44 | recoil, reload, switch | moving marker required |

Each confirmed state also records a native clip, reserve or weapon-slot change.
The crossbow launch itself kept the sampled marker pair rigid, but its switch
state did not. No per-ID static tip can therefore be treated as animation-safe
across the complete tested range. W5/W6 must recompute the tip from its current
marker vertices after native animation and before transforming it with the
render affine. The stored calibration point remains the idle reference.

The scoped rifle hides the viewmodel while scoped, so no moving tip is claimed
there. Its scoped-shot ammo change was not observed. The Sten had already
completed its magazine update before the query window, so its reload field is
explicitly `not-observed`; recoil and switching are confirmed. These are recorded
limits, not inferred passes.

Evidence: [moving-marker receipt](../../vr/proof/weapon-moving-muzzle-receipt.json),
[control sheet](../../vr/proof/weapon-moving-muzzle-controls.png) and
[build receipt](../../vr/proof/weapon-moving-muzzle-build-receipt.json).

## Remaining work

W3.4 desktop preparation is complete. The other 12 profiles still do not have a
rendered-muzzle native-shot override; their shot families and the moving-tip
consumer belong to W5/W6. W5.2 still needs live NPC/SP isolation. W3.3/W3.5
require operator hardware acceptance of size, attachment, recoil, reload,
recenter, focus recovery and both eyes.
