# M0 exit report: baseline and measurement contract

Date: 2026-10-30. Scope: M0 of
[PERFORMANCE_ARCHITECTURE_PLAN](PERFORMANCE_ARCHITECTURE_PLAN.md). This is a
desktop measurement record, not a headset acceptance.

## What M0 had to establish

1. Separate intervals for the guest quantum, explicit pacing and the canonical
   present; never relabel an inter-present interval as exclusive CPU.
2. Snapshot extraction/publication spans for the existing transactional pair.
3. XR wait, pose location, host preparation and submission spans.
4. Native VBlank progression, pair/snapshot age, fresh pairs, repeated images
   and missed deadlines.
5. Asynchronous GPU queries retrieved later, reported separately from CPU
   stages.
6. Reproducible reference measurements, a valid fixture strategy and a report
   that distinguishes simulation slowdown from presentation overload.

## Build, fixtures and provenance

- Production Release, `PSX_DEBUG_TOOLS=OFF`, OpenXR compiled ON but disabled
  for the desktop captures, hidden SDL window, dummy audio, diagnostic eye
  separation 8.
- Heavy reference: frozen slot-2 fixture from `analysis/fixtures/sp/openbios`,
  copied to a disposable output. Second scene: slot 5 (indoor/streaming).
- `PSX_FRAME_TRACE=1` writes `frame-trace.json`; `--runtime-perf` adds the
  opt-in cadence lines and embeds the offline report. Instrumentation overhead
  is part of these numbers.
- Source/binary/fixture hashes are in
  [m0-baseline-receipt.json](../../vr/proof/m0-baseline-receipt.json).

## Measurement model

| Field | Meaning | Do not |
|---|---|---|
| `work guest` / `sim` | Wall interval from the previous present's exit to this present's entry: the guest quantum | Call it exclusive simulation CPU |
| `pacer` | Explicit wall-clock wait inside the present body | Add it to `sim` |
| `canonical` | Canonical display selection + present span, measured at present entry to function exit | Treat it as guest rendering CPU |
| `pair_total` | One stereo pair, open to publish | Add nested `game_*` stages to it |
| `pair_age_ms` | Age of the retained published pair | Treat a stale repeat as a fresh render |
| `gpu_scene_us` / `gpu_present_us` | Asynchronous `GL_TIME_ELAPSED` results, retrieved later | Add them to any CPU stage |
| `gpu_sample_age_frames` | Host VBlank distance between the sampled frame and the retrieving present | Assume it belongs to the current frame |

Snapshot spans are the **existing pair's** baseline checkpoint
(`snapshot_extract`) and `gl_renderer_stereo_publish` (`snapshot_publish`),
not the future four-slot scene mailbox. HUD stages exist but never run in the
desktop captures (no hands/flat HUD); their absence is reported, not zero.

## Measurements

Existing baseline (three slot-2 windows, same binary): 21.95–23.41 fresh
pairs/s; native VBlank 43.90–49.48 Hz; pair p95 20.87–24.06 ms; verdict
`both_simulation_and_presentation`. Canonical-only control on the same scene:
60.00 Hz, 41.28% work interval, 58.03% pacer.

Final span captures (new instrumentation, 120 traced pairs each):

| Scene | Native VBlank | Fresh pairs | Pair p95 (no HUD) | GPU scene / present | Guest quantum | Pacer | Canonical | Verdict |
|---|---|---|---|---|---|---|---|---|
| Slot 2 | 58.80 Hz | 29.17/s | 18.588 ms | 26.957 / 2.933 ms | 967.28 ms/s | 24.87 ms/s | 4.15 ms/s | `both_simulation_and_presentation` |
| Slot 5 | 60.04 Hz | 29.99/s | 14.292 ms | 20.568 / 8.317 ms | 740.38 ms/s | 253.53 ms/s | 4.20 ms/s | `within_contract` |

Pair stage detail on slot 2: `pair_total` 17.73 ms mean,
`eye_guest_l/r` 7.84/7.72 ms, `snapshot_extract` 0.153 ms,
`snapshot_publish` 0.0009 ms, `game_traverse` 14.45 ms. Slot 5:
`pair_total` 13.48 ms, `eye_guest_l/r` 6.34/6.02 ms,
`snapshot_extract` 0.141 ms. GPU samples were retrieved 3 host frames later.

## How to read the result

- The canonical control proves native execution is real-time on this machine
  (60.00 Hz). The same scene with the per-eye replay drops to 43.9–58.8 Hz.
  That is added work from the stereo path, not a guest-instruction ceiling.
- Slot 5 shows the presentation headroom: the native clock is 60.04 Hz and the
  pair p95 is 14.29 ms. Slot 2 is over the 16.667 ms pair budget and its native
  clock falls below nominal; both classifications are reported.
- GPU work is now measured asynchronously rather than inferred from CPU
  submission. On slot 2 the GPU scene time (26.96 ms) is larger than the CPU
  pair time (17.73 ms); it is not added to any CPU stage.
- A desktop run with no XR submission cannot certify headset cadence. The
  verdict is a measurement-contract classification, not an acceptance.

## Absences and limits

- No headset/XR session: `xr_wait_frame`, `xr_locate`, `host_prep` and the XR
  submission stages are instrumented and unit-tested but absent from these
  captures. The report names them instead of treating them as zero.
- No hands/flat HUD in the desktop captures: HUD stages are absent.
- Snapshot spans describe the transactional pair's checkpoint/publish, not a
  scene mailbox.
- `sim` remains an interval; exclusive guest CPU time is not separable with the
  current scheduler and is not claimed.
- One fixture per scene; three alternating reference/candidate windows and a
  physical headset remain M6 qualification work, not M0.

## Reproduction

```powershell
cmake --build build-release --parallel 8
python vr/tools/profile_sp_production.py analysis/vr-baseline/m0-final-slot2-20261030 `
  --slot 2 --runtime-perf --eye-offset 8
python vr/tools/analyze_vr_measurement.py `
  analysis/vr-baseline/m0-final-slot2-20261030/frame-trace.json `
  --stdout analysis/vr-baseline/m0-final-slot2-20261030/stdout.log `
  --out analysis/vr-baseline/m0-final-slot2-20261030/measurement.json `
  --text analysis/vr-baseline/m0-final-slot2-20261030/measurement.txt
# repeat with --slot 5 and the slot-5 output directory
```

Evidence: the `measurement.json`/`measurement.txt` files under
`analysis/vr-baseline/m0-final-slot2-20261030` and
`analysis/vr-baseline/m0-final-slot5-20261030`, plus
[m0-baseline-receipt.json](../../vr/proof/m0-baseline-receipt.json).
