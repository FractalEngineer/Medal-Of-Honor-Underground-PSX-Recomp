# SP performance comparison with the first game

Historical 2026-10-28 comparative evidence, not the active task queue. Clean
image activation and world/music/pause/Sten headset smoke are now accepted.
Execute P3b/P3c through [PERFORMANCE_NEXT_STEPS.md](PERFORMANCE_NEXT_STEPS.md);
do not turn the remaining matched two-title dataset into another study that
blocks the measured native replay work. Existing framework ports stay closed.

2026-10-28. Scope: comparative source/configuration audit and reanalysis of
preserved measurements. **No new game launch or headset measurement.** The
operator reports the first game plays about fine at 60 FPS and would prefer 90.
That is the experience baseline to recover in Underground. The old null-HMD
numbers below describe particular scenes; they do not replace that observation.

Reference checkout:
`C:/Users/titan/Desktop/Github_Projects/Mine/Medal-Of-Honor-PSX-Recomp`.
Current reference HEAD `d82a5d0`, Underground HEAD `a8e6596`; working source and
build hashes are in the [comparison receipt](../../vr/proof/sp-performance-comparison-receipt.json).
Both checkouts already contain local changes. This audit leaves the reference
checkout, binaries, settings, saves, framework and generated guest code unchanged.

## What is already shared

There is no missing first-game framework performance branch to copy wholesale.
Both checkouts use framework **`555e1eab`**. The audited `render_pass.c`,
`gpu_gl_renderer.c` and `gte.cpp` are byte-identical between them.

| Component | First game | Underground | Implication |
| --- | --- | --- | --- |
| Local normal build | Release, `-O3`, debug tools OFF, PGXP | Same | Debug-OFF is already applied; do not present it as the next fix. |
| Normal VR shortcut | 1080p, projective replay, hand HUD, tracked weapon | Same features | Both ask for 5x internal scale. Compare effective scale too; preferences can differ. |
| Overlay cache configuration | `overlay_cache=true` | Same; launcher recently corrected to `game.toml` | The operator's old interpreter launch was a real discrepancy, now fixed. Verify warm native calls; a config flag alone is insufficient. |
| OpenGL batching | LLE | LLE | The first game's unqualified batching experiment is not an omitted accepted optimization. |
| Stereo checkpoint reuse | Shared framework implementation | Same | Already ported. Do not implement a second checkpoint-sharing solution. |
| HUD capture | Shared checkpoint for two mattes; one combined readback | Same API and implementation | Earlier first-game HUD savings are already present. Further readback work can benefit both games. |
| Shedding | Normal default OFF | OFF | Turning it on can cause empty submissions/black flicker; it is not a quality-preserving FPS fix. |
| Native drawing | Documented 30 Hz draw loop | Measured one pair per two guest VBlanks | Neither current game-side stereo path independently generates 60/90 fresh views. |

The first game's `.bat` passes `-WristHud -WristHudReplace`; its PowerShell
switch defaults alone are misleading. Disabling the HUD would change the
comparison and the desired product. The larger Underground HUD crop is native
art/layout, not a reason to copy the first game's crop coordinates.

## Measured workload difference

The first game's preserved trace is its **2026-10-23 debug-ON interpreter**
slot-2 indoor/crate control. Underground's is the **2026-10-28 debug-OFF native**
SP slot-3 courtyard control, without injected hands. Both use SteamVR's null HMD,
1080p and HUD capture. Their scene, build, backend, camera and hand conditions
differ. **This table is attribution, not a matched benchmark or predicted gain.**

Values are medians recalculated from 555 and 120 actually exported records,
respectively; the trace's cumulative `count` is not the exported row count.

| Measurement | First game | Underground |
| --- | ---: | ---: |
| Stereo pair | 27.195 ms | 32.650 ms |
| Traversal bracket | 24.485 ms | 28.796 ms |
| Host tree collection, nested | 0.174 ms | 0.089 ms |
| Final ordering-table submission | 0.964 ms | 1.666 ms |
| HUD capture, outside pair | 3.955 ms | 4.820 ms |
| HUD readback portion | 2.805 ms | 3.509 ms |
| XR image copy | 0.171 ms | 0.175 ms |
| XR end-frame call | 0.985 ms | 0.855 ms |
| Left-eye primitives | 1,251 | 2,108 |
| Right-eye primitives | 1,280 | 2,106 |

**Underground submits 65–69% more primitives per eye in these fixtures.** Its
roughly 73% longer OT-submit median is consistent with a heavier draw workload,
but does not establish scaling or identify unnecessary geometry. Its guest
cycle medians are similar (left about 6% lower, right about 5% higher); guest
cycles are not host CPU cost. Count GTE commands, vertices, selected leaves,
actors, hooks and backend work before assigning the excess to any one subsystem.

The first game's historical production timing file separately reports 48.24
**guest VBlanks/s**, pair-time EMA median 24.365 ms in that demanding scene.
It is not a current physical 60-FPS benchmark. The operator's better experience
may involve another scene/build/runtime or compositor behavior; this audit has
not identified which. Record all those dimensions in the next comparison.

Underground's mean pair plus mean HUD capture is **39.272 ms**, before remaining
XR work and canonical guest execution. Reducing just that partial workload to
16.67 ms requires about **58% less time**; 11.11 ms requires about **72% less**.
These are budget bounds, not FPS predictions. Small guard or logging changes
alone are unlikely to close the whole target.

## Ranked opportunities

### 1. Reuse the first game's profiling workflow before selecting a replacement

Start with both current production configurations, warm overlays, identical
resolution/eye profile, HUD/weapon/laser settings and one fixed gameplay fixture
per title. The levels cannot be identical across games: compare controlled
conditions and normalize workload; do not call the scenes matched.

Then profile Underground's **native** replay with the existing framework tools:
`phase_profile`, `host_profile`, `gcp_ring`, native/interpreter call deltas and
per-eye frame traces. These are the first game's actual attribution tools,
already available at this shared pin. Use a diagnostic build for localization,
then remeasure any candidate with debug OFF. A guest-cycle histogram does not
measure host cost. `host_profile.py` labels addresses outside the EXE as system
code/waits; cached native overlay DLLs also live outside the EXE. Preserve raw
addresses and resolve their module/symbols before calling that time a wait.

Locate the largest native transform/triangle/packet routines and their GTE/PGXP
work. The warm Underground native control already reduced dirty instructions
from 134 million to 379 thousand across 600 VBlanks. Restarting the historical
"everything is interpreted" investigation would be a dead end.

### 2. Make the replay as explicit and measurable as the first game's

Reference `vr/psx_vr_stereo.c:vr_draw_scene` calls setup, world, text, actor
traversal, icon and final OT routines explicitly. Underground's
`vr/underground/vr_diagnostic.c:vr_stereo_eye_draw` calls `80053BB4`, suppresses
its native submit tail, then submits the cleaned OT once.

The captured native wrapper calls `80053D4C`, `800976D0`, `8009865C`, `80070898`,
`8006B64C`, `80078E08`, `8008F9F4`, and `80053CFC`. These correspond structurally
to the reference's draw stages. **The wrapper is not proof of extra simulation
or a redundant second scene traversal.** Instrument the child stages first;
currently Underground's broad `game_traverse` includes work the reference splits
into environment/world/text/icon spans. Their traversal totals are not identical
scopes. Preserve the already-fixed single final submission and native HUD fallback.

If one stage dominates, port the reference's explicit replay organization around
the measured Underground bindings. If the native geometry producer dominates,
an explicit wrapper alone will not save it: consider a title-owned batch/HLE
implementation at that real caller interface. Preserve a runnable LLE control,
projective/PGXP provenance, clipping/facing, texture/OT output and completion
semantics. Do not start a one-traversal/two-eye rewrite before this attribution.

### 3. Remove HUD synchronization cost while retaining native art

Both games already capture two full 512x240 mattes in one call. The shared
`gl_renderer_stereo_stage_readback_pair` blits them together, then synchronously
reads **983,040 bytes** into CPU memory; title code extracts alpha/crops, and
surface submission uploads pixels again. Underground's readback mean is
5.175 ms, p95 11.144 ms in the preserved production window. Readback can include
waiting for earlier GPU work, so do not attribute all of it to transfer bandwidth.

The first game's plan names change-gated capture but does not deliver it as an
accepted completed optimization. Candidate order:

- Reuse extracted HUD artwork when its actual native dependencies are unchanged;
  continue locating/submitting it at the **fresh** hand pose every XR frame.
  Invalidate on health/ammo/weapon/compass/text-animation/texture-palette changes,
  load, scene/menu transitions and capture failure. Do not key only on ammo.
- Measure native-resolution or cropped capture rather than rendering full-size
  5x matte surfaces. Underground's two owned regions total 17,984 pixels per
  matte: 143,872 bytes for both, about 85% fewer bytes. A smaller read can still
  stall, so this is not an 85% time-saving promise.
- If synchronization remains dominant, add a shared GPU-resident matte/alpha
  surface path, or bounded asynchronous readback with explicit content-age rules.
  The current surface API accepts CPU RGBA; a texture path needs a real API and
  lifetime/GL-state contract, not a local pointer trick.

Validate native notification preservation, opaque black art, changing compass,
firing/reload ammo updates, per-hand tracking loss/fallback, pause/load and surface
failure. A generic capture improvement should be tested in both games.

### 4. Measure excess guard/hook work; cache only with correct invalidation

Underground installs more audited draw hooks than the first game. Its generic
role callback scans the 20-role map; `vr_head_frustum_filter` rehashes the whole
2,840-byte LVTX function before collecting the tree. HUD capture rehashes its
producer functions each capture; weapon validation hashes full geometry inside
each accepted held draw. The reference's LVTX filter checks four leading words.

Importantly, Underground's 0.089 ms `game_select` bracket covers only collection:
it excludes preceding signature validation and following queue writes. The
reference brackets its wider filter operation. Do not use those small medians
to prove the **whole** filter costs less or is free.

Profile callback invocations and hashing time. If material, separate discovery
hooks from required play hooks and cache verified immutable code/assets by a
reliable overlay/load/content generation. Owner/object/ID/pointers alone can
repeat after load or memory reuse. Keep range checks and exact SP petrol variant
acceptance; never simply delete guards or cache a signature forever. Any cache
must reject changed bytes and recover after reload. The prior named-counter
experiment was removed; it is not a proven fix to reinstate.

### 5. Separate render cadence after the replay cost is understood

Both game adapters request stereo from a native 30 Hz draw seam. The first
game's `MOH_FLIP_PERIOD_VBLANKS=2` and Underground's `period_vblanks=1` are budget
declarations, not an extra-frame scheduler. The first game's optional legacy
interpolation path is disabled by its normal launcher; it is not a ready-made
90-Hz stereo implementation to enable blindly.

Once CPU/GPU cost permits, use fresh head/hand poses to render additional stereo
views between native updates. Keep guest simulation/audio/movement/projectile
timing unchanged; never recursively enter an active rollback transaction.
Reusing the same pair at 90 compositor presentations is different from a new
view. First compare current physical/runtime counters with the operator's
known-good first-game build; if that build already supplies additional fresh
views, inspect and port that exact path before designing another scheduler.

## Next execution contract

1. **P0b:** produce current controlled baselines for both titles without changing
   the reference checkout. Record executable/source/framework hashes, save hash,
   native calls, actual scale/projection, runtime, input/HUD options, fresh pair
   deltas, VBlanks and trace distributions. Do not wear/launch a physical headset
   in this step. Null settings backup and restoration are mandatory.
2. **P3b:** use existing diagnostic sampling plus child-stage spans to identify
   the top three host costs in native Underground replay. Account for overlay
   DLL samples. Retain debug-OFF production baseline separately.
3. **P3c/P3:** change one measured bottleneck at a time. Use at least three
   alternating same-fixture baseline/candidate quiet windows; no screenshots,
   TCP traffic or VERIFY hashing inside timed windows. Require repeatable median
   and tail improvement with intact visual/rollback/gameplay controls. Keep HUD,
   correct FOV, tracked weapons and laser. Generic improvements must pass both
   consumers on feature/shared branches before pins change.
4. **P4-P6:** address the measured fresh-view cadence limit, then desktop/null
   pacing/recovery and finally one bounded physical SP check. Target stable 60
   fresh application frames/s, 90 preferred; also record the perceived experience,
   runtime refresh/reprojection, CPU/GPU time and audio. R6 combat expansion waits.

Do not rerun completed weapon discovery, tune away visible geometry, promote old
debug numbers to current headset FPS, or publish a speedup from different scenes.

Recreate this read-only analysis (no game launch):

```powershell
python vr/tools/compare_sp_performance.py `
  --reference-root ../Medal-Of-Honor-PSX-Recomp `
  --out vr/proof/sp-performance-comparison-receipt.json
```

The receipt hashes raw evidence and current source/build inputs; historical
trace binaries are not claimed to be the current binaries. Percentiles use
linear interpolation over the exported rows. The previous report remains the
owner of the petrol repair, failed cleanup incident and production runtime
receipt: [SP_PERFORMANCE_AND_PETROL.md](SP_PERFORMANCE_AND_PETROL.md).
