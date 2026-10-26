# P38 weapon coordinate contract

Updated: 2026-10-26. Scope: W1 and W3.1 measurements for Underground MP P38
(ID 0), copied root MP slot 1, zero weapon switches, stationary P2 and no
firing. These are desktop contracts. They are not physical grip, size, shot or
headset acceptance.

## Captured fixture and seams

The capture came from the existing guarded first-person caller and did not
scan for another object:

| Item | Observed value |
| --- | --- |
| Player root / input | `0x801483D0` / `0x801487D0` |
| First-person object | `[actor+0x114] == input+0x9F0 == 0x801491C0` |
| Weapon / slot | ID 0, loadout slot 0 |
| Geometry nodes / faces | 14 / 354 |
| Geometry FNV32 / mesh magic | `0x8544F8B9` / `0x000E0007` |
| First-person renderer / caller RA | `0x800892E8` / `0x8008A544` |
| Native producer | `0x8008DB98`, FNV32 `0xFAE3646E` |
| Pose sample / restore | `0x800894DC` / `0x80089D30` |
| Source vertex records | signed `int16 xyz` plus tag word, 8 bytes each |

The producer output table was `0x80188C00`. Its entries are pointers to the
native animated vertex records. The node-table pointers still identify the
source asset records, so source and animated samples can be captured without
mutating guest state.

Measured before changing absolute placement:

| Node | Source vertex | Native animated vertex (`x,y,z,w`) |
| ---: | --- | --- |
| 9 | `(-12,58,2,128)` | `(78,203,82,0)` |
| 11 | `(-12,58,2,128)` | `(66,111,312,0)` |
| 13 | `(-86,-8,-68,128)` | `(71,116,388,0)` |

The source and animated records are distinct spaces. The producer, not the
pose hook, is the animation owner. The measured complete animated screening
bounds in native camera coordinates were:

```text
x = [97.962890625, 561.470947266]
y = [295.773193359, 976.919189453]
z = [193.222900391, 916.708496094]
```

## Named spaces

| Space | Axes / handedness | Units | Meaning |
| --- | --- | --- | --- |
| `XR-LOCAL` | X right, Y up, Z back; right-handed | metres | OpenXR grip and aim poses before recentering |
| `origin` | PSX axes: X right, Y down, Z forward; right-handed | game camera units | Recentered tracking origin used by the desktop eye view |
| `hand` | XR aim orientation converted to PSX axes; right-handed | game camera units | Absolute right-hand frame; grip position is its translation |
| `animated model` (`M`) | Native object/local axes; exact per-node meaning comes from the producer | native model units | Output of `8008DB98` read through the producer output table |
| `native camera` (`C`) | X right, Y down, Z forward; right-handed | GTE camera units | Input to native `RTPS`, before eye-view and perspective division |
| `eye` (`Espace`) | X right, Y down, Z forward; right-handed | game camera units | Per-eye camera after the host render-view transform |

The XR-to-PSX conversion is the diagonal sign map `diag(1,-1,-1)`. Its
determinant is `+1`, so it changes axis directions but not handedness.
Quaternions are stored as `x,y,z,w`; matrices in this contract are row-major.

## Transforms

### `native_from_animated = A_n`

`A_n` is the guest GTE RT/TR state sampled at `800894DC` after the native
producer has run. It maps `M -> C`.

At the W1 fixture the eight raw words were:

```text
FFAE600A FFF8F847 FD323C0D 017D0294
00001FE8 00000000 00000000 00000000
```

RT entries are signed `int16` Q12 coefficients. TR entries are signed `int32`
integer camera units. Decoding RT gives:

```text
[ 6.002441406 -0.020019531 -0.482666016 ]
[-0.001953125  3.753173828 -0.175292969 ]
[ 0.161132812  0.093017578  1.994140625 ]
```

Each raw word stores its lower 16-bit RT entry first and its upper 16-bit RT
entry second. This basis is deliberately scaled and sheared. It is not an
orthonormal rotation. Its determinant is `45.314754560241`; the column scales
are approximately `6.002`, `3.753` and `2.006`. A full inverse exists. The
inverse must be used wherever a reconstruction converts camera coordinates
back to animated-model coordinates. Transposing this matrix or copying a
reference game's orthonormal assumption is invalid.

The measured full 3x3 inverse is:

```text
[ 1.655236093e-01 -1.097802097e-04  4.005403446e-02 ]
[-5.373667671e-04  2.658623159e-01  2.324029979e-02 ]
[-1.334976070e-02 -1.239239562e-02  4.971486022e-01 ]
```

TR was zero at this seam. The current authored placement is therefore carried
by `A_n` and the producer-space animated vertices, not by separate guest TR.
Code must preserve the complete affine rather than treating it as a rotation.

### `origin_from_native = H_abs`

The synthetic right-hand pose is converted by `vr_pose_to_transform`:

```text
q_aim: XR x,y,z,w quaternion
p_grip: XR LOCAL metres
R_hand = PSX-axis conversion of q_aim
t_hand = diag(1,-1,-1) * p_grip * units_per_meter
```

W1 uses the existing non-OpenXR hand conversion default
`48 / 0.067 = 716.4179104477612` GTE units per metre. That value is recorded
from the active code path; it is not inferred from a failed OpenXR session.

The provisional W1 pivot in native camera coordinates is
`c = (98.0, 296.0, 193.0)`, near the measured lower visible bound. It is a
diagnostic rotation marker, not a grip or muzzle marker. Rotation around it is:

```text
p_moved = R_hand * (p_native - c) + c + t_hand
```

Thus the complete absolute hand-to-native transform is:

```text
H_abs = translation(c + t_hand - R_hand*c) * R_hand
```

No first-accepted neutral pose is stored or subtracted. Changing the first
valid hand position or orientation changes placement.

### `hand_from_model`

W1 uses `A_n` as the provisional `hand_from_model` affine. This keeps the
native producer's animated mesh appearance and gives a complete numeric path
without pretending the diagnostic pivot is a physical grip. The game's native
camera origin is not added a second time: the absolute hand transform replaces
that origin, while `A_n` contributes the measured model-to-camera affine.
Per-weapon physical `hand_from_model`, scale and pivot belong to W3.

The composed guest matrix is:

```text
G_guest = H_abs * A_n
point_camera = G_guest * point_animated
```

`G_guest` replaces the existing guest RT/TR for this scoped draw. Native
animation/recoil/reload continue to change `point_animated`.

### `eye_from_origin = E`

The MP eye replay uses the P1-only view. At zero pose it is identity. Its
weapon render view has `projection_h_ref=400`, while the guest weapon
projection is `H=133`, `OFX=256`, `OFY=60`. The desktop head diagnostic
translation uses 1000 GTE units per metre; this is separate from the
716.4179104477612 hand units per metre.

The host applies `E` after the guest GTE transform:

```text
point_eye = E * point_camera
```

The final target relation is:

```text
point_eye = eye_from_origin
          * origin_from_hand
          * hand_from_model
          * point_animated
```

With the W1 definitions this is `E * H_abs * A_n * point_animated`.
`E` is applied exactly once, by the existing per-eye render view. It must not
also be folded into `H_abs` or `A_n`.

## Units and projection

| Boundary | Conversion |
| --- | --- |
| XR grip metres -> origin/game units | multiply by `716.4179104477612` |
| XR pose quaternion -> GTE direction | normalize, convert XR axes to PSX axes; no length scale |
| head diagnostic milli-units -> GTE units | divide by `1000` |
| GTE RT -> dimensionless linear basis | signed `int16 / 4096` |
| GTE TR -> camera translation | integer GTE camera units; no `*4096` |
| composed RT -> guest control | round `linear * 4096`, require signed `int16` range |
| composed TR -> guest control | round integer/affine camera units, require signed `int32` range |
| guest weapon projection | `OFX/65536 + 133*x/z`, `OFY/65536 + 133*y/z` |

The RT and TR units are intentionally different. Overflow or a non-finite
intermediate returns failure without partially writing guest control words.

## Expected values and tolerances

Using the captured `A_n`, expected native-camera points include:

```text
(78,203,82)  -> (424.547851562, 747.367919922, 194.970458984)
(66,111,312) -> (243.347167969, 361.781982422, 643.131591797)
(71,116,388) -> (236.576660156, 367.215820312, 795.957031250)
```

For W1 pure math, expected and observed double-precision values use a
tolerance of `1e-6` in the result's declared units. GTE RT storage may differ
by one Q12 quantization step (`1/4096` coefficient) and TR by one integer
unit. Image controls additionally require populated both-eye meshes, a
measurable changed-pixel region for each non-zero synthetic pose, zero-pose
eye equality when offset is zero, and unchanged sampled world pixels for
hand-only motion. The W1 desktop eye-pair check requires at least 64 non-black
pixels and 20 colours in each eye, which still admits the sparse upward-pitch
sky view while rejecting an empty pair.

Forward-axis tests use the explicitly provisional animated-model axis
`(0,0,1)`. Its native-camera direction is
`(-0.482666016,-0.175292969,1.994140625)` before hand/eye transforms. This is
a space and composition check, not a claim about the real P38 muzzle.

## Required invalid paths

Unfocused, inactive, missing-validity, stale (`age_ms > 150`), bad quaternion,
wrong identity/mesh, or unsupported profile samples must leave guest RT/TR and
the host render view native. Restore must drain apply/restore counters. A new
valid sample after invalid input is absolute and must not jump to an old
neutral anchor.

The measured contract is reproducible from
`analysis/vr-baseline/weapon-mesh-mapping/w1-space-capture-20261025f/`.
The implementation receipt under `vr/proof/` is authoritative for the binary
and source hashes actually tested.

## W3.1 provisional model-local calibration

W3.1 does not reinterpret the W1 camera-space marker. It captures all 69
node-13 source and animated vertex records atomically and derives a separate
calibration in the `8008DB98` animated-model output space. The grip marker is
the mean of the rear grip block (vertex indices 47 through 64). The muzzle is
the mean of the maximum-forward cap (indices 11, 12, 25, 26 and 38).

```text
grip_pivot = (76.555555555556, 100.777777777778, 287.888888888889)
muzzle     = (76.2, 109.8, 396.8)
right      = (0.999994671106, 0, 0.003264622472)
up         = (-0.000269517466, -0.996586343637, 0.082556568708)
forward    = (-0.003253478173, 0.082557008645, 0.996581032934)
```

Positions are integer native model units; axes are dimensionless and
orthonormal. The measured forward span is `114.525481833051` model units.
Dividing by the nominal 216 mm overall length of a P38 gives
`530.210564041902` model units per metre. This is an explicitly provisional
desktop estimate, not a headset-accepted size.

The values are stored in `MohuVrWeaponCalibration` with the P38 profile. The
data is currently inert: W1 still renders with its camera-space diagnostic
pivot, and nothing uses the new markers for shots, lasers or input. The
source-node-local centroids and axes are retained in the proof for audit, but
only the animated-model values are intended as the later hand-from-model
contract. Recoil, reload, switching and hardware acceptance remain
W3.2-W3.5.

Evidence: [calibration receipt](../../vr/proof/weapon-p38-calibration-receipt.json),
[atomic capture](../../vr/proof/weapon-p38-calibration-capture-receipt.json) and
[build receipt](../../vr/proof/weapon-p38-calibration-build-receipt.json).
