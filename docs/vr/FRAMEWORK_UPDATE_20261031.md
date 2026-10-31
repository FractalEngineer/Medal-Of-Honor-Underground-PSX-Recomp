# Framework performance update — 2026-10-31

**Superseded pin/status:** see
[CACHE_PGO_20261031.md](CACHE_PGO_20261031.md). The game now pins cleaner
framework master `e696907e`, the current overlay cache has been force-rebuilt,
and selective PGO is pending one representative fresh-state training run.

The production VR executable was rebuilt with upstream PR [#792](https://github.com/RetroPortingToolKit/psxrecomp/pull/792). **No gameplay speedup or 60/90 Hz result is established.** The final isolated slot-2 test rejects the old state with `enhancement_memory_layout_or_execution_profile_or_host_provider`. Obtain fresh states through normal play; never patch their headers.

## Completed work

- [x] Fetch upstream and fork histories; verify #792 is merged (`09ba00ed7ad9d5e7d88ca428e2c7dc23822a2ded`).
- [x] Sync framework fork master through upstream `a7b37e079e8c6e98e04cd1cd42ba559e95911ea7`, including #793.
- [x] Preserve existing shared VR changes. The remote fork already contained their rebase; range-diff confirmed the three shared patches and M0 patch were retained.
- [x] Update all four Git dependency pins below. Other vendored/archive libraries retain the revisions selected by the updated framework; no arbitrary library-version overrides.
- [x] Rebase active framework VR branches and both local M2 shelves. Keep shelved rendering work inactive.
- [x] Update game master and rebase `feature/vr-port` onto it.
- [x] Rebuild both emitters; regenerate game C on master and VR with their respective configurations. Normalize generated trailing whitespace. Retain 27 function hooks and 11 instruction hooks on VR.
- [x] Build production Release with two compile jobs, OpenXR/VR diagnostics ON, debug tools/IPO/experimental title kernels OFF.
- [x] Explicitly select `PSX_GL_BATCH_IMPL=HLE`; the old CMake cache retained LLE despite upstream's new default.
- [x] Enable upstream native CPU spans, media jobs, OpenBIOS reads, snapshot capture, host pacing and resident preparation.
- [x] Restage the matching overlay compiler, BIOS emitter and headers using `tools/release_stage.py stage-toolchain`. Final runtime reports `autocompile_degraded=0` and the optimizing compiler route.
- [x] Pass 171 VR Python/compiled-fixture tests and source diff checks.
- [x] Preserve original runtime, fixtures, preferences and personal saves; close owned probes.

Clang uses upstream's supported portable non-PGO route. Selective runtime PGO currently requires GCC; this build does not claim that optimization.

## Pins and artifact

| Component | Revision |
|---|---|
| Framework fork master / shared development | `b1d729e5b00a8369db5e7ff74880309826f4f25d` |
| Framework VR measurement branch / active game pin | `fd32746007d940ce5baff8bc215c954c76f03889` |
| recomp-ui | `a95615751b413e043983944441ed8912066c65ce` |
| recomp-net | `7a4d330ecf995b881d167234da3c0b01675fd512` |
| retcomm-rbengine | `28a2a472986a7d692d0378a22e756b0936413507` |
| Game sources used for final build | `e4106d83842b137294020cd99cc034a412d7d1eb` |

Executable: `build-release/Medal_of_Honor_Underground_Recompiled.exe`.

- SHA-256: `aadf9ffe09528044f523a4c9b916624cbc5e0ec8bc248bd14ca7596ddb20c553`.
- Execution identity: `534bcb1389d0580766e8f78c45001152afd64beef7656dfd824174b7dd919f23`.
- Overlay codegen hash: `0xe060fa62`; staged emitter SHA-256 `1e35e6a77253e05ce3c42a3039cfea87be545b795daf499e7e3094b8b5eb3bf3`.
- Old executable SHA-256: `cc69c669f6e7f1a666c9ba10f319a2fc2f6ed07afd6a29afb5035af224566c97`.

The pre-update executable, configs, execution contract, assets, cache and compiler bundle are preserved under `analysis/archive/framework-update-20261031/baseline/`. Build intermediates and temporary compiler scratch directories were excluded. Its staged configuration was already stale, and binary inspection confirms it lacks the VR diagnostic strings despite its cache saying diagnostics ON. Do not treat it as the historical M0 stereo binary.

Recovery refs `backup/20261031-*` preserve previous game/framework heads. The obsolete `mohu/openbios-stamp-379565a6` branch is retained unchanged as historical recovery: replaying that old stamp over upstream's regenerated BIOS would be wrong. The sibling first Medal of Honor checkout was not changed. The configured central Beads database at `F:/Software/beads/issues` is unavailable; no local database was created.

## Performance evidence and limits

| Attempt | Result | Usable gameplay comparison? |
|---|---|---|
| Preserved pre-update executable, copied slot 2 | No stereo export; binary has no VR diagnostics | No |
| First rebuilt candidate, copied slot 2 | Booted; stale overlay compiler detected, interpreting overlays | No; superseded after restaging |
| Final executable + matching compiler, copied slot 2 | Optimizing compiler enabled; old state explicitly rejected; clean close | No; new matching state required |

All three probe receipts have `complete=false`; do not convert their boot cadence into gameplay FPS. Final source-save and preference checks pass, exit code is zero and no game process remains. Dummy audio and hidden desktop windows do not certify audible playback or headset presentation.

Historical M0 slot-2 stereo measurements (21.95–23.41 fresh pairs/s, 19.79–20.86 ms pair work) remain in [M0_REPORT](M0_REPORT.md) and its receipts. They are historical context, not a matched A/B against this binary. The #792 PR itself describes component validation without a new game-specific performance claim.

Local evidence:

- `analysis/runtime/framework-update-20261031-{emitters,generate,master-generate,configure,build,final-build,stage,tests}.log`
- `analysis/runtime/framework-update-20261031-baseline-slot2/`
- `analysis/runtime/framework-update-20261031-candidate-slot2/`
- `analysis/runtime/framework-update-20261031-staged-slot2/` — final artifact, explicit rejection in stderr, non-degraded final run report.

## Resume the comparison

- [ ] Operator boots the rebuilt game normally and creates new states in the same heavy outdoor and indoor locations used for slots 2 and 5. Keep old states separately; memory cards remain normal game progress.
- [ ] Copy the new state/thumbnail pairs into a new frozen fixture root, e.g. `analysis/fixtures/sp-framework-20261031/openbios/`; hash and record them. Never point automated tests at personal saves.
- [ ] Confirm successful load and the same camera, scene, settings and workload before recording timings. A newly saved scene is not automatically equivalent to the old one.
- [ ] Run three production desktop windows per workload using the existing profiler, separated eyes and explicit resolution. Warm overlay compilation first and retain cold-start evidence separately.
- [ ] Record actual internal scale and effective mod settings on both versions. Here explicit `1080p` resolves to **5x**, while upstream's fresh default is **4x**; defaults alone are not a fair comparison.
- [ ] For a matched old/new comparison, use compatible fixtures captured independently on each version at the same scene. The preserved current flat executable cannot supply stereo timings; identify and verify the historical VR runtime if comparing stereo against it. Do not relabel a reconstructed reference as the original current build.
- [ ] Alternate validated reference/candidate windows; report native VBlank rate, fresh pairs/s, pair+HUD p95/p99, GPU sample validity, misses and pacing separately. Missing measurements stay missing.
- [ ] Only after desktop validation, test the physical headset at its actual application period. No 60/90 Hz acceptance follows from this dependency update.

Example after fresh fixture validation (from repository root, outside sandbox):

```powershell
python vr/tools/profile_sp_production.py analysis/runtime/framework-update-new-slot2-a1 --slot 2 --eye-offset 8 --runtime-perf --resolution 1080p --fixtures analysis/fixtures/sp-framework-20261031 --build-dir build-release --disc "Medal of Honor - Underground/Medal of Honor - Underground (USA).cue"
```

Use a new output directory for every run. Stop immediately on a genuine compatibility rejection. M2 independent rendering work remains shelved; this update does not complete any M2–M6 gate.
