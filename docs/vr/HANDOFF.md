# VR Port Handoff

Last updated: 2026-10-24

This is the canonical current-state handoff for the Underground VR port. Update
it before ending every implementation session.

## Repository state

| Item | Value |
| --- | --- |
| Target branch | `feature/vr-port` |
| Last game-tree checkpoint | `0d9d22c` |
| Current framework implementation | `d9b0f382` |
| Target base | `7fcb0ca35af683ac38c4c501347d59916a924aa4` |
| Reference branch | `master` |
| Reference commit | `b33a7d96d596214233d3aef5ecacbf3736ad29e3` |
| `psxrecomp` gitlink | `d9b0f382` |
| `recomp-ui` gitlink | `7c635c6b366a6e0d5d3c913a7fce6ec04dd9f256` |
| Reference version | `0.1.6` |
| Underground version | `0.1.0` |
| Game ID | `SLUS-01270` |

Framework `d9b0f382` adds render-scoped signed-NCLIP counters and their GTE
contract coverage. This game-tree checkpoint retains the five-pose PGXP counter
receipt in the linked evidence. The only unrelated untracked workspace entry is
`.commandcode/`. Do not add or modify it as part of VR work.

The verified PGXP fixture is isolated slot `2` under
`analysis/vr-baseline/saves/`. It was created by the operator with the PGXP
build and copied from the default save root; the base-flavor `slot00` files
remain untouched. Slot `1` is retained as a stale-identity control.

## Non-negotiable invariants

- All VR implementation, tools, tests, and integration files live under root
  `vr/`.
- All retained VR documentation lives under `docs/vr/`.
- The flat executable must launch without a headset, VR environment variable, or
  VR diagnostic package.
- `MOHU_VR_DIAGNOSTICS` defaults to `OFF`. With it off, the original
  `mods/preloaded` catalog is used and no VR source is compiled.
- `game.toml` and `generated/` remain unchanged by the current VR checkpoint.
- Never transplant a reference-game address without its Underground function
  signature, container identity, and call contract.
- Do not enable a state-changing hook before flat behavior and the relevant VR
  transaction tests have been rechecked.
- A PGXP diagnostic build uses boot-state ABI `131106`; the base flavor uses
  `34`. Savestates also carry the framework execution identity, so a source
  change can invalidate a fixture without changing the ABI. If a load reports
  `abi_tag=34(want 131106)`, `state_load_failed`, or `last_ok=0`, ask the
  operator to create a fresh PGXP save slot. Never patch the ABI, identity, or
  original state, and copy only the completed `.pst` and `.thumb` into the
  isolated tree.

## Current implementation

The engine map is in `vr/underground/engine_map.c`. Seventeen mappings are recorded
with function SHA-256 and FNV-1a guards:

| Role | Reference | Underground | Evidence |
| --- | --- | --- | --- |
| Entity transform | `0x80084718` | `0x80093830` | 41/41 opcodes; live execution |
| Entity node transformer | `0x80013AE4` | `0x80013B40` | 221/221 opcodes; live function ring |
| GTE RT/TR loader | `0x80013E58` | `0x80013EB4` | Byte-identical; live function ring |
| Level vertex transformer | `0x8008B3E8` | `0x80099960` | 710/710 opcodes; 12 RTPS; live execution |
| Gameplay render wait | `0x80090B80` | `0x8009D828` | 110/110 opcodes; live execution |
| Scene draw bridge | undiscovered | `0x80090760` | 669 instructions; live caller chain |
| Scene draw dispatcher | undiscovered | `0x80091854` | 840 bytes; live execution |
| Entity render entry | `0x800824D0` | `0x800913A0` | 1,204 bytes; live execution |
| Render-list wrapper | undiscovered | `0x80079AF8` | 180 bytes; live execution |
| Actor render entry | undiscovered | `0x80076A50` | 472 bytes; live execution |
| Player render entry | undiscovered | `0x8008AB84` | 352 bytes; live execution |
| Actor update dispatcher | undiscovered | `0x80078E08` | object vtable dispatch; live execution |
| Frame render | undiscovered | `0x80053BB4` | 240 bytes; live execution |
| Frame driver | undiscovered | `0x8006D65C` | 1,512 bytes; natural entry and replay execution |
| DrawOTag | `0x800172D8` | `0x80018B50` | 26 instructions; live submission |
| PutDrawEnv | `0x80017348` | `0x80018BB8` | 48 instructions; 0.981 structural match |
| Post-render update | undiscovered | `0x8004356C` | 1,588 bytes; live execution |

The live-confirmed entity transform calls `0x80013B40`, not the near-identical
duplicate at `0x80014184`. The node transformer calls `0x80013EB4`, not
`0x800144F8`.

The opt-in diagnostic plugin is:

- Source: `vr/underground/vr_diagnostic.c`
- Package: `vr/preloaded/packages/mohu.vr.diagnostic/0.1.0/manifest.toml`
- Plugin ID: `mohu.vr.diagnostic`
- Behavior: function-entry logging after exact function-byte verification, plus
  environment-gated replay experiments. Canonical execution is unchanged unless
  `MOHU_VR_STEREO_PROOF=1`.

The diagnostic target reports seventeen active bindings and thirteen overlay hooks.
The isolated slot-0 scene verifies the render chain through the frame driver.
The true natural frame entry is `0x8006D65C`: it loads the frame context and
status words, then falls into the previously recorded prologue at `0x8006D66C`.
Its observed caller is `0x80070444`; the call at `0x800705E4` returns to
`0x800705EC`. That caller is not registered as a hook because it also contains
simulation and device-state work.

The single-player scene roots are measured:

| Root | Global | Live value at slot 0 |
| --- | --- | --- |
| Scene pointer | `0x800AA174` | `0x800F2180` |
| Player pointer | `0x800AA17C` | `0x800F0BE0` |
| Player input | `player + 0x39C` | `0x800F0FDC` |

Read the pointer globals at use time; the heap addresses themselves are not
stable across level loads. A right-stick camera turn changed GTE RT and the
rendered world while GTE TR stayed zero and the player pointer stayed fixed.

Whole overlay-window hashes change between diagnostic runs even when function
bytes remain identical. They are observations only. The stable runtime guard is
the function-byte hash.

## Camera findings

- Right-stick rotation changes GTE RT while TR remains zero.
- OFX/OFY/H were `256/120/400` in 16.16/integer form at the sampled gameplay
  point.
- Scratchpad matrix bytes around `0x1F800014` changed with camera rotation.
- Scratch writes were produced by overlay code near
  `0x80090B98..0x8009115C`, with return address `0x800908E4` at base
  `0x8008C000`.
- The level transformer consumes the camera's rotation in GTE RT and projects
  camera-relative coordinates with TR zero.
- The stable scene/player pointer globals are mapped (see above). The frame
  render chain is mapped, but the high-level actor/camera update that originates
  camera motion remains unresolved.
- `0x80090760` is a render bridge, not the camera updater. It saves GTE state,
  calls `0x80093830`, projects three RTPS groups, builds packets, and restores
  state.
- The render call chain is
  `0x80053BB4 -> 0x80078E08 -> object+0x384 -> 0x8008AB84 -> ... ->
  0x80090760`.
- `0x80053BB4` is followed by the verified wait helper `0x80053CFC`, which calls
  `0x8009D828`.

See `CAMERA_EVIDENCE.md` for measurements.

## Transform probe

`MOHU_VR_DIAGNOSTICS=ON` now includes a diagnostic-only offset at the level
transformer. Setting `MOHU_VR_LEVEL_OFFSET_X=N` adds N to GTE TRX once per draw
span and restores the original TRX at the verified gameplay render-wait boundary:

```powershell
$env:MOHU_VR_LEVEL_OFFSET_X = '200'
```

The probe is inert without the environment variable. It verifies both boundary
functions before touching or restoring GTE state. It is not part of the flat
build and does not yet provide two-eye replay or OpenXR.

The current A/B receipt uses the same slot-0 scene:

| Probe | Result |
| --- | --- |
| `TRX = 0` | [Control](../../vr/proof/level-probe-control.png) |
| `TRX = 20` | [Depth-dependent world shift](../../vr/proof/level-probe-offset20.png) |
| `TRX = 200` | [Large world shift](../../vr/proof/level-probe-offset200.png) |

At `TRX + 20`, far rows aligned at +2 px, mid rows at +5 px, and near rows at
+6 px. The HUD and first-person weapon remained fixed. This establishes true
world-space parallax for the future eye-replay path.

## Stereo replay probe

The diagnostic build contains environment-gated stereo controls:

```powershell
$env:MOHU_VR_STEREO_PROOF = '1'
$env:MOHU_VR_EYE_OFFSET = '24'
$env:MOHU_VR_EYE_RENDER_VIEW = '1'
$env:MOHU_VR_EYE_GUEST_SUBMIT = '1'
```

This is the accepted frame-render replay path. It uses a complete
`PSXModRenderView` and submits the regenerated OT through guest `DrawOTag`, so
PGXP sees the packet source addresses. The older
`MOHU_VR_REPLAY_FRAME_DRIVER=1` experiment remains available but rejected.
`MOHU_VR_EYE_VIEW_OFFSET=1` remains a compatibility alias for the render-view
switch.

The OT-only control renders the already-built scene without regenerating it:

```powershell
$env:MOHU_VR_STEREO_PROOF = '1'
$env:MOHU_VR_EYE_OFFSET = '0'
$env:MOHU_VR_STEREO_OT_ONLY = '1'
```

Confirmed replay facts:

1. `0x80018C78` is the main-EXE `PutDispEnv` match and `0x80018BB8` is
   `PutDrawEnv`.
2. The frame context at `0x800A7138` points at a 512-entry OT through
   `[ctx + 0x2218]`. At the frame-render entry used by this scene that value was
   `0x800A72E0`; after the driver it toggled to `0x800A82E0`.
3. The OT-only control submits the prebuilt list with a bounded direct GP0 walk.
   It renders the complete courtyard, HUD, and weapon and publishes an identical
   zero-offset pair. This proves the OT head, packet tags, clear, and capture.
4. The clear is effective: a clear-only run produced two pure-black images.
5. Frame-render replay with `MOHU_VR_EYE_RENDER_VIEW=1` regenerates a
   full-scene pair. The full render-view path has a byte-identical zero control,
   a 93,376-pixel lateral pair, and a 91,984-pixel forward/downward near-plane
   pair.
6. The frame-driver replay still does not reveal the visible geometry
   transaction. Applying the level-transform TRX offset at every span under
   that path produced a black pair.
7. The visible packet list is already present before the natural frame driver
   entry. The driver toggles OT bases, but the post-driver base is not the
   accepted frame-render replay list.
8. The diagnostic's manual GP0 walker loses source addresses: every packet is
   reported as `vr.projective.miss0`. Guest `DrawOTag` preserves provenance and
   produced 1.4M homogeneous projective draws in the accepted zero and lateral
   runs.

At the tested zero-offset OT-only checkpoint:

| File | SHA-256 |
| --- | --- |
| [stereo-otonly-zero-left.png](../../vr/proof/stereo-otonly-zero-left.png) | `10ad3e8fbebe500c0d665b2eab2d509ecd012d44c96e4a6ab6d009ecbb11ebd1` |
| [stereo-otonly-zero-right.png](../../vr/proof/stereo-otonly-zero-right.png) | `10ad3e8fbebe500c0d665b2eab2d509ecd012d44c96e4a6ab6d009ecbb11ebd1` |

The current driver/TRX experiment produced a black pair with matching hash
`ffc1aaa604e5364b25926033bfdb5b792c1ce06597681358d212c8c386a72aa5`.
That result is rejected as stereo evidence.

Accepted same-checkpoint controls:

| Control | Result |
| --- | --- |
| [Zero left](../../vr/proof/stereo-view-zero-left.png) | [Zero right](../../vr/proof/stereo-view-zero-right.png); identical hash `10ad3e8f...`; zero changed pixels |
| [Offset-24 left](../../vr/proof/stereo-view-offset24-left.png) | [Offset-24 right](../../vr/proof/stereo-view-offset24-right.png); non-identical full-scene pair |

Block matching measured about 5 px of far-scene motion and 8 px of near-floor
motion. The runtime reported equal eye cycles for both pairs and zero failed
stereo attempts. Full commands, hashes, pair IDs, and runtime counters are in
[STEREO_VIEW_EVIDENCE.md](STEREO_VIEW_EVIDENCE.md).

PGXP full-pose controls:

| Pose | Result |
| --- | --- |
| [Zero left](../../vr/proof/stereo-pgxp-zero-left.png) | [Zero right](../../vr/proof/stereo-pgxp-zero-right.png); zero changed pixels |
| [Lateral left](../../vr/proof/stereo-pgxp-lateral24-left.png) | [Lateral right](../../vr/proof/stereo-pgxp-lateral24-right.png); 93,376 changed pixels |
| [Near-plane left](../../vr/proof/stereo-pgxp-nearplane24-left.png) | [Near-plane right](../../vr/proof/stereo-pgxp-nearplane24-right.png); pitch -15 degrees, forward 250 GTE units, no floor wedge |

The near-plane pair completed 1,544 verified passes with zero mismatches and
equal per-eye state hashes. Exact counters, image hashes, controls, and the save
flavor procedure are in
[PGXP_RENDER_VIEW_EVIDENCE.md](PGXP_RENDER_VIEW_EVIDENCE.md).

The render path now publishes `vr.nclip.render.*` through `mod_counters`.
Five 60-pair snapshots cover zero, lateral, pitch, yaw-left, and yaw-right
poses. All had zero precise-projection misses; final sign distributions and
corrections were pose-dependent. The old widescreen `nclip_stats` command
remains disabled (`enabled=0`) and is not the receipt for this path.

The diagnostic plugin now has an opt-in OpenXR path. `MOHU_VR_OPENXR=1` enables
the backend, presents a native head-relative surface until the first gameplay
frame, obtains the two headset `PSXModRenderView` values, and submits the
verified complete pair. The default world scale is 716.4179 GTE units per
metre. This remains diagnostic and off by default. No headset acceptance run
has been completed yet; the current receipt is compile plus fail-closed
no-runtime fallback.

## Build and test state

Use two persistent build directories. Do not create a new build directory for
each feature:

1. `build-release/` is the flat control. Keep it at
   `MOHU_VR_DIAGNOSTICS=OFF`, `PSX_OPENXR=OFF`, and the base hook flavor. Build
   it only when checking that the flat product still starts or when refreshing
   the flat baseline.
2. `build-vr-pgxp/` is the mutable VR development build. Reconfigure and rebuild
   this directory in place for render-view, NCLIP, and later OpenXR work.

This separation is still useful for A/B testing because the flat build has boot
state ABI `34` while the PGXP diagnostic build has ABI `131106`. A build
directory is only a workspace, not an A/B mode: switch diagnostic behavior with
the environment gates and compare against the retained evidence or committed
source revisions.

Creating another build directory does not repair an invalid savestate. A fresh
folder can contain the same runtime identity and the same ABI mismatch. A
source-level runtime change can still invalidate the PGXP fixture, so ask the
operator for a fresh PGXP save whenever the runtime reports
`state_load_failed`, `last_ok=0`, or an ABI mismatch.

The existing `build-vr-pgxp/` was reused after the operator created PGXP slot
`2`; its zero-pose run reached 240 consecutive pairs with status zero and equal
per-eye pose applications. That verified the fixture, not a new build, was the
missing state.

Flat build:

- Directory: `build-release/`
- Release, OpenGL, OpenXR off, debug tools off.
- `MOHU_VR_DIAGNOSTICS=OFF`.
- Six packages: framework-only.
- Builds and starts headless with the config, OpenBIOS, overlay autocompile, and
  guest execution all initialized.

PGXP diagnostic build:

- Directory: `build-vr-pgxp/`
- Release, OpenXR on, debug tools on.
- `MOHU_VR_DIAGNOSTICS=ON`; PGXP hook flavor `2`, ABI tag `131106`.
- Seven packages: one game-owned diagnostic plus six framework packages.
- PGXP slot 2 loads from `analysis/vr-baseline/saves/`.
- The saved state thumbnail confirms a playable courtyard scene.
- Interpreter-only diagnostic captures confirmed the camera roots and the
  `TRX` world-space probe.
- Hidden-window OpenGL replay confirmed complete pairs, projective draws, and
  balanced eye cycles.
- OpenXR lifecycle compiles and loads the headless fallback with PGXP slot 2.
  Without an active headset runtime, `openxr_stats` reports `result=-35`,
  `stage=system`, and zero submitted layers.

`build-vr-diagnostic/` is historical. Check its executable flavor and savestate
ABI before reusing it; a base-flavor executable cannot load the PGXP fixture.

Last checks:

- Nine Python tests pass.
- Both GTE transfer/contract tests pass, including render-NCLIP counter
  transitions for positive, negative, and zero outcomes.
- Engine-map and diagnostic-plugin C files compile with
  `-Wall -Wextra -Werror`.
- All VR documentation links resolve.
- The diagnostic target builds and activates seventeen guarded bindings.
- TRX 0/20/200 A/B captures produce the expected depth-dependent world motion.
- Frame-render replay with the scoped view offset publishes a byte-identical
  zero control and a complete depth-parallax pair.
- A verifier-enabled offset run completed 3,542 eye-transaction checks with
  zero mismatches and equal per-eye state hashes.
- The full render-view path completed 1,481 zero-pose checks and 1,544
  near-plane stereo checks with zero mismatches.
- The signed-NCLIP sweep completed zero, lateral, pitch, and both yaw poses;
  every sampled NCLIP had a precise projection and pose-dependent final sign.
- Guest `DrawOTag` reports homogeneous projective draws rather than untracked
  manual-GP0 submissions.
- The flat target reconfigures with `MOHU_VR_DIAGNOSTICS=OFF`, contains neither
  the PGXP define nor the VR diagnostic source, and starts headless without VR
  environment variables.
- Frame-driver replay and the all-span TRX variant remain rejected image
  controls.
- No owned game process remains running.

The first startup smoke used the default memcard directory before isolation and
refreshed two card timestamps. All later diagnostics use the copied directory.
Existing savestate files retained their original sizes and timestamps.

## Reproduce the diagnostic checkpoint

The diagnostic build needs a local libwebp source because network fetches are
restricted:

```powershell
$env:PSX_LIBWEBP_SOURCE_DIR = (Resolve-Path 'build-release\_deps\psx_libwebp-src').Path
cmake -S . -B build-vr-pgxp `
  -DCMAKE_C_COMPILER=clang `
  -DCMAKE_CXX_COMPILER=clang++ `
  -DCMAKE_C_COMPILER_LAUNCHER= `
  -DCMAKE_CXX_COMPILER_LAUNCHER= `
  -DPSX_DEBUG_TOOLS=ON `
  -DPSX_OPENXR=OFF `
  -DMOHU_VR_DIAGNOSTICS=ON
cmake --build build-vr-pgxp --target psx-runtime -- -j 8
```

Run from an isolated save copy:

```powershell
$env:PSX_LOAD_SLOT = '2'
$env:MOHU_VR_STEREO_PROOF = '1'
$env:MOHU_VR_EYE_RENDER_VIEW = '1'
$env:MOHU_VR_EYE_GUEST_SUBMIT = '1'
$env:MOHU_VR_EYE_OFFSET = '24'
$env:PSX_RENDER_PASS_VERIFY = '1'
$env:PSX_STEREO_SHED = '0'
.\build-vr-pgxp\Medal_of_Honor_Underground_Recompiled.exe `
  --game (Resolve-Path 'analysis\vr-baseline\game-interp.toml').Path `
  --headless-opengl --no-launcher --debug-port 4372 `
  --memcard-dir (Resolve-Path 'analysis\vr-baseline\saves').Path
```

Expected startup:

```text
mohu-vr-diag: active bindings=17 overlay_hooks=13 read_only=0 level_offset_x=0 stereo_proof=1 eye_offset=24 render_view=1 all_spans=0 replay_driver=0 yaw_mdeg=0 pitch_mdeg=0 head_milli=0,0,0 guest_submit=1
mohu-vr-diag: single_player_scene=0x800AA174 player=0x800AA17C player_input_offset=0x39C
```

## Open gates

1. Repeat the signed-NCLIP pose sweep in additional scenes and at near-wall
   positions.
2. Record the observed `0x80070444 -> 0x8006D65C` natural caller chain and the
   world-packet producer contracts before promoting any additional hook.
3. Keep clear, draw-environment, wait bypass, post-render skip, and transaction
   selectors scoped strictly to eye replay.
4. Label the actor/camera update function and separate camera motion from player
   translation over controlled inputs.
5. Complete interactive flat boot/menu/gameplay validation.
6. Accept the opt-in OpenXR native surface and per-eye presentation on a
   headset, then add input and HUD policy.

Do not treat the frame-driver replay as working stereo. The accepted evidence
uses the frame-render replay; the driver path still does not own the visible
world list.
