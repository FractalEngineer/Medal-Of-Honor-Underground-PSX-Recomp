# Underground VR execution handoff

Updated 2026-10-29 after the operator's weapon-priority instruction. **NEXT: G7a–G7f,
complete all existing MP weapon calibrations and tracked weapon-family control
in SP first.** Petrol bomb and Panzerfaust appear to retain fixed/native aiming;
this is an open report, not a repair. Start with [SP_WEAPON_PARITY](SP_WEAPON_PARITY.md).
Then resume G5 slot-1 missing world, G6 slot-2 performance and measured optimization.
P3b remains complete for its old fixture. Follow
[PERFORMANCE_NEXT_STEPS.md](PERFORMANCE_NEXT_STEPS.md) after G7 and G5/G6. Do not resume a
NEXT pointer from an archived report. [VR_PLAN.md](VR_PLAN.md) owns status;
[IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) owns history.

**Workspace cleanup checkpoint:** read [WORKSPACE_LAYOUT](WORKSPACE_LAYOUT.md)
before launching or creating a build. Both normal launchers now use the same
standard `build-release` executable and absolute root `saves/`. Current operator
VR slots 0–6/cards are there; all original Flat/VR files and retired executables
are preserved in `analysis/archive/workspace-cleanup-20261029`. No performance
implementation was done during cleanup. Historical paths below remain evidence.

## 1. Accepted checkpoint — do not reopen without a new regression

The operator reports: “smoke test passed, looking good no more missing level
and music,” then “pause menu is ok, sten is ok, performance still meh.” Record
these as human headset observations, not instrumented timing or all-ID tests.

| Scope | Current acceptance |
|---|---|
| Clean image activation / existing launchers | Complete; operator launched it personally |
| Historical SP slot-5 loading failure | Resolved for that case; desktop proof plus earlier operator headset pass |
| Current personal SP slot 1 / file slot01 visibility — G5 | OPEN: missing level rendering again; not yet reproduced/diagnosed |
| Current personal SP slot 2 / file slot02 performance — G6 | OPEN: severe performance; no measured FPS or attribution for this case yet |
| Stuck repeating music | Resolved; stream/refill proof plus operator headset pass |
| SP Sten hand aiming | Native construction/motion/loss controls pass; operator headset pass |
| SP pause menu | Native desktop/null-HMD controls pass; operator now confirms headset behavior |
| SP petrol model / laser | Earlier model/ray checks pass; they do not close the new fixed-aim throw report |
| Petrol bomb / Panzerfaust SP aim | OPEN: apparent fixed/native direction; no new trace/root cause or fix yet |
| Full MP-to-SP weapon calibration/control parity — G7 | OPEN, FIRST: all 13 source profiles and SP shot-family/final-origin behavior |
| Performance | Still unsatisfactory; 60 fresh application frames/s minimum, 90 preferred; OPEN |
| All-SP-ID live NPC damage/isolation | Not implied by smoke or G7 direction checks; R6 retains its separate scope |

Human report and its limits:
[clean-disc-headset-smoke-receipt.json](../../vr/proof/clean-disc-headset-smoke-receipt.json).
Do not ask for another general headset smoke now. Finish independent desktop
work; request a focused physical check only when its candidate is ready.

The latest report reopens overall world-visibility acceptance. Preserve the
historical slot-5/music fix without assuming it explains slot 1. Two reported
cases and their exact current source/fixture hashes are in the
[new receipt](../../vr/proof/sp-current-regressions-receipt.json). No new game
launch or performance measurement was done while recording this report.

Latest operator steering supersedes that report's old execution order: **G7
weapon parity first**, including petrol/grenade throw and Panzerfaust final
origin/initial direction. Existing MP poses/profiles are the source; do not
recalibrate them or port the HUD again. A model and laser following the hand
does not prove the native projectile follows it. This turn is document/push only.

## 2. Active checkout, disc and launch

- Repository: `C:/Users/titan/Desktop/Github_Projects/Mine/Medal-Of-Honor-Underground-PSX-Recomp`.
  Game branch `feature/vr-port`. Use the existing checkout/build; no new task,
  worktree, dependency update or code regeneration is needed for orientation.
- Reference, read first only where relevant:
  `C:/Users/titan/Desktop/Github_Projects/Mine/Medal-Of-Honor-PSX-Recomp`.
  [REFERENCE_REUSE_AUDIT.md](REFERENCE_REUSE_AUDIT.md) lists existing ports.
- Framework remains pinned to `555e1eabccc59b9b6ff0d9fca48aca783513dc86` in both
  games. No framework changes in this checkpoint. Generic work belongs on
  `vr/shared-development`/feature branches, never master; both affected games
  must pass before changing pins. [Upstream tracker](FRAMEWORK_UPSTREAM_TRACKER.md).
- Production executable: `build-release/Medal_of_Honor_Underground_Recompiled.exe`.
  Release, PGXP, OpenXR, diagnostics plugin ON, TCP debug tools OFF.
- Active image: `Medal of Honor - Underground/Medal of Honor - Underground (USA).cue`.
  BIN SHA-256 `2aed19d588f69274f8be70001eaa9b6400240b62088da72bace815ab902d56ed`.
  The old image and duplicate were deleted by the operator. Do not search for them.
- Source/staged `game.toml`, preparation/catalog digests, launcher selection and
  disc cache were updated. TOC fingerprint remains `5abe13ac...`, recomputed
  from unchanged layout; data hashes differ. Executable/SP/MP overlay payloads
  are identical, so existing hook mappings and native caches remain applicable.
- `mohu.repair.music-sector` is historical, default-OFF and locally disabled.
  **Never enable it or add the clean image to its target.** Clean data needs
  no synthesized header/silence. [Disc report](DISC_IMAGE_COMPARISON.md).
- Operator uses existing `RunVR-VDXR.bat` (Virtual Desktop); Oculus/SteamVR
  variants also remain. Do not create `LaunchVR.bat` or another wrapper.
  Defaults: normal boot, native HUD, laser, tracked gun-only weapons, movement.
  The laser follows hand-fixed bullet aim; native recoil remains visual.

## 3. Fixtures, ownership and mandatory boundaries

- **Every game launch is outside the sandbox**, including hidden, software,
  desktop and null-HMD probes. In execution tools use `require_escalated`.
- One game at a time, two compile jobs. Inspect existing processes; never kill
  the operator's game/runtime. Close/terminate only a child this session owns.
- Work solo. Read applicable `AGENTS.md`; new HLE must follow
  `psxrecomp/docs/HLE_EXECUTION.md`. Do not create a local Beads DB if the
  configured central DB/path is unavailable; record that fact once.
- Frozen SP fixtures: `analysis/fixtures/sp/openbios/`:
  new slot01 (missing world), new slot02 (severe performance),
  slot03 (P38/petrol), slot04 (Sten), slot05 (indoor/old world-loss
  repro). Frozen MP calibration inputs: `analysis/fixtures/mp/openbios/`.
  Root `saves/` is the personal shared Flat/VR store; never use it as an
  implicit test fixture. Probes must copy fixtures into disposable outputs.
  Headless RunVR requires an explicit `-MemcardDirectory`.
- Existing probes copy fixtures to a unique analysis directory. Preserve source
  states/thumbnails, personal saves, keybinds/settings and XR runtime settings.
  Never edit health/ammo/inventory, fabricate compatible saves or patch headers.
- A real execution/layout-cookie mismatch stops dependent gameplay tests.
  Inspect diagnostics and preserve the source. Do not remove identity guards,
  create another build merely to hide the mismatch, or claim a failed load passed.
- SP is the alpha target. MP is only a quick weapon calibration fixture.
  Do not implement MP features or make another MP matrix gate the SP alpha.

## 4. The next implementation, with evidence boundaries

Read the weapon parity contract and execute its first unchecked step. In brief:

**The next implementation agent starts with [G7](SP_WEAPON_PARITY.md).** Inventory
which MP calibration/render/shot code SP already consumes, then fill verified
SP family/adaptor gaps. Prioritize petrol/grenade final throw writers and the
Panzerfaust rocket path while completing all 13-ID SP coverage. Reuse authored
grip/scale/orientation, complete gun-only masks and the fixed hand basis; no new
calibration editor, MP campaign or duplicated profile table. Preserve current
P38/Sten behavior, native ballistics/timing and loss/load/rollback guards.

G7a–G7f define inventory, shared/firearm parity, thrown parity, rocket parity,
all-ID SP controls and honest acceptance/production restore. Use a valid visible
SP fixture for each available weapon. If G5 blocks one control, record/fix that
specific prerequisite or continue independent cases; do not replace the overall
weapon-first order with a broad rendering/performance detour.

**After G7, resume [G5/G6](SP_CURRENT_REGRESSIONS.md).** Compare copied slot 1 in native Flat
and stereo; require actual world geometry evidence, not just successful load or
pair counters. Then baseline copied slot 2 with its world present, identify the
dominant cost, and confirm/update the implementation target. Do not assume a
shared cause, damaged image or a culling-angle fix. Preserve both personal saves.

The operator uses internal/file/tool slot indices throughout. Use
`probe_sp_issues.py --slot 1` for G5 and production `--slot 2` for G6.
Do not shift these reports to 0/1 using menu display labels or renumber history.

After weapon parity and that triage, follow [runbook section 3.1](PERFORMANCE_NEXT_STEPS.md#31-ordered-execution-checklist--start-at-p3c2)
if preflight remains the measured target. Read the
complete `80011424` helper, caller and dispatch entries; begin the standalone
caller-contract harness and proceed into implementation. Capture alone is not
the requested deliverable. P3c2–P3c6 need no physical headset.

1. Preserve the accepted clean-image checkpoint. The current clean production
   baseline and completed P3b evidence are in [NATIVE_REPLAY_PROFILE.md](NATIVE_REPLAY_PROFILE.md).
   Do not restart attribution or compiler sweeps. For a genuinely new candidate,
   obtain one current clean
   production baseline with the existing tool. Do not rerun disc audits, all-ID
   matrices or old render-clip experiments. No physical HMD launch.
2. **P3b is complete:** exclusive packet/preflight/GPU-command segments cost
   5.729/3.805/1.143 ms per pair; full visibility hook only 0.068 ms. Loaded
   native DLL samples resolve against their own PE tables. Timings are
   diagnostic; raw host top-400 covers 1,881/3,085 samples. See the report for
   canonical/eye separation, resolved callers and limitations.
3. **P3c:** target `80011424` (668 bytes, FNV `C38CDCC1`), called by the packet
   builder at `80011000`, return `80011008`. Read the report's exact five-step
   implementation contract first. Capture its custom register/scratchpad/GTE/
   PGXP inputs/results before replacement; `$v0` alone is insufficient. Start
   with the standalone caller harness, then obtain valid per-execution game
   fixtures for integration; never bypass existing state identity guards.
   Optimize through the real caller
   interface, reusing the reference/shared services. Verify unchanged image/FOV,
   aiming, audio/simulation timing, pause/loss/load and original save contracts.
   Run three alternating production A/Bs before promoting an improvement.
4. **Budget decision after the preflight result:** if still too expensive,
   continue the larger packet builder P3d through the same qualification gates.
   P3e HUD work is conditional on a measured remaining stall. Read the existing
   dirty/change detection and shared capture first; do not port checkpoint or
   paired readback again. Use the [decision table](PERFORMANCE_NEXT_STEPS.md#33-what-follows-preflight--choose-by-measured-full-path-budget).
5. **P4/P5:** remove the native ~30-Hz fresh-view ceiling safely, retaining native
   simulation/audio timing. A cheaper pair alone does not produce 60/90 fresh
   views. No turbo, VBlank-rate change or compositor-repeat substitution.
6. Only then request a bounded SP headset performance check (P6). The last smoke
   accepted functionality; it did not certify FPS or every gameplay scope.

| Ordered task | Done only when |
|---|---|
| P3c2 — caller contract/fixtures | Real input/output cases, supported entry/resume contract and valid harness/fixture strategy exist |
| P3c3 — implementation | A build-selected faster helper exists, original reference runs, paired caller-result tests pass |
| P3c4 — correctness | Relevant world/FOV/PGXP/weapon/laser/timing and pause/loss/refusal/load controls pass separately from timing |
| P3c5 — production desktop A/B | Three alternating windows plus the second workload show a useful consistent gain, with exact binary/fixture/flags |
| P3c6 — full path/decision | Actual HUD/weapon/laser/XR work is measured, failures retained, candidate qualified or explicitly rejected; a desktop gain is insufficient |

**Fixture/tool trap:** a new execution family changes identity. Current probes
assume frozen SP fixtures and `build-release`; the old sibling executable-name
and profiler `--exe` launch overrides were removed during cleanup. Before cross-profile game timing,
extend the existing probes to select separate valid fixture roots and complete
build/assets/config/cache directories. Those selectors do not exist yet. See
[section 3.2](PERFORMANCE_NEXT_STEPS.md#32-execution-identity-and-fixture-handling--resolve-before-integration).
Never fake compatible states, overwrite shared fixtures, copy a candidate into
another profile's cache, or count a refused load as a pass. Continue independent
harness/implementation work if an integration fixture is unavailable.

**Larger fallback:** cached scene geometry may support fresh-pose rendering if
targeted replay work cannot meet the budget/cadence. It is a conditional design
decision, not the next task or a required alpha feature. Preserve the replay
reference and validate moving geometry/weapon/controller poses and FOV before
claiming success. Record one exact next task after each retain/reject/defer
decision; do not start helper, HUD, scheduler and renderer redesign in parallel.

Known measurements are leads, not a new matched-HMD benchmark:

- Older desktop A/B: pair work 17.668 → 17.608 ms, cadence 28.378 → 29.768/s.
  `MOHU_VR_SKIP_NATIVE_WORLD_COPY=1` skips only an unused canonical world draw.
  It passes Sten/pause/refusal/reload/hitch controls but stays OFF; it does not
  materially reduce stereo replay cost or close 60/90 acceptance.
- Traversal about 15.65 ms; submit 0.65 ms; tree collection 0.056 ms per pair.
  720p/native resolution still about 17.96/17.76 ms. Do not start by reducing
  resolution, caching tree collection or retuning frustum bounds.
- These desktop records have no XR copy/hand-HUD capture cost; full XR/HUD is
  additional. Use current clean image for new A/Bs. Historical two-title scenes
  differ; 65–69% more primitives is workload attribution, not a speed ratio.
- Clean-default slot-5 smoke: 17.391-ms desktop pair work, no HMD cost included.
  No minimum/steady 60-Hz or 90-Hz pass exists.
- Three inlining variants are rejected/removed. Shared IPO reduces desktop
  pair work about 4.3%, but one unchanged-binary null-HMD run regresses badly.
  Full-path gain is unqualified; **PSX_RUNTIME_IPO remains OFF**. Do not average
  away that run or repeat tuning sweeps. Native timers are diagnostic-only;
  restore `MOHU_VR_NATIVE_PROFILE=OFF` alongside debug OFF after their use.

## 5. Closed investigations and separate open scopes

Do not reopen these without new contrary evidence:

- Historical slot-5 missing world/music: damaged image stalled at raw sector 9469 and
  blocked a native arena load. Replacement passes all 318,028 sector checks;
  operator confirms resolution. No rendering/fog/CD timing bypass is needed.
  That acceptance does not close new personal slot-1 case G5; its cause is unknown.
- Queue terminator is `800B8458 = 800B74B8 + 1000*4`, not `800C8458` (signed
  displacement). Corrected/asserted; this alone was not the world fix.
- Common SP shot seam: `80048604 → 80076C28`, RA `8004860C`; exact firearm
  ID/type guard. Native SP motion stores `800793E4/80079400/8007941C` differ
  from MP's. Do not rediscover the Sten/P38 basis or move aim with recoil.
- Entry-hook config is now **25 entries / 11 instruction sites**. The extra
  arena-wrapper entry supports the default-OFF native-copy candidate. No
  temporary clipping/triangle trace hook remains; generated game C is unchanged.
- SP petrol uses an exact known metadata variant, 99 visible bottle / 97 masked
  arm vertices. Do not weaken all model guards or repeat PCA calibration.
- Checkpoint reuse and paired native HUD readback are already shared. Do not
  port them again or update the framework merely because master moved.

G7 now owns broader live SP calibration/weapon/final-origin coverage first,
especially thrown/rocket. Still separate: real SP NPC damage/isolation; focused HUD/transition
and clean-close acceptance; matching-fixture fog investigation only if still
reported. Pause and Sten physical smoke are now accepted. Do not require an MP
physical pause pass for the SP release.

Grenade ray calibration matches eight MP directions but two runs fail VRAM
restoration (2/3 mismatches, CPU hashes equal). Preserve failures. Full SP
grenade acceptance is unproven; only investigate that failure when it affects
the SP work/fixture, without expanding MP scope.

## 6. Required end-of-session checkpoint

- Restore/rebuild production debug-OFF after diagnostic builds. End with no
  owned game process/overrides left behind and no persistent XR settings change.
- Run focused checks appropriate to changes and `git diff --check`. Current
  baseline: 134 Python tests, including shared save-route regression coverage.
  Earlier strict plugin/native-timer syntax and 480 focused slot-5 rollback
  checks remain historical; the playable executable is unchanged by cleanup.
- Update stable IDs in VR_PLAN, the current handoff and compact receipts with
  actual source/binary/fixture provenance. Preserve failed controls and scope.
- Keep dumps, disc/BIOS data, saves and generated screenshots in ignored local
  directories. Do not stage `.commandcode/`, unrelated work or disc assets.
- Commit/push when requested; no PR creation or framework pin change is implied.

Detailed bindings remain in [WEAPON_MAPPING.md](WEAPON_MAPPING.md),
[SP_GAMEPLAY_REPAIRS.md](SP_GAMEPLAY_REPAIRS.md),
[PAUSE_MENU_PARITY.md](PAUSE_MENU_PARITY.md) and their receipts. The superseded
[old handoff](archive/HANDOFF_HISTORY_20261029.md) is evidence only, not a task queue.
