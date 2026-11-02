> Archived evidence only. Use [HANDOFF](../HANDOFF.md), [VR_PLAN](../VR_PLAN.md) and the [current runbook](../PERFORMANCE_NEXT_STEPS.md). Old NEXT pointers, save/build paths and proposed steps below are historical.

# SP petrol visibility and VR frame-rate blocker

Historical 2026-10-28 evidence. The operator has since accepted clean-image
world/music, SP pause and Sten headset smoke; performance remains open. Current
execution order and exact commands are in [HANDOFF.md](../HANDOFF.md) and
[PERFORMANCE_NEXT_STEPS.md](../PERFORMANCE_NEXT_STEPS.md). Old “next” wording below
must not restart the image/weapon/pause work or delay native replay implementation.

Date: 2026-10-28. The operator reports accurate weapon tracking and laser aim,
an invisible petrol bomb after one weapon switch in SP slot 3, and unacceptable
performance around 30 FPS. **60 fresh VR frames/s is the minimum target; 90 is
preferred. Performance takes priority over R6 combat expansion. MP remains a
calibration fixture only.** This report does not close whole-campaign or
all-weapon physical acceptance.

## Petrol bomb: reproduced and repaired

Use the compatible copied SP slot 3 under `analysis/vr-baseline/saves`, load it,
then switch once with native Circle input. Do not use root MP slot 3 or edit
inventory to reproduce this failure.

SP ID 15 has the expected magic `001C0007`, 397 faces, 28 nodes and the same
196 vertex XYZ coordinates as the existing MP calibration asset. The fourth
halfword of every vertex is **128 in SP versus 129 in MP**. The full geometry
FNV is therefore **408599AC in SP versus 7CA0DBEC in MP**. The old SP guard
accepted only the MP hash and rejected the native model before its tracked
projection. The captured stereo image reproduced the missing bottle.

`mohu_vr_weapon_sp_geometry_valid` now accepts this exact SP hash for ID 15
in addition to the existing profile identity. It retains the complete metadata
and geometry checks. No broad masking of unknown vertex flags, source-asset
mutation, recalibration, new arm topology or relaxed MP identity was needed.

`probe_sp_petrol.py` checks native P38 -> petrol switching, fresh projection,
both-eye counts **99 visible bottle vertices / 97 masked arm vertices**, no new
model-guard failures and zero rollback mismatches. Before/after stereo captures
were visually inspected. P38 fire/reload/load regression also passes with
96 gun / 142 arm vertices. These are desktop synthetic-hand checks; SP petrol
throw aiming and NPC damage are not newly claimed.

## Launcher: production config is now the default

The operator session log confirms `RunVR-VDXR.bat` selected
`analysis/vr-baseline/game-interp.toml`. The launcher automatically preferred
that diagnostic file whenever it existed, disabling the native overlay cache.
Default launch now selects `game.toml`; interpreter diagnostics require explicit
`-GameConfig`. The existing hand HUD, laser and weapon defaults remain enabled.

Matched production/debug-OFF desktop slot-3 window, 600 guest VBlanks, no HUD,
no XR or live hand, same pre-fix executable:

| Measurement | Interpreter | Native production config |
| --- | ---: | ---: |
| Wall time | 10,248.981 ms | 9,999.539 ms |
| Guest work | 9,771.330 ms | 8,163.857 ms |
| Quiet fresh stereo pairs/s | 28.438 | 30.000 |
| Native overlay calls in window | 0 | 2,813,918 |

Native config lowers measured guest work about 16.5%; it does **not** deliver
60 fresh VR frames/s. Do not describe this fix as solving the performance target.

## Profile findings and constraints

The current SP path calls `run_stereo_proof` at native frame-driver entry
`8006D65C`, and the measured production fixture submits one stereo pair per
two guest VBlanks. Declaring `frame.period_vblanks=1` is budget metadata; it does
not create additional render calls. The previous game's source also identifies
its draw loop as 30 Hz (`MOH_FLIP_PERIOD_VBLANKS=2`). Reusing that architecture
does not itself satisfy this new 60/90 target.

The reference's existing frame-trace stage brackets are now also used around
Underground SP traversal, exact laser, visibility selection and final OT submit.
`probe_sp_performance.py` supplies copied-save, synthetic-hand, no-VERIFY quiet
windows and can use the restore-protected SteamVR null HMD. Debug samples locate
cost; they are not production headset FPS:

- 1080p desktop with hand: about 19.7 ms/pair in the debug build.
- 1080p null HMD with HUD: about 36.4 ms/pair; HUD capture adds 4.87 ms
  (1.39 ms draw/rollback and 3.48 ms readback), separate from the eye pair.
- Clean null-HMD no-HUD/laser sample separates traversal, submission and laser.
  It confirms scene replay dominates. Compare its own receipt, not an estimate
  made by subtracting unmatched samples.
- Production/debug-OFF native-config null-HMD HUD sample: **19.20 fresh pairs/s**,
  mean pair **33.54 ms**, traversal **29.68 ms**, final submit **1.72 ms**,
  selection **0.094 ms**; HUD capture **4.50 ms** separately. The null HMD has no
  injected hand in this control. The actual runtime reports native overlay
  calls, zero XR/eye failures and no VERIFY. This confirms that simply disabling
  debug tools does not meet the target. It is not a physical headset measurement.
- Final rebuilt production control repeats the failure to meet budget:
  **18.92 fresh pairs/s**, pair **32.79 ms**, traversal **28.99 ms**, HUD capture
  **6.48 ms** (5.17 ms readback). It exits through the launcher's bounded stop
  with settings/saves unchanged, 120 valid published trace records and no
  remaining game process. This is the current debug-OFF binary in the receipt.
  HUD readback variability reinforces that one A/B sample is not a stable gain.
- Most time is guest scene traversal; CPU/GPU resolution knobs alone are not a
  measured solution. Do not remove world geometry, change projection/FOV or
  disable required HUD/weapon behavior to declare a pass.

Production/debug-OFF trace export is available with `PSX_FRAME_TRACE=1` and
`MOHU_VR_FRAME_TRACE_FILE=<absolute-file>`. It exports the newest 120 records
once after 180 pairs, outside the eye callback. With no opt-in it does no file
IO. The exported records precede the file write. `--production-null` uses this
without TCP or debug instrumentation; no injected hands means it measures HUD
capture cost, not physical hand-surface acceptance.

A pointer-cache experiment for generic named counters was measured on isolated
framework branch `vr/perf-counter-lookup` at the same base. One sample changed
pair mean from 33.54 to 31.03 ms, while HUD readback rose and fresh cadence only
reached 20.04/s. That single comparison does not establish a stable production
improvement or solve the budget. The experiment was removed and the original
framework rebuilt; **no framework source, commit or game pin change is retained**.
The empty experiment branch remains at `555e1eab`; master/shared-development
were untouched. Do not spend the next session tuning counter hashes as if that
closed the main replay cost, or claim reference counters were a proven root cause.

Reference audit: `docs/reverse/VR_SLOT2_PERFORMANCE.md` also attributes its
27.2 ms diagnostic pair to 24.5 ms traversal. `VR_OPTIMIZATION_STATUS.md`'s earlier
interpreter diagnosis must not be copied as this session's conclusion: Underground
production is demonstrably executing native overlays. Reference `VR_PHASE9_STATUS.md`
retracts an early 90-Hz feasibility claim. Do not use its original estimate as
proof that a one-traversal/two-eye rewrite is necessary; profile native hot work
before choosing that larger design.

## Runtime cleanup correction

One debug null-HMD probe was rejected: the harness's 15-second parent timeout
interrupted launcher cleanup. Do not promote `null-no-hud` as accepted evidence.
The synthetic driver settings were removed using the last saved physical
configuration for the affected keys, preserving current unrelated settings.
The exact immediately preceding file bytes were unavailable, so this recovery
is not claimed as a byte-identical restore. Subsequent `null-no-hud-clean`
completed with source saves and preferences unchanged and no game process.

The launcher now persists `steamvr.vrsettings.pre-headless` **before** modifying
settings, and the diagnostic harness allows 45 seconds for the launcher's
SteamVR stop/restore path. Keep that backup if any future process is interrupted.

## Required next steps; do not repeat discovery

The subsequent [comparative audit](SP_PERFORMANCE_COMPARISON.md) refines steps
1–3: current controlled baselines in both titles (P0b), native child-stage/host
attribution (P3b), then repeated one-change A/B controls (P3c). It confirms shared
framework/defaults and identifies a heavier Underground primitive workload,
HUD synchronization and extra guards as measured costs or candidates, with
explicit limitations. It does not establish a new performance fix.

1. Use production `game.toml`, debug OFF, VERIFY OFF. Keep current weapon/laser
   defaults and native HUD. Measure world-pair cadence separately from guest
   VBlanks and compositor repeat/reprojection rate. 60 requires <=16.67 ms;
   90 requires <=11.11 ms at the complete application-frame deadline.
2. Use existing frame traces to reduce scene replay cost first. The known SP
   traversal is `80053BB4`, final DrawOTag `80018B48`, visibility transformer
   `80099960`. Port reference timing/optimization work where applicable; verify
   Underground semantics before skipping native work. Do not re-map all weapons.
3. Add a safe render-only cadence independent of the 30 Hz native draw/update
   loop. Reuse framework rollback, fresh OpenXR pose/input, paired publication
   and native menu handling. Preserve native simulation, audio, movement speed,
   shot cadence, collision/damage and save compatibility. Do not use turbo or
   set native VBlank to 90 as a frame-rate fix. Repeating a stale pair does not
   close fresh-view acceptance. Any generic framework work belongs on shared
   development, never master, and requires both-game validation before pinning.
4. Desktop/null-HMD controls must cover frame pacing, steady fresh pair IDs,
   zero rollback/eye failures, weapon/laser pose freshness, pause/resume,
   load/recovery, and unchanged guest timing. Restore a production debug-OFF
   binary after diagnostics.
5. Only after those controls, ask for one bounded SP headset performance check
   at the chosen Virtual Desktop refresh rate. Record actual application frame
   times, fresh pair cadence, repeat/reprojection and CPU/GPU limits. Minimum
   steady 60; preferred 90. Then resume R6 NPC damage and broader SP families.

Raw evidence is under `analysis/vr-baseline/operator-perf-20261028/`. The compact
[receipt](../../../vr/proof/sp-performance-petrol-receipt.json) preserves hashes and
the accepted/failed scopes. No physical headset was started by these probes.
