# Current SP regression cases

Recorded 2026-10-29 from the operator's report: “save 1 has missing level
rendering again and save 2 has severe performance issues.” **The original report supplied no numeric FPS or exact trigger.** The new
desktop reproduction/repair and production baseline below supersede that
initial lack of diagnosis; physical acceptance remains separate.

## Case identity — do not mix up the slot numbers

| Plan ID | Personal source | Symptom | Frozen reproduction input |
|---|---|---|---|
| G5 — internal slot 1 | `saves/openbios/state_8001F844_slot01.pst` and matching thumbnail | Level rendering is missing again | `analysis/fixtures/sp/openbios/state_8001F844_slot01.pst` / `.thumb` |
| G6 — internal slot 2 | `saves/openbios/state_8001F844_slot02.pst` and matching thumbnail | Severe performance; current production desktop baseline 25.011 pairs/s | `analysis/fixtures/sp/openbios/state_8001F844_slot02.pst` / `.thumb` |

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

## Current result and priority

The owner requested a quick bounded weapon fix, then immediate return to
missing-world and performance. Both live petrol branches now use existing MP
values unchanged. Remaining G7 fixtures/physical gates do not gate G6.

**G5b is complete; the visibility defect is repaired in code.** Native Flat
renders the street while the old stereo path shows large black/missing sections.
A matched selector comparison found 116 leaves admitted from root `8011D0D8`
where native selected zero. The native selector compares MAC3 to the active
camera view descriptor+40, a 16.16 far plane of 10,000 units in this fixture.
The VR replacement omitted this test. Out-of-range primitives then overwrite
nearer world geometry. Retaining the native far plane restores the street in
both eyes, with per-eye primitives about 2,448 -> 1,513 in matched diagnostic
captures. A 90-degree head view at 1080p also passes with actual geometry and
268 VERIFY checks/zero mismatches. Angular FOV/PVS/shared math remain unchanged;
this is not a permanent native-selector fallback or another disc repair.

Pause/Continue, refusal recovery and real state reload recover the street.
One HUD/pause stress run still records a VRAM-only restoration mismatch (CPU
state hash equal); its 818 checks/one mismatch are retained as a failed control.
Another fixed capture has 563 checks/zero mismatches. G5c's broader restoration
acceptance remains open; do not claim the intermittent failure fixed.

**G6b scoped baseline is complete.** Slot 2's street/tank scene is captured in
both eyes, with 257 VERIFY checks/zero mismatches in its diagnostic run. Current
Release/debug-OFF 1080p desktop production measures 20.139 ms/pair, 16.710 ms
traversal, 1.028 ms submit and 0.066 ms full selector, at 25.011 fresh pairs/s.
XR/hand HUD/laser work is not included. Native traversal remains dominant;
continue G6c/P3c2–P3c6 preflight implementation through its real caller contract,
then the independent fresh-view cadence work. No 60/90 FPS or paired speedup is
claimed from these runs. [Compact receipt](../../vr/proof/sp-far-depth-world-receipt.json).

The checklist below retains the reproduction/qualification contract. Completed
G5b/G6b evidence need not be captured again unchanged.

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
