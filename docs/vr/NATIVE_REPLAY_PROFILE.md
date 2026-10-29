# Native replay attribution and compiler controls

2026-10-29 continuation. P3b is complete. P3c remains open: **no compiler
candidate is promoted and no headset performance improvement is certified**.
The accepted clean-disc, pause and Sten behavior remains the baseline.
Evidence: [receipt](../../vr/proof/native-replay-profile-receipt.json).

## Measured work

Copied clean-image slot 5, Release/debug ON, IPO OFF, paced hidden SDL,
synthetic hands, gun-only model and laser, VERIFY OFF during timing. No physical
headset. Diagnostic link wrappers time the original generated CPS segments:
a segment returns before its guest callee executes, so child time is not
counted twice. Timers/counter writes add diagnostic overhead and do not predict
production savings. Canonical, left and right scopes are separate; counters
approximately bracket the quiet window and normalize by its 205 fresh pairs.

| Operation | Real source/caller | Stereo host ms/pair | Share of traversal |
|---|---|---:|---:|
| Arena packet builder `80010CF0` | `generated/SLUS_012.70_full_00.c`; SP wrapper call `8009A514`, return `8009A51C` | 5.729 | 34.1% |
| Triangle preflight `80011424` | Same shard; packet-builder continuation `80011008` | 3.805 | 22.7% |
| GPU command/reset helper `8001A004` | `generated/SLUS_012.70_full_03.c`; caller `800198BC`, GP1/DMA register writes including host GPU service | 1.143 | 6.8% |

Traversal in the saved final trace is 16.781 ms/pair; complete pair 19.679 ms.
These are instrumented diagnostic timings, not the production floor. The earlier
independent diagnostic gave 5.659 / 3.748 / 1.165 ms in the same order.
Packet-builder time excludes preflight time. The two together consume about
9.53 ms, substantially more than tree selection or the measured subdivision
entry segments. Entity-node transform is 0.436 ms; RT/TR loader 0.115 ms.

The **entire visibility hook**, including code guards, camera/ray capture,
collector and queue writes, costs 0.068 ms. The nested collector costs 0.043 ms.
Underground records the full hook in the previously unused `game_world` slot;
`game_select` remains the collector. Both nest inside `game_traverse`; never
sum them as independent work. This rules out the unmeasured outer guard as a
large hidden selection cost in this fixture.

The host sampler resolves PGXP propagation, shadow writes and CPU cycle
helpers as real runtime work. All 3,085 samples have module-bin attribution;
the reported top 400 PCs cover 1,881 samples. Do not treat that truncated list
as a complete per-function histogram. Loaded DLL bases/paths are preserved and
cached native DLL PCs are resolved with their own PE symbol tables. Examples
include `overlay_flush_cycles` and `func_80090760`; system DLL samples retain
their module names and are **not labeled waits**. Phase/guest-cycle records are
supporting evidence, not a conversion to host milliseconds.

## Compiler implementation experiments

The original generated C, PGXP, cycle barriers and state identity remained
intact in every control. No framework source, pin, disc, save header or guest
asset changed. Each production binary was preserved with its execution
manifest; probes close only their owned child and verify source saves and
preferences. All timing windows use the clean image and no VERIFY overhead.

| Candidate | Production result | Decision |
|---|---|---|
| Clang shard inlining threshold 1000 | Three slot-5 pairs: baseline 17.241 ms mean, candidate 17.437 ms | Rejected; slower pair work |
| Explicit inline of cycle step/charge | One control 17.411 → 17.446 ms | Rejected; no useful gain |
| Also inline base/load helpers | One control 18.323 → 23.361 ms | Rejected; larger code and slower work |
| Existing shared `PSX_RUNTIME_IPO=ON` | Three alternating slot-5 windows: 17.517 → 16.767 ms mean, about 4.3%; slot 3 single control 18.384 → 18.021 ms | Desktop gain only; full-path qualification failed |

IPO desktop publication stays near 29 pairs/s; no native-cadence fix follows.
Production null-HMD/HUD controls expose much larger variation:

| Run order | Binary | Pair ms | Fresh pairs/s | HUD capture ms |
|---|---|---:|---:|---:|
| 1 | IPO | 31.217 | 20.925 | 3.762 |
| 2 | Baseline | 34.646 | 17.319 | 8.496 |
| 3 | Same IPO binary | 46.471 | 13.523 | 8.286 |
| 4 | Same baseline binary | 33.622 | 18.591 | 5.995 |

These controls restore SteamVR settings exactly and have no injected hands or
laser. HUD capture and XR submission run, but live hand surfaces/laser are not
certified. The second IPO run is worse; the cause of its variation is unresolved.
Two full-path windows per binary do not satisfy the three-window qualification
gate. **IPO stays OFF in the playable build.** Do not promote it using the
desktop average, average away the bad null-HMD run, or repeat compiler sweeps.
The inlining source changes were removed. The framework's existing optional
IPO facility is unchanged.

## Exact next implementation

P3c now targets **`80011424` through its real packet-builder interface**. It is
a bounded 668-byte leaf helper (FNV `C38CDCC1`) with one normal return and about
3.8 ms of measured stereo cost. Work on it before the larger 1840-byte packet
builder. Do not begin another outer-wrapper/visibility/renderer comparison.

1. Read the complete helper and its packet-builder caller in shard 00. Capture
   representative real entry/return contracts from copied slot 5, with the
   reference body still runnable. Its ABI is custom: `$s3` is scratchpad base
   `1F800000`, `$s6` carries face flags, `$s7` points to the face record, and the
   GTE SXY/SZ/FLAG state is an input. It returns to `80011008`; `$v0` alone is
   **not** its full output. Validate these leads against captured calls before
   writing a replacement.
2. Record live register results used by the continuation, scratchpad stores,
   GTE results and PGXP/projection provenance. Cover accepted/rejected faces,
   winding swap, clipping/depth and subdivision decisions. Preserve the same
   math/art/FOV and observable packet results. No blanket PGXP/GTE disable,
   culling bypass, native timing-rate change or dropping draw work.
3. Implement and compare at this caller boundary using
   `psxrecomp/docs/HLE_EXECUTION.md`. Select implementations at build time and
   keep the original runnable. Add meaningful caller-result tests, then repeat
   matched production A/B and full HUD/XR checks. Compiler hints alone are a
   rejected experiment, not this implementation.
4. A registered execution family changes the execution identity. Plan valid
   reference/candidate fixtures or a standalone caller-contract harness first;
   **do not rewrite existing save headers, bypass cookies, or assume slot 5
   loads across profiles**. Preserve the operator's playable baseline and saves.
   A fixture compatibility refusal is not a gameplay pass.
5. P4/P5 fresh-pose scheduling remains necessary after the cost reduction. The
   native draw ceiling is still about 30 Hz. Full 60/90 acceptance remains open;
   no new physical smoke is requested yet.

Diagnostic reproduction and production restore commands live in the current
[runbook](PERFORMANCE_NEXT_STEPS.md). The optional native timers are title-owned,
debug-only, Windows GNU-ABI link wrappers and absent from production. No new
function-entry hooks or generated guest edits are needed. `-ExecutableName`
on the existing launcher only supports preserved benchmark binaries beside
the normal assets; all existing RunVR batch defaults are unchanged.
