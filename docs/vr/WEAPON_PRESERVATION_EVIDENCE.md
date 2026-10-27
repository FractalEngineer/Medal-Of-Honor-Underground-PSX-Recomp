# Paired native/tracked weapon preservation

Updated: 2026-10-27. W5.3e is complete for the copied MP desktop fixture.
This receipt describes the earlier animated-origin candidate. The operator
subsequently selected a hand-fixed shot/laser ray with native recoil left
visual. Current all-13 revalidation and its explicitly recorded additional
explosive hits are in [RENDERED_MUZZLE_EVIDENCE.md](RENDERED_MUZZLE_EVIDENCE.md).
The numbers and hashes below remain historical.
No headset or XR runtime was launched. The two environments are separate owned
game launches because `MOHU_VR_WEAPON_AIM` is read during activation:

- Native launch: copied root MP slots 1-4, read-only lifecycle capture and no
  weapon shot override.
- Tracked launch: the same copied slots, native input and trigger/release
  timing, with `PSX_VR_WEAPON_POSE=1`, `MOHU_VR_WEAPON_CALIBRATED=1` and
  `MOHU_VR_WEAPON_AIM=1`.

Both launches waited eight guest frames after the canonical camera/hand setup.
The compact [paired receipt](../../vr/proof/weapon-preservation-receipt.json)
hashes the native and tracked raw receipts. Full streams remain under the
ignored analysis directory.

## Result

All 13 measured IDs passed. The native run observed 22 lifetimes / 18 linked
health decreases; the tracked run observed 21 lifetimes / 16 linked decreases.
The one-shot difference is the final StG44 lifetime at the release boundary.
Its common prefix retained type, position-history, family-stage, ammo-per-shot
and RNG behavior. Repeating-fire controls permit one frame-local lifetime
difference; single-shot, bolt and projectile counts remain exact.

Every tracked ordinary firearm and crossbow shot has converted marker evidence,
a first integration group and a native damage event where the paired native
control had damage. Single-shot target-ray residuals were at most 0.73 world
units. Automatic-fire minimum residuals were 0.13/6.38/0.30 world units for
MP40/Sten/StG44, within the stated 10-unit tolerance. Native damage remains the
contact event; the ray residual is the alignment evidence.

Grenade, petrol bomb and Panzerfaust converted at their guarded final-origin
stages. Their release phase, history writes and relative stage path match the
native traces. Grenade and petrol produced no fabricated damage. Panzerfaust
retained one linked native damage write and a minimum rendered-axis cosine of
`0.999999158`.

The shotgun retained six pellets and native RNG consumption:

| Measurement | Native | Tracked | Limit |
| --- | ---: | ---: | ---: |
| Pellets | 6 | 6 | exact |
| Maximum pair angle | 5.257088 deg | 5.259963 deg | 1 deg pair delta |
| Median pair-angle delta | 0 | 0.010589 deg | 1 deg |
| Median speed | 529.1113 | 529.1276 | 10% |
| Speed ratio range | 1 | 0.999816..1.000286 | 10% |
| RNG updates through last birth | 21 | 21 | exact state sequence |
| Linked damage writes | 4 | 4 | native presence preserved |

## Fallback controls

The tracked launch also exercised five focused P38 controls:

| Control | Observed result |
| --- | --- |
| Missing marker | marker invalid, one native shot, no candidate write |
| Stale marker | frozen marker invalid, one native shot, no candidate write |
| Unfocused hand | marker valid, native hand fallback, no candidate write |
| P2 fire | P1 family eligibility zero, no candidate write |
| Recovery | valid marker and focused hand, candidate write restored |

The controls consumed native ammunition and never borrowed an idle P38 point.
The run recorded 379 replay-rejected marker updates and 94 P2-rejected marker
updates. Unsupported profile/type combinations remain rejected by the existing
`shot.h` fixtures; no unsupported runtime ID was present in the copied slots.

## Limits

This closes desktop preservation and P2 impact against the copied MP fixture.
It does not close W5.2 live NPC/SP isolation, W3.3/W3.5 physical acceptance,
non-P38 physical bore measurement, zoom-fire, thrown explosion damage or
operator-confirmed barrel-to-impact alignment. Candidate flags remain OFF by
default.

## Reproduction

```powershell
python -X utf8 vr/tools/probe_shot_families.py `
  analysis/vr-baseline/<fresh-native> --lifecycle --pair-settle-frames 8
python -X utf8 vr/tools/probe_weapon_aim.py `
  analysis/vr-baseline/<fresh-tracked>
python -X utf8 vr/tools/check_weapon_preservation.py `
  analysis/vr-baseline/<fresh-native> analysis/vr-baseline/<fresh-tracked> `
  --proof vr/proof/<fresh-proof>.json
```
