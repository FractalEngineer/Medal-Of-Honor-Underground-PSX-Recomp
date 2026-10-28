# Performance implementation runbook

Updated 2026-10-29. **Execute P3b, then P3c, then P4/P5.** The operator's clean
image headset smoke accepted world rendering, music, pause and Sten. Performance
is still “meh.” Minimum 60 fresh application frames/s, preferred 90, remains
the alpha blocker. This file supersedes older NEXT pointers in evidence logs.

## 0. Do not restart solved work

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

P0b's fully matched two-title/XR dataset remains open. It must not delay P3b
native attribution or trigger another broad parity study. The first game's
reported good 60-FPS experience is a target, not a measured like-for-like pair.

## 2. Attribute native replay, not just its outer wrapper (P3b)

Build the SAME working build with TCP temporarily ON, with no running game:

```powershell
cmake -S . -B build-release -DPSX_DEBUG_TOOLS=ON
if ($LASTEXITCODE -ne 0) { throw 'Configure failed' }
cmake --build build-release --target psx-runtime -j 2
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
New-Item -ItemType Directory -Path $perfRoot -Force | Out-Null
'{"MOHU_VR_WEAPON_TRACE":"0"}' | Set-Content -LiteralPath "$perfRoot/profile-env.json" -Encoding ascii
python vr/tools/probe_sp_issues.py "$perfRoot/slot5-profile" --slot 5 --audio --hud --laser --seconds 8 --env-json "$perfRoot/profile-env.json"
if ($LASTEXITCODE -ne 0) { throw 'Probe incomplete; inspect receipt/stderr' }
```

This is an owned copied-fixture diagnostic, not a physical headset session.
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

Proceed from P3b into implementation; the task is not another study-only pass.
For HLE/host replacements, read `psxrecomp/AGENTS.md` and
`psxrecomp/docs/HLE_EXECUTION.md`. Preserve the runnable reference, real caller
interface, observable results/side effects, completion and saved-state contract.
Do not patch identity cookies or silently drop PGXP/FOV/native art to get a
number. New shared behavior belongs on an appropriate framework feature/shared
branch, never master, with both affected consumers checked before pin changes.

Already measured/rejected shortcuts:

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
cmake -S . -B build-release -DPSX_DEBUG_TOOLS=OFF
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
