# VR Port Handoff

Last updated: 2026-10-24

This is the canonical current-state handoff for the Underground VR port. Update
it before ending every implementation session.

## Repository state

| Item | Value |
| --- | --- |
| Target branch | `feature/vr-port` |
| Starting game-tree checkpoint for sky-ghost correction | `4dbe4cd` (local and live remote matched) |
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
- The flat launcher must start without a headset or VR environment variable.
  `build-release` may contain the inert diagnostic plugin for development.
- `MOHU_VR_DIAGNOSTICS` defaults to `OFF`. With it off, the original
  `mods/preloaded` catalog is used and no VR source is compiled.
- `game.toml` and `generated/` remain unchanged by the current VR checkpoint.
- Never transplant a reference-game address without its Underground function
  signature, container identity, and call contract.
- Do not enable a state-changing hook before flat behavior and the relevant VR
  transaction tests have been rechecked.
- The active development build uses the PGXP flavor and boot-state ABI `131106`;
  the base flavor uses `34`. Savestates also carry the framework execution
  identity, so a source
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
| DrawOTag | `0x800172D8` | `0x80018B48` | Complete 112-byte function, including two-instruction prefix |
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

The diagnostic target reports seventeen active bindings and fourteen overlay hooks,
including the independently guarded native submission tail at `0x80053CFC`.
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
9. Eye replay always targets the rollback-protected `y=0` VRAM scratch buffer.
   Following the native display flip to `y=240` cleared a rectangle that the
   y-rooted eye geometry did not draw, producing alternating complete black
   pairs. `MOHU_VR_STEREO_DUMP_DIR` records the first 60 pairs for recurrence
   checks. See [FLICKER_EVIDENCE.md](FLICKER_EVIDENCE.md).

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
verified complete pair. The launcher defaults to `WorldScale=3` with a 67 mm
user-IPD calibration, producing the reference profile's effective 238.806 GTE
units per metre. This remains diagnostic and off by default.

The launcher can now test OpenXR without a physical headset through SteamVR's
null HMD:

```powershell
.\RunVR-SteamVR.bat -Headless -Seconds 10
```

The mode starts the selected runtime, waits for complete stereo pairs, records
the startup and smoke receipts, then stops SteamVR and restores its original
settings. A failed headset run using the previous unscaled profile reported
correct head tracking but an oversized world and black flashing. World scale was
corrected to the reference profile. The remaining flash was reproduced
headlessly as alternating pure-black complete pairs and fixed by the `y=0`
scratch-buffer replay. The operator confirmed the corrected scale and image.

## Head-turn and flat-HUD correction

The normal VR launcher now renders at `1080p` instead of the native 240-line
buffer. It also enables `PSX_VR_HEAD_FRUSTUM=1` and
`PSX_VR_SUPPRESS_FLAT_HUD=1`. `-InternalResolution native`,
`-NoHeadFrustumDiagnostic`, and `-KeepFlatHud` remain A/B controls.

Underground's `0x80099960` level selector is a 710-instruction match for the
accepted reference selector and uses the same visibility-tree layout. The
diagnostic builds a complete 1000-leaf queue from the actual eye view before
writing guest RAM, verifies the full function bytes on every override, and
falls back to the native selector on malformed trees or overflow. The mapped
state is masks `0x800B7490`/`0x800B7494`, bypass `0x800B7498`, count
`0x800B74B4`, queue `0x800B74B8`, and sentinel `0x800C8458`.

The fixed HUD was content inside each eye image, not an extra OpenXR layer.
The guarded text producer at `0x8006B64C` is skipped only during eye replay.
The measured head-locked packet block at `0x800B8C88..0x800BA4B0` and the bar
node at `0x800F109C` are unlinked from the regenerated OT inside the same
rollback transaction. This temporarily hides the flat gameplay HUD in stereo;
the hand/wrist HUD is still future work.

At the final code checkpoint, zero and both 90-degree poses completed with the
host selector (`frustum=960/960`, zero fallbacks), the fixed compass, ammo text,
and bar were absent, and side views retained world geometry. The final
zero-offset eye images were byte-identical
(`AEECA835133FAE5DADF3047D28D612AA0258FE087098BEE04EAFB46E3C23735B`).
See [HEAD_TURN_HUD_EVIDENCE.md](HEAD_TURN_HUD_EVIDENCE.md) and
[head-turn-hud-fix.png](../../vr/proof/head-turn-hud-fix.png).

### Operator observation and isolated cause

After the final headset test, the operator reported that the dominant flat HUD
ghost was gone, but a smaller residual ghost remains and is visible only in the
sky. They described it as a headset-indexed flat render of the whole scene. The
world appears to occlude it, leaving it visible only where the sky is clear.

That observation was initially a hypothesis. The completed headless controls
now isolate an extra native OT submission/display tail inside eye replay.
Clear-only eyes/application layers are uniform black or magenta; disabling
native OpenXR surfaces does not remove the scene. Omitting the final eye submit
still produces the flat courtyard, proving that frame replay itself draws it.

The corrected path skips the full 80-byte-guarded tail at `0x80053CFC` only
during frame-render eye replay, then submits the cleaned projected OT once.
It also uses the complete `DrawOTag` entry at `0x80018B48`. The ammo artwork's
second 40-byte buffer is now removed with a full-payload guard, correcting the
previous single-buffer "bar" rule. All guest changes remain rollback-scoped.

The same executable restores the ghost when `MOHU_VR_KEEP_REPLAY_SUBMIT=1`.
The fix removes it from both raw eyes and the submitted application layer,
with 100% identical measured static foreground pixels. The default debug-off
build is restored after diagnostic capture. Physical-headset confirmation is
the next operator gate; do not claim additional-level or transition coverage.

Full controls, rejected attempts, commands and limitations:
[SKY_GHOST_EVIDENCE.md](SKY_GHOST_EVIDENCE.md),
[proof](../../vr/proof/sky-ghost-fix.png), and
[receipt](../../vr/proof/sky-ghost-receipt.json).

## Build and test state

There is one active build directory, matching the reference game repository:

- Directory: `build-release/`
- Release, OpenGL, OpenXR on, debug tools off.
- `MOHU_VR_DIAGNOSTICS=ON`; PGXP hook flavor `2`, ABI tag `131106`.
- Seven packages: one game-owned diagnostic plus six framework packages.
- `RunFlat.bat`, `RunVR-VDXR.bat`, `RunVR-Oculus.bat`, and
  `RunVR-SteamVR.bat` all launch this same executable.
- The flat launcher clears VR environment variables. The diagnostic plugin
  remains loaded but inert in that mode.

Creating another build directory does not repair an invalid savestate. A fresh
folder can contain the same runtime identity and the same ABI mismatch. A
source-level runtime change can still invalidate the PGXP fixture, so ask the
operator for a fresh PGXP save whenever the runtime reports
`state_load_failed`, `last_ok=0`, or an ABI mismatch.

The reusable `build-vr-pgxp/`, `build-vr-diagnostic/`, `build-vr-pose/`,
`build-fw-tests/`, and `build-recompiler/` directories were deleted on
2026-10-24. Only `build-release/` remains.

Current `build-release/` state:

- PGXP slot 2 loads from `analysis/vr-baseline/saves/`.
- The saved state thumbnail confirms a playable courtyard scene.
- Interpreter-only diagnostic captures confirmed the camera roots and the
  `TRX` world-space probe.
- Hidden-window OpenGL replay confirmed complete pairs, projective draws, and
  balanced eye cycles.
- OpenXR lifecycle compiles and loads the headless fallback with PGXP slot 2.
  Without an active headset runtime, `openxr_stats` reports `result=-35`,
  `stage=system`, and zero submitted layers.
- `RunFlat.bat` starts the same executable with no VR activation.
- Pass `-Build` to any VR launcher to reconfigure and build `build-release` in
  place.

Last checks:

- Sky-ghost checkpoint: thirteen Python tests, strict frustum and ammo-packet C
  fixtures, strict diagnostic C compilation, and documentation links pass.
- The final diagnostic XR run reached 180 logged pairs, zero XR failures,
  `frustum=720/720 fallback=0/0`, and 180 suppressed native tails per eye.
  At capture, 150 rollback checks had zero mismatches/leaks/watchdogs/repairs.
- Both 90-degree views remain populated; both zero-offset captured pairs have
  identical left/right hashes. Pair 10 SHA-256 is
  `49c4cf094ca0fc587d10091be29219742e9036d9f99e91a16803858b02117c7e`.
- Raw eyes and the submitted application layer have clear sky and no residual
  head-locked HUD in both captured buffer phases. Same-binary A/B reproduces
  the old full-scene ghost only when the native tail is re-enabled.
- Every completed null-HMD capture restored SteamVR settings byte-for-byte and
  left no owned game process. Slot 2 remained valid; no save migration occurred.
- The final normal `build-release` was rebuilt with debug tools OFF. Its null-HMD
  smoke reached 360 logged pairs, zero XR begin/view failures,
  `frustum=1440/1440 fallback=0/0`, and 360 native tails skipped per eye.
  A flat-launcher smoke with inherited VR activation variables still reported
  `read_only=1 stereo_proof=0 openxr=0`, native resolution, and normal boot.

Earlier checkpoint checks (historical image hashes/counters):

- Thirteen Python tests pass.
- Both GTE transfer/contract tests pass, including render-NCLIP counter
  transitions for positive, negative, and zero outcomes.
- Engine-map and diagnostic-plugin C files compile with
  `-Wall -Wextra -Werror`.
- All VR documentation links resolve.
- The diagnostic target builds and activates seventeen guarded bindings.
- A SteamVR null-HMD run loaded PGXP slot `2`, submitted fresh stereo pairs at
  the corrected 238.806 units-per-metre profile, and recorded zero XR begin or
  eye-view failures.
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
- `RunFlat.bat` starts the shared release executable without activating VR.
- A final 60-pair null-HMD sequence had zero black left or right images.
- Eight consecutive compositor and application-layer captures were nonblank.
- Normal VR launch renders at 1080p (5x the 240-line reference).
- The final zero and 90-degree sweeps used the host visibility queue with zero
  fallbacks and retained populated world geometry on both sides.
- The final stereo captures have no head-locked text, compass, or bar packet;
  zero-offset left/right hashes remain identical.
- The final null-HMD OpenXR run completed 30 pairs with zero XR failures,
  `frustum=120/120`, and `hud_unlinked=525/525`.
- Frame-driver replay and the all-span TRX variant remain rejected image
  controls.
- No owned game process remains running.

The first startup smoke used the default memcard directory before isolation and
refreshed two card timestamps. All later diagnostics use the copied directory.
Existing savestate files retained their original sizes and timestamps.

## Reproduce the diagnostic checkpoint

The shared release build needs local dependency sources when network fetches are
restricted:

```powershell
$env:PSX_LIBWEBP_SOURCE_DIR = (Resolve-Path 'build-release\_deps\psx_libwebp-src').Path
$env:PSX_OPENXR_SDK_SOURCE_DIR = (Resolve-Path 'build-release\_deps\psx_openxr_sdk-src').Path
cmake -S . -B build-release `
  -DCMAKE_BUILD_TYPE=Release `
  -DPSX_DEBUG_TOOLS=OFF `
  -DPSX_OPENXR=ON `
  -DMOHU_VR_DIAGNOSTICS=ON `
  -DPSXRECOMP_REQUIRE_GAME_C=ON
cmake --build build-release --target psx-runtime -- -j 8
```

The clickable VR launchers build the same target when passed `-Build`:

```powershell
.\RunVR-VDXR.bat -Build
.\RunVR-Oculus.bat
.\RunVR-SteamVR.bat
```

Run the headless proof from the isolated save copy:

```powershell
$env:PSX_OPENXR_ENABLE = '1'
$env:MOHU_VR_OPENXR = '1'
$env:PSX_LOAD_SLOT = '2'
$env:PSX_RENDER_PASS_VERIFY = '1'
$env:PSX_STEREO_SHED = '0'
.\build-release\Medal_of_Honor_Underground_Recompiled.exe `
  --game (Resolve-Path 'analysis\vr-baseline\game-interp.toml').Path `
  --headless-opengl --no-launcher --debug-port 4372 `
  --memcard-dir (Resolve-Path 'analysis\vr-baseline\saves').Path
```

The no-headset OpenXR acceptance path uses the same isolated slot:

```powershell
.\RunVR-SteamVR.bat -Headless -Seconds 10
```

Expected startup:

```text
mohu-vr-diag: active bindings=17 overlay_hooks=13 read_only=0 level_offset_x=0 stereo_proof=1 eye_offset=0 render_view=1 all_spans=0 replay_driver=0 yaw_mdeg=0 pitch_mdeg=0 head_milli=0,0,0 guest_submit=1 head_frustum=1 openxr=1 flat_hud=1 units_per_meter=238.806
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
6. Extend the pair-sequence and compositor checks to motion, wall proximity,
   menus, transitions, and additional levels, then add input and HUD policy.
7. Confirm the headlessly isolated sky-ghost correction in the physical headset:
   look up and turn both ways; verify no flat courtyard, ammo icon, or compass
   remains in the sky. The instrumented source fix and A/B proof are complete;
   physical-headset acceptance remains pending.

Do not treat the frame-driver replay as working stereo. The accepted evidence
uses the frame-render replay; the driver path still does not own the visible
world list.
