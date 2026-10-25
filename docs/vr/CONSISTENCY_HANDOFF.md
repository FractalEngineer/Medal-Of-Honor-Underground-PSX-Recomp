# Cross-game VR consistency pass

Updated: 2026-10-26. Requested after the
[reference reuse audit](REFERENCE_REUSE_AUDIT.md). This file specifies the next
implementation handover; this documentation session does not implement the
refactor. [VR_PLAN.md](VR_PLAN.md) owns C1-C4 status. W2.3 remains the next
feature task after this bounded pass. Completed W1/W2.1/W2.2 stay closed.

## Answer: what was duplicated, and what was a valid port?

There are parallel copies and alternate implementations worth reconciling.
Source comparison proves overlap and divergence; it does not prove whether an
author wrote a routine from memory or deliberately adapted it. Do not call all
Underground work wasted or replace every difference with first-game code.

Reference root:
`C:/Users/titan/Desktop/Github_Projects/Mine/Medal-Of-Honor-PSX-Recomp`.
Target root:
`C:/Users/titan/Desktop/Github_Projects/Mine/Medal-Of-Honor-Underground-PSX-Recomp`.
Baseline revisions and dependency pins are recorded in the reuse audit; re-read
Git state before editing. Both projects must remain independently buildable and
packagable. Never make a release depend on the adjacent game checkout.

| Area | Evidence and classification | Disposition |
| --- | --- | --- |
| Matrix inverse | Reference `moh_vr_matrix_inverse` in `vr/moh_vr_aim.c`; local `vr_laser_inverse` in `vr/underground/vr_diagnostic.c`. Same cofactor algorithm, different rejection policies and failure-output behavior. | Consolidate the pure calculation; keep verified game/caller limits in wrappers. |
| Conservative box visibility | Reference `moh_vr_box_visible` and local `mohu_vr_box_visible` implement the same corner/plane logic. Local MP adds center/radius and view validation. | Share the pure eye-space box test; keep MP adapter, ownership and code guards local. |
| Slab ray/box intersection | Reference `moh_vr_ray_box`; local `mohu_vr_ray_box` adds pointer/range validation. Tree traversal is substantially the same SP layout. | Share the pure slab test, retain stronger validation. Leave target memory readers/traversal local in this pass. |
| Laser projection/line clipping | Both plugins have `vr_laser_project`/`vr_laser_clip` variants with equivalent formulas, different inputs/globals and checks. | Characterize against the framework projection contract now; defer extraction until W6 consumes the rendered muzzle. Similar source is not proof the formula is correct. |
| Input | Local `input.c` is already a reference-style port. Native converter center +/-37/clamping differs from reference thresholds. Menu/buttons/deadzone/inverse lookup are mostly copied policy. | Preserve native response functions. Add a parity/difference record; do not replace the mapper or move title button policy into the framework. |
| Weapon transforms | Reference transforms producer vertices through `moh_vr_weapon_transform`; local W1 composes absolute pose into scoped GTE RT/TR. Both call shared `vr_pose_to_transform`. | Keep tested title adapters. Align spaces/units/failure contract and tests, not the hook or storage representation. No W1 rewrite. |
| Legacy local helpers | `mohu_vr_weapon_relative_delta` and `mohu_vr_weapon_rotate_node_q12` have only declaration/definition/test references in the current `vr/` search. `compose_gte_control` still has a live diagnostic caller. | Record the call graph. Do not migrate unused prototypes into shared code or delete live direct-delta controls. Cleanup can be a separate small change after scope/consumer verification. |
| Headless tools | Both `headless_steamvr.py` files share null settings/OpenVR capture. Local code has additional blank-capture/temporal controls and tests. | Preserve the local improvements and documented port lineage. Do not overwrite either file wholesale to make the files match. |
| Shared pose/XR/PGXP services | Framework pose math/header and mod API header are already byte-identical. Transactions, surfaces and projection already live in the framework. | Reuse them. No duplicate renderer, OpenXR backend, pose-origin system or surface API. |
| Exact triangles / native hand HUD | These exist in the reference, but local exact-triangle laser/HUD port is still future work. | These are missed reuse opportunities, not two finished implementations to refactor now. Port current code during W6/H1 with target data. |

The input port's history explicitly says "Add reference VR movement" at
`2fad9aa`. The SP visibility port entered at `ab8ce00`; local box-pointer work
at `a5185d1`. Current production comparisons must use the latest sources, not
those historical commits as a reset target.

## C1 - characterize before replacing anything (NEXT)

1. Read this file, the reuse audit and current handoff. Read applicable rules in
   both repositories, and framework `AGENTS.md`/`CLAUDE.md` before framework edits.
   Preserve existing documentation changes and unrelated `.commandcode/`.
2. Record branch/HEAD, dirty paths, framework/UI gitlinks and build flags for both
   games. Inspect current framework diffs; do not reset or force both projects to
   one old pin. Take a compact source/hash baseline and retain existing receipts.
3. Add one host-only parity harness that compiles each game's current helpers
   behind distinctly named test adapters and feeds the same numeric vectors.
   It must not boot a game, modify saves/settings or depend on private assets.
   Proposed new local entry point: `vr/tools/check_reference_parity.py` with
   explicit `--reference-root` and a fresh ignored output directory; this file
   does not exist yet. Keep adapters/fixtures under `vr/tests/`.
4. For a helper currently static in the plugin, use a narrow test seam or extract
   the unchanged pure function first, checking it before changing the algorithm.
   Do not compile/execute the whole game plugin just to test a matrix inverse.
   Do not maintain a third handwritten implementation as the parity oracle.
5. Record exact match, expected policy difference or unexpected disagreement for
   each case. Mathematical identities and declared contracts provide independent
   assertions; agreement between two copied bugs is insufficient.
   Do not invoke an old raw helper outside its supported input domain (for
   example a null pointer when it dereferences unconditionally). Test rejection
   at its adapter boundary and mark the raw case unsupported, not a parity pass.

Minimum vectors:

- Inverse: identity, scaled/sheared W1 matrix, translation reconstruction,
  singular/nearly singular, non-finite and threshold-edge inputs. Check `M*inv`
  against identity and no unintended writes when a wrapper rejects.
- Visibility: forward/behind/side, box crossing a plane, eye rotation/translation,
  precise versus Q12 paths, asymmetric focal/principal point, saturation and both
  512x240 and MP 540x120 bounds. Match visibility and fallback decisions.
- Slabs: positive/negative/parallel rays, origin inside, near/far boundaries,
  nearest/range cases, reversed bounds, null and non-finite inputs. Define the
  invalid-input contract instead of silently inheriting weaker checks.
- Input characterization: valid/invalid/focus-loss buttons/menu/merge policy;
  compare native converter outputs per title rather than requiring those outputs
  to match. Do not route the reference's native threshold into Underground.
- Projection characterization: zero and asymmetric center deltas, H/ref=1 and
  133/400, with nonzero OFX/OFY; compare each laser helper to the actual framework
  GTE projection contract. Any mismatch is a recorded follow-up, not permission
  to alter global projection during this refactor.

Known inverse differences must be made explicit: reference rejects determinant
magnitudes above 64 and inverse coefficients above 8; local has no upper
determinant bound and permits coefficients up to 64. The local loop can partially
write its output before rejecting; the reference computes into a temporary.
Decide wrapper/output policy from callers and tests, not from which file is older.

**C1 exit:** executable numeric fixtures plus a compact difference table. No
guessed native hook, hardware result or new acceptance claim is required.

## C2 - one small shared implementation

First batch is exactly three pure operations: **3x3 inverse, conservative box
visibility and slab ray/box intersection**. Reuse current algorithms and improve
their shared validation only where C1 specifies the behavior. No generic scene
graph, input manager, weapon framework or renderer redesign.

- Put the reusable numeric implementation/tests in `psxrecomp`, following its
  rules. Inspect existing math homes first; if none fits, use one small VR
  geometry-math module. Expose no guest addresses, memory access or title assets.
- Keep small source-compatible adapters in each game. Wrappers retain differing
  inverse limits, measured dimensions and title-specific failure/native fallback.
  The generic inverse should compute into temporaries; test any resulting change
  in observable failure-output behavior explicitly.
- Keep SP/MP selectors, traversal layouts, masks, queues, calibrated input
  response, weapon profiles, RT/TR packing and native hooks in their games.
- Both games must consume the same shared helper implementation/revision through
  intentional framework dependency updates. Update provenance; do not require
  every unrelated dependency revision to become identical. Do not copy source
  through sibling paths or leave one game silently using its old calculation.
- Preserve Underground's signed-NCLIP and hand-origin/age additions and the
  reference's accepted behavior. Do not drop existing framework work to simplify
  pin alignment. Keep any necessary framework changes reviewable as their own
  diff; no force resets or unexplained dirty submodule pointers.
- Do not move the projection/laser origin, native-shot path, HUD, Python runtime
  ownership or input mapper into this first batch. The parity manifest records
  their remaining duplication and future owner. Three pure operations is the bound.

**C2 exit:** both game adapters use the shared core; C1 vectors pass; remaining
differences are intentional and recorded. If a helper cannot preserve its
contract, leave that extraction pending with the exact failed vector and stop
that part rather than weakening its acceptance gate.

## C3 - verify both consumers

- Run the common module's focused tests and both games' inverse/frustum/raycast
  fixtures, including malformed input and plane-crossing cases. Confirm flat
  configurations still link with optional VR disabled.
- Build each game in its existing build directory with its own intended flags;
  do not reuse one game's binary/cache/save root for the other.
- Because inverse/visibility/raycast affect images, run one affected-path
  diagnostic batch per changed consumer: same-fixture zero/lateral/side views,
  current weapon controls and real rollback/failure recovery. Use the current
  receipts' recipes and title-specific copied fixtures, not old document paths.
  Underground retains W1/MP/SP controls; reference retains its accepted world and
  weapon path. Do not rerun unrelated combat/HUD/performance campaigns.
- Compare pre/post observable outputs for this refactor. Publish new receipts
  with both source revisions, shared-core revision, wrappers/policies, flags,
  executable hashes and remaining limits. Keep historical receipts unchanged.
- Leave debug OFF in each normal build, no owned processes, source saves/settings
  unchanged, normal feature defaults unchanged. A docs-only or host-only run
  cannot close this runtime gate. No headset run is needed for a claimed
  behavior-preserving math extraction; changed physical behavior needs its own
  acceptance and is outside this pass.

**C3 exit:** both consumers build and pass their affected regressions. A green
Underground build alone does not prove cross-game consistency.

## C4 - prevent another split, then resume W2.3

Retain a compact `vr/proof/reference-parity-receipt.json` (planned new file)
with shared operations, adapters, policy differences, hashes, tested vectors,
consumer checks and deferred operations. Keep a repeatable host-only command.
Add an appropriate check to both projects' existing test workflow so shared
math changes exercise both policies; do not invent a new build/test orchestrator.

Document the same source-of-truth rule in both game handoffs: fix shared math
once in the framework; keep measured bindings in title adapters; label a copied
tool with its origin and meaningful local differences. A later generic fix must
reach both consumers or explicitly record which consumer remains pending.

Then update C1-C4 evidence/status and set NEXT back to **W2.3**. No feature gate
was completed by the consistency pass. No commit/push is implied by this
documentation handover; obey the user's current authorization at execution time.

## Limits and recovery

- Do not reopen mesh discovery, reconstruct MP replay, retune calibration or
  enable tracked shots/HUD to complete this pass.
- Do not make the first game canonical for a game-specific difference or a
  suspected bug; use measured/native contracts and independent assertions.
- Keep parity tests about observable numeric behavior, not source formatting,
  line count, symbol names or requiring all files to be identical.
- If access/build/fixture availability blocks one consumer, record exactly
  which C item remains open and what can still run. Do not claim both games
  validated, silently omit the consumer or ask for source-save replacement
  before trying existing compatible copied fixtures.
- Same failed hypothesis twice: retain evidence and choose the missing fact;
  no repeated rebuild/test loop with unchanged inputs.

Current continuation: **C1 not started**. Documentation only. W2.3 remains the
next feature task; all runtime sources, builds and existing receipts are unchanged.
