# PGXP Render-View and Near-Plane Evidence

Date: 2026-10-24

This note records the first Underground stereo pairs produced with a full
`PSXModRenderView`, guest `DrawOTag` submission, and PGXP homogeneous
projective clipping. It is diagnostic evidence, not an OpenXR or headset
acceptance receipt.

## Save-state flavor requirement

The PGXP diagnostic runtime is the framework's overlay flavor `2`. Its boot
state ABI tag is `131106`; the previous base-flavor slot has tag `34`.
The framework correctly rejects a base slot before applying any state.

The saved state also carries the framework's execution identity. Rebuilding a
runtime from changed implementation sources can therefore invalidate an
otherwise valid PGXP slot, even when the ABI tag still matches. A failed startup
load reports `state_load_failed` or `last_ok=0`; do not patch the stored
identity.

Do not patch the ABI field and do not rewrite the original save. If a run
reports:

```text
boot_state: reject - abi_tag=34(want 131106)
```

ask the operator to launch the PGXP-flavored diagnostic build, save a new slot
outside slot `0`, and report the slot number. Copy the resulting `.pst` and
`.thumb` into the isolated save tree. This request is expected whenever only a
base-flavor fixture is present or a source change has invalidated the execution
identity.

The operator originally created PGXP slot `1`, then created slot `2` after the
render-NCLIP instrumentation changed the execution identity. Slot `2` is the
current fixture. Its two files were copied to:

```text
analysis/vr-baseline/saves/openbios/state_8001F844_slot02.pst
analysis/vr-baseline/saves/openbios/state_8001F844_slot02.thumb
```

The old `slot01` and base `slot00` files were not modified.

## Implementation

`vr/underground/vr_diagnostic.c` now:

- builds a complete `PSXModRenderView` from the guest `H`, `OFX`, and `OFY`
  values, with a centered `H=400` fallback for frame entry;
- supplies row-major rotation, Q12 rotation, integer translation, precise
  double translation, focal lengths, and projection metadata;
- exposes yaw, pitch, and sub-unit head translation in GTE camera units;
- submits the regenerated OT through the guarded guest `DrawOTag` at
  `0x80018B50`, preserving GP0 packet source addresses for PGXP;
- keeps the old manual GP0 walker only as an OT control. It loses provenance and
  therefore reports every projective lookup as `vr.projective.miss0`.

The diagnostic build is the PGXP hook flavor. The flat build remains the base
flavor and does not link this plugin.

## Controls

```powershell
$env:PSX_LOAD_SLOT = '2'
$env:MOHU_VR_STEREO_PROOF = '1'
$env:MOHU_VR_EYE_RENDER_VIEW = '1'
$env:MOHU_VR_EYE_GUEST_SUBMIT = '1'
$env:MOHU_VR_EYE_OFFSET = '24'
$env:PSX_RENDER_PASS_VERIFY = '1'
$env:PSX_STEREO_SHED = '0'
```

`MOHU_VR_EYE_VIEW_OFFSET=1` remains a compatibility alias for
`MOHU_VR_EYE_RENDER_VIEW=1`.

Pose controls:

| Variable | Meaning |
| --- | --- |
| `MOHU_VR_EYE_OFFSET` | Signed per-eye lateral separation in GTE camera units |
| `MOHU_VR_EYE_YAW_MDEG` | Head yaw in thousandths of a degree |
| `MOHU_VR_EYE_PITCH_MDEG` | Head pitch in thousandths of a degree |
| `MOHU_VR_EYE_HEAD_X_MILLI` | Head X translation in thousandths of a GTE unit |
| `MOHU_VR_EYE_HEAD_Y_MILLI` | Head Y translation in thousandths of a GTE unit |
| `MOHU_VR_EYE_HEAD_Z_MILLI` | Head forward translation in thousandths of a GTE unit |

The diagnostic calibration uses 1000 GTE units per meter. That calibration is
fixture-specific and is not yet an OpenXR world-scale decision.

## Results

All runs used the same PGXP slot, interpreter overlay profile, frame-render
replay, guest `DrawOTag`, and `PSX_RENDER_PASS_VERIFY=1`.

| Pose | Pair | Changed pixels | Verification | Projective work |
| --- | --- | --- | --- | --- |
| Zero | `666` | 0 / 122,880 | 1,481 checks, 0 mismatches | 1,450,878 draws; 1,459,770 `miss0` |
| Lateral `+/-24` | `662` | 93,376 / 122,880 | 1,446 checks, 0 mismatches | 1,414,911 draws; 1,424,310 `miss0` |
| Pitch `-15 deg`, forward `250`, lateral `+/-24` | `702` | 91,984 / 122,880 | 1,544 checks, 0 mismatches | 1,360,264 draws; 1,520,840 `miss0` |

Every measured pair used one guest cycle and equal state hashes for both eyes.
The verified runs also reported zero aborts, watchdogs, dropped device stores,
VRAM leaks, and nesting repairs.

## Render-path NCLIP receipt

The PGXP runtime now increments render-scoped counters at the signed
homogeneous-winding decision in `gte_nclip`:

```text
vr.nclip.render.total
vr.nclip.render.precise
vr.nclip.render.miss
vr.nclip.render.corrected
vr.nclip.render.positive
vr.nclip.render.negative
vr.nclip.render.zero
```

`precise` counts NCLIPs whose three PGXP projections were available; `miss`
counts the remainder. `corrected` counts nonzero precise signs that replaced a
different native sign. `positive`, `negative`, and `zero` describe the
final sign used by the render path. Query them through the debug server:

```text
{"cmd":"mod_counters"}
```

The following snapshots each followed 60 completed stereo attempts on slot `2`.
The counters continued for one or two host frames while the query was serviced,
so the snapshot frame is recorded with the totals.

| Pose | Frame | NCLIPs | Precise | Miss | Corrected | Positive | Negative | Zero |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Zero | 124 | 186,157 | 186,157 | 0 | 15,243 | 98,604 | 87,309 | 244 |
| Lateral `+/-24` | 131 | 197,080 | 197,080 | 0 | 16,055 | 104,520 | 92,300 | 260 |
| Pitch `-15 deg`, forward `250` | 128 | 182,912 | 182,912 | 0 | 17,344 | 97,472 | 85,248 | 192 |
| Yaw `+15 deg` | 127 | 192,780 | 192,780 | 0 | 18,396 | 101,997 | 90,531 | 252 |
| Yaw `-15 deg` | 130 | 186,485 | 186,485 | 0 | 14,950 | 99,255 | 86,970 | 260 |

All five snapshots report zero projective-lookup misses. The changing correction
and facing totals confirm that the render path observes pose-dependent signed
winding rather than a fixed counter.

Lateral pose:

```text
eye_cycles=[2345596177,2345596177]
eye_hashes=[8053f8e21b46f779,8053f8e21b46f779]
eye_view=[[24,0,0],[-24,0,0]]
```

Near-plane stereo pose:

```text
eye_cycles=[2390755220,2390755220]
eye_hashes=[66bc9884bb13788a,66bc9884bb13788a]
eye_view=[[24,65,-241],[-24,65,-241]]
```

The near-plane image keeps the floor, foreground weapon, and nearby steps
present without the black wedge seen in the earlier integer-only failures. The
`vr.projective.draw` counter proves the homogeneous draw path is active.

The framework's widescreen-oriented `nclip_stats` command still reports
`enabled=0` because this title does not arm `[widescreen] precise_nclip`.
The render-scoped `vr.nclip.render.*` counters above are independent of that
option and provide the accepted signed-NCLIP receipt for this path.

## Retained images

| Image | SHA-256 |
| --- | --- |
| [Zero left](../../vr/proof/stereo-pgxp-zero-left.png) | `93e44b30ae6cb8b1993cdbc4a1e35203b217482feb3488a5ef033b265cac4538` |
| [Zero right](../../vr/proof/stereo-pgxp-zero-right.png) | `93e44b30ae6cb8b1993cdbc4a1e35203b217482feb3488a5ef033b265cac4538` |
| [Lateral left](../../vr/proof/stereo-pgxp-lateral24-left.png) | `f8ce2debe262f8bd40d1fcf32e86e33c93164f160f5b347c42a9e49d19efb13f` |
| [Lateral right](../../vr/proof/stereo-pgxp-lateral24-right.png) | `2a9f7d4ae87576184aa6dcefcfe1e28846f8dd590080104d05f65c51fc56d41ed` |
| [Near-plane left](../../vr/proof/stereo-pgxp-nearplane24-left.png) | `0e389b32373159a4a7d09b7f1084ba16d532cdfe10700c70155b2057cc7f6a3b` |
| [Near-plane right](../../vr/proof/stereo-pgxp-nearplane24-right.png) | `2462e07d31ece1e59fd8a00f4d73a0cba81b8ce1cf21f086926a28bd03f60703` |

Side-by-side receipts:

- [Zero PGXP control](../../vr/proof/stereo-pgxp-zero-sbs.png)
- [Lateral PGXP pair](../../vr/proof/stereo-pgxp-lateral24-sbs.png)
- [Near-plane PGXP pair](../../vr/proof/stereo-pgxp-nearplane24-sbs.png)

## Reproduction

Configure the shared release build once. Reuse and reconfigure `build-release/`
in place; a new build directory does not repair a savestate invalidated by ABI
or runtime identity changes:

```powershell
$env:PSX_LIBWEBP_SOURCE_DIR = (Resolve-Path 'build-release\_deps\psx_libwebp-src').Path
cmake -S . -B build-release `
  -DCMAKE_C_COMPILER=clang `
  -DCMAKE_CXX_COMPILER=clang++ `
  -DCMAKE_C_COMPILER_LAUNCHER= `
  -DCMAKE_CXX_COMPILER_LAUNCHER= `
  -DPSX_DEBUG_TOOLS=OFF `
  -DPSX_OPENXR=ON `
  -DMOHU_VR_DIAGNOSTICS=ON
cmake --build build-release --target psx-runtime -- -j 8
```

`RunFlat.bat` clears VR variables. The root `RunVR-*.bat` wrappers enable VR in
the same executable, so no second build target is required.

The accepted runs use `analysis\vr-baseline\game-interp.toml`, so the overlay
hook chain remains visible and the real guest `DrawOTag` provides packet
provenance. If testing the autocompile path instead, stage an overlay toolchain
and capture history with codegen hash `0x115b1739`; the manual GP0 walker is not
valid projective evidence.

Capture after the mapped frame-render hook appears:

```text
stereo_dump path=analysis\vr-baseline\pgxp-pose-nearplane-stereo count=1
```
