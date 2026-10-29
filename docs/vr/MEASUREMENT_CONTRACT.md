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
- `pacer` is explicit wall-clock waiting and is reported separately.
- `hud_capture` is a CPU transaction; it is added to `pair_total` only because
  the trace shows it executing on the frame's own thread. If it never ran
  (`hud_capture_included: false`) its cost is unmeasured, not zero.
- `xr_*` stages are CPU waits/submissions, never GPU execution time.
- `xr_display_delta_us / target_period_us - 1` is the missed-period count; it
  requires an XR submission and a known display period.

## Async GPU work

The plan requires asynchronous GPU queries retrieved later. Until such a query
exists, the report must not present `pair_total` as GPU completion time. A
future GPU stage is reported as its own field and never added to overlapping
CPU stages.

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
