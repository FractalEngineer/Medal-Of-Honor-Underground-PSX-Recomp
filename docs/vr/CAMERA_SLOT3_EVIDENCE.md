# Slot 3 objective camera

Updated 2026-11-02 after bounded-controller separated-eye validation and
operator acceptance of the wrist placement.

## Implemented behavior

- The camera is SP weapon ID `7`, mesh magic `0x170007`, 390 faces and 23
  nodes. Its exact asset identity is geometry `53506D92` / pose `3EDCCA12`.
- Node 22 is the 128-face camera body with 99 vertices. Nodes 1 through 12 are
  the 206-face arm/hand assembly and remain masked in both eyes.
- Nodes 15, 16, 18 and 19 are the 56-face paper prop with 40 vertices. While
  Cross is held for unaimed fire, the renderer swaps the camera body to those
  paper vertices instead of leaving the hand or camera visible.
- The camera uses the authored `+Z` forward basis and a 340 model-unit metre,
  a 2.5x display scale relative to the original 850-unit calibration. Grip
  pivot `(-7, -27.5, -3.5)`, the body's measured bounding-box centre, anchors
  the model on the right controller. The default controller-local correction is
  `(0, 0, 0)` so the measured centre maps directly to the tracked wrist origin.
- The objective camera offset can be changed while the game is running:
  `python vr/tools/tune_camera_offset.py --up 0.02 --forward -0.01`.
  Values are absolute controller-local offsets; omitted axes remain unchanged.
  `--read` reports the current values and `--reset` restores the built-in
  wrist origin. Release builds poll an atomically replaced tuning file; debug
  builds can also use the TCP command when its server is compiled in.
  The equivalent launch overrides are `MOHU_VR_CAMERA_OFFSET_UP_M` and
  `MOHU_VR_CAMERA_OFFSET_FORWARD_M` (plus `..._RIGHT_M`).
- For SP only, while weapon ID 7 is equipped, right-squeeze above `0.55` maps to
  native R2 (`0x0200`). Right-trigger above `0.55` continues to map to native
  Cross (`0x4000`). Other weapons and multiplayer remain unchanged.
- While the camera aim grip is held, all analog movement and turn axes are
  neutral. Trigger, face buttons and the native R2 mapping remain available.
- Normal trigger without grip opens/show the papers. Trigger while grip is held
  enters the native camera view and takes the photograph.

## Live controls

The owned probe copied source slot 3 into a disposable directory, placed both
bounded synthetic controllers inside the rendered view, and captured the
ordinary separated-eye OpenXR path. The source `.pst`, `.thumb` and preference
hashes were unchanged.

| Check | Result |
| --- | --- |
| Camera identity and profile | ID 7, 390 faces, 23 nodes |
| Both-eye tracked projection/apply | 16 / 16 each |
| Model guard failures | 0 |
| Visible camera vertices per eye | 99 / 99 |
| Masked arm vertices per eye | 157 / 157 |
| Camera-to-papers despawn/swap counters | 16 / 16 |
| SP input guard / tracking fallbacks | 0 / 0 |
| Right trigger without grip | Camera body disappears; paper prop remains; no completion |
| Right grip then trigger | Native camera view, followed by `PHOTOGRAPHED CIPHER KEY BOOK` |
| Separated-eye idle image difference | 116,066 / 122,880 pixels |
| Separated-eye papers image difference | 116,166 / 122,880 pixels |
| Separated-eye camera-view difference | 107,239 / 122,880 pixels |
| Source saves / preferences / owned processes | unchanged / unchanged / none |

Evidence paths:

- `analysis/runtime/camera-slot3-paper-swap-20261101/receipt.json`
- Idle camera pair:
  `analysis/runtime/camera-slot3-paper-swap-20261101/camera-idle-stereo/`
- Trigger-held paper pair:
  `analysis/runtime/camera-slot3-paper-swap-20261101/camera-unaimed-stereo/`
- Grip-held aim pair:
  `analysis/runtime/camera-slot3-paper-swap-20261101/camera-stereo/`
- Photograph-complete pair:
  `analysis/runtime/camera-slot3-paper-swap-20261101/camera-photo-stereo/`

Reproduce after building the diagnostic target:

```powershell
python vr/tools/probe_sp_weapon_inventory.py `
  analysis/runtime/camera-slot3-objective-YYYYMMDD `
  --slots 3 --switches 1 --source saves --weapon-trace `
  --build-dir analysis/builds/mp40-diagnostic `
  --dump-ram --camera-objective
```

The probe never edits the source save. It copies `slot03.pst`/`.thumb`, exercises
the unaimed and aimed paths, reloads the disposable copy between controls, and
verifies source and preference hashes after shutdown.

## Build acceptance

- The active Release runtime was relinked after the wrist-zero and file-based
  calibration changes.
- Installed production executable SHA-256:
  `B5E22F1F349EA09B04DEAF7799577EC15B7EA00306B906900C707734F9926A36`.
- Normal `run_vr.ps1 -WristHudTest` headless launcher smoke on copied slot 3
  completed 300/300 stereo pairs over ten seconds with zero XR failures,
  `300/300` weapon hits and zero weapon fallbacks.
- Full suite: 173 Python tests and focused input/weapon/shot C tests pass.

## Remaining physical check

- [x] Validate the camera from separated-eye headset renders with both bounded
  controllers in view.
- [x] Confirm idle renders the camera body without the arm model.
- [x] Confirm trigger without grip swaps the camera body to the paper prop.
- [x] Confirm trigger-plus-grip completes the objective without accidental
  trigger input in the synthetic OpenXR path.
- [x] Hold the camera in the physical headset and confirm grip position, scale,
  wrist orientation and comfort.
- [ ] Confirm no movement occurs while the right grip holds camera aim in the
  physical headset.
- [ ] Confirm the camera-to-papers swap and aimed viewfinder remain comfortable
  and stable at the physical runtime cadence.

## 2.5x model refinement and wrist correction

The 850-to-340 model-unit scale change makes both the node-22 camera body and
the nodes-15/16/18/19 paper prop 2.5x larger. The body's measured bounds are
`(-45,-64,-10)..(31,9,3)`, confirming the `(-7,-27.5,-3.5)` centre. The default
controller-local correction is `(0,0,0)` metres; unlike the rejected
camera-space offset, any live correction rotates with the hand.

The bounded-controller probe now uses a 60-degree test-wrist roll instead of the
prior 90-degree roll. This is still synthetic capture geometry; the operator
confirmed that the physical headset controller orientation itself is correct.
The refreshed separated-eye evidence is under
`analysis/runtime/camera-slot3-scale-25x-headset-20261101/`. The source save and
preference hashes remained unchanged, the objective completed, and the run
reported zero model/input/tracking fallbacks. The installed PGO smoke held
300/300 stereo pairs over ten seconds with zero XR failures and `300/300`
weapon hits with zero fallbacks.
