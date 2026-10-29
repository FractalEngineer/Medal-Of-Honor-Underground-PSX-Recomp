# Independent VR scene renderer: implementation and acceptance plan

Created: 2026-10-30. Status: **planned; no implementation or new performance qualification implied**.

## Progress tracking between runs

This document records the agreed architecture and execution gates. Read [HANDOFF.md](HANDOFF.md), [WORKSPACE_LAYOUT.md](WORKSPACE_LAYOUT.md), and applicable agent instructions before execution. This plan extends the world-space renderer direction in [RENDER_KERNEL_CHECKPOINT.md](RENDER_KERNEL_CHECKPOINT.md) to a complete independently scheduled scene renderer.

- Check an item only after its work and validation are complete. A milestone is complete only when its exit gate passes.
- Record evidence paths, source/binary/fixture identities, failures, and remaining unsupported cases in a compact receipt. Link that receipt in the run log below.
- Leave failed or blocked gates unchecked. Do not treat partial coverage, a lighter scene, or desktop-only success as full acceptance.
- At each checkpoint, update this tracker and HANDOFF with the next failed or unfinished gate. Do not restart completed investigations without new contrary evidence.

| Milestone | State | Evidence / remaining blocker |
| --- | --- | --- |
| M0: baseline and measurement contract | In progress | Two scenes: canonical-only real-time (~60 Hz, 41% work interval); stereo 21.95–27.68 pairs/s, native clock below nominal, 96% work interval. Snapshot/async-GPU spans and alternating matched windows open |
| M1: static-world resource decoder | In progress | Decoder/cache/selection landed; real packet/face capture proves the 12-byte record is six parameter halves, not a material descriptor. Texture page/CLUT and decoded-vs-captured tree counts open |
| M2: host GPU static-scene rendering | In progress | Host reference transform/projection + real-view adapter landed; retained GPU buffers, shaders, ordering and separated-eye visual/performance gates open |
| M3: complete dynamic scene snapshots | Not started | All encountered producer families |
| M4: GPU HUD and resource transport | Not started | Existing HUD/pause restoration regression remains open |
| M5: independent XR scheduling | Not started | Ownership and injected-stall gates |
| M6: qualification and promotion | Not started | Heavy scene, second scene, full XR and physical acceptance |

### Run log

| Date | Work / gate | Receipt | Next action |
| --- | --- | --- | --- |
| 2026-10-30 | Plan saved; implementation not started | Existing evidence linked below | Begin M0 when implementation is requested |
| 2026-10-30 | M0 measurement contract: offline classifier, opt-in cadence capture, tests | [MEASUREMENT_CONTRACT](MEASUREMENT_CONTRACT.md); `analyze_vr_measurement.py` + 10 tests pass | Capture three slot-2 `--runtime-perf` windows, then add canonical/snapshot/async-GPU spans |
| 2026-10-30 | M1 geometry/topology decoder + strict fixture | [STATIC_WORLD_DECODER](STATIC_WORLD_DECODER.md); `world_decode.c`, `test_world_decode.c`, 155 Python tests pass | Map real `80010CF0` materials, then compare an arena capture |
| 2026-10-30 | M1 snapshot cache: identity+generation key, source-span fingerprint revalidated once per snapshot | Same fixture; cache tests cover hit/revalidate/stale/generation/reset | Wire a default-OFF native census for the real arena root/generation |
| 2026-10-30 | M1 conservative per-eye selection over retained geometry | `world_select.c` + fixture; rotated/translated/UNKNOWN/budget controls | Compare selection counts against a native eye capture |
| 2026-10-30 | M1 real `80010CF0`/`80011424` capture (slots 2 and 5) | [receipt](../../vr/proof/sp-world-capture-receipt.json); caller/range/level/root/table confirmed, `record_index` = base word 1 upper half, 12-byte record = six 16-bit fields (not material) | Map texpage/CLUT fields and dump the full tree for a count comparison |
| 2026-10-30 | M2 host reference transform/projection + `PSXModRenderView` adapter + screen draw list | `world_project.c` + fixture; exact coords, near clip, triangle/quad triangulation, guards | Add retained GPU buffers/shaders and compare projected output against a native capture |
| 2026-10-30 | M0 baseline: three production slot-2 windows with `--runtime-perf` | [receipt](../../vr/proof/m0-baseline-receipt.json); 21.95–23.41 pairs/s, native VBlank 43.9–46.8 Hz | Add canonical/snapshot/async-GPU spans; capture a second scene |
| 2026-10-30 | M0 canonical-only control on the same slot-2 scene | Same receipt; native 60.00 Hz, work interval 41% vs stereo 96%, pacer 58% vs ~0.8% | Run canonical/stereo alternating; then add snapshot/async-GPU spans |
| 2026-10-30 | M0 second scene (slot 5 indoor/streaming) stereo + canonical | Same receipt; stereo 27.68 pairs/s at 16.99 ms, canonical steady 59.99 Hz (~41% work); one streaming hitch recorded | Run alternating matched windows on both scenes |

## 1. Decision and evidence

**Build a host scene renderer that consumes immutable game snapshots and renders at the headset's cadence. Keep native simulation at its original rate.**

The current architecture makes modern hardware perform expensive emulation bookkeeping repeatedly:

- Each eye calls the SP scene renderer at `80053BB4`, rebuilding visibility, geometry and packets inside a rollback transaction.
- Historical profiling attributes **9.53 ms/pair** to packet construction and triangle preflight alone. Visibility selection costs approximately **0.07 ms**.
- The latest physical trial delivered **44.14 fresh pairs/s**, while native VBlank progression fell to **73.6% of real time**.
- OpenXR's blocking frame wait runs on the emulation/main thread. The existing framework render thread is explicitly ineligible during active XR sessions; enabling its setting cannot solve this.
- HUD capture includes synchronous GPU readback, CPU alpha reconstruction and subsequent upload.
- The exact-pose cache provides no improvement with separated eyes.

These findings justify replacing the execution model, rather than another compiler, cache-key or instruction-level optimization. Sources: [native replay attribution](NATIVE_REPLAY_PROFILE.md), [current renderer checkpoint](RENDER_KERNEL_CHECKPOINT.md), [physical rejection receipt](../../vr/proof/sp-performance-headset-rejection-receipt.json), and [framework render-thread contract](../../psxrecomp/docs/RENDER_THREAD.md).

**Agreed defaults:** faithful appearance with small rasterization differences allowed; framework changes included; interpolate game motion with one native update of presentation delay, while head and hands remain current.

This is a substantial renderer project. Its performance is a hypothesis to validate through the gates below, not a promised result.

## 2. Architecture and interfaces

### Ownership and scheduling

Use two independent owners:

| Owner | Responsibilities | Forbidden operations |
| --- | --- | --- |
| Simulation/main thread | Guest execution, audio, input application, canonical GPU/VRAM behavior, scene extraction and publication | Waiting for an XR frame or presentation mailbox capacity |
| XR/render thread | XR session, tracking, swapchains, host scene rendering, HUD composition | Guest calls, live guest RAM reads, mutation of canonical GPU/PGXP state |

Keep canonical rendering operational initially. Eliminate the **additional per-eye and intermediate guest replays** from the new path. Do not bypass canonical draw functions until a separate caller-side-effects contract proves that safe.

Create a separate GL context for the XR renderer. Its buffers, shaders, FBOs and state are independently owned. Share immutable textures only through explicit publication and fences; never invoke the existing global-state GL backend concurrently from both threads.

Retain the existing synchronous implementation as the runnable reference. Do not remove its thread guards to make the new path appear enabled.

### New shared interfaces

Add versioned, size-tagged C interfaces with these responsibilities:

- `PSXHostMesh`: owned vertex/index data, bounds, material references and resource generation.
- `PSXHostMaterial`: texture/CLUT references, texture window, shading, transparency, mask and ordering semantics.
- `PSXHostSceneSnapshot`: epoch, sequence, simulation timestamp, resource versions, camera/player transform, visibility data, dynamic instances, HUD state and discontinuity flags.
- `PSXHostTrackedInput`: timestamped head/controller poses, origin generation, validity/focus flags and controller state.
- Scene publication/acquisition/release functions; generation reset; renderer start/stop; diagnostic export.
- GPU-surface publication for HUD/native menus using handles, dimensions, generation and readiness fences. Preserve the existing CPU-image API for legacy consumers.

The framework owns transport, lifetime, graphics and XR scheduling. Underground owns guest addresses, geometry decoding, visibility policy, entity identity and weapon calibration.

### Snapshot transport

Implement a fixed four-slot mailbox: producer writing, latest published, and up to two consumer-held snapshots for interpolation.

- Publication never waits for XR. Replace an unconsumed snapshot or decline publication if no slot is free; count both cases.
- Never overwrite a consumer-held slot.
- Snapshots reference immutable, retained resource versions. No guest pointers or borrowed scratch buffers cross threads.
- Allocate reusable storage outside the steady-state frame loop.
- Resource updates must remain recoverable after skipped snapshots: publish complete version references, not deltas that depend on receiving every snapshot.
- Reset epochs on load, level/resource replacement, owner change and tracking-origin discontinuity.
- On reset, reject old snapshots and clear interpolation history before presenting the new epoch.

XR waits and renders independently using `predictedDisplayTime`. It acquires the newest complete snapshot pair and locates current eye/hand poses for each frame.

At a 90-Hz headset, target **90 application submissions**, not an alternating 60-on-90 schedule. A 60-Hz configuration is the first qualification target where supported; otherwise qualify at the runtime's actual full cadence.

### Game-motion interpolation

Present game state at predicted display time minus one native scene interval, initially approximately 33.37 ms.

- Interpolate player locomotion, rigid entity transforms and matching animated vertices between snapshots.
- Use stable object identity plus spawn/resource generation—not pointer or draw-order identity alone.
- Use quaternion interpolation for rotation.
- Hold the newest available state if the interpolation target lacks a newer endpoint; do not extrapolate.
- Snap on spawn/despawn, teleport, topology change, load or invalid correspondence.
- Apply current head pose after interpolated player locomotion.
- Apply current tracked-hand pose to held weapons using the existing authored calibration. Native recoil/animation remains a visual contribution.
- Keep controller input and shooting on the current simulation timeline; never feed delayed presentation transforms back into gameplay.

## 3. Ordered implementation milestones

Each milestone must leave a buildable candidate, focused tests and a compact receipt. A failed gate means fix that milestone; do not promote it or substitute a lighter scene.

### M0 — Establish the architectural baseline and measurement contract

Extend existing profiling tools rather than creating another launcher.

- [ ] Record separate simulation active CPU time, pacing waits and canonical-rendering spans.
- [ ] Record snapshot extraction/publication spans.
- [ ] Record XR wait, pose location, host preparation, GPU work and submission spans.
- [ ] Record native VBlank progression, native scene updates, snapshot age, fresh-pose renders, repeated images and missed deadlines.
- [ ] Use asynchronous GPU queries and retrieve results later. Do not add nested spans together or relabel historical `guest_sim` inter-frame intervals as exclusive simulation time.
- [ ] Measure canonical-only execution with stereo replay disabled on the heavy scene. If it still falls behind, attribute the remaining canonical cost separately; do not claim threading solves it.
- [ ] Preserve the existing heavy slot-2 reference. For changed execution identities, obtain candidate scenes through copied-card native boot/input and genuine saves. Record mission, location, camera and scene contents.
- [ ] **M0 exit:** reproducible reference measurements, valid fixture strategy and a report distinguishing simulation slowdown from presentation overload.

A mission-start scene cannot replace the heavy-scene acceptance gate.

### M1 — Decode complete static-world resources

Implement a title-owned decoder using the actual `80010CF0` inputs and its caller at `8009A514`, returning to `8009A51C`.

Reuse the bounds and strip-reading knowledge in `vr/underground/raycast.h`:

- Vertex table at level `+0x2C`, vertex count at `+0x3C`, eight-byte vertices.
- Eight-byte base triangles, four-byte strip extensions, `0x1FFF` terminators.
- Strip winding and render flags.

**The raycast reader is not a material decoder.**

- [ ] Complete material extraction from the original packet/preflight/subdivision bodies before rendering textured output. Produce a mapping table linking every decoded field to its native read/use and a captured fixture.
- [ ] Decode all resident leaves before view-dependent culling, including geometry outside the native camera's current view. Preserve masks, far-plane policy and spatial bounds separately for per-eye selection.
- [ ] Cache by resource identity, generation and validated source content, not eye pose or final screen coordinates. Initially validate relevant source spans once per native snapshot; do not hash the entire resource per eye.
- [ ] Reject malformed counts, cycles, invalid indices and unsupported materials explicitly. Never silently omit faces.
- [ ] **M1 exit:** one arena family decodes deterministically; triangle counts, winding, materials and bounds agree with reference captures. Unsupported cases have named rejection reasons.

### M2 — Render one complete static scene through the host GPU path

- [ ] Create retained GPU buffers; transform/project vertices from each current eye pose in shaders. Remove guest instruction execution, per-instruction PGXP propagation and guest packet writes from this path.
- [ ] Reuse or extract framework shader/material logic with explicit renderer state rather than shared mutable globals.
- [ ] Preserve textures, palettes, texture windows and animated texture versions.
- [ ] Preserve vertex colors, fog and configured texture-interpolation behavior.
- [ ] Preserve near-plane clipping, winding and native far-depth behavior.
- [ ] Preserve native ordering-table bucket semantics, insertion-order ties, transparency and mask behavior.
- [ ] Compute view-dependent ordering from retained geometry using host math. Batch only adjacent compatible primitives; do not globally sort by material or substitute a conventional opaque depth buffer for PSX ordering.
- [ ] Reproduce native subdivision decisions that affect visible appearance; do not assume hardware perspective correction is an equivalent replacement.
- [ ] Render new output into separate host targets without modifying canonical VRAM. Use the transactional renderer only as a comparison/reference path.
- [ ] **M2 exit:** complete supported arena at separated eyes, yaw 0/±90/180 degrees, pitch, translation and near-wall views. Repeated renders after warmup execute zero world guest calls and perform zero geometry redecodes without resource changes.

### M3 — Publish dynamic objects and complete the scene

Capture moving entities after native animation/transforms and before camera-dependent clipping or packet generation. Use existing scene bindings and verified weapon seams—including `80090954` and `80090A78`—as leads, not proof that they cover every object type.

- [ ] Publish owned geometry/material/transform data for enemies and animated props.
- [ ] Publish doors, projectiles, particles, sprites and muzzle flashes.
- [ ] Publish held weapons with existing gun-only masks and calibration.
- [ ] Include resident entities visible after a head turn even when absent from the native camera's packet list. Camera-culled output is not a complete snapshot.
- [ ] Document each producer family's capture point, coordinate space, lifetime, material source and identity rule. Unknown families reject candidate scene completeness rather than disappearing.
- [ ] Implement the game-motion interpolation policy above, including discontinuity and invalid-correspondence handling.
- [ ] Move laser intersection to retained world geometry. Compute one world-space hit for the shared hand ray, then render it independently into both eyes.
- [ ] **M3 exit:** moving-scene snapshots render without calling the guest from either eye. Existing weapon orientation, recoil, tracking-loss fallback and laser alignment remain correct. New head views reveal both world and entities.

### M4 — Remove HUD readback and synchronize resources correctly

- [ ] Render existing native HUD content into owned GPU surfaces once per native update.
- [ ] Preserve the dual-matte algorithm initially, but reconstruct alpha in a shader instead of reading pixels to the CPU. Attach panels to current hand poses every XR frame; update artwork only when native inputs/resource versions change.
- [ ] Capture committed CPU-to-VRAM uploads and copies in command order; never publish partially completed uploads.
- [ ] Publish GPU-generated sampled regions through owned copies and fences.
- [ ] Prevent XR-thread reads of live canonical VRAM and avoid full-VRAM readback on every snapshot.
- [ ] Use the same surface transport for pause, loading and FMV. Preserve guest-visible VRAM operations and save/load synchronization.
- [ ] **M4 exit:** zero steady-state HUD `glReadPixels` calls and CPU image uploads; texture animation and HUD changes remain current; pause/load controls show no restoration corruption.

### M5 — Enable independent XR scheduling

- [ ] Integrate the complete snapshot renderer with the separate XR thread; all XR frame/session/swapchain calls belong to that thread.
- [ ] Feed simulation copied input snapshots and an ordered input-edge queue so short presses are not lost.
- [ ] Route main-thread window events and XR requests through explicit queues.
- [ ] Make old synchronous XR/stereo code and the new owner mutually exclusive.
- [ ] Ensure missing render credit never triggers another guest render.
- [ ] On overload, retain a complete usable snapshot and render it with current tracking. Count repeated simulation state separately from repeated eye images.
- [ ] During incomplete resource transitions, use the native transition surface; never display a partially populated world.
- [ ] Report sustained overload as failure. Do not hide it with empty-layer shedding or stale-image counting.
- [ ] Implement focus loss, session loss, restart and orderly shutdown. Destroy XR resources on their owner thread, join it, then release shared resources.
- [ ] Inject 50–100 ms XR-thread stalls. Native clock/audio progression must continue without corresponding stalls or mailbox blocking.
- [ ] Inject resource-publication delays separately; verify no partial snapshots or use-after-free.
- [ ] **M5 exit:** ownership, lifecycle and injected-stall controls pass with the complete scene path.

### M6 — Qualify and promote

- [ ] Complete M1–M5 before production comparisons or a new focused headset request.
- [ ] Keep experiments build-selected through existing execution-family machinery, with REFERENCE runnable. Validate observable gameplay and agreed rendering behavior; do not require identity of every scratch register or emulated instruction for new host math.
- [ ] Run all correctness and performance gates in section 4 and preserve failed results.
- [ ] Request one focused physical performance test only after independent desktop/full-path prerequisites pass.
- [ ] Implement generic framework work on a feature/shared-development branch and validate both game consumers before updating pins.
- [ ] Leave normal launchers and personal saves on accepted production until qualification.
- [ ] **M6 exit:** full qualification and physical acceptance recorded; deliberate production promotion completed with a retained reference and rollback path.

## 4. Acceptance tests and performance gates

### Correctness

- [ ] Decoder termination, malformed geometry, winding, all encountered material families and resource invalidation.
- [ ] Both eyes, broad head rotation, translation, near clipping, fog, transparency, animated textures and native far-plane behavior.
- [ ] Entity motion, doors, projectiles, animation correspondence and spawn/despawn.
- [ ] Current-hand weapon motion, native visual recoil, tracking loss and laser alignment.
- [ ] Pause/resume, load, streaming, death/restart, focus loss, XR loss and clean shutdown.
- [ ] Snapshot drops, consumer stalls, resource replacement and generation reset.
- [ ] Simulation/audio behavior against reference with identical recorded inputs.
- [ ] Image differences inspected: small rasterization differences are acceptable; missing geometry, wrong depth order, opaque transparency and broken fog fail. Do not mask failing regions to obtain a pass.

### Performance

- [ ] Run three alternating reference/candidate windows per workload, each with at least 60 seconds of measured gameplay after warmup. Include the heavy scene and a second materially different scene.
- [ ] Run a separate streaming/transition stress window.
- [ ] Record resolution, GPU, runtime, effective settings, binary/fixture hashes and actual eye separation.
- [ ] Disable debug tracing, VERIFY, screenshots and per-face logging during production timing; retain the bounded production telemetry needed for the measurements.

Initial engineering budgets—not measured predictions:

| Work | Target |
| --- | --- |
| Snapshot extraction/publication | ≤2 ms p95 per native scene update |
| XR CPU preparation for both eyes and surfaces | ≤3 ms p95 |
| GPU stereo scene and surfaces | ≤5 ms p95 |
| Complete active render-to-submit work | ≤12 ms p99 for 60 Hz; ≤9 ms p99 for 90 Hz |

CPU/GPU overlap must be measured; do not add overlapping stages to fabricate total cost.

- [ ] Native VBlank progression within 1% of nominal NTSC rate in steady gameplay.
- [ ] At least 99% of the runtime's full-rate frame opportunities receive a newly rendered current-pose pair.
- [ ] No sustained half-rate application cadence, accumulating snapshot delay or recurring black frames.
- [ ] No XR-induced simulation blocking in the injected-stall test.
- [ ] All normal HUD, weapons, hands and laser features actually executing.
- [ ] Focused physical confirmation of smooth head motion, locomotion, aiming and audio.

Desktop 60 Hz is an intermediate gate. A runtime still granting 45 Hz cannot be labeled a headset pass regardless of pair CPU cost.

## 5. Execution boundaries and deliverables

- Work solo; two compile jobs; one game process at a time.
- Every game launch uses the required unsandboxed approval route.
- Preserve personal saves, frozen fixtures, accepted production binaries and runtime preferences.
- Never modify save headers, remove compatibility guards, change guest clock speed, narrow FOV or drop visible work to meet a timing target.
- Keep exact-pose caching and synchronous extra-view injection out of the new path.
- Do not expand this project into MP features, weapon recalibration or unrelated compiler work.
- Preserve the existing HUD/pause restoration failure as an open regression until explicitly resolved.
- Follow [the repository HLE policy](../../psxrecomp/docs/HLE_EXECUTION.md). At planning time the referenced external `F:/Projects/recomp-template/HLE.md` and central Beads path `F:/Software/beads/issues` were unavailable. Do not initialize a replacement local database.

Each milestone delivers source, focused tests and a receipt stating **what passed, what failed and what remains unsupported**. Update the handoff with the next failed or unfinished gate.

The completion criterion is a complete scene rendered from current tracking at full application cadence while native simulation stays real-time—not a faster packet kernel or a higher compositor counter.
