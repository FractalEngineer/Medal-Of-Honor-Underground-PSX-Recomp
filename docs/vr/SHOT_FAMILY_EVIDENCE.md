# Underground multiplayer shot families

Updated: 2026-10-27. No headset was used. This is a read-only native
constructor map, not an all-weapon aim override.

Follow-up: [SHOT_LIFECYCLE_EVIDENCE.md](SHOT_LIFECYCLE_EVIDENCE.md) adds native
constructor-to-motion/damage controls and the moving-shot origin continuation.
It does not enable non-P38 shot writes or close tracked preservation acceptance.

## Result

All 13 measured MP weapon IDs reach the shared basis constructor entry
`0x8006C8B0` with return address `0x800488D8`. Their native shot type is selected
by weapon ID as follows:

| Type | Family label | Weapon IDs | Native evidence |
| --- | --- | --- | --- |
| `0x13F1` | rocket | 13 Panzerfaust | one basis construction; reserve decreased |
| `0x13F3` | thrown | 10 stick grenade, 15 petrol bomb | slot/weapon changed and clip/reserve decreased |
| `0x13F6` | single | 0 P38, 5 scoped rifle, 8 Colt .45, 9 silenced pistol, 12 M1 Garand | one basis construction; clip decreased |
| `0x13F7` | repeating | 1 MP40, 4 shotgun, 16 Sten, 17 StG44 | native constructions; clip decreased |
| `0x13FA` | bolt | 14 crossbow | slot/weapon changed and clip/reserve decreased |

The shotgun produced six basis constructions from one trigger window, matching
the native pellet path. Sten and StG44 produced one or two constructions
depending on the exact native fire window; both remained in `0x13F7`.

## Native contract

| Meaning | Value |
| --- | --- |
| Basis entry | `0x8006C8B0`, 260 bytes |
| Common measured caller / RA | `0x800488D8` |
| Shot argument | `A0 == S0`; argument is the shot object |
| P1 owner | `S2`, also equal to the live MP P1 root |
| Weapon ID | owner input byte at `+93` |
| Shot type | shot object `+8` |
| One-shot candidate cap | 64 samples |

The family table is implemented by `mohu_vr_shot_type()` and
`mohu_vr_shot_family()` in
[shot.h](../../vr/underground/shot.h). Unknown IDs return zero and stay native.

The diagnostic capture command now has two read-only modes:

- `mohu.vr.shot start` retains the existing broad MP/P2 capture behavior.
- `mohu.vr.shot start-p1` filters capture to the live P1 owner for family work.

`MOHU_VR_P38_AIM` remains restricted to P38 ID 0, type `0x13F6`, caller
`0x800488D8`, P1 ownership and a fresh canonical camera. No non-P38 shot pose is
written.

## Limitations

- This map does not preserve shotgun spread under an override because no
  all-weapon override exists yet.
- Rocket collision, crossbow flight and both native throw/release/flight paths
  still need focused constructor-to-motion controls.
- The scoped-rifle family was measured with ordinary native fire. Zoom-plus-fire
  did not construct a shot in this isolated raw-R2 control and remains separate.
- Moving-marker origins are still required for every ID. The P38 candidate's
  existing static/recovered tests do not certify moving-shot alignment.
- No live NPC/SP fixture or SP shot/camera binding is claimed.

## Reproduction

```powershell
python vr/tools/probe_shot_families.py `
  analysis/vr-baseline/<fresh-directory> `
  --proof vr/proof/weapon-shot-families-receipt.json
```

Evidence:

- [compact family receipt](../../vr/proof/weapon-shot-families-receipt.json)
- [build and regression receipt](../../vr/proof/weapon-shot-families-build-receipt.json)
- ignored raw receipt: `analysis/vr-baseline/shot-families-final-20261027/receipt.json`
