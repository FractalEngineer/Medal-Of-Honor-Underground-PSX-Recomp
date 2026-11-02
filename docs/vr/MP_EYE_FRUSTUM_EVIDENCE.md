# Underground MP eye-frustum evidence

Date: 2026-10-26

This document records the W2.2 coordinate and selector contract measured before
the eye-frustum override was enabled. The fixture was a fresh copy of root MP
slot 1 with P38 ID 0, zero weapon switches, stationary P2 and no firing.

## Native AABB contract

The complete `80096EF4` selector reads three signed-short center coordinates
from level node `+0x2F4`, `+0x2F6` and `+0x2F8`, plus a signed-short radius from
`+0x2FC`. It forms a cube from `center - radius` through `center + radius` and
passes the lower and upper corners to `80096AC8`.

The complete `80096AC8` helper:

1. obtains the camera through `[800A35C0]`, its input at `camera + 0x39C`,
   and the live view descriptor at `input + 0xC8`;
2. loads the current GTE RT/TR from `800A2CEC..800A2D0C`;
3. transforms the cube corners with `RTPS`;
4. rejects projection overflow;
5. compares projected coordinates against the measured screen bounds; and
6. compares the final projected depth against the descriptor value at `+0x40`.

The screen-bound globals `800A2D10` and `800A2D14` measured as **540 x 120**.
The GTE projection registers measured as H `400`, OFX `256.0` and OFY `60.0`.
The live view descriptor was `8014A350` in this fixture, but it is heap memory
and is never a fixed address. Its words from `+0x40` through `+0xCC` remained
identical across all 21 samples in one frame. The helper's five plane rows start
at `+0x50`, `+0x6C`, `+0x88`, `+0xA4` and `+0xC0`; `+0x40` is the depth
threshold used after the final `RTPS`.

## Measured P1 selection

All 21 level nodes in the flat queue reached `80096EF4` through return address
`8006C690`. The capture retained each node's center, radius, current eight GTE
RT/TR words, screen bounds, projection registers, camera/input/view pointers,
view-descriptor words and native selector result.

Native P1 selected three level nodes in the retained measurement run:

| Node | Center | Radius |
| --- | --- | --- |
| `80138310` | `(-2444, 504, -1010)` | `38` |
| `8013D750` | `(-617, 503, -785)` | `78` |
| `80142B90` | `(23, 725, -2308)` | `32` |

The other 18 level nodes were rejected. The live visibility set changes with
the scene and camera; it is not a static node allowlist. This is the comparison
baseline for the override, so a host selector that simply keeps every node is
not equivalent.

## Override contract

The guarded MP eye-frustum path replaces only the decision of `80096EF4` while
an existing P1 eye replay is active. It uses:

```text
world_point = native_tr + native_rt_q12 * animated_or_world_point
eye_point   = eye_view.translation + eye_view.rotation * world_point
visible     = no eye near/screen plane has all eight cube corners outside it
```

RT coefficients are Q12; TR is integer camera units. The eye view is the
existing `PSXModRenderView` already used by the P1-only eye renderer. The
selector's screen rectangle is 540 x 120 with the measured effective center
256, 60; the replay image remains 512 x 120.

The override requires the complete frame, camera selector, scene dispatch,
level callback, selector and helper hashes; the natural selector return address
in `{8006C66C, 8006C690}`; a valid selected P1 snapshot; the level callback
field at node `+0x384`; an aligned live node; finite render-view values; and a
non-wrapping center/radius cube. Any failure executes the untouched native
selector. Unknown mode, non-P1 ownership, inactive replay, missing eye view and
malformed layout stay native.

The override is controlled by `MOHU_VR_MP_FRUSTUM=1` and remains off by default.
It does not change the SP PVS selector, native scene-list traversal, input,
shots, saves or the 512 x 120 eye replay rectangle.

## Zero-angle implementation control

The final zero-angle P38 run enabled the override and exercised the native,
translated, yawed and lost weapon cases. Both eyes applied 126-147 frustum
decisions per case. No guarded level-node fallback occurred. The P2 player node
was counted separately as a non-level selector skip and remained native.

Every case retained populated 512 x 120 eyes, matching zero-IPD hashes, clean
rollback and unchanged source saves/preferences. The native pair ID 22 had left
and right SHA-256
`de83c69d0a08f5933805c07dc86ac27f2310df3ef8eb1e920b12d0608d9b3c9e`.
The same diagnostic executable also passed the full 13-ID MP matrix, lateral
eye offset, native pistol damage/refusal recovery, flat pose cycle and SP
zero-eye regression.

## W2.3 head-turn and near-wall acceptance

W2.3 extended `check_mp_view.py` with one OFF/ON control mode rather than a
second selector or renderer. The fixture remained copied root MP slot 1 with
P38, no weapon switches and no firing.

For each case, the diagnostic sampler recorded all 21 level nodes separately
for each eye, both native and shared-frustum decisions, the 540x120 selector
bounds, eye pair hashes/cycles and rollback counters. World coverage was
measured only in the top 45 rows so a lower-screen weapon or body silhouette
could not masquerade as visible world geometry.

- Zero yaw preserved every natively visible node. Each eye selected 7 override
  nodes versus 3 native nodes and retained 23,040 top-screen world pixels.
- +90 degrees selected a changed native/override set and retained 2,908 world
  pixels in each eye after the override.
- -90 degrees selected a changed set and retained 6,444 world pixels in each
  eye. The two headings used separate measured native body rotations because
  this flat fixture exposes one side at a time.
- The near-wall approach reached two consecutive movement chunks at or below
  200,000 raw position units and retained 23,040 world pixels in each eye.

All cases had matching zero-IPD eye hashes/cycles, zero frustum fallback and
zero rollback mismatch, leaks, watchdogs or nesting repairs. The affected
regressions also passed the 13-ID MP matrix, lateral offset, native pistol fire
with refusal recovery, flat inventory and SP zero control.

## Evidence

- [Measurement proof](../../vr/proof/weapon-mp-frustum-measurement.json)
- [Build and regression receipt](../../vr/proof/weapon-mp-frustum-build-receipt.json)
- [Both-eye zero control](../../vr/proof/weapon-mp-frustum-controls.png)
- [W2.3 control receipt](../../vr/proof/weapon-mp-visibility-receipt.json)
- [W2.3 control sheet](../../vr/proof/weapon-mp-visibility-controls.png)
- [W2.3 build/regression receipt](../../vr/proof/weapon-mp-visibility-build-receipt.json)
- Raw capture:
  `analysis/vr-baseline/weapon-mesh-mapping/w2-frustum-capture-20261026i/receipt.json`
- Probe: `vr/tools/probe_mp_level_selector.py`

The measurement run exited 0, left no game or debug listener, changed neither
source save hashes nor preferences, and kept the P38 fixture at clip 8 with P2
health 32. W2.3 completed the zero, +/-90-degree and near-wall acceptance.
