# Workspace and save locations

Updated 2026-10-29. This file owns the active filesystem/launcher policy.
[HANDOFF](HANDOFF.md) owns the next task; [VR_PLAN](VR_PLAN.md) owns status.

2026-10-30 operator-requested performance trial **failed physical acceptance**.
Default RunVR BATs are restored to production/personal saves. The explicit
`-PerformanceTest` route remains diagnostic, not recommended normal play.
It routes to the complete
`analysis/builds/preflight-enhanced` runtime and isolated persistent playtest
saves at `analysis/playtest/render-kernels/saves`. It boots normally for a new
game, enables host kernels and extra fresh views, leaves packet caching OFF,
and records a trace under timestamped `analysis/runtime/vr-performance-test`.
Plain RunVR (and its explicit `-Baseline` option) uses the normal
production route described below. RunFlat remains unchanged. No executable,
state header or personal save is replaced. Preparation verifies the tested
binary/execution identity and never overwrites existing playtest progress.

## Normal play — one build, one save store

| Purpose | Location relative to repository root |
|---|---|
| Playable flat **and** VR executable | `build-release/Medal_of_Honor_Underground_Recompiled.exe` |
| Personal memory cards | `saves/card1.mcd`, `saves/card2.mcd` |
| Personal save states and thumbnails | `saves/openbios/state_8001F844_slotNN.pst` / `.thumb` |
| Flat launcher | `RunFlat.bat` |
| VR launchers | Existing `RunVR-VDXR.bat`, `RunVR-Oculus.bat`, `RunVR-SteamVR.bat` |
| Normal logs/runtime dumps | `analysis/runtime/flat/`, `analysis/runtime/vr/` |
| Current game configuration | Root `game.toml`; explicit full path from launchers |
| Writable preferences | `build-release/settings.toml`, `build-release/keybinds.ini` |
| Active verified disc | `Medal of Honor - Underground/Medal of Honor - Underground (USA).cue` |

Both normal launchers pass the same **absolute** `--memcard-dir` and print the
chosen executable and save location. Switching flat/VR does not choose another
save tree or change slot numbering. RunFlat prefers the active build; a packaged
root executable is used only when there is no `build-release` directory.
RunVR boots normally unless explicitly given `-Slot N`.

The operator's slot references throughout this project are internal/file/tool
indices: slot 1 is `slot01` / `-Slot 1`, slot 2 is `slot02` / `-Slot 2`.
Do not convert those references through menu display labels or renumber history.

The executable is unchanged by this cleanup; no state headers, identities,
health/inventory or game code were modified. Layout/BIOS/execution compatibility
guards still apply, but they are not the cause of the reported missing slots.

## What caused the missing saves and what was preserved

Previously RunVR silently preferred `analysis/vr-baseline/saves` whenever that
directory existed. RunFlat used root `saves`. They were two independent stores,
even when both launched the same executable. The operator's latest VR slots
0/1/2 were therefore absent from Flat. The VR card 1 also contained progress
while the old root cards were empty; choosing by file modification date alone
would have selected the wrong card.

Cleanup promoted the complete current VR store — slots **0 through 6**, matching
thumbnails and both cards — into root `saves`. This retains the VR slot numbers.
Every overlapping old Flat file was backed up before replacement; all original
VR files were also preserved. Copies were checked by SHA-256, including complete
state/thumbnail pairs. No source state was edited or rebased.

Local recovery archive: `analysis/archive/workspace-cleanup-20261029/`.

| Archived item | Subdirectory |
|---|---|
| All previous Flat states/cards, including old MP slots | `previous-flat-saves/` |
| Complete original VR save store | `previous-vr-saves/` |
| Three benchmark binaries, matching manifests and nine test executables | `retired-executables/` |
| Retired `build-flat-check` tree | `retired-builds/build-flat-check/` |
| Old root runtime heartbeat/reports/freeze dumps | `root-runtime-dumps/` |
| Exact file hashes and move map | `cleanup-receipt.json` |

Archives are recovery/evidence material. Do not run their executables in place,
make normal launchers prefer them, or copy their build caches over the active
build. The old Flat build is archived, not a second maintained play target.

## Automated diagnostics — separate fixtures and disposable outputs

| Fixture source | Scope |
|---|---|
| `analysis/fixtures/sp/openbios/` | Internal slots 1 (missing world), 2 (severe performance), 3 (P38/petrol), 4 (Sten), 5 (historical indoor streaming/rendering) |
| `analysis/fixtures/mp/openbios/` | Preserved old MP calibration slots 0–4 |

These are explicit test inputs, not another personal play store. Probes copy
them into their own unique output directory and pass that copied directory as
`--memcard-dir` / `-MemcardDirectory`. They must never launch against the frozen
source itself or discover personal `saves/` as an implicit fixture source.
The old `analysis/vr-baseline/saves` directory no longer exists.

Internal slots 1/2 were deliberately added to this fixture library following the
new operator report, with state/thumbnail hashes preserved. They are not the
old MP slots 1/2. See [current cases](SP_CURRENT_REGRESSIONS.md) for scope and
the new priority; the cleanup receipt still describes its original capture date.

Headless RunVR now refuses to start without an explicit disposable save root.
Diagnostic build/run options must be explicit; there is no automatic
`build-flat-check` default or executable-name override. Normal RunVR uses only
the standard executable name. Profilers no longer launch sibling `--exe`
aliases. The offline symbol-report tool retains `--exe` solely to **read** a
preserved binary whose SHA-256 matches its historical receipt.

Put compiled test tools in their own ignored analysis output directory, never
beside the playable executable. If real execution-family work requires another
build, use clearly scoped temporary reference/candidate output directories,
complete matching assets/caches and valid per-profile fixtures under the HLE
policy. Preserve the operator's normal build and remove/archive the temporary
targets after qualification. Current profiling tools still need explicit
build/fixture selection support before those new-family comparisons.

Do not generate a fixture copy for every executable during normal play. Snapshot
a regression fixture deliberately when an issue needs it, record its provenance,
and keep that source fixed while the operator's own slots continue to change.

## Documentation and cleanup boundaries

Active entry points are this file, HANDOFF, VR_PLAN, PERFORMANCE_NEXT_STEPS,
NATIVE_REPLAY_PROFILE and the current implementation log. Four superseded
handoff/planning/performance reports moved to [archive](archive/README.md),
with relative links adjusted. Other named evidence reports and compact receipts
are retained because they establish bindings and completed work; they are not
alternate task queues.

Historical receipts retain the original paths/hashes used at capture time.
Those paths may now be archived. Do not rewrite old receipts to make them claim
they measured the new directory layout or a new binary. Use the cleanup map to
locate preserved material. No performance result or new headset acceptance is
claimed by reorganizing files.

Never bulk-delete `analysis`, `saves`, fixtures, BIOS/disc data, active build
dependencies or unrecognized files. Check running game processes and resolved
workspace paths before any recursive move. Preserve a verified recovery copy
before changing an overlapping save slot/card. Unrelated `.commandcode/` and
the reference game's checkout remain untouched.
