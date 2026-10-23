# Camera Evidence

Measured from the diagnostic build at slot 0 on 2026-10-23. This is
discovery evidence, not a camera hook design.

## Motion probe

The session was loaded from an isolated save copy, then given right-stick
rotation input through the debug input override.

| Check | Before | After |
| --- | --- | --- |
| Frame | 367 | 605 |
| GTE RT (control words 0-4) | changed | changed |
| GTE TR words 5-7 | zero | zero |
| GTE OFX/OFY/H | unchanged | unchanged |
| Scratchpad `0x1F800014..0x1F80004A` | baseline | changed |

The rotation changed the view matrix while translation registers remained
zero. This agrees with the reference game's camera-relative storage model.

## Write trace

A write trace over scratchpad `0x1F800000..0x1F800100` reported sampled writers
in the range `0x80090B98..0x8009115C`, with return address `0x800908E4`. The
producer is in the overlay loaded at base `0x8008C000`. Its owning function
boundary and caller contract still need disassembly before any hook is proposed.

The trace also exposed stable pointer-like arguments:

- `s4 = 0x800F130C`
- `s3`/`a2` pointed into the current scene matrix area near `0x80157D90`; the
  exact pointer varied with allocation and camera motion.

## Root map

The Underground level transformer's prologue is instruction-equivalent to the
reference transformer except for relocated data addresses. Aligning the two
710-instruction bodies maps the reference's scene data table to Underground:

| Reference global | Underground global | Meaning |
| --- | --- | --- |
| `0x8009D638` | `0x800AA160` | Current scene object |
| `0x8009D64C` | `0x800AA174` | Scene pointer |
| `0x8009D654` | `0x800AA17C` | Single-player actor/player pointer |

In a live slot-0 session, the Underground values were:

```text
*(0x800AA174) = 0x800F2180   scene
*(0x800AA17C) = 0x800F0BE0   player
*(player+0x39C) = 0x800F0FDC  player input
```

The `+0x39C` input offset matches the reference actor's `+0x388` field after
the measured Underground structure shift. A 2-second right-stick turn changed
the GTE RT matrix and the rendered world while TRX/Y/Z remained zero. The
player pointer itself stayed fixed at `0x800F0BE0`.

This establishes stable pointer globals for the loaded scene. It does not make
the pointed-to heap objects permanent across level loads; consumers must read
the pointer globals rather than pin those object addresses.

## Transform A/B

The diagnostic entry hook applied `MOHU_VR_LEVEL_OFFSET_X` to GTE TRX once per
draw span and restored it at the verified gameplay render-wait entry. All three
captures use the same isolated slot-0 save and interpreter-only diagnostic
configuration.

| Capture | Result | Changed pixels |
| --- | --- | ---: |
| [Control](../../vr/proof/level-probe-control.png) | Unmodified baseline | - |
| [TRX + 20](../../vr/proof/level-probe-offset20.png) | World shift with a depth gradient | 39,975 / 122,880 (32.53%) |
| [TRX + 200](../../vr/proof/level-probe-offset200.png) | Unmistakable world-scale shift | 78,943 / 122,880 (64.24%) |

At `TRX + 20`, best horizontal alignment by screen band was:

| Rows | Best DX |
| --- | ---: |
| 0-120 (far walls) | +2 px |
| 120-180 (mid ground) | +5 px |
| 180-210 (near ground) | +6 px |

The displacement grows toward the camera. That is parallax in the level's
camera-space projection, not a uniform screen-space translation. The compass,
ammo display, and first-person weapon stayed fixed across the captures.

This proves the Underground level transformer is the correct world-space seam
for later per-eye rendering. It does not yet prove a complete two-eye render
transaction or OpenXR presentation.

## GTE projection observation

At the sampled gameplay point:

```text
OFX = 0x01000000  (256.0 in 16.16)
OFY = 0x00780000  (120.0 in 16.16)
H   = 0x00000190  (400)
```

This is consistent with a 512x240 PSX display and the reference world
projection. It does not yet prove which guest function owns the camera.

## Open work

- Separate camera translation from player and entity transforms with a forward
  movement trace.
- Record the exact active overlay hash for `0x800908E4` before considering a
  hook.
- Do not register camera hooks from the pointer values above; they are runtime
  heap addresses and are not stable identifiers.
