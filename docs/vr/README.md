# Underground VR documentation

**FIRST: continue MP weapon calibration/control parity in SP, G7b–G7f.** G7a
inventoried the shared 13-profile path and the frozen SP fixtures; naturally
reachable IDs are only 0, 13, 15 and 16. Panzerfaust first motion now follows the
hand under synthetic desktop controls, while petrol has no observed native throw
constructor and nine IDs lack SP fixtures. Follow
[SP_WEAPON_PARITY](SP_WEAPON_PARITY.md); the remaining parity scope is open.
Then return to the other reports: personal SP slot 1 is missing level rendering again; slot 2
has severe performance problems. Start with [current regressions](SP_CURRENT_REGRESSIONS.md)
and the updated HANDOFF. These open G5/G6 cases precede the preflight replacement;
old slot-5 evidence does not establish their cause or acceptance.
The operator means internal slots 1/2: files `slot01`/`slot02` and tool arguments
1/2. Do not renumber these reports or any historical slot references.

Updated 2026-10-29 after workspace/save cleanup. **Normal Flat and VR use the
same `build-release` executable and root `saves/` store.** The previous silent
VR redirect into analysis was removed; current VR saves were promoted with all
old Flat/VR files preserved. See [WORKSPACE_LAYOUT](WORKSPACE_LAYOUT.md) for
paths, recovery archives, frozen fixtures and the rules that prevent recurrence.

## Active instructions

Read these in order. Older evidence is not another execution queue.

1. [WORKSPACE_LAYOUT](WORKSPACE_LAYOUT.md): launch/save paths and cleanup map.
2. [HANDOFF](HANDOFF.md): acceptance, boundaries and the next exact task.
3. [VR_PLAN](VR_PLAN.md) and [SP_WEAPON_PARITY](SP_WEAPON_PARITY.md): authoritative
   checkboxes and the FIRST implementation sequence, including all 13 IDs.
4. [PERFORMANCE_NEXT_STEPS](PERFORMANCE_NEXT_STEPS.md): ordered P3c2-P3c6
   implementation/qualification, fixture constraints and budget decisions.
5. [NATIVE_REPLAY_PROFILE](NATIVE_REPLAY_PROFILE.md): completed attribution and
   rejected compiler experiments. Evidence, not instructions to rerun them.
6. [IMPLEMENTATION_LOG](IMPLEMENTATION_LOG.md): chronological changes and scope.

World/music, SP pause and Sten have operator headset smoke acceptance.
Performance remains unresolved: minimum 60 fresh application frames/s, 90
preferred. G7 weapon parity precedes that work. P3b is complete; the later performance candidate is preflight
`80011424`, then measured packet/HUD decisions and independent fresh views.
Cleanup did not change the game executable or establish an FPS improvement.
SP is the release target; MP is only a quick weapon-calibration fixture.

## Reference and retained evidence

| Topic | Documents |
|---|---|
| Shared framework branches / upstream work | [FRAMEWORK_UPSTREAM_TRACKER](FRAMEWORK_UPSTREAM_TRACKER.md) |
| Previous-game reuse / completed common work | [REFERENCE_REUSE_AUDIT](REFERENCE_REUSE_AUDIT.md), [CONSISTENCY_HANDOFF](CONSISTENCY_HANDOFF.md) |
| Weapon bindings and profiles | [WEAPON_MAPPING](WEAPON_MAPPING.md), [WEAPON_COMPLETE_PROFILES](WEAPON_COMPLETE_PROFILES.md), [ALPHA_WEAPON_REPAIRS](ALPHA_WEAPON_REPAIRS.md) |
| SP repairs / input | [SP_GAMEPLAY_REPAIRS](SP_GAMEPLAY_REPAIRS.md), [SP_NATIVE_HOOK_EVIDENCE](SP_NATIVE_HOOK_EVIDENCE.md), [FLAT_LOCAL_INPUT](FLAT_LOCAL_INPUT.md) |
| Pause / native hand HUD | [PAUSE_MENU_PARITY](PAUSE_MENU_PARITY.md), [NATIVE_HAND_HUD](NATIVE_HAND_HUD.md) |
| Disc provenance | [DISC_IMAGE_COMPARISON](DISC_IMAGE_COMPARISON.md) |
| Muzzle / shot / surface ray | [RENDERED_MUZZLE_EVIDENCE](RENDERED_MUZZLE_EVIDENCE.md), [SHOT_LIFECYCLE_EVIDENCE](SHOT_LIFECYCLE_EVIDENCE.md) |
| Older proposals and superseded reports | [archive index](archive/README.md) |

Other evidence reports remain to preserve measured bindings, math, failures
and completed gates. Historical paths/NEXT pointers describe their capture date.
Current HANDOFF/VR_PLAN/runbook take precedence. Compact receipts in `vr/proof/`
are immutable historical evidence; bulk captures remain local under `analysis/`.

Do not recreate benchmark executable aliases in `build-release`, launch tests
against personal saves, regenerate unchanged guest code, revisit the damaged
disc, or start a fresh MP feature campaign while following old reports.
