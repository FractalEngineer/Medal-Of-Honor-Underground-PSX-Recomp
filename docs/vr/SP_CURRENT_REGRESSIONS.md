# Current SP regression cases

Recorded 2026-10-29 from the operator's report: “save 1 has missing level
rendering again and save 2 has severe performance issues.” **These are open
issues, not reproduced or diagnosed by this documentation update.** No FPS
measurement, exact head pose, runtime/mode, trigger or common cause was supplied.

## Case identity — do not mix up the slot numbers

| Plan ID | Personal source | Symptom | Frozen reproduction input |
|---|---|---|---|
| G5 — internal slot 1 | `saves/openbios/state_8001F844_slot01.pst` and matching thumbnail | Level rendering is missing again | `analysis/fixtures/sp/openbios/state_8001F844_slot01.pst` / `.thumb` |
| G6 — internal slot 2 | `saves/openbios/state_8001F844_slot02.pst` and matching thumbnail | Severe performance problems; FPS not yet measured | `analysis/fixtures/sp/openbios/state_8001F844_slot02.pst` / `.thumb` |

**Numbering is explicit:** the operator confirmed that “slots” have meant the
internal/file/tool indices **since the beginning**. Slot 1 means `slot01` /
`--slot 1`; slot 2 means `slot02` / `--slot 2`. Do not reinterpret these through
the menu's display numbering or shift them to 0/1. Historical slot references
retain their original internal indices; do not renumber existing evidence.

Both sources are the operator's current shared Flat/VR **SP** saves. They are
not MP calibration slots 1/2 and not the historical SP slot-5 damaged-disc
case. The existing SP fixture library now preserves these two reported cases
alongside slots 3/4/5; this adds no alternate personal save store or executable.
Copy a selected frozen input into a unique disposable test output before launch.

Receipt: [reported cases and observed file identities](../../vr/proof/sp-current-regressions-receipt.json).
It records the files present at documentation time. The current disk binary
hash does not prove which exact executable/runtime was used for the report.
Never edit personal states or rewrite old receipts to manufacture that proof.

## Priority and the next concrete actions

**Latest operator order: G7 full MP-to-SP weapon parity FIRST**, including
petrol bomb/Panzerfaust fixed-aim reports. See [SP_WEAPON_PARITY](SP_WEAPON_PARITY.md).
G5/G6 stay open; after G7, G5 correctness precedes G6 performance measurement.
This overrides this report's previous G5-first order. P3b remains completed for
its original slot-5 fixture, and P3c2–P3c6
remain the implementation runbook once the new cases are understood. No new
general physical headset smoke is needed now.

The actions below are the G5/G6 continuation **after G7**, except a specific
rendering prerequisite needed to validate one SP weapon case. Do not use such a
prerequisite to start a broad performance/renderer campaign before weapon parity.

1. **G5b — reproduce/classify slot 1.** Use copied SP slot 1 on the current clean
   image and standard build. Compare native Flat against stereo replay under
   matching camera/scene conditions. Record exact build/config/fixture/pose,
   capture both eyes, and inspect level selection, native draw/packet activity,
   streaming completion and render failures. A successful load, nonblank enemy,
   growing pair counter or `complete=true` from a probe does **not** prove that
   the world is present. Require actual world geometry/rendering evidence.
2. If Flat also loses the level, follow the native scene/load path indicated by
   that capture. If Flat renders it and stereo does not, follow the measured
   per-eye selection/projection/replay path. Only vary one relevant factor at a
   time. Do not assume this is another damaged disc, narrow the visible FOV,
   disable guards, or rerun every old clipping/culling experiment. The old G2
   repair remains evidence for its old fixture only.
3. **G5c — fix the demonstrated cause** and verify the same copied slot/head
   pose recovers world geometry in Flat and both eyes, without rollback, weapon,
   laser, pause/load, music or streaming regressions. If the symptom is not
   reproduced, retain captures and the exact missing reproduction condition;
   do not mark it fixed or tune rendering blindly.
4. **G6b — baseline copied slot 2.** First verify that its world is actually
   rendering. Collect production/debug-OFF complete pair cost, fresh pairs/s,
   guest cadence and CPU/GPU stages. Then attribute the dominant work in a
   separate bounded diagnostic window if needed. Use actual HUD/weapon/laser/XR
   execution when claiming full-path cost; desktop flags alone are insufficient.
   Severe performance is a user observation until these numbers exist.
5. **G6c — choose the implementation from this scene.** If packet/preflight
   still dominates, continue P3c2–P3c6 using these additional regression cases.
   If another operation dominates, record that evidence and update the single
   next target before implementing it. Keep the old rejected compiler tuning
   closed. Full budget and independent fresh-view cadence remain separate
   requirements: 16.67 ms / 60 fresh frames/s minimum, 11.11 ms / 90 preferred.

G5/G6 are not automatically one bug. Preserve separate failure/results records
unless measurements establish a shared cause. Do not start a new renderer,
framework update or MP campaign to avoid the bounded comparisons above.

## Existing tool use and limits

Use `probe_sp_issues.py --slot 1` for slot 1's diagnostic comparison: its
`--flat --audio` path is the native control; `--audio --hud --laser` is desktop
stereo with synthetic controls. Prepare a new output directory for each and
disable weapon trace logging as in the current performance runbook. These TCP
probes require a temporary debug-ON build; they are not production timings.
Preserve a matching pose and capture conditions rather than comparing arbitrary
screenshots taken at unrelated guest times. A desktop failure to reproduce
does not establish physical-HMD acceptance.

Use `profile_sp_production.py --slot 2` for slot 2's production desktop baseline after
restoring debug OFF and checking the world. It copies the frozen SP input, not
the operator's live save. It does not measure live hand surfaces or full XR.
Never mix its cost with debug/VERIFY timings as an optimization comparison.

All actual game launches remain outside the sandbox; one game at a time, two
compile jobs, and close only owned children. Preserve personal saves/settings
and the frozen cases. Restore production with debug/native timers/IPO OFF after
diagnostics. Follow [workspace rules](WORKSPACE_LAYOUT.md) and the
[performance runbook](PERFORMANCE_NEXT_STEPS.md) for ownership, proof and cleanup.
