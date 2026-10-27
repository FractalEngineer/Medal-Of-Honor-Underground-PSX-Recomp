# Reference-game reuse audit

Reviewed: 2026-10-26. This is a documentation and source comparison, not a new
runtime or hardware test. [VR_PLAN.md](VR_PLAN.md) owns task status;
[HANDOFF.md](HANDOFF.md) owns the next experiment. No acceptance box was closed
by this review.

Follow-up: the owner requested reconciling existing duplicated helpers too.
[CONSISTENCY_HANDOFF.md](CONSISTENCY_HANDOFF.md) defines C1-C4, which are complete.
The task dependencies below describe this audit's historical checkpoint; use
[HANDOFF.md](HANDOFF.md) and [VR_PLAN.md](VR_PLAN.md) for the current
continuation. [FRAMEWORK_UPSTREAM_TRACKER.md](FRAMEWORK_UPSTREAM_TRACKER.md)
records generic changes, both consumer pins and merged/pending upstream work.

## 2026-10-28 repair review (current precedence)

The original audit identified reusable work but the SP implementation did not
carry the full reference pattern through. Follow R1-R7 in VR_PLAN and section 1
of HANDOFF, not the historical W2.3/serial priority below. The new evidence is
[SP_PARITY_REPAIR.md](SP_PARITY_REPAIR.md).

| Area | Existing first-game solution | Underground discrepancy / current repair |
| --- | --- | --- |
| Held draw | `vr_weapon_geometry_filter` + `vr_weapon_vertices_filter` in `vr/psx_vr_stereo.c`: scope the weapon, transform after animation, restore before other entities | SP initially changed an earlier dispatcher and omitted its post-animation adapter. Now apply at `80090954` and mask/projected-tip capture at `80090A78`. |
| Weapon only | Native face filtering using validated profile gun islands; mixed nodes retain suppressor/barrel islands | MP already had a validated projected-vertex equivalent, but SP left arms visible. SP now reuses the same local profile/mask; P38 keeps 96 and masks 142 vertices, including loss fallback. |
| Precision | Uniform weapon-coordinate and eye-translation enlargement avoids native H/2 rejection without changing apparent scale | Now adapt the reference precision rule with a bounded Q12 power-of-two factor. Shot coordinates remain unscaled. |
| Muzzle placement | Reference laser captures the actual scoped weapon affine/view. Its native muzzle flash has no separate packet-relocation function in the reviewed source. | The old SP flash also used a color-source address as bank 0's tag, so that visible bank never moved while bank 1 supplied successful counters. It added a second fixed-400 projection and used static markers. Now use the actual projected animated tip, avoiding duplicate projection math. Reference calibration/IDs are still not portable data. |
| Scene visibility | Existing frustum/PGXP correction, with native geometry and state restoration | Slot 3 also exhausted the native primitive arena before the gun draw. This target-specific cause was measured at `8009086C`; a guarded spare native-bank region now restores the held draw. |
| Performance | `VR_SLOT2_PERFORMANCE.md`: separate production OFF from detailed debug ON, VERIFY separately, report actual pairs and guest cadence | The playable checkpoint retained debug ON and the launcher uses an interpreter-only analysis config. Restore production OFF and measure matched windows; native cached config currently skips VR hooks and gives zero pairs. Instrumentation integration remains R4. |
| Plan status | Separate physical acceptance, desktop controls and shipping defaults | Removed stale “physical next”, “no SP binding” and W6-first pointers. Real SP NPC damage, fog, broader scenes/families and physical acceptance remain open. |

No framework, first-game source, gitlink or generated guest C was modified by
this repair. Shared geometry helpers retain their existing ownership and pins.

## Finding

The plan was too serial and did not name enough reusable implementations.
Desktop tracked-aim development need not wait for physical headset acceptance.
Triangle intersection, native HUD extraction, hand surfaces and weapon-control
tooling already exist in the first game. Port their algorithms and test
structure, then verify Underground's bindings and data. Do not design those
systems again.

Several earlier measurements were still necessary. Underground's converter
differs, its first-person assets differ, and its MP world selector is a flat
scene list rather than the SP tree. Existing W1/W2.1/W2.2 results stay closed.
This review does not justify rewriting their working implementation.

## Exact sources and precedence

| Checkout | Source observed in this review |
| --- | --- |
| Reference | `../Medal-Of-Honor-PSX-Recomp`, HEAD `b33a7d96d596214233d3aef5ecacbf3736ad29e3`, VERSION `0.1.6` |
| Reference framework / UI | `31df2e1e0e0a6525733e68ff70e72ecbef84bb09` / `7c635c6b366a6e0d5d3c913a7fce6ec04dd9f256` |
| Underground | HEAD `2b3cbd8` at review start; W1 and W2.1-W2.2 already committed |
| Underground framework / UI | `b982e66e2536eaf738fbe3021db4d8f6c0feb90b` / same UI as reference |

The framework history is `31df2e1e -> d9b0f382 -> b982e66e`: Underground adds
signed-NCLIP instrumentation and synthetic-hand age/origin controls. Its
`runtime/src/vr_pose_math.c`, `runtime/include/vr_pose_math.h` and
`runtime/include/mod_plugins.h` are byte-identical to the reference checkout.
This is evidence that those sources/APIs can be reused, not that every backend
file or runtime result is identical.

Read the reference [AGENTS_VR.MD](../../../Medal-Of-Honor-PSX-Recomp/AGENTS_VR.MD),
[current handoff](../../../Medal-Of-Honor-PSX-Recomp/docs/reverse/VR_HANDOFF.md)
and [alpha backlog](../../../Medal-Of-Honor-PSX-Recomp/docs/reverse/VR_ALPHA_TODO.md)
with their later corrections. They describe historical release pins such as
`9b2100fe`; those are not instructions to change either current checkout.
The reference `docs/VR_PLAN.md` is explicitly historical. Some feature plans
contain implemented outcomes followed by obsolete proposed steps: use current
source and the latest outcome first.

## Reuse decisions for the complete plan

| Underground scope | Reuse / current implementation | Only remaining Underground work |
| --- | --- | --- |
| B1-B5: plugin, stereo, PGXP, OpenXR, transactions | Already integrated through the shared framework and guarded plugin. Reference projective/render-pass design applies. | Keep existing checks; do not scaffold another renderer, backend, checkpoint or SDK. |
| B6-B8: scale, sky, SP visibility, input, menus | Already ported. SP uses the reference tree/frustum model. `input.c` follows `moh_vr_input.c`; headless runtime helper is already local. | Preserve accepted defaults; validate changed paths only. |
| M1-M11: mesh inventory, P1 MP eyes, native damage | Already measured and tested locally. Reference MP bench provides the same architectural pattern. | No new inventory, seam search or renderer project unless a specific regression appears. |
| W1: pose spaces | Completed local absolute P38 controls plus existing framework pose math. Reference aim code already demonstrates full scaled-matrix inversion. | Keep the completed contract. W3 replaces provisional physical markers; it does not repeat W1. |
| W2.3: visibility validation | Local `mohu_vr_mp_box_visible` already calls the shared local box/frustum math. Local head controls, eye capture and rollback helpers exist. Reference head-turn checks supply test cases. | Extend the existing MP control with turn/near-wall cases; compare native/override output. No new selector implementation. |
| W2.4-W2.5: MP input | Reuse local `mohu_vr_input_map`, `mohu_vr_menu_input_map` and the reference mode-specific calibration selection pattern. | Verify MP player/converter/table bindings and integrate them into the existing source callback. Do not implement a second mapper or guest movement system. |
| W3: calibration/profiles | Reuse reference profile validation, mixed-node face checks, model-scale controls and batch runner structure. Local 13-ID full meshes already have profiles. | Set measured Underground grip/scale/muzzle data and test animations. Reference IDs, node selections and calibration numbers are not portable asset data. |
| W4: native shot binding | Reuse reference constructor-to-basis strategy, ownership/freshness guard structure and streaming trace analysis. | Locate the Underground MP equivalents and verify fields/units/first motion before writes. No need to discover the aiming architecture again. |
| W5: tracked native aim | Adapt reference pure conversion and guarded basis-hook pattern, using a single declared mesh/muzzle-to-world contract. | Replace addresses/IDs/fields and validate opt-in desktop controls. Physical impact acceptance remains separate. |
| W6: exact laser | Port `moh_vr_ray_tri`, appropriate bounded traversal and fixtures; reuse reference rendered-affine capture/project/clip/beam/dot structure. Local box raycast/project/clip already exist. | Bind actual Underground triangle records/vertex tables and capture the actual rendered weapon muzzle. MP bounds are not triangle records. |
| H1-H2: hand HUD/native surfaces | Reuse dual-matte RGBA extraction, per-hand fallback and FACE_HEAD surface submission. Generic APIs are already present. | Bind Underground HUD producers, owned text/packets, cutout regions and mode support. Keep menus/subtitles separate. |
| B9-B10, Q1-Q4: hardware, coverage, performance, release | Reuse reference trace/report/package workflow and existing framework readiness/copy/color behavior. | Test Underground scenes, transitions, runtimes and extracted package. First-game hardware/performance receipts do not certify this title. |

## Implementation entry points: open these before adding code

All reference paths below are in the adjacent first-game checkout. They are
source entry points, not commands to run against Underground unchanged.

| Work | Reference sources / functions | Local starting point |
| --- | --- | --- |
| Visibility | [moh_vr_frustum.h](../../../Medal-Of-Honor-PSX-Recomp/vr/moh_vr_frustum.h), [head visibility result](../../../Medal-Of-Honor-PSX-Recomp/docs/reverse/VR_HEAD_VISIBILITY_FIX.md) | [frustum.h](../../vr/underground/frustum.h), `vr_mp_frustum_filter`; `set_head`/`capture_eyes` in [pose tools](../../vr/tools/check_weapon_pose_spaces.py) and ownership in [MP control](../../vr/tools/check_mp_view.py) |
| Input | [moh_vr_input.c](../../../Medal-Of-Honor-PSX-Recomp/vr/moh_vr_input.c), `vr_controller_source` in [reference plugin](../../../Medal-Of-Honor-PSX-Recomp/vr/psx_vr_stereo.c) | [input.c](../../vr/underground/input.c), `vr_controller_source` in [local plugin](../../vr/underground/vr_diagnostic.c), [movement tool](../../vr/tools/check_movement.py) |
| Profiles / batches | [moh_vr_weapons.h](../../../Medal-Of-Honor-PSX-Recomp/vr/moh_vr_weapons.h), [profile checks](../../../Medal-Of-Honor-PSX-Recomp/vr/check_weapon_profiles.py), [pose checks](../../../Medal-Of-Honor-PSX-Recomp/vr/check_weapon_pose.py), [batch runner](../../../Medal-Of-Honor-PSX-Recomp/vr/weapon_batch.py) | [weapon.c](../../vr/underground/weapon.c), [inventory/pose tool](../../vr/tools/inspect_weapon_sets.py); retain full meshes until a separate gun-only filter is requested |
| Aim math | [moh_vr_aim.c](../../../Medal-Of-Honor-PSX-Recomp/vr/moh_vr_aim.c): `moh_vr_matrix_inverse`, `moh_vr_aim_shot`; [aim fixtures](../../../Medal-Of-Honor-PSX-Recomp/vr/test_moh_vr_aim.c) | Existing `vr_laser_inverse`, local weapon math and [W1 contract](WEAPON_CALIBRATION.md); adapt bounded helpers instead of another matrix implementation |
| Native shot hook | Reference plugin: `vr_cache_camera`, `vr_mp_level_entry`, `vr_shot_basis_entry`; [aim trace tool](../../../Medal-Of-Honor-PSX-Recomp/vr/check_weapon_aim.py) | Measured MP P1 ownership, native damage trace and local copied-save tools; shot constructor/basis binding remains unmeasured |
| Laser | [moh_vr_raycast.h](../../../Medal-Of-Honor-PSX-Recomp/vr/moh_vr_raycast.h), [raycast fixtures](../../../Medal-Of-Honor-PSX-Recomp/vr/test_moh_vr_raycast.c); reference plugin `vr_laser_capture`/`vr_laser_draw` | [raycast.h](../../vr/underground/raycast.h), `vr_laser_project`/`vr_laser_clip`/`vr_laser_draw`; local path currently casts boxes and uses right aim |
| HUD | [moh_vr_hud.c](../../../Medal-Of-Honor-PSX-Recomp/vr/moh_vr_hud.c), [HUD fixtures](../../../Medal-Of-Honor-PSX-Recomp/vr/test_native_hud.c), [matte verification](../../../Medal-Of-Honor-PSX-Recomp/vr/verify_native_hud.py), [gameplay checks](../../../Medal-Of-Honor-PSX-Recomp/vr/check_native_hud_gameplay.py) | [hud_packets.h](../../vr/underground/hud_packets.h), existing native-menu path; capture/surface APIs in [mod_plugins.h](../../psxrecomp/runtime/include/mod_plugins.h) |
| Coverage / performance | [world stability](../../../Medal-Of-Honor-PSX-Recomp/vr/check_world_stability.py), [trace exporter](../../../Medal-Of-Honor-PSX-Recomp/vr/trace_frames.py), [hitch report](../../../Medal-Of-Honor-PSX-Recomp/vr/hitch_report.py), [slot-2 findings](../../../Medal-Of-Honor-PSX-Recomp/docs/reverse/VR_SLOT2_PERFORMANCE.md) | Existing local headless helper, receipts and launcher; port reporting and configuration, not old FPS claims or alternate build folders |

Do not copy reference scripts wholesale: they contain SLUS-00974 save names,
old build paths, mode-specific addresses, shot IDs, arena ranges and, in some
cases, diagnostic ammo edits that are not authorized for these Underground
fixtures. Reuse control/analysis functions with explicit target parameters.

## Corrections to task dependencies

1. **W2.3 remains the next feature task, after C1-C4.** Complete its bounded visibility validation using the
   already implemented override. No completed gate is reopened by this audit.
2. **W2.4 is a mode adapter, not a new input implementation.** The local callback
   currently reads SP roots, code and calibration tables. That is why MP binding
   validation is necessary even though the pure mapper exists.
3. **W3 desktop preparation precedes one hardware batch.** W3.1/W3.2/W3.4 can
   progress without a headset; W3.3/W3.5 remain physical acceptance. Expand local
   profile data and controls; do not rerun mesh discovery for all 13 IDs.
4. **W4 read-only mapping does not require working XR locomotion or physical
   calibration.** The native pad/copied MP fixture already supports fire controls.
   If W2 is concretely blocked, record its continuation and use W4.1 as the
   explicit independent task. Do not abandon W2 silently.
5. **W5 desktop implementation may use a declared provisional calibration after
   W4 and the W3.1 desktop contract.** Require a separate opt-in diagnostic flag,
   native fallback, negative controls and unchanged normal defaults. Hardware
   acceptance gates normal enablement and physical accuracy claims, not writing
   or testing an isolated candidate. W5.4 retains physical impact acceptance.
6. **W6 algorithms do not depend on physical acceptance.** Port and fixture-test
   them with verified geometry and a declared muzzle contract, then batch physical
   alignment with weapon testing. Unknown MP geometry stays unsupported rather
   than borrowing SP addresses or calling a box hit triangle-exact.

This is a dependency graph, not permission for unbounded side projects. Finish
the current task or record a specific blocker before selecting an independent
one. HUD/performance remain later priorities; their reusable architecture is
recorded now so nobody invents it later.

## Target facts that prevent blind copying

- **Assets and IDs differ.** Underground ID 0 P38 is 14 nodes / 354 faces;
  reference ID 0 Luger is 14 nodes / 348 faces. A matching ID or node count is
  insufficient. Mixed arm/gun nodes and suppressor islands need local face data.
- **Native input math differs.** Underground SP uses center +/-37 with a clamped
  response lookup; the reference converter uses another threshold. Local input
  math already handles this. MP still needs its own live binding check.
- **MP world selection differs.** Local W2.1 found 21 level objects in a flat
  26-node scene list. An SP 1000-leaf queue is not its replacement.
- **A scaled matrix is expected.** Full inverse math already exists in the
  reference and local laser code. W1 still had to measure Underground's actual
  scaled/sheared basis, RT Q12, integer TR and authored placement.
- **Calibration is data.** Reference 850 units/metre, pivot `(80,150,100)` and
  projection precision 16 are reference settings, not measured P38 calibration.
  Do not replace the working local H133/ref400 relationship by copying them.
- **Reference aim is not a solved barrel alignment contract.** Its pure aim
  helper starts from the action-space aim pose. Reuse the inverse/angle/guard
  logic, but W5/W6 must share the declared rendered-muzzle origin/axis. Physical
  barrel-to-hit validation is still open in the reference backlog too.
- **The current local laser camera cache is render-only.** `vr_laser_capture_level`
  requires active eye replay. A simulation shot needs a fresh canonical P1 camera
  cache outside replay, as in the reference `vr_cache_camera` pattern. Do not
  reuse a last-eye camera merely because an inverse is available.
- **Exact triangles require real triangle tests.** The reference has both box
  and triangle paths; the bottom of its laser plan still describes the earlier
  box proposal. Reuse current source and fixtures, review bounds/indices and
  origin-inside behavior, and bind target geometry before claiming an exact hit.
- **HUD services already exist.** Current API is
  `psx_mod_render_capture_rgba_pair` plus `psx_mod_openxr_surface` and
  `PSX_MOD_OPENXR_SURFACE_FACE_HEAD`. Use dual mattes and per-hand fallback.
  Do not apply the historical framework patch again or build separate surface
  swapchains; that experiment is superseded. Native capture rectangles, text
  ownership and SP/MP support are target data.
- **Hardware and coverage remain title-specific.** Reference visual acceptance,
  wrist placement and playable assessment do not certify Underground combat,
  transitions, wider sectors, other runtimes or performance.

## Review coverage and changes

Inventoried all 48 Markdown files under the reference `docs/` (623,196 bytes),
including the reverse-engineering documents. Read current authority and relevant
feature contracts; searched chronological status/performance logs and older
plans for implemented outcomes, corrections and remaining limits. Checked the
current source entry points above rather than treating every historical step
as work still to do. Reviewed Underground's plan, handoff, mapping/evidence,
calibration, index and corresponding code.

The review covers stereo/projection, OpenXR/lifecycle, head visibility,
input/movement/combat, weapon profiles/aim/laser, HUD/native surfaces, cadence,
performance, diagnostics, release and evidence retention. Long historical logs
remain reference material; this audit is not a claim that every historical
experiment or hardware result was reproduced.

Updated the plan/handoff/mapping/index and stale equivalence-table guidance.
Corrected the frustum document's wording: reject a box only if all its corners
are outside one plane, not unless all corners pass every plane. No source,
framework pin, binary, save, setting or historical receipt changed. No games,
builds or hardware sessions were launched for this review.
