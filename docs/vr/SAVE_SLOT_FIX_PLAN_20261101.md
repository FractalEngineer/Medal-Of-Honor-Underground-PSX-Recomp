# Save Slot VR Fix Plan

Updated 2026-11-02 after operator acceptance of the mission-end frontend fix.
The sniper zoom is implemented; sniper view-distance extension remains open.

## Slot map

| System save | UI label | Purpose |
| --- | --- | --- |
| `03` | `04` | Objective camera wrist placement |
| `04` | `05` | Under-fire HUD and gameplay flat-frame suppression |
| `05` | `06` | Scoped sniper rifle |

All runtime probes use copied saves. Source saves, thumbnails, preferences and
keybinds remain unchanged. Single-player behavior only.

## Slot 03 / UI 04: objective camera

- [x] Remove the rejected camera-space correction and keep the accepted `340`
  model-unit display scale.
- [x] Anchor the measured node-22 centre `(-7, -27.5, -3.5)` to the tracked
  wrist through the controller-local transform. Default offset is zero.
- [x] Add live `right`/`up`/`forward` calibration through
  `vr/tools/tune_camera_offset.py` and Release-build file polling.
- [x] Preserve paper swap, R2 photograph input, arm masking and native guards.
- [x] Operator confirmed physical camera placement and wrist centering.

## Slot 04 / UI 05: flat frame and damage HUD

- [x] Refuse native flat presentation surfaces during active gameplay.
- [x] Capture the native damage marker and place it above the compass but below
  the solid health ring on the left wrist HUD.
- [x] Suppress the screen-space marker only after the wrist surface uploads;
  tracking or upload failure retains native feedback.
- [x] Reproduce under fire with no centered flat-scene flash.
- [x] Operator confirmed the flat-frame flash and wrist marker behavior.

## Slot 05 / UI 06: scoped sniper rifle

- [x] Right grip on weapon ID `5` applies a held `2.5x` focal zoom without
  entering native ADS or pinning movement.
- [x] Preserve asymmetric eye centres, IPD, movement axes and native ammunition,
  recoil, collision and damage behavior.
- [x] Use the same zoomed eye projection for the rifle and right-grip laser so
  their screen-space aiming angle matches.
- [x] Releasing grip, switching weapons, pausing or losing tracking restores the
  unscoped view and normal laser behavior.
- [x] Remove the scrapped scope mask, mobile aim path and title-specific extra
  OpenXR overlay.
- [ ] Sniper view distance/fog extension is still not working in VR. The flat
  Slot 01 reference demonstrates the intended final scope transition; current
  VR changes cover focal zoom only.
- [ ] Physical headset: confirm zoom comfort, rifle/laser alignment, clean grip
  release and final long-range visibility.

## Slot 02 / UI 03: laser and Panzerfaust

- [x] Use one weapon-independent one-pixel laser packet for all held weapons.
- [x] Rotate the Panzerfaust tube onto the shared controller bore while keeping
  its grip pivot and native shot/damage semantics.
- [x] Add focused calibrated-weapon coverage for the coaxial tube.
- [ ] Physical headset: confirm matching beam width and Panzerfaust alignment.

## Frontend and mission transitions

- [x] Keep the native flat frontend available for boot, menus and states with no
  active gameplay player while refusing it during gameplay.
- [x] Allow the native surface after the guarded stale-scene interval so a
  mission-complete evaluation screen survives a stale player pointer.
- [x] Headless Slot 02 capture rendered the mission evaluation in the headset.
- [x] Operator confirmed the mission-end frontend fix.
- [ ] Physical headset: confirm navigation from gameplay through every frontend
  transition.

## Validation

- [x] `build-release` is the only build tree and is configured as Release with
  debug tools OFF and OpenXR ON.
- [x] All 173 Python tests pass.
- [x] Focused scope, HUD, frustum, input, weapon and calibrated-weapon tests pass.
- [x] Copied Slot 01 and Slot 02 source saves retain their pre-run hashes.
- [x] Null-HMD scoped runs complete with complete stereo pairs and zero XR
  begin/view failures.
- [ ] Sniper view-distance acceptance remains open.
- [x] Final Release executable SHA-256:
  `B5E22F1F349EA09B04DEAF7799577EC15B7EA00306B906900C707734F9926A36`.

## Evidence

- Mission-end frontend:
  `analysis/runtime/mission-end-slot2-native-20261102/layers/compositor.png`
- Scoped rifle/laser:
  `analysis/runtime/scope-zoom-refactor-slot1-20261102/layers/compositor.png`
- Flat camera/HUD:
  `analysis/runtime/camera-slot3-wristzero-20261101/` and
  `analysis/runtime/vr-slot4-damage-underlay-20261101-run5/`
- Latest focused/headless run logs:
  `analysis/runtime/scope-zoom-refactor-slot1-20261102/vr-launch.stdout.log`
