# Project Documentation

Updated 2026-11-09 for the `v0.1.3` Windows x64 VR and Mouse/Keyboard alpha.
This directory is the central index for retained project documentation.

## Start here

| I need to... | Read |
| --- | --- |
| Understand the project or build it | [Project README](../README.md) |
| Install, play or report an alpha issue | [Player guide](../ALPHA_README.md) |
| Check what shipped in the current alpha | [v0.1.3 release notes](release/v0.1.3.md) |
| Configure mouse and keyboard gameplay | [MKB controls](controls/MOUSE_KEYBOARD.md) |
| See current acceptance and open gates | [Release handoff](vr/HANDOFF.md) |
| Find launches, saves and recovery files | [Workspace layout](vr/WORKSPACE_LAYOUT.md) |
| Browse VR implementation and evidence | [VR documentation index](vr/README.md) |
| Review storage and cleanup candidates | [Workspace cleanup audit](WORKSPACE_CLEANUP_AUDIT.md) |
| Find superseded session notes | [Archive index](vr/archive/README.md) |

## Documentation ownership

Each entry point has one job. Summaries in other documents should link back
here instead of becoming independent installation or status instructions.

| Document | Owns |
| --- | --- |
| [Project README](../README.md) | Project overview, legal boundary, release downloads and build flow |
| [Player guide](../ALPHA_README.md) | Installation, controls and player-facing alpha limitations |
| [v0.1.3 release notes](release/v0.1.3.md) | Versioned release summary and package expectations |
| [Release handoff](vr/HANDOFF.md) | Current acceptance surface, verification and open gates |
| [Workspace layout](vr/WORKSPACE_LAYOUT.md) | Executable, launcher, save, fixture and cleanup policy |
| [VR plan](vr/VR_PLAN.md) | Technical program, accepted checkpoints and remaining work |
| [Implementation log](vr/IMPLEMENTATION_LOG.md) | Chronological implementation record |
| [Archive index](vr/archive/README.md) | Superseded handoffs and historical reports |

## VR port

- [Current release handoff](vr/HANDOFF.md)
- [VR documentation index](vr/README.md)
- [Workspace and save locations](vr/WORKSPACE_LAYOUT.md)
- [Master implementation plan](vr/VR_PLAN.md)
- [Implementation log](vr/IMPLEMENTATION_LOG.md)
- [Framework upstream tracker](vr/FRAMEWORK_UPSTREAM_TRACKER.md)
- [Reference-game reuse audit](vr/REFERENCE_REUSE_AUDIT.md)
- [Historical archive](vr/archive/README.md)

## Technical reference

- [Verified baseline](vr/BASELINE.md)
- [Engine equivalence](vr/ENGINE_EQUIVALENCE.md)
- [Generated engine report](vr/ENGINE_EQUIVALENCE_REPORT.md)
- [Camera pose evidence](vr/CAMERA_EVIDENCE.md)
- [OpenXR bootstrap](vr/OPENXR_EVIDENCE.md)
- [Stereo view](vr/STEREO_VIEW_EVIDENCE.md)
- [Stereo OT output](vr/STEREO_OT_EVIDENCE.md)
- [PGXP render view](vr/PGXP_RENDER_VIEW_EVIDENCE.md)
- [Draw bridge](vr/DRAW_BRIDGE_EVIDENCE.md)
- [Alternating black-pair investigation](vr/FLICKER_EVIDENCE.md)
- [Head-turn HUD](vr/HEAD_TURN_HUD_EVIDENCE.md)
- [Stick grenade SP behavior](vr/STICK_GRENADE_SP_EVIDENCE.md)
- [Render kernel checkpoint](vr/RENDER_KERNEL_CHECKPOINT.md)
- [Static world decoder](vr/STATIC_WORLD_DECODER.md)
- [Native replay profile](vr/NATIVE_REPLAY_PROFILE.md)
- [VR source and diagnostic workspace](../vr/README.md)
- [Engine adapter implementation map](../vr/underground/README.md)
- [Performance campaign](vr/PERFORMANCE_NEXT_STEPS.md)
- [Performance architecture plan](vr/PERFORMANCE_ARCHITECTURE_PLAN.md)

## Game reference

- [Default controls](DEFAULT_CONTROLS.md)
