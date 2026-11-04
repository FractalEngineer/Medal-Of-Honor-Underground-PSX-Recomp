# Underground VR documentation

## Release status

`v0.1.1` is the first Underground Full 6dof VR alpha. It includes per-eye OpenXR
rendering, tracked weapons, the wrist HUD, objective-camera support, native
frontend restoration and the held sniper scope with native range.

Start with the player-facing [alpha guide](../../ALPHA_README.md) and
[v0.1.1 release notes](../release/v0.1.1.md). For setup paths and save
locations, see [WORKSPACE_LAYOUT](WORKSPACE_LAYOUT.md).
The [project documentation map](../README.md) lists the other entry points,
technical references and cleanup policy.

Current release status and open acceptance gates are summarized in
[HANDOFF](HANDOFF.md). The sniper behavior and its evidence are in
[SAVE_SLOT_FIX_PLAN_20261101](SAVE_SLOT_FIX_PLAN_20261101.md) and
[SCOPE_RANGE_EVIDENCE_20261103](SCOPE_RANGE_EVIDENCE_20261103.md).

## Current open work

- Demanding scenes still fall below the 60/90 fresh-frame target. Performance
  work and measured baselines remain in
  [PERFORMANCE_NEXT_STEPS](PERFORMANCE_NEXT_STEPS.md),
  [PERFORMANCE_ARCHITECTURE_PLAN](PERFORMANCE_ARCHITECTURE_PLAN.md) and
  [SP_CURRENT_REGRESSIONS](SP_CURRENT_REGRESSIONS.md).
- The sniper range, rifle/laser alignment and scope comfort need a focused
  physical-headset pass.
- Broader weapon impact, NPC damage and final-origin checks remain open in
  [SP_WEAPON_PARITY](SP_WEAPON_PARITY.md).
- Some frontend, reconnect and tracking-loss transitions need wider testing.

These are known alpha limits, not claims that the release is feature-complete.

## Documentation map

| Topic | Documents |
| --- | --- |
| Install, controls and limitations | [ALPHA_README](../../ALPHA_README.md) |
| Release notes | [v0.1.1](../release/v0.1.1.md) |
| Launch paths, saves and recovery | [WORKSPACE_LAYOUT](WORKSPACE_LAYOUT.md) |
| Current release checkpoint | [HANDOFF](HANDOFF.md) |
| Master implementation plan | [VR_PLAN](VR_PLAN.md) |
| Chronological implementation history | [IMPLEMENTATION_LOG](IMPLEMENTATION_LOG.md) |
| Framework branches and upstream work | [FRAMEWORK_UPSTREAM_TRACKER](FRAMEWORK_UPSTREAM_TRACKER.md) |
| Previous-game reuse | [REFERENCE_REUSE_AUDIT](REFERENCE_REUSE_AUDIT.md) |
| Weapon bindings and calibration | [WEAPON_MAPPING](WEAPON_MAPPING.md), [WEAPON_COMPLETE_PROFILES](WEAPON_COMPLETE_PROFILES.md) |
| SP gameplay repairs | [SP_GAMEPLAY_REPAIRS](SP_GAMEPLAY_REPAIRS.md), [SP_NATIVE_HOOK_EVIDENCE](SP_NATIVE_HOOK_EVIDENCE.md) |
| Pause, HUD and input | [PAUSE_MENU_PARITY](PAUSE_MENU_PARITY.md), [NATIVE_HAND_HUD](NATIVE_HAND_HUD.md), [FLAT_LOCAL_INPUT](FLAT_LOCAL_INPUT.md) |
| VR rendering and performance evidence | [OPENXR_EVIDENCE](OPENXR_EVIDENCE.md), [STEREO_VIEW_EVIDENCE](STEREO_VIEW_EVIDENCE.md), [RENDER_KERNEL_CHECKPOINT](RENDER_KERNEL_CHECKPOINT.md) |
| Historical reports | [archive index](archive/README.md) |
| Documentation ownership and index | [project documentation map](../README.md) |

Compact receipts under `vr/proof/` are retained evidence. Bulky captures and
logs live in the ignored local `analysis/` tree. Historical documents keep
their capture-date instructions and paths; they are not current task queues.
