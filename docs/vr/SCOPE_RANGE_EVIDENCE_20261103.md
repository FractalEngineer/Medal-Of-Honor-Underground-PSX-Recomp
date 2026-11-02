# Held sniper range: copied Slot 01

Implemented on `feature/vr-port`, starting from `032892b`. Desktop/null-HMD
range verification passes. Physical-headset acceptance remains open.

## Native ownership and trace

`analysis/runtime/scope-range-native-cutoff-20261103/receipt.json` records
idle, native R2 held for 240 frames, and released, using disposable Slot 01
copies. `trace-disassembly.txt` in that directory contains the guest callers
and consumers. The earlier descriptor write trace is in
`analysis/runtime/scope-range-native-20261102/receipt.json`.

| State | Idle | Native scope | Released |
| --- | ---: | ---: | ---: |
| Player input `+AC`, native projection H | 400 | 2463 | 400 |
| Player input `+B0`, target H | 2447 | 2447 | 2447 |
| Player input `+B4`, ramp step | 1 | 65 | 1 |
| `800B7480`, subdivision distance | 250 | 2313 | 250 |
| View descriptor `+3C` (Q16 H) | 400 | 2463 | 400 |
| View descriptor `+40` (Q16 far plane) | 8000 | 8000 | 8000 |
| Scene `+CC`, software fog start | 5700 | 5700 | 5700 |

Slot 01 roots: player `800DDBC0`, player input `800DDFBC`, active camera
`800DF160`, camera input `800DF55C`, view descriptor `800DEE40`, scene
`8014BB70` (scene pointer stored at `800A977C`). Runtime follows pointers;
these fixture addresses are evidence, not hard-coded object locations.

The caller returning to `80089E4C` reaches the native scope ramp. At
`8008A090..8008A0E4`, the guest increases input `+AC` and `800B7480` by the
same accelerating step. It stops after overshooting target 2447 to 2463.
`8004C50C` writes camera input `+C4` to descriptor `+40` at `8004C704`, and
the selected player's input `+AC` to descriptor `+3C` at `8004C74C`, then
calls `8009B64C` to construct view planes. `80053D4C` reads player input
`+AC` into `800A7140` and installs GTE H through `8001D2D8`.

Crucially, descriptor `+3C` is projection distance, not the fog field.
The unchanged descriptor far plane alone cannot reproduce this transition.
VR's head-frustum collector consumes descriptor `+40`; the existing eye
projection supplies the angular frustum and continues to apply 2.5x zoom.

`80010DB0` reads `800B7480` into scratch `+39C`. Preflight `80011424`
classifies vertices below four times that value as near, setting subdivision
bits. `800110E0..800110FC` skips software fog for those classified triangles.
Otherwise `800110C0` reads scene `+CC`; `80011120..800111D4` computes per-vertex
fog from SZ relative to that start and emits DPCS colors. This software path,
not just GTE DQA/DQB, hides the farther arch.

Thus native scope's effective fog-free distance reaches `4*2313 = 9252`.
Increasing the subdivision distance in VR also expands packet work and caused
missing wall sections in the diagnostic control. Increasing H alone did not
reveal the arch. Neither approach is retained.

## Implementation boundary

During each single-player eye replay only, a guarded weapon-5 grip hold raises
scene `+CC` to the larger of its original value and the measured final native
fog-free distance. `scope.c` reproduces the integer ramp from the guest-owned
target; it does not use the focal zoom factor as a distance multiplier.
The scene halfword is restored immediately after the synchronous native draw,
and the render transaction also restores guest state on failure.

The existing weapon tracking validator gates the range change, including focus,
origin, pose flags, age and forced-loss diagnostics. Native instruction guards
verify the ramp and fog consumer before writing. No persistent range state is
cached. A release, weapon change, pause or tracking failure cannot leave the
scene field extended. The draw-distance/subdivision scalar, descriptor, H,
camera, input mapping, HUD, rifle and laser projection code are unchanged.
No native ADS, mask, extra surface, ammunition or movement changes are added.

This matches the observed final-scope visibility within the unchanged 8000-unit
view descriptor. It does not claim a general extension beyond the native far
plane or universal scene parity.

## Visible verification

Final diagnostic run:
`analysis/runtime/scope-range-transitions4-20261103/receipt.json`.
Each stage directory contains `application_layer.png` and `compositor.png`:

- `before/`: ordinary unzoomed corridor, farther arch hidden.
- `held/`: farther arch and floor visibly revealed; rifle and red grip laser
  remain aligned in both eyes, with no scope mask or flat gameplay panel.
- `zoom-only-control/`: exactly the same 2.5x projection and pose, but the
  disposable guest target is temporarily set to 400; farther arch is hidden.
  This control changes neither source saves nor production code.
- `released/`: original fog visibility and unzoomed projection return.
- `tracking-lost/` and `tracking-restored/`: farther arch disappears and returns
  while grip stays held. Existing zoom behavior is outside this range change.
- `weapon-switched/`: weapon 14, ordinary range.
- `paused/`: native pause screen; no extended gameplay state persists.
- `moving-held/`: player position changes with the grip held; pad LY is 26,
  native R2 remains released (`buttons=0xFFFF`), native H remains 400 and
  `800B7480` remains 250.

The same-zoom image difference is confined to corridor/floor pixels; neither
rifle nor laser is moved by the range change. Source/preference hashes match.
The final run records 1104 restoration checks, zero mismatches, and no XR
failure. Native pause/frontend submissions are expected only during pause and
startup; the gameplay captures contain the stereo projection.

173 Python tests pass. Focused scope, input, frustum, HUD, weapon and calibrated
weapon C tests pass. Logs:
`analysis/runtime/scope-range-tests-20261103/`.
Final Release build uses `build-release` only, Release, `PSX_DEBUG_TOOLS=OFF`,
and OpenXR ON. Final debug-OFF capture:
`analysis/runtime/scope-range-release-final-20261103/layers/application_layer.png`.
It visibly retains the farther arch; the launcher exits successfully with no
game process remaining. Its log records 390/390 complete stereo pairs, zero
XR begin/view failures and 390/390 laser hits in both eyes. Final executable
SHA-256: `DF276A974F2167D06039D02E2BE3AA5B4A97067E177F4DF5BDF9F2D5BFEF3DFB`.
`analysis/runtime/scope-range-tests-20261103/final-verification.json` records
the build configuration and unchanged source-save/preference hash checks.

Physical headset range, comfort and sustained alignment require
the user's physical test and are not certified by these captures.
