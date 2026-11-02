# Underground VR release handoff

Updated 2026-11-03 for the `v0.1.1` Windows x64 native VR alpha.

## Release checkpoint

- Branch: `feature/vr-port`.
- Framework pin: `e57fd0279b86edf48cfe42364da4388046772bad`.
- Release backend: Windows x64, OpenGL, OpenXR enabled, guarded VR plugin
  enabled, debug tools and experimental performance kernels disabled.
- Flat and VR launchers use the same production executable and root `saves/`
  directory.
- Release behavior and player instructions are summarized in
  [ALPHA_README](../../ALPHA_README.md) and
  [v0.1.1 release notes](../release/v0.1.1.md).

## Accepted release surface

- OpenXR stereo gameplay with independent eye poses and motion-tracked head
  movement.
- Native videos, menus, briefing and frontend surfaces outside active gameplay.
- Tracked first-person weapons, shared shot/laser direction and native recoil,
  ammunition and collision behavior.
- Left-wrist health/compass HUD, under-fire damage marker ordering and
  fallback behavior.
- Tracked objective camera with physical placement accepted by the operator.
- Pause menu, Sten and music behavior accepted in the headset.
- Held sniper 2.5x zoom, native final-scope range, release/switch/pause/tracking
  recovery and movement while scoped verified in copied-save desktop/null-HMD
  runs.

## Open alpha gates

- Performance: demanding scenes remain below 60 fresh application frames per
  second. Existing plans and failed experiments are evidence, not permission to
  claim an improvement or rerun rejected work unchanged.
- Sniper: physical comfort, sustained rifle/laser alignment and final long-range
  visibility are not yet accepted.
- Weapons: broader impact, damage, final-origin and unavailable weapon fixtures
  remain open.
- Frontend and headset lifecycle: every transition, reconnect and tracking-loss
  path is not yet covered.
- Runtime coverage: Quest 3 with VDXR is the primary tested setup. SteamVR and
  Oculus launch paths exist but are not broadly accepted.

## Release verification

The current game tree records 173 passing Python tests plus focused scope,
input, HUD, frustum, weapon and calibrated-weapon C tests. The latest copied
Slot 01 scope run recorded 1,104 restoration checks with zero mismatches and a
clean process exit. See
[SCOPE_RANGE_EVIDENCE_20261103](SCOPE_RANGE_EVIDENCE_20261103.md) and the
[save-slot plan](SAVE_SLOT_FIX_PLAN_20261101.md).

Release packaging is built by `.github/workflows/release.yml` from the committed
generated C and pinned submodules. The Windows package includes OpenBIOS and the
runtime overlay toolchain; no disc, retail BIOS or personal saves are shipped.

## Documentation policy

- Keep player-facing claims in `ALPHA_README.md` and the versioned release notes.
- Keep current acceptance status here.
- Put superseded handoffs and dated session notes under `archive/`.
- Preserve compact proof under `vr/proof/`; keep bulk captures local under
  ignored `analysis/`.
- Do not describe desktop or null-HMD evidence as physical-headset acceptance.
