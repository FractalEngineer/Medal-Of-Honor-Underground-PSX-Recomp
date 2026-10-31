# Slot 3 objective camera

Updated 2026-11-01. This is desktop synthetic-controller evidence. Physical
headset fit and comfort remain open.

## Implemented behavior

- The camera is SP weapon ID `7`, mesh magic `0x170007`, 390 faces and 23
  nodes. Its exact asset identity is geometry `53506D92` / pose `3EDCCA12`.
- Nodes 1 through 12 form one 206-face camera assembly. The profile retains its
  85 vertices and masks the 139 arm/hand vertices in nodes 15 through 19 and 22
  independently in each eye.
- The camera uses the authored `+Z` forward basis and an 850 model-unit metre.
  Grip pivot `(0, -5, 0)` anchors the bottom of the body to the right hand.
- For SP only, while weapon ID 7 is equipped, right-squeeze above `0.55` maps to
  native R2 (`0x0200`). Right-trigger above `0.55` continues to map to native
  Cross (`0x4000`). Other weapons and multiplayer remain unchanged.
- Normal trigger without grip opens/show the papers. Trigger while grip is held
  enters the native camera view and takes the photograph.

## Live controls

The owned probe copied source slot 3 into a disposable directory, loaded the
diagnostic build, supplied focused synthetic hands and used the ordinary
OpenXR/base-PSX input path. The source `.pst` and `.thumb` hashes were unchanged.

| Check | Result |
| --- | --- |
| Camera identity and profile | ID 7, 390 faces, 23 nodes |
| Both-eye tracked projection/apply | 26 / 26 each |
| Model guard failures | 0 |
| Visible camera vertices per eye | 85 / 85 |
| Masked arm vertices per eye | 139 / 139 |
| SP input guard / tracking fallbacks | 0 / 0 |
| Right trigger without grip | Native papers action; no completion |
| Right grip then trigger | Native camera view, followed by `PHOTOGRAPHED CIPHER KEY BOOK` |
| Separated-eye idle image difference | 115,684 / 122,880 pixels |
| Separated-eye camera-view difference | 102,161 / 122,880 pixels |
| Source saves / preferences / owned processes | unchanged / unchanged / none |

Evidence paths:

- `analysis/runtime/camera-slot3-objective-final2-20261101/receipt.json`
  (`ACAF640BA344FDFA7534544A03D541F45D9FEE6D9FBFBF57234BDCCDEC6B76BF`)
- Unaimed papers and camera model:
  `analysis/runtime/camera-slot3-objective-final2-20261101/camera-unaimed.png`
- Native camera viewfinder:
  `analysis/runtime/camera-slot3-objective-final2-20261101/camera-aim.png`
- Objective completion text:
  `analysis/runtime/camera-slot3-objective-final2-20261101/camera-after.png`
  (`5609D8CD5970C5DC51911E30F970838B22150CAD5A857777091A3A46F86A3EAD`)
- Separated-eye idle and aimed pairs are recorded in the receipt.

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

- Fresh selective PGO was generated from the final source in
  `build-pgo-camera-20261101`: baseline, generate, 35-second heavy-slot-1
  synthetic VR training with normal profile flush, then use.
- All three expected `.gcda` profiles were emitted.
- Installed production PGO executable SHA-256:
  `FB19115147DD970B54F7D8D247F007A6BE30550AA77CC7EAF8A97AB94F187478`.
- Normal `run_vr.ps1` headless launcher smoke on copied slot 3 produced 57
  complete stereo pairs in two seconds with zero XR failures. With
  `-WristHudTest`, the same launcher path reported `60/60` weapon hits, zero
  weapon fallbacks and `60/60` separated-eye pose applications.

## Remaining physical check

- [ ] Hold the camera in the headset and confirm grip position, scale, wrist
  orientation and comfort.
- [ ] Confirm the unaimed papers and aimed viewfinder remain comfortable and
  stable at the physical runtime cadence.
- [ ] Confirm trigger-plus-grip completes the objective without accidental
  trigger input.
