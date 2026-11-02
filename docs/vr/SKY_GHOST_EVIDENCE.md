# Sky-only flat-scene ghost

Date: 2026-10-24. Starting local and live remote checkpoint: `4dbe4cd`.

The operator's description is reproduced headlessly: a flat courtyard remains
behind the rotated world and shows through its open sky. The source is the
native submission/display tail inside frame-render replay. It is present in
the raw eye textures, before OpenXR. The corrected captures remove it from both
eyes and the submitted SteamVR application layer. The operator confirmed the
sky ghost fixed in the physical headset on 2026-10-24.

Retained proof: [before/after image](../../vr/proof/sky-ghost-fix.png) and
[machine receipt](../../vr/proof/sky-ghost-receipt.json). Bulk captures stay in
ignored `analysis/vr-baseline/sky-ghost/`: two raw pairs and one application-layer
and compositor capture per XR control. No original save was changed.

## Controls before changing the hook

| Control | Observation |
| --- | --- |
| Baseline raw eyes vs application layer | Flat scene/HUD content is inside the eye images, with the same content in the submitted layer. |
| Clear-only black | All four raw images are uniformly black; the application layer is black. |
| Clear-only `MOHU_VR_CLEAR_RGB=0xC020D0` | Both eyes and application layer are uniformly distinctive magenta. GP0 encodes red in the low byte. |
| Coloured clear plus normal replay | Uncovered sky follows the new clear colour; clearing itself does not retain a scene. |
| Native surface explicitly disabled | `native_submitted=quad_submitted=0`; scene content is still drawn in the eyes. |
| `-KeepFlatHud` | Changes the intended flat HUD; does not prevent the extra native scene submission. |
| `-NoHeadFrustumDiagnostic` | Changes visibility selection; does not remove the native scene draw. |
| Replay with final eye submission omitted | Produces the flat courtyard/HUD despite the initial clear. This isolates drawing inside frame replay. |
| Second clear immediately before final submission | Removes the flat courtyard behind the rotated world. Used as a control, not the production correction. |

The pre-fix baseline sampled 9 -> 37 submitted frames with `submitted_layer=1`,
`submitted_source=1`, zero empty submissions/failures, and native/quad counts
fixed at 2 from startup. Native-off sampled 63 submissions with both native
counters zero. Retained-pair ID, stale-frame count, and stereo failures were
zero. These counters alone did not identify the cause; the replay-only control
did. There is no evidence for a retained OpenXR quad or compositor reprojection
as the cause of this reproduced defect.

## Guest contract and correction

The guarded frame render at `0x80053BB4` calls `0x80053CFC` at `0x80053C80`.
That tail waits through `0x80053CA4`, submits a native OT through `DrawOTag` at
`0x80053D30`, then selects the native display environment. Previously only the
deeper gameplay wait at `0x8009D828` was bypassed. The native OT submission and
display change still ran, before HUD packet removal and our explicit projected
eye submission. The native flat image survived where the projected world did
not overwrite it.

The new function filter skips the complete native tail only while the accepted
frame-render callback is executing inside an active eye transaction. It checks
all 80 bytes on every invocation:

- entry: `0x80053CFC`, size: 80 bytes;
- FNV-1a: `0xA7A38EA0`;
- SHA-256: `f03e52974e1653ea3bc3f6ece47ddc183dca3efdfb11c08f7752559432ab5369`.

A mismatch logs once and leaves the stock call available. The final cleaned OT
is still submitted through guest `DrawOTag`, preserving PGXP provenance. No
second clear, compositor change, broad packet filter, generated-code edit, or
frame-driver replay is used by the correction. This follows the reference
port's explicit render/build/submit sequence, which omits the native tail.

Disassembly also corrected the full `DrawOTag` entry from its prologue at
`0x80018B50` to `0x80018B48`. The preceding two instructions load the native
library state. The complete 112-byte guard is now FNV-1a `0x8A6D3CE2`, SHA-256
`172bd5d3777d5854d2095f7c35beb84a8d5b36de7cd06663ac79effad359678a`.
The main-EXE generated function does not expose a mod entry hook at this address
in the existing generated output. A trial hook there recorded zero skips and
was rejected. The verified filter is on the interpreted overlay tail instead;
`generated/` and `game.toml` are unchanged.

The remaining small gold artwork was the ammo icon, previously called the
"bar" packet. Its two captured FT4 packets are at `0x800F109C` and `0x800F10C4`,
40 bytes apart, with identical nine-word payloads and distinct OT links. The
old rule removed only the first buffer. The new classifier selects the current
buffer and requires every payload word to match. It removes neither other
world FT4s nor changed artwork. A strict C fixture covers both captured buffers,
wrong-buffer/address/length cases, and mutation of every payload word.

## Final verification

All final image runs use the same release target with diagnostics temporarily
enabled, isolated PGXP slot 2, 1080p internal rendering (5x, `2560x1200` per eye),
67 mm calibration, WorldScale 3, and 238.805970 effective units/metre for XR.
The null driver reports its own 63 mm runtime eye spacing; calibration does not
replace the runtime eye poses.

- Same-binary XR A/B: re-enabling the native tail restores the flat full-scene
  ghost in both raw eyes and the application layer. Disabling it removes
  1,294,352 left-eye and 1,289,357 right-eye background pixels. The measured
  static foreground building pixels are **100% identical** in both eyes.
- Both captured buffer phases have a clear sky ROI and no residual ammo icon.
  Both eyes and both application-layer halves were inspected.
- The verified XR run reached 180 logged pairs with zero XR begin/view failures,
  `frustum=720/720 fallback=0/0`, `hud_unlinked=3240/3240`, and
  `replay_submits_skipped=180/180`.
- During capture, `openxr_stats` reported 77 submissions, projection/source
  `1/1`, zero empty submissions/failures, no auxiliary surfaces, and only the
  two startup native submissions. `openxr_views` proved submitted pair IDs
  advanced. Stereo retained-pair/stale/failure counters remained zero.
- 150 render-pass verification checks at the XR capture had zero mismatches,
  VRAM leaks, watchdogs, or nesting repairs. Guest cycles and state hashes agree
  between the eyes. Final ±90-degree captures retain populated world geometry,
  non-identical eye images, and zero frustum fallbacks.
- Zero-offset pair 10 has identical left/right SHA-256
  `49c4cf094ca0fc587d10091be29219742e9036d9f99e91a16803858b02117c7e`;
  pair 11 also matches (`687c6df6...`). Hashes across different game frames are
  not required to match.
- Thirteen Python tests, the strict frustum C fixture, the ammo-packet C
  fixture, strict diagnostic-source compilation, and documentation links pass.
- Every completed headless run restored SteamVR settings byte-for-byte to its
  own pre-run backup and left no owned game process.

The default debug-tools-off build and final flat/headless smoke receipts are
recorded in [HANDOFF.md](HANDOFF.md). The proof does not claim physical-headset,
additional-level, mission-transition, or moving-player acceptance.

## Reproduce

Enable debug tools **in the existing `build-release`**, then build `psx-runtime`.
The capture helper refuses an occupied port 4372 or an existing game process.
Normal VR remains debug-tools-off; `vr/run_vr.ps1 -Build` restores that profile.

```powershell
cmake -S . -B build-release -DPSX_DEBUG_TOOLS=ON
cmake --build build-release --target psx-runtime -- -j 8
python vr/tools/sky_ghost_control.py analysis/vr-baseline/sky-next/fixed --case baseline --pitch-mdeg 45000
python vr/tools/sky_ghost_control.py analysis/vr-baseline/sky-next/control --case baseline --pitch-mdeg 45000 --keep-replay-submit
```

`--pitch-mdeg` uses the framework's debug-only synthetic XR pose override and
clears it afterward. It is explicitly not physical tracking evidence. The
diagnostic zero/side/sky cases use the existing non-XR render-view seam.

Additional control environment variables are `MOHU_VR_CLEAR_ONLY`,
`MOHU_VR_CLEAR_RGB` (GP0 low-byte red), `MOHU_VR_NO_NATIVE_SURFACE`,
`MOHU_VR_SKIP_FINAL_SUBMIT`, `MOHU_VR_CLEAR_BEFORE_SUBMIT`, and
`MOHU_VR_KEEP_REPLAY_SUBMIT`. They are inactive in normal flat mode. The capture
helper clears inherited VR experiment variables before selecting its control.

Rejected harness attempts: absolute log paths initially failed in the launcher;
the launcher now accepts them. Its sparse 30-pair log cadence could also make a
healthy slower run fail the two-second smoke check; it now waits up to five
seconds for a strictly newer valid pair count. One eye-state snapshot caught an
in-progress next eye and was rejected; the helper now resamples for a completed
matching eye-state snapshot. Settings and owned-process cleanup succeeded in
these attempts. There were **no failed save-slot migrations** in this session;
slot 2 remained valid throughout. On any future failure: ask the operator for a
fresh PGXP slot; never alter save headers or execution identity.

Operator acceptance: sky confirmed fixed. Subsequent movement work rechecked
raw eyes and the application layer; see [MOVEMENT_EVIDENCE.md](MOVEMENT_EVIDENCE.md).
