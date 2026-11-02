# VR measurement contract (M0)

Created: 2026-10-30. Scope: the offline classification used by
[PERFORMANCE_ARCHITECTURE_PLAN](PERFORMANCE_ARCHITECTURE_PLAN.md) M0. It does
not add a launcher, change guest timing or certify a headset pass.

## What the contract must answer

Two independent failures produce the same "unplayable" report:

- **Simulation slowdown** — native VBlank progression falls below real time.
  Cheaper presentation cannot fix it.
- **Presentation overload** — the native clock is real-time but a pair, HUD
  capture or XR submission misses the display period. Threading presentation
  is the lever.

`vr/tools/analyze_vr_measurement.py` classifies a run as
`simulation_slowdown`, `presentation_overload`,
`both_simulation_and_presentation` or `within_contract`, and states which
measurements were absent rather than treating them as zero cost.

## Evidence and provenance

| Input | Producer | Notes |
|---|---|---|
| `frame-trace.json` | `PSX_FRAME_TRACE=1` ring exported by the title plugin | One row per traced frame; authoritative stage times |
| `stdout.log` cadence lines | `PSX_RUNTIME_PERF_DIAG=1` | Opt-in; adds instrumentation overhead, record it |
| receipt `build`/hashes | `profile_sp_production.py` | Binary, fixture and execution-identity provenance |

`profile_sp_production.py --runtime-perf` enables the cadence lines and embeds
the report under `receipt.measurement`. Without the flag the tool is unchanged,
so the historical production floor stays comparable.

Fixture policy stays [WORKSPACE_LAYOUT](WORKSPACE_LAYOUT.md): the heavy
reference is the frozen slot-2 fixture, copied to a disposable output; a
mission-start scene is not a substitute.

## Stage semantics (do not relabel)

- `pair_total` is the authoritative pair cost. `eye_*` stages describe one
  eye; `game_traverse` contains `game_select`, and `game_world`/`game_env`/
  `game_text`/`game_icon`/`game_submit`/`game_laser` are pair-level subsets of
  the eye guest draw. **Never add nested stages.**
- `guest_sim` and the runtime `work guest=` value are the **interval between
  traced frames (or vblank samples)**, not exclusive simulation CPU time.
  In the cadence line this is also printed as `sim=`; it ends at present entry,
  so it is the guest quantum, not the whole present body.
- `pacer` is explicit wall-clock waiting and is reported separately.
- `canonical` is the canonical display selection + present span, measured from
  present entry to the present function's exit. It is outside `sim`/`work`, so
  do not subtract it from them.
- `snapshot_extract` / `snapshot_publish` are the existing transactional pair's
  baseline checkpoint and publish, not the future scene-mailbox transport.
- `xr_locate` / `host_prep` bracket `xrLocateViews` and the view/hand
  preparation after it. `xr_wait_frame`, `xr_*`, `pose_age` and `hud_*` keep
  their existing meanings.
- `hud_capture` is a CPU transaction; it is added to `pair_total` only because
  the trace shows it executing on the frame's own thread. If it never ran
  (`hud_capture_included: false`) its cost is unmeasured, not zero.
- `xr_*` stages are CPU waits/submissions, never GPU execution time.
- `xr_display_delta_us / target_period_us - 1` is the missed-period count; it
  requires an XR submission and a known display period.

## Async GPU work

The GL renderer's `GL_TIME_ELAPSED` sampling ring is enabled for traced frames
(and for diagnostics builds). Results are retrieved several presents later into
`gpu_scene_us`, `gpu_present_us` and `gpu_sample_age_frames`. They describe a
past frame's GPU execution, never the current frame's CPU work, and are never
added to `pair_total` or any other CPU stage. A missing sample is reported as
unmeasured, not zero. `pair_total` remains CPU submission time.

## Absent spans

The report lists `scope.absent_stages` and a finding instead of treating an
unexercised stage as zero. A stage that ran below the 1 us resolution may also
appear there; snapshot publish is rounded up to 1 us when its tick delta is
nonzero so a completed publish is not misreported as absent.

## Baseline capture

```powershell
python vr/tools/profile_sp_production.py analysis/vr-baseline/m0-$stamp `
  --slot 2 --runtime-perf --eye-offset 8
python vr/tools/analyze_vr_measurement.py `
  analysis/vr-baseline/m0-$stamp/frame-trace.json `
  --stdout analysis/vr-baseline/m0-$stamp/stdout.log `
  --out analysis/vr-baseline/m0-$stamp/measurement.json `
  --text analysis/vr-baseline/m0-$stamp/measurement.txt
```

Run unsandboxed, one game at a time. Three alternating reference/candidate
windows and a second scene remain required for any gain claim; one window is a
control, not a qualification.

## Limits

- Desktop/no-XR classification cannot certify headset cadence.
- A null-HMD run does not execute hand surfaces or laser work.
- `--eye-offset 8` is a diagnostic separation, not a physical IPD.
- The report never converts stage means into a predicted FPS.
