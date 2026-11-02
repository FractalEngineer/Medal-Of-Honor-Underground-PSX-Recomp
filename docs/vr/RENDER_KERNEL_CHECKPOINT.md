# Render kernels and the world-space renderer decision

2026-10-30. **60 fresh application frames/s is the first target. 90 is later.**
The target remains open. All candidates here remain OFF in normal play.

**Later physical trial failed:** operator reports unplayable motion. Its VDXR
trace has 44.139 fresh pairs/s, 22.081 native scene draws/s and a 22.222-ms runtime
application period (~45 Hz), despite the reported panel 90 FPS. Native VBlank
progress is also 44.139/s rather than nominal NTSC ~59.94/s. Default RunVR was
returned to baseline. This full-path failure supersedes launcher readiness;
do not request another trial of this unchanged candidate. [Receipt](../../vr/proof/sp-performance-headset-rejection-receipt.json).
Mean pair cost is 12.264 ms, HUD capture 2.407 ms and pose age 15.420 ms.
The trace's `guest_sim` stage is the interval between traced frames, not an
exclusive simulation cost; do not add it to pair work or count nested stages twice.

The preflight host helper and batched packet kernel now exist and pass their
bounded caller comparisons. They reduce repeated CPU work, but the remaining
guest execution plus two eye renders still exceeds the real-time cadence budget.
The next implementation is reusable world-space geometry, projected from each
current eye/head pose. More same-pose packet-cache tuning is rejected.

## Measurements and limits

These are genuine per-execution **mission-start** fixtures, not a replacement
benchmark for the operator's heavier frozen slot 2. All production windows use
Release/debug OFF, PGXP/OpenXR compiled ON, IPO/timers/harnesses OFF, hidden SDL
and dummy audio. XR is disabled and no hands are injected during these timings.
HUD/laser flags do not mean those surfaces/rays executed.

| Control | Pair work, ms | Fresh pairs/s | Decision |
|---|---:|---:|---|
| Preflight reference, three alternating windows | 14.273 / 14.454 / 14.292 | Native draw cadence | Retained reference |
| Preflight host, same sequence | 12.963 / 13.149 / 13.088 | Native draw cadence | About 9% less pair work; no full-path promotion |
| Both kernels + extra fresh view, cache OFF, three latest windows | 10.860 / 10.934 / 10.944 | 48.354 / 48.770 / 48.178 | Useful intermediate implementation, below 60 |
| Same + exact-pose packet cache, coincident eyes | 8.546 / 8.538 / 8.592 | 56.345 / 57.047 / 56.856 | Gain depends on coincident views; not a VR gain |
| Kernels + fresh view, separated eyes, cache OFF | 10.947 | 48.691 | Limited stereo control |
| Same separated eyes, cache ON | 11.023 | 47.619 | Reject cache as the 60-FPS architecture |
| Final rebuilt enhanced, separated eyes, cache ON | 11.103 | 47.073 | Confirms no 60 pass after build isolation |
| Final normal production, original heavy frozen slot 2 | 19.994 | 23.848 | Smoke only; experiments OFF, no cross-scene speed ratio |

The three cache comparisons ran B1/A1/B2/A2/B3/A3 with the same binary,
execution identity and copied fixture. The desktop helper historically defaults
to eye offset zero. New `--eye-offset 8` controls expose the cache's lack of
benefit with distinct eye views. Do not present 56–57 as headset performance.
All source records, binary/manifest/fixture hashes and effective flags are in
the [compact receipt](../../vr/proof/render-kernel-checkpoint-receipt.json).

## Fresh-view prototype

`MOHU_VR_FRESH_60=1` permits one extra pair between native draws at the verified
SP VSync query wait. Entry `80017628` is 376 bytes / FNV `C04D3214`; only
`a0=-1` and exact SP wait return sites are admitted. The native VBlank counter
`80031A6C` is read, never advanced. Ownership/generation, pause and discontinuity
guards cancel the request. Render rollback preserves canonical simulation.
The desktop projection uses H/OFX/OFY saved at native frame-render entry, rather
than incidental GTE state in the wait. OpenXR keeps its own eye projection.

Latest traces contain 60 native-draw and 60 intermediate pairs, with distinct
native counter/cycle stamps. CPU saturation still slows the native counter in
wall time to the measured 48 or 57/s; this fails the 60 target. Counting twice
per draw is insufficient. No turbo, native-rate change or compositor repeats
are used to manufacture a pass.

## Exact-pose cache prototype

`MOHU_VR_WORLD_CACHE=1` is a bounded, default-OFF experiment. It reuses world
packet bytes and native precision geometry only within the same native draw,
generation, exact view/projection, GTE control, arguments, arena and incoming
ordering-table state. Entities, hands, weapons, selector and laser remain live.
Actual pose changes fall back. Numeric view equality treats signed zeros as
equal and rejects nonfinite poses, lens changes and real movement.

The first precision-receipt transport was correctly refused by the shared
timeline guard: projective precision becomes active after checkpoint entry.
That failed run remains evidence. The prototype now transports owned native
coordinates through public GTE/PGXP APIs in the current timeline. It never
rewrites generation receipts or weakens restore guards.

The latest diagnostic has 1,176 VERIFY checks, zero mismatches and actual
cache hits, plus HUD/laser, pause, forced refusal/recovery and reload controls.
This proves bounded restoration, not pixel equivalence under every packet
state or a motion-capable cache contract. Native projectile calibration and
the earlier intermittent HUD/pause VRAM failure remain separate.

## One next implementation

Replace repeated world packet interpretation with a title-owned decoded mesh
path at the real `80010CF0` caller. Cache **source geometry/material/topology**,
before camera culling and projection; project/clip it for each current eye.
Start from the existing SP geometry/raycast strip decoder and retained native
packet body, with an explicit bounded native fallback for unsupported material,
subdivision or resource cases. Do not reinterpret already culled screen packets
as a complete world mesh, reuse one eye for another or narrow visible FOV.

Implement one arena family first with an isolated native comparison: texture,
CLUT/tpage, winding, ordering/depth, near clipping, fog and subdivision must
remain visible and correct at separated eyes and 0/90-degree head views. Keep
moving objects and all weapon/laser/HUD work on existing paths initially.
Retain the shared transaction/precision/GPU services and original reference.
Then measure separated-eye production cadence before adding more coverage.
Do not repeat compiler, inventory, calibration, attribution or cache-pose sweeps.

No new user save is required for the current mission-start work. Per-execution
fixtures are obtained by disposable copied-card native boot/input automation.
Heavy-scene parity and actual XR/hand performance still require valid matching
coverage before any normal-play promotion or physical FPS claim.
