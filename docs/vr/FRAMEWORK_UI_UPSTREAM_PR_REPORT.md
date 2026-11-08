# Recomp framework and UI upstream PR report

Date: 2026-11-08
Scope: the merged framework and UI upstream submissions, their cleanup, and
the delivered VR stack for context.

## Game-agnostic confirmation

All ten proposed PRs are game-agnostic at the implementation and public-contract
level. The included framework and UI commits contain no real game names or title
IDs, disc or executable hashes, asset paths, memory addresses, saved settings,
or title-specific branches. The only title-like string is the synthetic
`SLUS-TEST` identifier inside isolated parser fixtures. The game-specific
material in this report is evidence only: Underground runtime receipts, the
second-consumer parity check, and the title/CI runs used to validate the
changes. Those tests do not make the code depend on that game. Runtime validation
is not equally broad across every topic; the focused unit tests remain the
portability gate, with consumer runs supplying integration evidence.

## Snapshot

| Item | Revision / status |
| --- | --- |
| Game branch | `master` at pin commit `fa87fe1` |
| Framework checkout | `master` at upstream `64dff482` |
| UI checkout | `master` at upstream `29fa3d1` |
| Framework upstream | `RetroPortingToolKit/psxrecomp` master `64dff482` |
| UI upstream | `RetroPortingToolKit/recomp-ui` master `29fa3d1` |
| Framework local common base | `a7b37e079e8c6e98e04cd1cd42ba559e95911ea7` |
| UI local common base | `a95615751b413e043983944441ed8912066c65ce` |
| Overlapping upstream PRs before submission | None found by author/head-name checks |
| Submitted pull requests | Framework #841 through #849; UI #136; all merged |
| Delivered VR stack | PRs #739 through #746 are merged; do not recreate them |

The branch tips are linear development stacks on old bases. They are useful as
tested aggregates, but they are not suitable as one upstream PR. Cherry-pick
one topic at a time onto the current upstream heads and resolve integration
there.

Preserve these dirty/untracked items when rebasing:

- Root `game.toml`
- Untracked `.commandcode/`
- Framework edits in `runtime/include/mod_plugins.h`,
  `runtime/src/gpu_gl_renderer.c`, `runtime/src/psx_openxr.c`, and
  `runtime/tests/test_openxr_input.c`

The four framework edits are an uncommitted screen-overlay experiment. They are
not part of any commit in this report and are not PR-ready. Before the upstream
repin they were preserved in the named stash
`mkb/configurable-input pre-upstream-repin 2026-11-08`.

## Evidence sources

- Framework delivery status: [FRAMEWORK_UPSTREAM_TRACKER.md](FRAMEWORK_UPSTREAM_TRACKER.md)
- Shared geometry scope and consumers: [CONSISTENCY_HANDOFF.md](CONSISTENCY_HANDOFF.md)
  and [reference-parity-receipt.json](../../vr/proof/reference-parity-receipt.json)
- VR implementation history: [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md)
- M0 measurement behavior: [M0_REPORT.md](M0_REPORT.md) and
  [MEASUREMENT_CONTRACT.md](MEASUREMENT_CONTRACT.md)
- Mouse/keyboard feature and regression evidence:
  [MOUSE_KEYBOARD_HANDOFF.md](../controls/MOUSE_KEYBOARD_HANDOFF.md),
  [MOUSE_KEYBOARD.md](../controls/MOUSE_KEYBOARD.md), and
  [MOUSE_KEYBOARD_TEST_REPORT.md](../controls/MOUSE_KEYBOARD_TEST_REPORT.md)
- Release and CI result: [v0.1.2.md](../release/v0.1.2.md)

## Recommendation

The ten upstream PRs have been created and merged:

1. [#841](https://github.com/RetroPortingToolKit/psxrecomp/pull/841):
   Safe mod command registry initialization.
2. [#842](https://github.com/RetroPortingToolKit/psxrecomp/pull/842):
   OpenXR synthetic overrides in release builds.
3. [#843](https://github.com/RetroPortingToolKit/psxrecomp/pull/843):
   Synthetic hand age/origin controls.
4. [#844](https://github.com/RetroPortingToolKit/psxrecomp/pull/844):
   Shared VR geometry math.
5. [#845](https://github.com/RetroPortingToolKit/psxrecomp/pull/845):
   Signed NCLIP render counters.
6. [#846](https://github.com/RetroPortingToolKit/psxrecomp/pull/846):
   Function-entry hook preservation through native overlays.
7. [#847](https://github.com/RetroPortingToolKit/psxrecomp/pull/847):
   M0 frame-trace spans and asynchronous GPU samples.
8. [#848](https://github.com/RetroPortingToolKit/psxrecomp/pull/848):
   Captured mouse wheel delivery to local mouse policies.
9. [#849](https://github.com/RetroPortingToolKit/psxrecomp/pull/849):
   Framework mod binding and slider option metadata.
10. [#136](https://github.com/RetroPortingToolKit/recomp-ui/pull/136):
    UI binding capture and scaled slider presentation.

Do not submit `b1d729e5` as a feature PR. Its dependency bump is already present
on current upstream master (`recomp-net` `7a4d330e`, `retcomm-rbengine`
`28a2a472`).

## Created pull requests

All branches were rebuilt from the current upstream heads checked immediately
before submission. PR 9 contains two topic commits; every other framework PR
contains one. The UI PR depends on framework PR 9. Every row below is now merged.

| PR | Repository | Branch | Head | Status | Merge commit |
| ---: | --- | --- | --- | --- | --- |
| [#841](https://github.com/RetroPortingToolKit/psxrecomp/pull/841) | `psxrecomp` | `fix/mod-command-registry-startup` | `e29c1237` | Merged | `3d566496` |
| [#842](https://github.com/RetroPortingToolKit/psxrecomp/pull/842) | `psxrecomp` | `fix/openxr-release-test-overrides` | `7631fd93` | Merged | `a1d6863d` |
| [#843](https://github.com/RetroPortingToolKit/psxrecomp/pull/843) | `psxrecomp` | `vr-pr/synthetic-hand-origin-age` | `57e4d907` | Merged | `d8efdab7` |
| [#844](https://github.com/RetroPortingToolKit/psxrecomp/pull/844) | `psxrecomp` | `vr-pr/shared-vr-geometry` | `a52fded6` | Merged | `cbb95a15` |
| [#845](https://github.com/RetroPortingToolKit/psxrecomp/pull/845) | `psxrecomp` | `vr-pr/render-nclip-counters` | `2c391172` | Merged | `06533096` |
| [#846](https://github.com/RetroPortingToolKit/psxrecomp/pull/846) | `psxrecomp` | `vr-pr/native-overlay-function-hooks` | `958116b8` | Merged | `e2e75557` |
| [#847](https://github.com/RetroPortingToolKit/psxrecomp/pull/847) | `psxrecomp` | `vr/perf-counter-lookup` | `eae08d8d` | Merged | `a8f5f57f` |
| [#848](https://github.com/RetroPortingToolKit/psxrecomp/pull/848) | `psxrecomp` | `input/local-mouse-wheel-events` | `4070bf50` | Merged | `0f25e9ae` |
| [#849](https://github.com/RetroPortingToolKit/psxrecomp/pull/849) | `psxrecomp` | `mods/binding-and-slider-options` | `737bf0a0` | Merged | `15833933` |
| [#136](https://github.com/RetroPortingToolKit/recomp-ui/pull/136) | `recomp-ui` | `mods/binding-and-scaled-slider-controls` | `8db4f00` | Merged | `cc758119` |

Submission-time checks: both upstream remotes were refreshed immediately before
branch creation. All ten branches are based on the current upstream heads and
their pushed heads match the local topic branches. The code-only audit found no
real title names or IDs, disc or executable hashes, asset paths, saved settings,
or title-specific branches. PR 9 was reconciled with upstream's newer decimal
option type while retaining the new binding and slider metadata. The affected
framework tests were compiled and passed in `build-release` through a combined
PR 1 plus PR 9 validation branch; that temporary branch was then deleted and
the original submodule revisions and uncommitted framework experiment were
restored.

## Post-merge cleanup

The game now points `.gitmodules` at the RetroPortingToolKit upstream
repositories and records the upstream submodule heads:

| Item | Previous pin | Upstream pin |
| --- | --- | --- |
| `psxrecomp` | `3c1050e8` | `64dff482` |
| `recomp-ui` | `73dc1cb5` | `29fa3d1` |

Both local `master` branches track `origin/master`, and both fork `master`
branches match their upstream head. The merged PR branches and patch-equivalent
local/remote branches were deleted. The `mkb/configurable-input` branches with
unique work and the two unique shelf branches were retained. The dirty framework
experiment is recoverable from the named stash recorded above.

## Commit ledger

There are 13 commits outside the local common bases. Twelve map to the proposed
PRs; one is obsolete against upstream.

| # | Repo | Commit | Date | Subject | PR disposition |
| ---: | --- | --- | --- | --- | --- |
| 1 | psxrecomp | `a39f46b4` | 2026-10-24 | Instrument render-path signed NCLIP decisions | Framework PR 5 |
| 2 | psxrecomp | `f80033dd` | 2026-10-26 | Preserve synthetic hand age and origin overrides | Framework PR 3 |
| 3 | psxrecomp | `cdfdb73c` | 2026-10-26 | Add shared VR geometry math | Framework PR 4 |
| 4 | psxrecomp | `b1d729e5` | 2026-10-31 | Update netplay and capture engine dependency pins | Omit; already upstream |
| 5 | psxrecomp | `e696907e` | 2026-10-31 | Preserve VR hooks through native overlays | Framework PR 6 |
| 6 | psxrecomp | `e57fd027` | 2026-10-31 | Allow VR overrides in release builds | Framework PR 2 |
| 7 | psxrecomp | `0e4c7c5f` | 2026-11-06 | Deliver captured mouse wheel events to local input policies | Framework PR 8 |
| 8 | psxrecomp | `03ec8d2a` | 2026-11-06 | Support configurable mod bindings and integer sliders | Framework PR 9 |
| 9 | psxrecomp | `6b0ae62d` | 2026-11-07 | Support decimal display scales for integer mod sliders | Framework PR 9 |
| 10 | psxrecomp | `3c1050e8` | 2026-11-07 | Initialize mod command registry safely before main | Framework PR 1 |
| 11 | psxrecomp | `ad57c1bc` | 2026-10-30 | Add M0 measurement spans and async GPU samples | Framework PR 7 |
| 12 | recomp-ui | `5fe69597` | 2026-11-06 | Add mod binding capture and sensitivity sliders | UI PR 10 |
| 13 | recomp-ui | `73dc1cb5` | 2026-11-07 | Display decimal values on scaled mod sliders | UI PR 10 |

## Proposed upstream PRs

### PR 1: Initialize the mod command registry safely before `main()`

**Repository:** `RetroPortingToolKit/psxrecomp`
**Proposed branch:** `fix/mod-command-registry-startup`
**Commits:** `3c1050e8`

**Draft title**

`runtime: initialize mod command registration before static construction`

**Draft description**

Current behavior: command registration uses a namespace-scope `std::mutex` and
command array. A C plugin constructor can call `psx_mod_register_command()`
before that C++ translation-unit storage is constructed. On GCC 16 this
surfaced as `std::system_error` before `main()` in a Windows release package.

Desired behavior: construct command storage and its mutex together on first use
through a function-local registry. Preserve the existing limited command table,
duplicate replacement, reply-buffer termination, and missing-command result.
Add a focused regression whose constructor registers before `main()`.

Tested: `test_mod_command_startup` exercises registration before `main()`,
duplicate replacement, successful execution, missing commands, and invalid
names. The game-side CI run `42288651175` passed the six title checks and
published v0.1.2 with this fix.

### PR 2: Honor OpenXR synthetic overrides in release builds

**Repository:** `RetroPortingToolKit/psxrecomp`
**Proposed branch:** `fix/openxr-release-test-overrides`
**Commits:** `e57fd027`

**Draft title**

`openxr: honor synthetic test overrides in release builds`

**Draft description**

Current behavior: `PSX_NO_DEBUG_TOOLS` removes the getter-side synthetic input
and hand override paths. Release packages therefore silently ignore overrides
that were successfully installed, preventing deterministic release-build
headset-state tests.

Desired behavior: always honor an installed override in the OpenXR getter path,
clear it during shutdown, and keep the real tracking path unchanged when no
override is installed. Add a release-mode compile fixture with
`PSX_NO_DEBUG_TOOLS=1`.

Tested: `openxr_override_release_test` checks synthetic input and both hand
poses in a release-definition build and checks clean shutdown. The game release
evidence also records 171 VR Python/compiled-fixture checks, the release
override test, a normal launcher smoke, and clean rollback.

### PR 3: Add synthetic hand age and origin controls

**Repository:** `RetroPortingToolKit/psxrecomp`
**Proposed branch:** `vr-pr/synthetic-hand-origin-age`
**Commits:** `f80033dd`

**Draft title**

`vr: make synthetic hand age and tracking origin testable`

**Draft description**

Current behavior: the debug hand override always rewrites `age_ms` to zero and
cannot control origin validity or origin pose. That makes stale-hand, lost
tracking, and recenter/origin cases difficult to reproduce deterministically.

Desired behavior: accept `age_ms`, `origin_valid`, optional origin position, and
optional origin quaternion in the debug override. Validate the complete request
before mutating state. Preserve the supplied age and origin in synthetic
snapshots; retain the existing real-tracking behavior when overrides are off.

Tested: `test_openxr_input` covers a 151 ms age, resetting to zero, partial
flags, invalid pose rejection without mutation, focus loss, and shutdown. The
game-side pose harness also includes the invalid-stale 151 ms case.

### PR 4: Add shared VR geometry math

**Repository:** `RetroPortingToolKit/psxrecomp`
**Proposed branch:** `vr-pr/shared-vr-geometry`
**Commits:** `cdfdb73c`

**Draft title**

`vr: share inverse, visibility, and ray-box geometry helpers`

**Draft description**

Current behavior: consumers duplicate 3x3 inverse, conservative eye-space box
visibility, and slab ray/box intersection code. The copies have drifted in
threshold checks, malformed-input handling, and failure-output behavior.

Desired behavior: publish a small pure-C VR geometry module with:

- policy-controlled 3x3 inverse
- conservative eight-corner visibility
- validated slab ray/box intersection

Keep title-specific transforms, masks, selector policy, memory readers, and
fallbacks in the games. Outputs are written only on success.

Tested: the 33-case cross-game parity harness covers inverse policies, singular
and non-finite matrices, forward/behind/side/plane-crossing boxes, Q12 and
precise view paths, asymmetric projection, MP expansion, and positive,
negative, parallel, reversed, and malformed rays. Both consumers built in
Release, both flat/OpenXR-off configurations linked, and runtime receipts for
Underground and the reference title passed their affected controls.

### PR 5: Expose signed NCLIP render decisions as counters

**Repository:** `RetroPortingToolKit/psxrecomp`
**Proposed branch:** `vr-pr/render-nclip-counters`
**Commits:** `a39f46b4`

**Draft title**

`vr: expose signed NCLIP render-path decisions`

**Draft description**

Current behavior: render-scoped signed-NCLIP correction is observable only
through widescreen precise-NCLIP telemetry or by attaching a debugger. It is
difficult to tell whether a missing face was a precise-projection miss, a sign
correction, or an ordinary zero/positive/negative result.

Desired behavior: add always-on named counters in the render-projective path:
total, precise, miss, corrected, positive, negative, and zero. Keep the existing
facing correction unchanged.

Tested: `test_gte_register_access` checks both windings and every counter
transition. Five real 60-pair Underground snapshots recorded zero precise
projection misses; corrected decisions ranged from 14,950 to 18,396.

### PR 6: Preserve function-entry hooks through native overlays

**Repository:** `RetroPortingToolKit/psxrecomp`
**Proposed branch:** `vr-pr/native-overlay-function-hooks`
**Commits:** `e696907e`

**Draft title**

`runtime: keep function-entry hooks visible to native overlay routing`

**Draft description**

Current behavior: generated and interpreted backends call configured
function-entry hooks, but cached native overlay shards can execute the same
entry directly. A title/mod hook can therefore be skipped or run at a different
time depending on whether the overlay is native or interpreted.

Desired behavior: expose an alias-aware query for whether an address has an
active mod or netplay entry hook. If it does, native overlay dispatch leaves the
entry to the interpreter so the hook runs exactly once. Clearing the active plan
must release the guard.

Tested: `test_mod_runtime` checks alias matching, unrelated addresses, no guard
before activation, and guard removal after clear. Underground's native-overlay
runtime controls advanced native calls while retaining fresh stereo pairs,
expected weapon/arm vertices, zero eye failures, and zero rollback mismatches.
The release build retained 27 function hooks and 11 instruction hooks.

### PR 7: Add M0 frame-trace spans and asynchronous GPU samples

**Repository:** `RetroPortingToolKit/psxrecomp`
**Proposed branch:** `vr/perf-counter-lookup`
**Commits:** `ad57c1bc`

**Draft title**

`vr: add snapshot, XR, host-preparation, and async GPU frame-trace spans`

**Draft description**

Current behavior: frame traces distinguish the guest eye work but do not
separate snapshot extraction/publish, `xrLocateViews`, host view/hand
preparation, or later-retrieved GPU work. GPU samples can be mistaken for the
current frame's CPU time.

Desired behavior: add `snapshot_extract`, `snapshot_publish`, `xr_locate`, and
`host_prep` stages plus asynchronous `gpu_scene_us`, `gpu_present_us`, and
`gpu_sample_age_frames`. Never fold GPU samples into CPU spans. Include the new
columns in JSON/CSV and document when the timer ring is enabled.

Tested: `test_frame_trace` covers stage ordering, JSON/CSV output, GPU values,
and sample age. Fourteen analyzer tests passed. Real M0 runs on two scenes
recorded CPU stages and GPU samples retrieved three host frames later; slot 2
reported 58.80 Hz and slot 5 reported 60.04 Hz.

### PR 8: Deliver captured mouse wheel events to local mouse policies

**Repository:** `RetroPortingToolKit/psxrecomp`
**Proposed branch:** `input/local-mouse-wheel-events`
**Commits:** `0e4c7c5f`

**Draft title**

`input: forward captured mouse wheel events to local mouse policies`

**Draft description**

Current behavior: local mouse policies receive motion and button events but not
wheel input, so titles cannot offer rebindable wheel actions while the mouse is
captured.

Desired behavior: add a `PSX_MOD_MOUSE_WHEEL` event carrying normalized scroll
detents. Deliver it only while the policy is captured and eligible, with finite
value and timestamp validation. Preserve SDL's flipped-wheel direction
normalization and ignore wheel input outside capture.

Tested: `local_mouse_policy_test` covers captured wheel delivery, rejected
delivery after release, and non-finite/timestamp guards. The game-side P38
control used explicit wheel debug input to change the clip and select petrol;
physical wheel events, SDL2, and non-Windows hosts were not separately proven.

### PR 9: Add configurable binding and numeric slider metadata

**Repository:** `RetroPortingToolKit/psxrecomp`
**Proposed branch:** `mods/binding-and-slider-options`
**Commits:** `03ec8d2a`, `6b0ae62d`

**Draft title**

`mods: support binding and numeric slider option metadata`

**Draft description**

Current behavior: mod manifests can expose boolean, choice, integer, and text
options, but no binding control and no presentation hint that an integer is a
slider. Consumers also cannot request decimal presentation without changing the
stored integer value.

Desired behavior:

- Add manifest format 12 `binding` options with one to three alternatives.
- Accept portable key, mouse-button, and optionally wheel tokens.
- Reject malformed tokens, out-of-range codes, empty slots, duplicate
  alternatives, and wheel input unless explicitly allowed.
- Add `slider` metadata for integer options.
- Add manifest format 13 `display_divisor` for integer sliders, requiring a
  power of ten from 1 through 1,000,000 while persistence remains exact.
- Expose the metadata through the launcher provider without changing older
  option layouts' zero-initialized behavior.

Tested: `test_mod_binding_options` covers format gating, all token classes,
wheel permission, slider bounds, three alternatives, persistence/reload, and
invalid divisor/manifests. The consuming game passed root CTest 5/5, live
rebinding from W to I and reset to W, independent sensitivity sliders, and
17/17 firearm/scope/crossbow regression cases. The live launcher displayed
`1.25` for stored integer `125`.

### PR 10: Render mod binding capture and scaled integer sliders

**Repository:** `RetroPortingToolKit/recomp-ui`
**Proposed branch:** `mods/binding-and-scaled-slider-controls`
**Commits:** `5fe69597`, `73dc1cb5`
**Depends on:** framework PR 9

**Draft title**

`launcher: render binding capture and scaled mod sliders`

**Draft description**

Current behavior: the launcher renders boolean, choice, integer, and text mod
options. It has no binding capture widget and no decimal presentation for an
integer slider.

Desired behavior: render the new binding option as three capture slots. Click
to capture; Escape cancels; right-click clears; Reset restores the manifest
default. Accept keyboard, mouse-button, and manifest-authorized wheel input.
Render integer options marked as sliders with range and step enforcement. When
`display_divisor` is greater than one, display the precise integer through a
decimal scale while sending the exact integer back to the provider.

Tested: the consuming game built and passed CTest 5/5. A real launcher session
captured Forward from W to I, persisted `key:12`, reset to W, changed global
sensitivity from 5 to 7 while aiming remained 4, and displayed the decimal zoom
slider as `1.25`. The 17/17 gameplay regression suite passed at the new
defaults.

## Already delivered

Do not recreate PRs #739 through #746. Their branch stack is already merged.

| PR | Delivered service | New topic commits |
| --- | --- | --- |
| [#739](https://github.com/RetroPortingToolKit/psxrecomp/pull/739) | Opt-in stereo/XR frame attribution | `8400b55d`, `4f40f6f3`, `89161e93` |
| [#740](https://github.com/RetroPortingToolKit/psxrecomp/pull/740) | Bounded shedding and deadline recovery | `0cdf9595` |
| [#741](https://github.com/RetroPortingToolKit/psxrecomp/pull/741) | One guest checkpoint per eye pair | `4419d234` |
| [#742](https://github.com/RetroPortingToolKit/psxrecomp/pull/742) | Paired HUD matte capture/readback | `e4f1f985`, `ea3b1e32` |
| [#743](https://github.com/RetroPortingToolKit/psxrecomp/pull/743) | Synthetic head translation/pitch | `18d52c8b`, `6c9d618f` |
| [#744](https://github.com/RetroPortingToolKit/psxrecomp/pull/744) | Ambiguous-origin diagnostics | `689f3b34` |
| [#745](https://github.com/RetroPortingToolKit/psxrecomp/pull/745) | Precise eye poses and near-camera clipping | `510560e5`, `182073bc` |
| [#746](https://github.com/RetroPortingToolKit/psxrecomp/pull/746) | XR readiness without the debug server | `ebca6c5a`, `910c4760` |

## Consumer pin checkpoints

These root commits record the framework/UI revisions consumed by the game. They
are useful provenance, but they are not upstream framework PRs.

| Game commit | Framework pin | UI pin |
| --- | --- | --- |
| `9130dad` initial scaffold | `379565a6` | `0546fbcf` |
| `d4a10ce` OpenBIOS emitter checkpoint | `6118cd95` | unchanged |
| `7fcb0ca` framework pin refresh | `31df2e1e` | `7c635c6b` |
| `f3c3f0b` performance integration | `b1d729e5` | `a9561575` |
| `9158200` direct MKB controls | `e57fd027` | unchanged |
| `b1794eb` editable MKB bindings | `0e4c7c5f` | `5fe69597` |
| `38668df` v0.1.2 source release | `6b0ae62d` | `73dc1cb5` |
| `daba7ac` early command registration | `3c1050e8` | unchanged |
| `fa87fe1` upstream repin | `64dff482` | `29fa3d1` |

## Submission order

1. **Framework PR 1** first. It is a release startup bug and independent of VR.
2. **Framework PR 2**, so release-build synthetic-state tests are meaningful.
3. Merge the independent VR pieces in this order: **PR 3**, **PR 4**, **PR 5**,
   **PR 6**, then **PR 7**. Each should get its own branch from current
   upstream; do not rebase the whole linear stack as a single submission.
4. Merge **PR 8**, then **PR 9**, then **UI PR 10**. The UI change must not be
   proposed before the framework ABI is accepted.
5. Omit `b1d729e5`. Current upstream already has the same dependency revisions.

## PR checklist

- Recreate each branch from current upstream, not from the old common base.
- Cherry-pick only the named topic commits. Do not submit the aggregate branch
  tip, which also contains unrelated earlier topics.
- Exclude `game.toml`, `.commandcode/`, and the four uncommitted framework VR
  experiment files.
- Run focused unit tests with `BUILD_TESTING=ON`.
- Build with two compile jobs and run an OpenXR-off link check where an API is
  generic.
- For VR-rendering changes, rerun the affected consumer controls and one
  rollback/refusal path; do not claim new physical acceptance without a headset
  run.
- For the binding API, add a recomp-ui screenshot/headless case before opening
  the cross-repository PR pair.
- Record source, executable, and evidence hashes in the PR description when a
  runtime receipt is reused.
- Re-check open upstream PRs immediately before submission; neither repository
  currently has an overlapping open PR, but both masters have advanced.
