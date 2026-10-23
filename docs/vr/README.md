# VR Port Documentation

Medal of Honor: Underground is being ported from the current Medal of Honor
PSXRecomp VR implementation. The target must remain playable without a headset,
and every Underground-specific hook must be verified against this game's own
executable and live overlay content.

## Start here

1. [VR_PLAN.md](VR_PLAN.md) defines scope, gates, and implementation order.
2. [BASELINE.md](BASELINE.md) records the exact source and target revisions,
   build configuration, and current verification status.
3. [ENGINE_EQUIVALENCE.md](ENGINE_EQUIVALENCE.md) tracks candidate function
   mappings and the evidence required before a hook can be registered.
4. [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) records completed work and
   reproducible checks.

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

## Current state

The framework and UI gitlinks match the reference, but the target has no VR
sources, plugin package, launcher, or OpenXR build enabled. Engine landmark
mapping remains gated: no reference overlay address may be copied to Underground
without disassembly, live invocation evidence, and a runtime signature guard.
