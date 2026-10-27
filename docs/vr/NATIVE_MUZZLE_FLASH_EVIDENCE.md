# Native muzzle-flash eye-replay alignment

Updated: 2026-10-27. This is a desktop synthetic result, not physical
acceptance.

## Observation

The operator reported that the P38 muzzle flash stayed near the centre of the
view while the hand-fixed gun moved. The native flash is not part of the
calibrated gun mesh. A bounded fire capture identifies it as a 32x32
semi-transparent textured quad:

| Field | Measured value |
| --- | --- |
| Packet tag | `actor+0xCB8` |
| Colour command source | `actor+0xCBC` |
| XY word offsets | `+0xC0`, `+0xC8`, `+0xD0`, `+0xD8` from the actor |
| Texture window | 32x32; UV `(192,128)..(223,159)` |
| CLUT / texpage | `15998` / `47` |
| Draw issuer | PC `8001A048`, RA `8001A4A8` |
| Packet refresh writers | guest PC range around `80070170..80070D58` |

The unmodified packet is built in screen space. In the captured desktop pose its
natural centre was near `(293,106)` in the 512x120 replay coordinate space, so
the calibrated gun could move independently while the flash stayed there.

## Implemented path

`MOHU_VR_WEAPON_AIM=1` with the calibrated all-family path now:

1. samples the actual animated P38 muzzle vertices from the same eye's weapon
   capture;
2. transforms them through the applied hand affine and eye render view;
3. projects the animated muzzle with the native weapon projection;
4. translates the existing four flash XY words by the delta from the packet's
   authored centre; and
5. preserves the native texture, colour, size, OT position, timing and draw
   order. No new sprite or shot write is introduced.

The packet guard requires the tag length, colour, texture/CLUT and UV words to
match. Failure stays native and increments `mohu.vr.flash.fallback`. A successful
translation increments `mohu.vr.flash.align`. Normal defaults remain OFF.

## Desktop controls

Two fresh copied-slot-1 P38 runs used the same synthetic pose and three native
shots. A second run translated the hand by +150 mm in X.

| Case | Shots | Align | Fallback | Flash centres in 512x120 replay |
| --- | ---: | ---: | ---: | --- |
| Baseline | 3 | 234 | 0 | `(287,92)`, `(289,98)`, `(291,99)` |
| Hand +150 mm X | 3 | 231 | 0 | `(320,92)`, `(320,92)`, `(320,92)` |

The natural, unaligned packet remained visible in the raw GPU history near
`(293,106)`. The eye-replay packet moved with the displaced muzzle. Both runs
had a clean process exit, unchanged copied source saves/preferences and no
remaining owned game.

Evidence:

- baseline raw:
  `analysis/vr-baseline/p38-effect-flash-align-final-20261027a/receipt.json`,
  SHA-256 `368941d10807cb36634072877bc147b2d91f173f44279bc0b73c2bf2dcbce58f`
- displaced-hand raw:
  `analysis/vr-baseline/p38-effect-flash-align-final-20261027b/receipt.json`,
  SHA-256 `823089e2766ad3c06980faaa6945770c995cc572af9c431ef8c4af7229a0df59`
- focused tracked shot:
  `analysis/vr-baseline/flash-focused-shot-final-20261027a/receipt.json`,
  SHA-256 `d7916ad6a9f9e9e4749a47a74bc3f9d6ccb2c5ef851d4669913d0318bd59c3fa`
- binary SHA-256:
  `0dbdb244fc7379f6757598856b86274325da84c01c77a96c47ba70118a18110b`
- compact receipt: `../../vr/proof/native-flash-alignment-receipt.json`

## Verification

- 121 Python VR tests pass.
- Strict C fixture `test_weapon.c` covers centre translation, malformed
  targets, off-screen rejection and packet-shape preservation.
- MP-view and rendered-muzzle C fixtures pass.
- A focused tracked P38 shot still consumes native ammunition, produces the
  expected first motion and applies linked P2 damage.
- Strict `vr_diagnostic.c` syntax and the active Release build pass.

## Limits

This proves packet ownership and eye-replay movement, not physical visibility,
comfort or exact apparent barrel alignment. A frame-selected screenshot of the
three-frame flash was not retained; the full GP0 history is retained instead.
The operator still reports impacts slightly high. Do not treat flash translation
as a shot-ray pitch fix. Physical flash location and impact alignment remain
open, and this document does not close W3.3, W3.5 or W5.4d.
