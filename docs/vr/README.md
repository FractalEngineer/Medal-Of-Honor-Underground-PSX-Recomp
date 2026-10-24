# VR Port Documentation

Medal of Honor: Underground is being ported from the current Medal of Honor
PSXRecomp VR implementation. The target must remain playable without a headset,
and every Underground-specific hook must be verified against this game's own
executable and live overlay content.

## Start here

1. [HANDOFF.md](HANDOFF.md) is the canonical current state and next-action file.
2. [VR_PLAN.md](VR_PLAN.md) defines scope, gates, and implementation order.
3. [BASELINE.md](BASELINE.md) records the exact source and target revisions,
   build configuration, and current verification status.
4. [ENGINE_EQUIVALENCE.md](ENGINE_EQUIVALENCE.md) tracks candidate function
   mappings and the evidence required before a hook can be registered.
5. [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) records completed work and
   reproducible checks.
6. [CAMERA_EVIDENCE.md](CAMERA_EVIDENCE.md) records the current camera-motion
   probe and its unresolved mapping work.
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

The framework and UI gitlinks match the reference. Underground now has a
fail-closed engine map under `vr/underground/` with seventeen live or
statically confirmed mappings, including the natural frame entry, PutDrawEnv,
the scene draw bridge, and the render wait. The default flat build does not
include them. `MOHU_VR_DIAGNOSTICS=ON` builds the opt-in diagnostic plugin.
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
now run through the offline input source; headset movement, multiplayer
fixtures, transitions, and the hand/wrist HUD remain active work.
