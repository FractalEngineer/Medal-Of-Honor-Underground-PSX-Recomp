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

All VR implementation and diagnostic files live under root `vr/`. No VR source
is wired into the current `psx-runtime` target yet. The existing flat executable,
its launcher, config, keys, and save path must remain launchable without a
headset or VR environment variable.

## Current state

The framework and UI gitlinks match the reference. Underground now has a
fail-closed engine map under `vr/underground/` with live-confirmed entity,
scene-transform, level-projection, and render-wait mappings. The default flat
build does not include them. `MOHU_VR_DIAGNOSTICS=ON` builds a read-only
diagnostic plugin that verifies function bytes before logging entry registers.
No OpenXR mode, launcher, or state-changing VR hook is active yet.
