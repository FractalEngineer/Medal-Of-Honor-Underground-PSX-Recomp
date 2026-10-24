# OpenXR Bootstrap Evidence

Date: 2026-10-24

This note records the first Underground OpenXR frame-lifecycle integration. It
does not claim headset acceptance or gameplay completeness.

## Implemented path

`vr/underground/vr_diagnostic.c` now supports an opt-in
`MOHU_VR_OPENXR=1` mode. The mode:

- enables the framework OpenXR backend;
- presents a native 2 m surface while boot, menus, or videos have no gameplay
  stereo frame;
- begins one headset frame at the guarded Underground frame render;
- reads the located left and right `PSXModRenderView` values from OpenXR;
- reuses the accepted same-checkpoint frame-render replay and guest `DrawOTag`
  submission;
- ends the headset frame only after a complete pair is available; and
- defaults to 716.4179 GTE units per metre, matching the reference's 48-unit
  eye separation at a 67 mm IPD.

The native surface is disabled before gameplay stereo begins. A failed OpenXR
begin leaves the flat native presentation path active and does not submit a
stale stereo pair.

## Configuration

Build the shared release directory in place:

```powershell
$env:PSX_LIBWEBP_SOURCE_DIR = (Resolve-Path 'build-release\_deps\psx_libwebp-src').Path
$env:PSX_OPENXR_SDK_SOURCE_DIR = (Resolve-Path `
  'C:\Users\titan\Desktop\Github_Projects\Mine\Medal-Of-Honor-PSX-Recomp\build-release\_deps\psx_openxr_sdk-src').Path
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

Run with the headset runtime active before launching the process:

```powershell
$env:PSX_OPENXR_ENABLE = '1'
$env:MOHU_VR_OPENXR = '1'
$env:PSX_LOAD_SLOT = '2'
$env:PSX_STEREO_SHED = '0'
.\build-release\Medal_of_Honor_Underground_Recompiled.exe `
  --game (Resolve-Path 'analysis\vr-baseline\game-interp.toml').Path `
  --no-launcher --debug-port 4372 `
  --memcard-dir (Resolve-Path 'analysis\vr-baseline\saves').Path
```

Optional tuning:

| Variable | Default | Range |
| --- | --- | --- |
| `MOHU_VR_UNITS_PER_METER` | `716.4179` | 1..65536 |
| `MOHU_VR_MENU_DISTANCE` | `2.0` m | 0.25..20 m |
| `MOHU_VR_MENU_WIDTH` | `2.0` m | 0.25..10 m |

`PSX_OPENXR_ENABLE=1` selects the required OpenGL 4.6 context. Start Virtual
Desktop XR or the selected OpenXR runtime before the executable; a failed
initial system query leaves the backend disabled rather than retrying on every
guest frame.

## Build and fallback receipt

The shared `build-release/` directory was reconfigured in place with
`PSX_OPENXR=ON`. Rebuilding produced the OpenXR loader and runtime executable
successfully. Strict C compilation with `-Wall -Wextra -Werror` passed.

A 15-second hidden OpenGL run loaded PGXP slot `2` and kept the process alive
without a headset. The activation line reported:

```text
mohu-vr-diag: active bindings=17 overlay_hooks=13 read_only=0 level_offset_x=0 stereo_proof=1 eye_offset=0 render_view=1 all_spans=0 replay_driver=0 yaw_mdeg=0 pitch_mdeg=0 head_milli=0,0,0 guest_submit=1 openxr=1 units_per_meter=716.418
```

The OpenXR lifecycle then failed closed:

```text
mohu-vr-diag: OpenXR begin failed; flat native surface remains active
```

TCP `openxr_stats` reported `compiled=1`, `runtime=VirtualDesktopXR`,
`result=-35`, `stage=system`, and zero submitted layers. This is the expected
no-active-headset control, not evidence of a presented stereo pair.

## Remaining acceptance scope

The corrected lifecycle has reached the operator's headset with stable tracking,
correct scale, and no observed black flashing. Broader acceptance still needs:

1. `openxr_stats.running=1`, `submitted>0`, and `submitted_source=1`;
2. a native menu submission before the first gameplay stereo submission;
3. stable head tracking and correct upright scene presentation;
4. clear image and near-wall sweeps without floor holes or stale-eye frames;
5. interaction, HUD, controller, performance, and mission-transition coverage
   beyond this bootstrap.

The controller and HUD work remains future scope. The current acceptance is
limited to the tested gameplay scene and the corrected OpenXR presentation.

## Headless null-HMD acceptance

The shared launcher now has a SteamVR null-HMD mode, matching the reference
repository's test layout. It temporarily forces Valve's null driver, starts
SteamVR, runs the normal OpenXR path, and restores the original
`steamvr.vrsettings` after stopping its own processes:

```powershell
.\RunVR-SteamVR.bat -Headless -Seconds 10
```

The default scale profile now matches the accepted reference profile:

| Setting | Value |
| --- | --- |
| User IPD calibration | `67` mm |
| `WorldScale` | `3` |
| Base units per meter | `716.417910447761` |
| Effective units per meter | `238.805970149254` |
| Stereo shedding | off |
| Desktop VSync while XR runs | off |

The first headset run used the previous unscaled `716.418` units-per-meter
profile. It tracked correctly, but the operator reported an oversized world and
black flashing. The scale profile was corrected to the reference game's
`67 mm / WorldScale=3` setting. The remaining flashing was then reproduced
headlessly as alternating black complete pairs, not empty layers, and fixed by
using the `y=0` rollback-protected scratch buffer for both eye replays. See
[FLICKER_EVIDENCE.md](FLICKER_EVIDENCE.md).

On 2026-10-24, a 6-second null-HMD run loaded PGXP slot `2` and produced:

- startup receipt `submitted=3`, `empty=0`, `failures=0`, `tracking=1`;
- stereo proof advancing from `pairs=3` to `pairs=60` in the 2-second sample;
- `rendered=1` with `pairs=attempts` at every sample;
- zero OpenXR begin failures and zero eye-view failures;
- 120 guest `DrawOTag` submissions by the second sample;
- successful SteamVR stop and settings restoration (`forcedDriver` and
  `driver_null` absent after exit).

The retained receipt is generated as `analysis/vr-baseline/startup.json` and
`analysis/vr-baseline/openxr-smoke.json` for each local run. Null-HMD testing
verifies runtime submission and cadence. The operator confirmed that the final
scale and flicker correction looked correct in the headset.

The helper can also retain a timed sequence of compositor and application-layer
images instead of only one startup proof:

```powershell
python vr/headless_steamvr.py `
  --capture analysis/vr-baseline/flicker-check `
  --steamvr-root 'C:\Program Files (x86)\Steam\steamapps\common\SteamVR' `
  --pid <game-process-id> --samples 8 --interval 0.25 --require-clean
```

The final run retained eight nonblank samples in both layers and wrote
`clean: true` to `capture-series.json`.
