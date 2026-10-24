# Underground VR Adapter

This directory owns title-specific engine bindings for Medal of Honor:
Underground. It is intentionally not compiled into the current flat
`psx-runtime` target.

`engine_map.c` contains mappings that have both:

- matching normalized instruction shape across the source and target functions;
- a specific target overlay capture hash;
- observed execution in the loaded Underground gameplay capture.

The map itself does not register hooks. Its opt-in diagnostic consumer verifies
function bytes and logs entry registers. An additional transform probe is inert
unless `MOHU_VR_LEVEL_OFFSET_X` is set in the diagnostic build. The flat launcher
and existing executable must continue to work without any VR state.

Current confirmed mappings:

| Role | Reference | Underground | Evidence |
| --- | --- | --- | --- |
| Entity transform | `0x80084718` | `0x80093830` | 41/41 opcodes, live execution |
| Entity node transformer | `0x80013AE4` | `0x80013B40` | 221/221 opcodes, live call ring |
| GTE RT/TR loader | `0x80013E58` | `0x80013EB4` | Byte-identical, live call ring |
| Level vertex transformer | `0x8008B3E8` | `0x80099960` | 710/710 opcodes, 12 RTPS, live execution |
| Gameplay render wait | `0x80090B80` | `0x8009D828` | 110/110 opcodes, live execution |

Main-executable SHA-256 values and every function SHA-256/FNV-1a value are
recorded in `engine_map.c`. Whole overlay-capture hashes remain empty because
the capture windows change between sessions; function bytes are the stable
identity.

## Shared release build

The guard path is opt-in at runtime and built into the single `build-release`
target used by every launcher. Reconfigure that directory in place; do not
create a build directory per feature:

```powershell
cmake -S . -B build-release `
  -DMOHU_VR_DIAGNOSTICS=ON `
  -DPSX_DEBUG_TOOLS=OFF `
  -DPSX_OPENXR=ON
```

`vr_diagnostic.c` registers function-entry hooks. On first entry it computes the
function's FNV-1a checksum in guest RAM and logs the entry registers only when
the checksum matches `engine_map.c`. A mismatch disables that binding.

The optional transform probe adds `MOHU_VR_LEVEL_OFFSET_X` to GTE TRX at the
level transformer once per draw span. It restores the saved TRX at the verified
gameplay render-wait entry. With the environment variable unset, the probe does
not alter GTE state.

The same-checkpoint stereo control supports a complete per-eye render view:

```powershell
$env:MOHU_VR_STEREO_PROOF = '1'
$env:MOHU_VR_EYE_RENDER_VIEW = '1'
$env:MOHU_VR_EYE_GUEST_SUBMIT = '1'
$env:MOHU_VR_EYE_OFFSET = '24'
```

It replays the guarded frame render at `0x80053BB4`, builds a full
`PSXModRenderView` from the guest projection, and submits the regenerated list
through guarded guest `DrawOTag`. Guest TR registers are not modified. With
`MOHU_VR_EYE_OFFSET=0` and the same seam enabled, the pair is byte-identical.

Both eye replays target the rollback-protected `y=0` VRAM scratch buffer. The
native game alternates its display origin between `y=0` and `y=240`, but the eye
packet coordinates are rooted at `y=0`; following the native origin produced
alternating pure-black pairs. The render transaction backs up and restores the
scratch rectangle, so this does not change guest VRAM. Set
`MOHU_VR_STEREO_DUMP_DIR` to an existing directory to write the first 60
submitted pairs when diagnosing a recurrence.

`MOHU_VR_EYE_YAW_MDEG`, `MOHU_VR_EYE_PITCH_MDEG`, and
`MOHU_VR_EYE_HEAD_{X,Y,Z}_MILLI` add diagnostic head rotation and sub-unit
translation. The manual GP0 walker loses packet provenance and is not valid for
PGXP projective validation. `MOHU_VR_EYE_OFFSET_ALL_SPANS=1` selects the
rejected direct-TRX experiment; that variant produced a black pair.

While the projective render pass is active, `{"cmd":"mod_counters"}` reports
`vr.nclip.render.{total,precise,miss,corrected,positive,negative,zero}`. These
counters are scoped to the signed homogeneous-winding decision and do not
require widescreen `precise_nclip`.

The same diagnostic build can opt into the headset lifecycle:

```powershell
$env:PSX_OPENXR_ENABLE = '1'
$env:MOHU_VR_OPENXR = '1'
```

OpenXR mode implies the render-view, guest-submit, and stereo-proof flags. It
shows boot/menu content on a native head-relative surface, then switches to one
complete per-eye pair at gameplay. The launcher defaults to `WorldScale=3`
with a 67 mm IPD calibration, leaving 238.80597 effective GTE units per metre.
`MOHU_VR_UNITS_PER_METER`, `MOHU_VR_MENU_DISTANCE`, and
`MOHU_VR_MENU_WIDTH` remain the underlying runtime controls. Start the headset
runtime before a physical launch.

The opt-in right-grip pointer uses the same per-eye render pose:

```powershell
$env:PSX_VR_LASER = '1'
```

Holding right squeeze casts the OpenXR aim ray through the level visibility
tree. The beam ends at the nearest tree node and draws an impact dot. The
fixed-range fallback is controlled by `MOHU_VR_LASER_RANGE_M`; dot radius is
`MOHU_VR_LASER_DOT`. `MOHU_VR_LASER_SYNTHETIC=1` provides a deterministic
camera-space ray for diagnostics. The geometry fixture is
`vr/tests/test_raycast.c`.

For no-headset OpenXR validation, use SteamVR's null driver through the shared
launcher:

```powershell
.\RunVR-SteamVR.bat -Headless -Seconds 10
```

The launcher forces the null HMD only for that process, waits for complete
stereo pairs, restores the original SteamVR settings, and stops SteamVR when
done. The default profile is `-IPDmm 67 -WorldScale 3`, which matches the
reference game's accepted provisional profile and produces
`238.805970149254` effective GTE units per metre. `-UnitsPerMeter` remains
available as a base-mapping override; `WorldScale` is applied after it.
Headset IPD positions still come from the OpenXR runtime.

Normal VR launch also uses `-InternalResolution 1080p`, enables
`PSX_VR_HEAD_FRUSTUM=1`, and enables `PSX_VR_SUPPRESS_FLAT_HUD=1`. The
frustum selector is a guarded host-side queue builder over Underground's
visibility tree. Flat-HUD suppression skips the guarded HUD text producer and
unlinks the measured head-locked bar/compass packet block only inside the eye
transaction. It does not alter native play.

Diagnostic opt-outs remain available:

```powershell
.\RunVR-VDXR.bat -InternalResolution native -NoHeadFrustumDiagnostic -KeepFlatHud
```

Use `-KeepFlatHud` to compare the old head-locked HUD, `-NoHeadFrustumDiagnostic`
to restore native body-camera culling, and `-DebugPort 4372` when a debug-tools
build is present. `MOHU_VR_STEREO_DUMP_PAIRS` limits pair dumps (default 60);
`MOHU_VR_HUD_TRACE=1` emits one OT trace for packet mapping.

PGXP diagnostic states use ABI `131106`; base-flavor states use `34`. Savestates
also carry the framework execution identity, so runtime source changes can
invalidate an older slot. Never patch a save header. If the PGXP runtime rejects
the fixture with `state_load_failed` or `last_ok=0`, ask the operator for a fresh
PGXP slot and copy its `.pst` and `.thumb` into the isolated tree.

`build-release/` is the only active build. The root `RunFlat.bat` and
`RunVR-*.bat` launchers all target it. Flat mode clears the VR environment and
leaves this diagnostic plugin inert. Creating more build directories does not
prevent ABI or runtime-identity state invalidation.

The CMake default remains `MOHU_VR_DIAGNOSTICS=OFF` so package builds can use
the original `mods/preloaded` catalog without compiling these sources.
