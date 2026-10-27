# VR Port Documentation

Current SP repair and next priorities: [SP_PARITY_REPAIR.md](SP_PARITY_REPAIR.md).
The operator reopened muzzle placement, arms, slot-3 visibility and performance;
R1-R7 in VR_PLAN supersede old W6-first or headset-first continuation text.

Medal of Honor: Underground is being ported from the current Medal of Honor
PSXRecomp VR implementation. The target must remain playable without a headset,
and every Underground-specific hook must be verified against this game's own
executable and live overlay content.

## Start here

Shared framework branches, the merged upstream VR stack and the three pending
generic changes are tracked in [FRAMEWORK_UPSTREAM_TRACKER.md](FRAMEWORK_UPSTREAM_TRACKER.md).
Framework development uses `vr/shared-development`; master mirrors upstream.

1. [HANDOFF.md](HANDOFF.md) is the current execution contract: W5 desktop gates
   and W6.1 hand-fixed ray capture are complete. The shot and future laser share
   the hand-fixed aim ray; native recoil stays visual. W6.2 target triangle
   binding is next. Physical hand-aim/impact acceptance and live NPC/SP
   isolation remain separate open gates.
   [P38_NATIVE_AIM_EVIDENCE.md](P38_NATIVE_AIM_EVIDENCE.md) records the
   restored barrel, complete calibration, W4/W5.1 and automated native damage.
   [SHOT_FAMILY_EVIDENCE.md](SHOT_FAMILY_EVIDENCE.md) records the read-only
   all-ID constructor map, native shot types and shotgun pellet count.
   [SHOT_LIFECYCLE_EVIDENCE.md](SHOT_LIFECYCLE_EVIDENCE.md) records native
   trajectories, spread, damage and the final-origin writer mapping.
   [CANONICAL_MARKERS_EVIDENCE.md](CANONICAL_MARKERS_EVIDENCE.md) records the
   completed natural P1 animated-marker/timing contract and final-origin stages.
   [weapon-aim-all-receipt.json](../../vr/proof/weapon-aim-all-receipt.json)
   records the all-family desktop conversion.
   [WEAPON_PRESERVATION_EVIDENCE.md](WEAPON_PRESERVATION_EVIDENCE.md) and
   [weapon-preservation-receipt.json](../../vr/proof/weapon-preservation-receipt.json)
   record the paired native/tracked, fallback and impact acceptance.
   [COMBAT_STATE_EVIDENCE.md](COMBAT_STATE_EVIDENCE.md) records the paired
   reload/empty/switch/scoped/recoil/load desktop controls.
   [DEATH_RESPAWN_EVIDENCE.md](DEATH_RESPAWN_EVIDENCE.md) closes the P1
   death/native respawn/fresh-shot desktop supplement.
   [RENDERED_MUZZLE_EVIDENCE.md](RENDERED_MUZZLE_EVIDENCE.md) records W6.1's
   shared hand-fixed shot/laser ray, animation diagnostics and stereo controls. W6.2
   triangle/vertex binding is next; physical barrel alignment remains open.
   [WEAPON_COMPLETE_PROFILES.md](WEAPON_COMPLETE_PROFILES.md) records the
   all-ID topology, provisional calibration, desktop controls and moving-marker
   animation evidence.
   Headset verification must run under the interactive Windows account; see
   [the mandatory execution-context section](HANDOFF.md#headset-execution-context---mandatory).
2. [VR_PLAN.md](VR_PLAN.md) is the checkbox/status list and dependency order.
   Do not restart checked foundation/renderer work without a demonstrated regression.
   [REFERENCE_REUSE_AUDIT.md](REFERENCE_REUSE_AUDIT.md) maps every workstream
   to reusable first-game code and local counterparts; consult it before adding
   a new implementation. Hardware acceptance does not block isolated desktop work.
   [CONSISTENCY_HANDOFF.md](CONSISTENCY_HANDOFF.md) records the completed
   three-operation shared math and both-game runtime evidence.
3. [BASELINE.md](BASELINE.md) records the historical 2026-10-23 starting tree.
   Its old framework pin and no-VR state do not override the current handoff.
4. [ENGINE_EQUIVALENCE.md](ENGINE_EQUIVALENCE.md) tracks candidate function
   mappings and the evidence required before a hook can be registered.
5. [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) records completed work and
   reproducible checks.
6. [CAMERA_EVIDENCE.md](CAMERA_EVIDENCE.md) records the historical camera-motion
   probe. Use the current handoff/calibration documents for completed mappings;
   its earlier unresolved notes do not reopen those tasks.
7. [DRAW_BRIDGE_EVIDENCE.md](DRAW_BRIDGE_EVIDENCE.md) records the guarded
   overlay draw bridge and the boundary between renderer output and camera
   ownership.
8. [STEREO_OT_EVIDENCE.md](STEREO_OT_EVIDENCE.md) records the corrected frame
   entry, OT controls, and rejected eye-replay experiments.
9. [STEREO_VIEW_EVIDENCE.md](STEREO_VIEW_EVIDENCE.md) records the accepted
   same-checkpoint zero control and full-scene depth-parallax pair.
10. [PGXP_RENDER_VIEW_EVIDENCE.md](PGXP_RENDER_VIEW_EVIDENCE.md) records the
    full render-view, guest OT submission, projective near-plane path, and
    PGXP save-state flavor requirement.
11. [FLICKER_EVIDENCE.md](FLICKER_EVIDENCE.md) records the alternating
    black-pair cause and corrective scratch-buffer replay.
12. [OPENXR_EVIDENCE.md](OPENXR_EVIDENCE.md) records the opt-in headset frame
    lifecycle, native menu surface, headless pair checks, and timed compositor
    capture.
13. [HEAD_TURN_HUD_EVIDENCE.md](HEAD_TURN_HUD_EVIDENCE.md) records the 1080p
    default, per-eye level visibility, side-view coverage, and rollback-scoped
    removal of the flat HUD projection.
14. [SKY_GHOST_EVIDENCE.md](SKY_GHOST_EVIDENCE.md) isolates the extra native
    OT submission inside eye replay and records the same-binary correction,
    both HUD packet buffers, and submitted application-layer proof.
15. [MOVEMENT_EVIDENCE.md](MOVEMENT_EVIDENCE.md) records the reference control
    mappings, Underground calibration, input checks, and operator save workflow.

16. [FLAT_LOCAL_INPUT.md](FLAT_LOCAL_INPUT.md) records P1 Steam Controller /
    separate P2 keyboard setup for operator save preparation.

17. [WEAPON_MAPPING.md](WEAPON_MAPPING.md) is the current working handoff for
    multiplayer-first weapon pose mapping and its validation matrix.
    [WEAPON_COMPLETE_PROFILES.md](WEAPON_COMPLETE_PROFILES.md) owns the all-ID
    assembly masks, provisional calibrations and desktop control evidence.

The latest machine-ranked function candidates are in
[ENGINE_EQUIVALENCE_REPORT.md](ENGINE_EQUIVALENCE_REPORT.md). They are
discovery evidence only and must not be registered as hooks.

## Source of truth

The adjacent `Medal-Of-Honor-PSX-Recomp` checkout is the behavioral reference.
Its `AGENTS_VR.MD`, `docs/reverse/VR_HANDOFF.md`,
`docs/reverse/VR_PROJECTIVE_RENDERING.md`,
`docs/reverse/VR_SLOT2_PERFORMANCE.md`, and current `vr/` sources take priority
over historical plans and receipts.

The framework owns generic render transactions, PGXP projection, OpenXR, and
state restoration. Underground owns title-specific addresses, overlay identity,
player/camera layouts, hooks, input policy, weapon profiles, and HUD content.
`generated/` is generated output and must not be edited to implement VR.

All VR implementation and diagnostic files live under root `vr/`. VR sources are
wired only into opt-in `MOHU_VR_DIAGNOSTICS=ON` builds; the default target stays
on the base flavor and links no VR source. The existing flat executable, its
launcher, config, keys, and save path must remain launchable without a headset
or VR environment variable.

## Current state

Use the current framework/UI pins in HANDOFF, not the historical baseline.
Underground now has a
fail-closed engine map under `vr/underground/` with twenty live or
statically confirmed mappings, including the natural frame entry, PutDrawEnv,
the scene draw bridge, the render wait, and the first-person draw path. The
default flat build does not include them. `MOHU_VR_DIAGNOSTICS=ON` builds the
opt-in diagnostic plugin.
Frame-render replay now produces a byte-identical zero-offset pair and
full-scene parallax pairs from a complete `PSXModRenderView`. Guest `DrawOTag`
preserves packet provenance for PGXP homogeneous clipping, including a tested
forward/downward near-plane pose. Render-scoped signed-NCLIP counters now
receipt zero, lateral, pitch, and yaw poses with no precise-projection misses.
The OT-only and frame-driver paths remain controls, not stereo evidence. The
diagnostic plugin can now opt into OpenXR, obtain headset eye views, and submit
the verified pair. Normal VR launch now uses 1080p internal rendering, per-eye
world selection, and a temporary stereo-only suppression of the head-locked
flat HUD. The operator confirmed the sky fix. Reference movement/button maps
now run through the offline input source; physical headset movement, physical
multiplayer transitions and the hand/wrist HUD remain active work. The operator's four
multiplayer fixtures now have closed native inventory cycles and damage
receipts for 13 weapons. Weapon-position work uses those fixtures and the
stationary P2 target one weapon at a time; see
[WEAPON_MAPPING.md](WEAPON_MAPPING.md) and
[WEAPON_SET_EVIDENCE.md](WEAPON_SET_EVIDENCE.md).

The real first-person seam and P1-only MP desktop eye renderer are verified for
all 13 measured IDs. All IDs now have complete-gun masks, animated node captures,
provisional calibration and moving-marker animation evidence; 64 calibrated MP
controls pass in both eyes. Native recoil, reload, switch, scope and prop-action
samples show that the tip must be recomputed after animation. W1 is
complete for the P38 absolute synthetic head/hand
coordinate contract and is not a mesh-hook search. W2.1 measured the native MP
flat scene-list selector. W2.2 added its measured, separately guarded
eye-frustum override and passed a zero-angle both-eye control. W2.3 passed
zero, +/-90-degree and near-wall controls with populated world geometry,
per-eye selector decisions and clean rollback. W2.4 then verified the
separate MP converter, dispatcher, P1 action mask, axis records and response
curve. W2.5 expanded that path to both signs of every movement axis, seven
native button masks, focus recovery and native Start pause/resume, with zero
input samples during eye replay. Isolated SP and OpenXR-off flat controls also
pass. W3.1 then measured all 69 P38 node-13 vertices atomically, stored a
provisional animated-model grip/muzzle/axis/scale contract and kept it inert in
the renderer. C1-C4 and the shared ownership/test workflow are complete.
Physical size/attachment, physical MP controls, tracked shot alignment, exact
barrel laser and wrist HUD remain open under the ordered plan. See
[WEAPON_CALIBRATION.md](WEAPON_CALIBRATION.md),
[MP_LEVEL_SELECTOR_EVIDENCE.md](MP_LEVEL_SELECTOR_EVIDENCE.md),
[MP_EYE_FRUSTUM_EVIDENCE.md](MP_EYE_FRUSTUM_EVIDENCE.md),
[P38 pose receipt](../../vr/proof/weapon-pose-space-receipt.json) and
[P38 calibration receipt](../../vr/proof/weapon-p38-calibration-receipt.json),
[MP eye receipt](../../vr/proof/weapon-mp-eye-receipt.json).
