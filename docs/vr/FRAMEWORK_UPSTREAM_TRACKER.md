# Shared VR framework and upstream PR tracker

Updated: 2026-10-27. This file tracks framework delivery, not game feature
acceptance. [VR_PLAN.md](VR_PLAN.md) owns Underground completion status.

## Branch contract

- Framework fork: `https://github.com/FractalEngineer/psxrecomp`.
- Shared development: [`vr/shared-development`](https://github.com/FractalEngineer/psxrecomp/tree/vr/shared-development),
  currently `555e1eabccc59b9b6ff0d9fca48aca783513dc86`.
- Fork `master` mirrors upstream `RetroPortingToolKit/psxrecomp`; verified tip
  `1a3fc0db303adcef9b6999747f90c30fb25da50f`. Do not commit VR development to master.
- Both games remain pinned to tested framework `555e1eab`. No rebase, checkout,
  code regeneration or consumer pin update was performed by the branch move.
- `.gitmodules` still names `master` for remote-update convenience. Ordinary
  submodule initialization uses the committed SHA. Do not use `submodule update
  --remote` to advance these games: mirror master lacks the three pending changes.
  Select and validate an explicit shared-development commit instead.
- Complete implementation first. Then prepare separate feature branches against
  the current upstream base, run focused framework tests and both affected game
  consumers, and open individual PRs only when requested. No new PR is open for
  the three changes below; proposed branch names are not existing submissions.

## Pending generic changes

| Proposed PR / branch | Existing commit | Scope and evidence | Status |
| --- | --- | --- | --- |
| Render NCLIP diagnostics / `vr-pr/render-nclip-counters` | [`d9b0f382`](https://github.com/FractalEngineer/psxrecomp/commit/d9b0f382) | Render-pass total/precise/miss/corrected/sign counters in `gte.cpp`; register-access fixture. Existing facing correction predates this instrumentation. Review counter cost before submission. | Preserved on shared development; no PR |
| Synthetic hand freshness/origin / `vr-pr/synthetic-hand-origin-age` | [`b982e66e`](https://github.com/FractalEngineer/psxrecomp/commit/b982e66e) | Debug override accepts age, origin validity, origin position/quaternion; injected snapshots preserve age. OpenXR input fixture plus Underground stale/loss/recenter controls. Real tracking behavior is not replaced. | Preserved on shared development; no PR |
| Shared geometry math / `vr-pr/shared-vr-geometry` | [`555e1eab`](https://github.com/FractalEngineer/psxrecomp/commit/555e1eab) | Pure inverse, conservative eye-space box visibility and slab ray/box intersection; public header/build wiring/tests. Both games consume the same source hash and retain title policies. | Preserved on shared development; no PR |

These changes contain no guest addresses, title IDs, weapon calibration or game
assets. Their commits are already separated by topic, but are a linear stack on
the old common base `31df2e1e`. Do not present each old tip as an independent PR
against today's master: cherry-pick only its intended change into its own new
branch and resolve current-upstream integration there. Keep the tested aggregate
branch and game pins until replacement revisions pass their consumer gates.

Shared math evidence: [consistency handoff](CONSISTENCY_HANDOFF.md) and
[33-case/both-consumer receipt](../../vr/proof/reference-parity-receipt.json).
Neither source parity nor a branch move proves physical weapon alignment.

## Earlier VR stack — merged, not pending

GitHub API status checked 2026-10-27: all eight PRs are **merged**. Their draft
text in the first-game `docs/reverse/VR_UPSTREAM_PR_DRAFT.md` is historical.
Do not recreate or resubmit this stack.

| PR | Delivered service | Merge commit |
| --- | --- | --- |
| [#739](https://github.com/RetroPortingToolKit/psxrecomp/pull/739) | Opt-in stereo/XR frame attribution | `fcf5dbe9` |
| [#740](https://github.com/RetroPortingToolKit/psxrecomp/pull/740) | Bounded shedding/deadline recovery | `ba5a6091` |
| [#741](https://github.com/RetroPortingToolKit/psxrecomp/pull/741) | One guest checkpoint per eye pair | `4be0669d` |
| [#742](https://github.com/RetroPortingToolKit/psxrecomp/pull/742) | Paired HUD matte capture/readback | `eb659c1b` |
| [#743](https://github.com/RetroPortingToolKit/psxrecomp/pull/743) | Synthetic head translation/pitch | `ca60f089` |
| [#744](https://github.com/RetroPortingToolKit/psxrecomp/pull/744) | Ambiguous-origin diagnostics without recentering | `e4301fb8` |
| [#745](https://github.com/RetroPortingToolKit/psxrecomp/pull/745) | Precise eye poses/near-camera clipping | `2338ce09` |
| [#746](https://github.com/RetroPortingToolKit/psxrecomp/pull/746) | XR readiness without TCP debug server | `31df2e1e` |

The latest upstream tip also contains unrelated rendering, CD, audio, save and
mod API work. The 94 commits beyond the common base (including merges) are not
94 pending VR changes. Integrate upstream deliberately in the shared branch;
do not change either consumer merely to match a moving master.

## Parity review and delivery boundaries

- C1-C4 remain complete: shared geometry has one implementation and documented
  wrapper differences. Both games currently use `555e1eab` and source SHA-256
  `9e51708f0f05a16182e4d5893063a06f656d4fc723965f72cea9191632661a23`.
- First-game aim conversion/guards and trace collectors are reusable. Its
  `vr/psx_vr_stereo.c` writes a common aim pose and does not prove preservation
  of Underground's six-pellet spread or thrown/rocket/bolt lifecycle.
- Underground W3.4 all-ID profiles and animated-marker evidence are complete.
  W4/W5.1 certify the bounded P38 contract. W5.3's all-ID family discovery is
  complete, as are its native lifecycle baseline and final projectile origin
  writer measurements. Canonical animated sampling is now complete within its
  [measured timing/ownership contract](CANONICAL_MARKERS_EVIDENCE.md).
  Family-aware writes, paired preservation/impact and the W5.4 desktop
  combat-state controls and headless P1 death/native respawn supplement are
  complete, as is W6.1's per-eye rendered-muzzle capture. W5.4d operator
  alignment remains. The 2026-10-28 SP repair now takes priority; R4/R4b native
  callback integration and bounded production cadence are complete. Fog is
  paused on fixture selection; live SP impact is next before W6.2. These
  title-specific samplers add no pending framework PR or master change.
- SP P38 render/shot bindings and copied SP fixtures are now available. W5.2
  still requires linked live-NPC isolation/damage and broader SP family coverage. Physical W3.3/W3.5 and W5.4 operator acceptance remain open. Desktop work
  continues without treating those gates as implementation prerequisites.
- Keep game hooks, model masks, moving markers, shot-family policy and native
  layout/calibration in the game. Future generic fixes belong on the shared
  framework branch once, then reach both consumers through tested pins.
