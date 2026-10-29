# Performance implementation runbook

Workspace policy: [WORKSPACE_LAYOUT](WORKSPACE_LAYOUT.md). Normal play shares
root `saves`; automated sources are frozen `analysis/fixtures/sp` and
`analysis/fixtures/mp`, copied to disposable outputs. Retired benchmark aliases
and the old flat-check build are archived, not runnable alternate play targets.

Updated 2026-10-29. **G7 full MP-to-SP weapon calibration/control parity is FIRST**
under the latest operator instruction: [SP_WEAPON_PARITY](SP_WEAPON_PARITY.md).
This performance runbook is deferred until that scoped port/coverage decision.
Petrol bomb/Panzerfaust apparent fixed aiming is an open report, not a repair.
After G7, G5/G6 precede preflight optimization: reproduce
and classify personal SP slot 1 missing-world rendering, then baseline personal
SP slot 2 severe performance and confirm the implementation target. Then use
[SP_CURRENT_REGRESSIONS](SP_CURRENT_REGRESSIONS.md). No game was launched while
recording these reports; causes/FPS are unknown. P3b remains complete for its
historical fixture; P3c and P4/P5 remain open. After the new-case triage, read the
[native profile and rejected experiments](NATIVE_REPLAY_PROFILE.md) first.
Its final section specifies the next `80011424` caller-contract implementation.
Do not repeat P3b or compiler sweeps. The operator's clean
image headset smoke accepted world rendering, music, pause and Sten. Performance
is still “meh.” Minimum 60 fresh application frames/s, preferred 90, remains
the alpha blocker. This file supersedes older NEXT pointers in evidence logs.

All operator slot references are internal/file/tool indices, as confirmed by
the operator. Select `--slot 1` for G5 and `--slot 2` for G6. Do not reinterpret
the report as menu labels or shift indices to 0/1.

## 0. Do not restart solved work

The old slot-5 damaged-image case remains historical; the new slot-1 rendering
report is legitimate new evidence and must be investigated. Compare native
Flat/stereo on that exact copied fixture before assuming a disc, frustum or
preflight cause. Do not narrow the visible FOV or start the planned optimization
blindly. A successful probe/load does not demonstrate complete world rendering.

Read [HANDOFF.md](HANDOFF.md), current P/G items in [VR_PLAN.md](VR_PLAN.md),
then this file. Read [REFERENCE_REUSE_AUDIT.md](REFERENCE_REUSE_AUDIT.md) before
introducing a replacement architecture. Do not read the historical handoff as
instructions. No further disc audit, image migration, general headset smoke,
Sten basis mapping, pause port, weapon PCA or unchanged 13-ID matrix is needed.

Use the existing `feature/vr-port` checkout and `build-release`. The source
config already selects the verified remaining clean image. Historical recovery
stays disabled. Both games retain framework `555e1eab`; no update/pin change is
needed for orientation. Reference source is read-only unless a concrete shared
change requires a coordinated consumer edit.

## 1. Establish the current clean production floor (P0b contribution)

The current continuation already collected this floor and alternating compiler
controls in `analysis/vr-baseline/perf-20261029-next/`. Do not rerun them before
the preflight caller-contract work. Use this section for a new candidate's A/B.

**Run all game commands unsandboxed; one game at a time.** Check that the operator
has no running game before each launch. Leave unrelated/owner processes alone.
The normal state is Release/debug-OFF. Shell examples below assume repository
root and PowerShell; choose a fresh output directory every time.

```powershell
$perfStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$perfRoot = "analysis/vr-baseline/perf-$perfStamp"
python vr/tools/profile_sp_production.py "$perfRoot/slot5-baseline" --slot 5
if ($LASTEXITCODE -ne 0) { throw 'Baseline incomplete; inspect receipt/stderr' }
```

This tool uses the current config, copies slot 5, creates a hidden SDL window
with normal pacing/dummy audio, exports 120 records after 180 stereo pairs and
closes only its owned child normally. It requires debug-OFF; no TCP, headset,
SteamVR changes, disc override or recovery-isolation flag is needed. It does
not inject hands. Its HUD/laser flags **do not mean actual hand surfaces/ray
cost was measured**. No physical FPS or audio-listening claim follows.

Accept only `complete=true`, source saves/preferences unchanged, exit 0,
no forced cleanup and no remaining game PID. Inspect failure/flags in
`frame-trace.json`, not only the printed cadence. If the command fails, inspect
that directory before rerunning; never overwrite it.

Use slot 3 as a second focused workload when comparing a candidate, not as a
reason to repeat unrelated weapon tests. Existing clean/default slot-5 receipt:
`analysis/vr-baseline/clean-disc-activation-20261029/default-slot5/receipt.json`
(17.391-ms desktop pair, no XR/HUD capture). Old A/B receipts in
`sp-issues-20261028/` are historical; use the active clean image for new claims.

P0b's fully matched two-title/XR dataset remains open. It must not delay P3c
implementation or trigger another broad parity study. The first game's
reported good 60-FPS experience is a target, not a measured like-for-like pair.

## 2. Attribute native replay, not just its outer wrapper (P3b)

**Complete. Reproduction only:** packet/preflight/GPU-command exclusive segments
cost 5.729/3.805/1.143 ms per pair; full visibility hook 0.068 ms. Canonical/eye
timings and resolved DLL evidence are in the report/receipt. For changed code
that needs re-attribution, use the optional title-owned native segment timers:

Build the SAME working build with TCP temporarily ON, with no running game:

```powershell
cmake -S . -B build-release -DPSX_DEBUG_TOOLS=ON -DMOHU_VR_NATIVE_PROFILE=ON -DPSX_RUNTIME_IPO=OFF
if ($LASTEXITCODE -ne 0) { throw 'Configure failed' }
cmake --build build-release --target psx-runtime -j 2
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
New-Item -ItemType Directory -Path $perfRoot -Force | Out-Null
'{"MOHU_VR_WEAPON_TRACE":"0"}' | Set-Content -LiteralPath "$perfRoot/profile-env.json" -Encoding ascii
python vr/tools/probe_sp_issues.py "$perfRoot/slot5-profile" --slot 5 --audio --hud --laser --seconds 8 --env-json "$perfRoot/profile-env.json" --native-profile
if ($LASTEXITCODE -ne 0) { throw 'Probe incomplete; inspect receipt/stderr' }
python vr/tools/summarize_native_profile.py "$perfRoot/slot5-profile/receipt.json" --out "$perfRoot/slot5-profile-summary.json"
```

This is an owned copied-fixture diagnostic, not a physical headset session.
Resolve symbols before overwriting the diagnostic executable. For an archived
capture, `summarize_native_profile.py --exe <preserved-executable>` verifies its
SHA-256 against the receipt before using that file's symbols. Never force a
new production binary's symbol table onto an old capture.
It injects synthetic hands/grip and captures stage/host/phase/guest-cycle data.
Do not add `--verify`, geometry dumps, screenshots, RAM reads or repeated TCP
requests inside the quiet timing interval. The explicit override disables the
shot tool's otherwise-enabled weapon/flash logging. Use VERIFY in a separate correctness
control after implementation. The tool's `--audio` mode is paced SDL; the
default `--headless-opengl` path has no audio and is unpaced throughput.

Read these saved fields/files offline AFTER it closes:

| Evidence | Meaning / constraint |
|---|---|
| `receipt.json: trace.trace.records` | Debug response nests the actual frame trace; older file exports have `records` directly |
| `host_profile.top` | EXE-relative sampled instruction addresses and counts; resolve before attribution |
| `host_profile.modules` | Counts in executable, cached native DLLs and system modules; outside-EXE is not automatically idle |
| `phase_hot_native`, `phase_hot_static` | Guest function/phase sample attribution; native and static are different sets |
| `phase_profile.window_s` | Actual window; the API clamps requests, so `300` is not evidence of a 300-frame/s window |
| `guest-cycles.csv` | Native guest-cycle workload; never convert directly to host ms |
| `overlay` / startup log | Whether real native overlay calls ran, compilation/cache activity and code identity |

Reuse `psxrecomp/tools/host_profile.py`'s `symbols(nm, exe)` and PE-relative
lookup for offline EXE symbols. Its CLI needs a LIVE debug process and its
generic “outside executable: waits” label does not resolve cached native DLLs.
Do not call that CLI after the owned probe has closed or treat that label as
proof. Resolve DLL samples against the loaded module/cache metadata or keep
them explicitly unresolved; aggregate system-module samples separately.

Existing broad stage `game_traverse` includes world and entity work, while
`game_select` measures just the host collector. Add bounded title-owned host
spans/counters at real call/return boundaries to separate the child costs:

| Known operation | Address / contract lead |
|---|---|
| SP arena draw wrapper | `8009A478`, 208 bytes, FNV `981FD4DF`, caller RA `80057DF4` |
| Arena packet builder | `80010CF0` |
| Native subdivision paths | `80010000` and `80010508` |
| Native preflight helper | `80011424`, 668 bytes, FNV `C38CDCC1` |
| Level selection | `80099960`; native queue count `800B74B4`, queue `800B74B8`, terminator `800B8458` |
| Entity/scene traversal | Existing `vr_diagnostic.c` engine bindings/scene brackets; follow measured callers |

Read the actual functions/callers before instrumenting. The listed helper
addresses are attribution targets, not instructions to bypass culling. Keep
canonical work and eye 0/1 measurements separate. Reuse existing span services
where their semantics fit; do not overwrite the same shared stage in nested
spans and call its sum independent work. No per-vertex logging, file I/O or
profiling debug overhead in a claimed production gain. Cache/guard costs must
be measured around the whole entry path, not only the inner collector.

**P3b exit:** name the top three host costs, including resolved source/caller,
pass/canonical scope, measured ms/share and fixture/build/flags. Choose ONE
dominant operation for P3c. A table of guest instructions alone or another
“profile more” handoff does not close P3b. If evidence disproves a suspected
cost, record it and choose the actual measured target; do not rerun unchanged.

Useful focused reference material: first-game `vr/psx_vr_stereo.c`,
`docs/reverse/VR_SLOT2_PERFORMANCE.md`, and measured sections of
`docs/reverse/VR_OPTIMIZATION_STATUS.md`. Historical failed experiments there
are not current instructions. The earlier checkpoint/HUD readback ports are
already shared; do not implement them again.

## 3. Implement the measured improvement (P3c)

Start at [the preflight caller contract](NATIVE_REPLAY_PROFILE.md#exact-next-implementation).
Read/capture `80011424` and its continuation `80011008`; do not treat `$v0`
as its entire custom ABI. Plan valid caller fixtures before an execution-family
identity change. The selected helper costs about 3.8 ms/pair and is a smaller
first implementation than the 1840-byte parent packet builder.

### 3.1 Ordered execution checklist — start at P3c2

These IDs match VR_PLAN. P3c1 is the old native-copy experiment, already done
and OFF; it is **not** the first step of this new implementation. P3b is done.
Complete this sequence for the preflight helper before starting packet-builder,
HUD or cached-scene work. This is an implementation assignment: capture alone
does not finish it. No physical headset is required for P3c2–P3c6.

| Order / plan ID | Required action | Evidence needed before advancing |
|---|---|---|
| 1 — P3c2 | Capture the real preflight caller contract and choose a valid reference/candidate fixture strategy | Contract document, real captured cases and a runnable comparison harness/fixture design; no save-header edits |
| 2 — P3c3 | Implement the faster helper through that interface, selected at build time, retaining the original reference | Actual source/CMake change and paired caller-result tests; a compiler flag or profiling report is insufficient |
| 3 — P3c4 | Run focused correctness and lifecycle controls separately from timing | Preserved geometry/FOV/PGXP, gun/laser, pause, tracking-loss, refusal/recovery, load and native timing results; record failures |
| 4 — P3c5 | Compare three alternating production baseline/candidate windows, then the second SP workload | Identified binaries, execution manifests, effective flags, validated fixtures and a consistent useful gain beyond run spread |
| 5 — P3c6 | Qualify the actual HUD/weapon/laser/XR path and make a retain/reject decision | Full-path timing/freshness and unchanged correctness; three matched windows per binary for a gain claim; no averaging away bad runs |
| 6 | Follow the budget decision in section 3.3 | A single recorded next task: P3d, conditional P3e, or P4; no parallel exploratory projects |

**P3c2 — the first concrete work:** read the complete `func_80011424` body and
its `func_80010CF0` caller in `generated/SLUS_012.70_full_00.c`, plus the helper's
entries in `generated/SLUS_012.70_dispatch.c`. The real call is `80011000`,
normal continuation `80011008`, helper size 668 bytes / FNV `C38CDCC1`.
The custom register/scratchpad/GTE leads are in NATIVE_REPLAY_PROFILE. Validate
them from real calls; do not invent a conventional `a0..a3 → v0` ABI.

Create `docs/vr/PREFLIGHT_KERNEL_CONTRACT.md` when implementing this task. It
must name the supported code/caller and input memory ranges, live input/output
registers, scratchpad writes, GTE and PGXP/projection state, continuation and
completion behavior. Capture all potentially relevant state first, then
identify what the caller actually observes. Account for the internal resume
PCs mapped to this function by the dispatch table, not just its first address.
Define unsupported cases rather than consuming an unknown guest call.

Use real cases covering accepted/rejected triangles, winding swap, clipping,
depth and subdivision choices. Store bulk captures in a unique ignored
`analysis/vr-baseline/` directory. Record which branches remain unexercised;
never fabricate guest inventory, geometry or state to claim gameplay coverage.
Keep fixed-point/GTE math and precision propagation. Per-instruction internal
timing identity is not a universal HLE requirement; observable completion,
simulation/audio cadence and the policy's caller contract are required.

**P3c3 — implementation delivery:** start from the original helper and shared
GTE/PGXP/checkpoint services. Follow `psxrecomp/docs/HLE_EXECUTION.md` for
build-selected implementations and a runnable REFERENCE path. Do not hand-edit
committed generated game bodies to remove checks, blanket-disable GTE/PGXP,
drop triangles or change native VBlank/guest-cycle rates. Handle the fact that
the original helper shares a generated translation unit with other functions;
the selected implementation must keep their symbols/behavior available and
must not accidentally link two public definitions of the replaced helper.
Paired tests must compare the real caller-visible results, including precision
and memory effects, not merely a duplicated formula or a returned integer.

**P3c4 — correctness delivery:** use the existing probes/contracts for slot 5
world/stream/load, slot 4 Sten shot direction and tracking-loss fallback,
slot 3 P38/petrol visibility/fire/reload, pause/resume, and forced render
refusal/recovery. Use valid profile-specific equivalents where needed below.
Keep the hand-fixed laser, visual recoil, complete gun-only model, native HUD
and edge visibility. VERIFY runs belong here, outside performance windows.
One failed restoration or changed native outcome is an unresolved failure;
do not silently discard it or reopen unrelated accepted weapon matrices.

**P3c5/P3c6 — performance delivery:** preserve baseline and candidate artifacts,
their actual SHA-256/execution manifests, fixture hashes, effective resolution,
projection/runtime options and original settings. Alternate B1/C1/B2/C2/B3/C3
under matching conditions; report each run, spread, pair work, fresh publication
rate, guest cadence and failures. Full-path qualification must actually execute
the native HUD capture, hand weapon/laser and XR path. A desktop flag requesting
HUD/laser or a production null-HMD run without injected hands does not measure
those complete surfaces/rays. Extend the existing owned probes only as needed
to obtain the missing measurement; do not label their old limited mode full.
No physical controller/HMD acceptance is implied by synthetic/null-HMD data.

### 3.2 Execution identity and fixture handling — resolve before integration

The default starting choice is a **standalone caller-contract harness** using
real captured calls, with reference and candidate isolated/restored through
existing services. Keep this harness out of normal live gameplay. Once the
paired contract is established, register the real implementation family and
qualify it with valid game fixtures. Do not replace a failed game-load check
with harness success and call the full integration validated.

- Adding/changing an implementation family changes the execution identity.
  The current slot-3/4/5 states may therefore refuse to load. Preserve them;
  do not rewrite cookies, relax guards or promise cross-profile compatibility.
- Keep the accepted `build-release` runnable while developing. If the registered
  family needs separate REFERENCE/ENHANCED output directories, that is justified
  implementation work under the HLE policy, not an orientation build or a way
  to hide a mismatch. Use separate full runtime assets and overlay caches per
  execution profile; never copy a candidate executable into another profile's
  cache/assets and treat the result as qualified.
- The current `profile_sp_production.py` and `probe_sp_issues.py` select the
  frozen SP fixture tree and normal `build-release`. The former sibling `--exe`
  profiler launch override was removed during cleanup; normal play/probes use
  the standard game executable name. Offline symbol inspection can still read
  an archived binary by hash. New-family fixtures/builds still need isolation.
- Before cross-profile gameplay timing, minimally extend the existing tools
  to select the intended build/assets/config and a separate validated copied
  fixture root, recording both in the receipt. Such build/fixture selectors
  are **not implemented yet**; do not invoke invented CLI options or overwrite
  the shared source-save tree to trick the existing tools.
- Genuine reference/candidate states must come from supported normal boot,
  gameplay or memory-card load paths for each execution identity. Record scene
  differences; use matched caller captures for isolation. If suitable game
  states are unavailable, continue independent harness/implementation work,
  report the precise missing integration fixture once, and leave the gameplay
  qualification boxes open. Repeatedly trying the same refused save is no work.
- New shared APIs require the framework feature/shared branch and both consumer
  checks before a pin update. A title-owned helper does not justify unrelated
  framework updates. No live implementation switch in the playable build.

### 3.3 What follows preflight — choose by measured full-path budget

There are two independent blockers: **work per stereo pair** and **the native
~30-Hz draw trigger**. Fixing only one cannot certify 60/90 fresh application
frames/s. A 3.8-ms diagnostic helper cost is not a guaranteed 3.8-ms production
saving, and even that saving alone would not establish the complete XR budget.

| Option / plan ID | When to do it | Required scope / exit |
|---|---|---|
| Preflight — P3c2–P3c6 | First, now | Complete the ordered implementation/tests/measurement above; retain only a qualified gain |
| Parent packet builder — P3d | After the preflight decision if the native path is still over budget | Target measured `80010CF0` (1840 bytes), caller `8009A514`, return `8009A51C`; use the same contract, correctness and A/B gates. Do not sum its exclusive timing as though it includes preflight |
| HUD synchronization — P3e, conditional | Only when current full-path evidence still identifies a significant remaining HUD stall | Inspect existing local/shared capture and dirty/change detection first. Reuse texture data when contents are unchanged or remove a measured synchronization stall only if that work is missing; preserve native updates, pause/fallback and restoration. Checkpoint reuse and paired readback already exist |
| Independent fresh views — P4, then P5 | Once affordable replay is available; cost alone still leaves the ~30-Hz ceiling | Publish views from fresh head/hand poses while preserving native simulation/audio/fire/reload/stream timing; pass the timestamp/recovery gates in section 4 |
| Cached scene geometry — conditional fallback within the P3/P4 design decision | Only if measured native replay cannot meet the budget or support the required fresh-view cadence after the targeted work | Record why incremental replay is insufficient, inspect reuse in the shared renderer, then isolate a bounded prototype. Validate visibility/FOV, moving entities, animated weapons and fresh controller poses; do not blindly reuse camera-culled packets |

Cached scene rendering is a larger architecture change, **not a third project
to start now or a mandatory alpha feature**. It means reusing suitable decoded
scene data while rendering fresh poses, not counting repeated old images or
compositor reprojection as fresh frames. Preserve the runnable replay path.

At each decision, record `retained`, `rejected` or `deferred`, the evidence and
one exact next task in HANDOFF. A rejected preflight candidate leaves P3c open;
move to the justified next target rather than repeating the same experiment.
Do not require every conditional option if the full budget and P4/P5 gates
already pass. Only P6 then asks the operator for a focused headset check.

Proceed from P3b into implementation; the task is not another study-only pass.
For HLE/host replacements, read `psxrecomp/AGENTS.md` and
`psxrecomp/docs/HLE_EXECUTION.md`. Preserve the runnable reference, real caller
interface, observable results/side effects, completion and saved-state contract.
Do not patch identity cookies or silently drop PGXP/FOV/native art to get a
number. New shared behavior belongs on an appropriate framework feature/shared
branch, never master, with both affected consumers checked before pin changes.

Already measured/rejected shortcuts:

- Three compiler-inlining variants are removed. Existing framework IPO gives
  about 4.3% desktop pair-work savings, but the second null-HMD run is worse.
  It is unqualified and OFF. Preserve that run; no further tuning sweeps.

- The native-copy skip is implemented and guarded but OFF. Three old A/Bs give
  about +4.9% desktop cadence and essentially unchanged 17.6-ms stereo work.
  Its Sten/camera/pause/refusal/reload/hitch checks pass, but that is not a
  shipping 60/90 optimization or a reason for another six identical runs.
- Tree collection is about 0.056 ms versus 15.65-ms traversal. Tightening or
  caching it is not the presumed major lever. Do not reintroduce edge culling.
- 720p/native resolution leave pair work about 17.96/17.76 ms. Do not degrade
  the default resolution as the presumed CPU replay fix.
- Slot-5 geometry/music failure was a damaged-disc streaming stall. Native,
  all-leaf, full-interpreter and software controls plus both clip bypasses
  already ruled out the earlier render hypotheses; all temporary bypasses were
  removed. New clean-image operator acceptance closes that investigation.

Validate correctness separately from timing. Use focused clean-image controls:
slot 5 world/stream/load, slot 4 Sten/native-motion/loss, slot 3 P38/petrol,
pause/resume and forced render refusal/recovery. Use existing helpers/contracts,
not guest health/ammo/inventory or code edits. Preserve the accepted hand-fixed
laser and native visual recoil. Broader all-ID/SP damage work is a later scope.
Record any forced close/VERIFY mismatch as a failure, not a pass to discard.

Restore production OFF before timing. Run **three alternating baseline/candidate
windows** at identical effective flags/resolution/fixture with each binary's
actual hash and clean image identity. Establish a stable gain beyond spread;
check pair work AND complete-frame/freshness, including XR/HUD when claiming
the full budget. Preserve the baseline artifact; do not compare debug ON to
debug OFF as if only the optimization changed. Failed/no-gain experiments are
reverted or explicitly opt-in, with exact rejection evidence.

## 4. Fresh view cadence and validation (P4/P5/P6)

Current native scene draw is about 30 Hz. Cheaper guest execution alone does
not give 60/90 fresh poses. Inspect/reuse the reference's current pacing path
before designing another scheduler. A render-only solution must retain native
simulation, audio, firing/reload and streaming time. Do not change PSX clock,
VBlank rate, turbo or guest-cycle scale to double gameplay speed.

P4/P5 acceptance needs application publication/fresh pose timestamps, source
guest cadence, complete CPU/GPU frame budget, stale pairs/repeats and recovery
under pause, focus/tracking loss, load and streaming. Compositor display rate,
reprojection and drawing the same pair again do not certify fresh frames.
Full 60-Hz budget is 16.67 ms, preferred 90-Hz budget 11.11 ms, including the
actual HUD/laser/weapon/XR path. Desktop no-XR numbers are not this acceptance.

Only when the candidate is ready and desktop controls pass, ask the operator
for one bounded SP physical performance check. Do not repeat the general
world/music/pause/Sten smoke that was just accepted. Keep SP grenade/rocket,
broader damage, focused transitions and release teardown scopes honest; do not
make MP gameplay completeness a gate for this SP alpha.

## 5. Finish each implementation checkpoint

```powershell
cmake -S . -B build-release -DPSX_DEBUG_TOOLS=OFF -DMOHU_VR_NATIVE_PROFILE=OFF -DPSX_RUNTIME_IPO=OFF
if ($LASTEXITCODE -ne 0) { throw 'Production configure failed' }
cmake --build build-release --target psx-runtime -j 2
if ($LASTEXITCODE -ne 0) { throw 'Production build failed' }
python -m unittest discover -s vr/tests -p 'test_*py'
if ($LASTEXITCODE -ne 0) { throw 'Regression tests failed' }
git diff --check
```

Run affected strict C/renderer/framework tests when that code changes. Restore
all temporary overrides/settings, source-save hashes and owned process/runtime
state. Do not leave a diagnostic build as the operator's playable build.
Use ignored `analysis/` for RAM/media/bulk captures; compact receipts in
`vr/proof/` name binaries/fixtures/flags, controls, limitations and failed runs.
Update P/G IDs, HANDOFF's exact next action and the log. Commit/push when
requested; do not submit unrelated PRs or stage personal/disc/BIOS files.
