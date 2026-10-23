# Medal of Honor: Underground — VR Port Plan

**Status:** Active Underground implementation plan; not a validation receipt  
**Reviewed:** 2026-10-23  
**Target:** `FractalEngineer/Medal-Of-Honor-Underground-PSX-Recomp` (default branch **`master`**)  
**Reference:** `FractalEngineer/Medal-Of-Honor-PSX-Recomp` (branch **`master`**)  
**Working approach:** Port the current proven game VR plugin onto Underground, preserving flat gameplay; isolate title-specific engine bindings and prove them with measurements.

**Working branch:** `feature/vr-port`  
**Target evidence:** [BASELINE.md](BASELINE.md), [ENGINE_EQUIVALENCE.md](ENGINE_EQUIVALENCE.md), [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md)

Paths such as `AGENTS_VR.MD`, `docs/reverse/...`, and `vr/...` below refer to the
adjacent reference checkout unless they explicitly name Underground.

## 0. Verified source baseline — aligned branches and framework pins

The following are **repository-tree observations**, not successful build or headset tests of Underground:

| Item | Medal of Honor reference | Underground target |
|---|---|---|
| Branch | `master` | `master` |
| Git tree SHA | `b33a7d96d596214233d3aef5ecacbf3736ad29e3` | `7fcb0ca35af683ac38c4c501347d59916a924aa4` |
| `psxrecomp` submodule | `31df2e1e0e0a6525733e68ff70e72ecbef84bb09` | `31df2e1e0e0a6525733e68ff70e72ecbef84bb09` |
| `recomp-ui` submodule | `7c635c6b366a6e0d5d3c913a7fce6ec04dd9f256` | `7c635c6b366a6e0d5d3c913a7fce6ec04dd9f256` |
| Executable/game ID | `SLUS_009.74` / `SLUS-00974` | `SLUS_012.70` / `SLUS-01270` |
| PSX load address | `0x80010000` | `0x80010000` |
| Entry PC | `0x8001DFD4` | `0x8001F844` |
| Main EXE text length | `0x2A000` | `0x2B800` |
| Game-specific VR plugin | Implemented | Not present in reviewed target tree |

**Pin alignment verified (2026-10-23):** Both default branches are now `master` and both submodule **gitlinks** match exactly. Underground still has no VR harness registered in its root CMake configuration. The `framework_pins.txt` in the original repository contains stale scaffold snapshots; always trust the submodule gitlinks and `git submodule status` over that file. **Do not bump the pins back to the earlier values in this document.**

**CRITICAL:** Use the **current** source implementation as the baseline, not early `docs/VR_PLAN.md`, historical v0.1.3 recipes, or older handwritten hook lists. Source `VERSION`/handoff identifies the original's **v0.1.6** production baseline. Its normal VR build is **Release, OpenGL/OpenXR, `MOH_PGXP=ON`, debug tools OFF, LLE batching, projective eye replay ON, stereo shedding OFF**. The implementation is described in `AGENTS_VR.MD`, `docs/reverse/VR_HANDOFF.md`, `VR_PROJECTIVE_RENDERING.md`, `VR_SLOT2_PERFORMANCE.md`, and `VR_OPTIMIZATION_STATUS.md`.

### Recently accepted reference behavior to preserve

- Real binocular eye views from **one** guest-frame checkpoint, with atomic publication and rollback; stereo checkpoint reuse.
- Precise host eye rotation/translation during guest replays, **PGXP projective provenance**, signed triangle facing and near-plane clipping. This fixed near-player floor holes and world shake; accepted on Quest 3/VDXR 2026-10-23.
- The normal native PSX render path remains available; rollback protects CPU, RAM, GTE, VRAM, and assets, including exceptional aborts.
- Real native HUD elements captured and presented on head-facing, hand-anchored surfaces, plus original flat menus/briefings/movies.
- Tracked first-person weapon geometry, guarded mesh profiles, laser raycast, optional combat interception, input and movement mapping.
- Production launch without required developer TCP, build provenance, and no forced stereo shedding on overload (previous shedding caused black flicker).
- Reuse tracing and verification tooling; heavyweight debug tools must be off in release builds.

**Avoid regressions:** Do **not** bring back integer-only eye projection, the old frame-shedding default, rejected jitter-tolerance hacks, old bicubic FMV experiment, or stale button maps. Current reference handoff says **jump = left-stick click, crouch = right-stick click**; confirm Underground's game action mappings rather than hardcode from old docs.

### Existing limitations (do not accidentally claim them solved)

The first game's accepted floor and shake fixes do not close all-sector pop-in, streaming/ruins tiles, special weapon damage alignment, all mission paths, or headset refresh-rate performance. In an intensive slot-2 scene, production improved guest cadence ~23–27% versus diagnostics but remained below 60 guest frame-counter increments/s. Guest scene traversal and interpreted overlay work dominated; overlay caching showed an attractive speedup but failed a six-cycle guest-fidelity comparison and was **not** enabled. Avoid copying an experimental acceleration path into Underground.

## 1. Outcome, scope, and ordering

**Goal:** An optional native PC OpenXR VR mode for Underground that retains fully usable flat mode; accurate stereo world geometry and six-degree head motion; tracked weapons with native combat; motion controls; HUD on hands; boot/menus/FMVs on native VR screens; stable frame-state rollback; bounded performance regressions; reproducible releases.

**Priority order:** (1) verify aligned baseline; (2) engine equivalence; (3) plugin activation; (4) safe double-render and stereo; (5) exact projective world and visibility; (6) input; (7) weapon/combat; (8) HUD; (9) performance and release.

**Non-goals for the first vertical slice:** Redesigning PSXRecomp; new art/assets; implementing a new OpenXR backend; rewriting the game; speculative overlay-cache activation; redesigning the original game's established control scheme.

**Implementation ownership:** Framework (`psxrecomp`) owns host VR APIs, PGXP, transactions, OpenXR, compositor and rollback. Underground owns function hooks, native camera/player/weapon/scene layout, policies and assets. `generated/` is generated output, **never** a place for manual VR patches.

## 2. Phase 0 — Verify the already-aligned baseline

1. Checkout and record exact SHAs, branches, submodule gitlinks, `VERSION`, build flags, generated-code identity, and existing savestate ABI in both repos.
2. Create an Underground branch `feature/vr-port`; keep original clean. Preserve existing local worktrees and saves. Capture flat boot, menu, first playable scene, combat, and mission transitions using Underground's **current matched pin**.
3. **Already completed:** Underground and original now both pin `psxrecomp` at `31df2e1e` and `recomp-ui` at `7c635c6b`. **Do not update or churn these pins just for this port.** Verify the submodules resolve and that Underground builds and plays flat at the matched pins, including emitter/codegen compatibility. If a later framework change becomes necessary, make it in a separate, justified commit.
4. Set up an isolated development save/memcard directory; do not silently rewrite original saves or bypass execution-identity/savestate safeguards. Generate new compatible savestates when needed.
5. Document platform/runtime setup, emitter provenance and exact binary flags. Never copy stale runtime binaries or generated C blindly.

**Gate G0:** Current matched gitlinks checked; Underground flat build, boot and gameplay validated with no changes to disc assets/original saves. Matching SHAs alone are **not** proof of runtime compatibility.

## 3. Phase 1 — Produce an evidence-backed engine equivalence map

### 3.1 Mandatory hook discovery

Do **not** transplant original PSX addresses into Underground. Build a machine-readable and human-reviewed mapping of signatures, call sites, entry/exit contracts, function ownership and overlay identity. Representative **original game** candidates from `vr/psx_vr_stereo.c` (not target values):

| Reference address | Role to confirm in Underground |
|---|---|
| `0x80084718` | Entity transform hook |
| `0x800814C4` | Geometry entry |
| `0x80080DD4` | Geometry filter |
| `0x800824D0` | Render routine |
| `0x8008B3E8` | Level vertex transformation/GTE RTPS |
| `0x80016E38` | Main EXE VSync wrapper (historical probe; **not** assume best gameplay boundary) |
| `0x80090B80` | Main gameplay draw wait / replay checkpoint seam |
| `0x8007E414` | Weapon geometry filter |
| `0x800836C0` | Weapon vertex filter |
| `0x8006591C` | Shot basis |

Inspect the **current plugin registration** because addresses/guards/entry hooks may have evolved. Also map native scene roots, camera globals, player object, active input, held weapon, per-level node/triangle structures, framebuffer state, HUD producers, display flip and single-/multiplayer variants. Overlay-resident function addresses can have different active overlay content: map signature **and overlay generation**.

### 3.2 Efficient comparison method

Use Ghidra on both PSX EXEs plus representative active overlay dumps. Implement optional `tools/match_moh_engine.py` to propose matches by normalized MIPS instruction sequence, GTE opcode pattern (e.g. repeated RTPS), control-flow graph, constants, callees and live invocation. Normalize relocation/jump destinations rather than using raw address equality. Automatically rank matches but require disassembly and live-trace confirmation for any hook that writes guest state or skips original execution.

Store `docs/vr/ENGINE_EQUIVALENCE.md` and `vr/underground/engine_map.[ch]` with fields: reference address, target address, binary/overlay signature, calling convention, RAM dependencies, diagnostic evidence, confidence, status. Use `unknown`/disabled rather than fabricated addresses. Treat same-offset player structs and same weapon IDs as **hypotheses**, not facts.

**Gate G1:** Target render boundary, world geometry transformer, camera source and player scene pointers verified in a real Underground level. Unsafe hook registration fails closed on wrong signature.

## 4. Phase 2 — Bootstrap a title-isolated VR plugin

1. Copy/reference the **current** `vr/psx_vr_stereo.c`, `moh_vr_input.[ch]`, `moh_vr_aim.[ch]`, `moh_vr_hud.[ch]`, `moh_vr_frustum.h`, `moh_vr_raycast.h`, and tests. Initially retain proven generic code; avoid premature extensive refactoring.
2. Introduce `vr/underground/` adapter for addresses, signature validation, scene detection, player/input layout, camera, weapon content and native HUD. Prefer typed accessors and per-mode descriptors to a table of addresses alone.
3. Add sources with `target_sources(psx-runtime PRIVATE ...)` in Underground `CMakeLists.txt`. Transfer the opt-in mod manifest but assign an Underground-specific plugin/feature ID and `[[target]] game_id = "SLUS-01270"`. Ensure registered plugin IDs match the manifest and activated feature.
4. Update `game.toml` `[recompiler].mod_function_entry_funcs` **only for validated static recompiler entry hooks**. Regenerate committed C with supported emitter process if entry hooks change; do not manually edit generated output. Distinguish static EXE hooks from runtime-loaded overlay hooks.
5. Port `vr/run_vr.ps1` and VR runtime launchers, updating executable, game ID, disc handling, paths, cleanup and diagnostics. Keep `RunFlat` completely independent of OpenXR.
6. Bootstrap with only OpenXR/session/native flat-screen behavior; enable each hook behind a feature flag, never all hooks simultaneously.

**Gate G2:** VR opt-in registers, launches native screen to OpenXR and exits cleanly; flat play remains unchanged; unrecognized game/overlay signatures disable the corresponding hook rather than crash.

## 5. Phase 3 — Prove rollback and real stereo

1. Locate Underground's actual gameplay main-thread rendering wait, GPU ordering-table submission and display flip. Original's legacy VSync hook alone proved insufficient; investigate its analogous render-wait seam first.
2. With the framework renderer, create a **no-op pass** from a paused/controlled gameplay checkpoint. Verify identical pixels, zero CPU/GTE/RAM/GPU/asset drift, zero verification mismatch and watchdog rollback recovery.
3. Trace and isolate a replayable **draw slice** including level, dynamic objects and weapon/HUD producers but excluding simulation advance, input, audio/CD, IRQ/flip and unrelated side effects. Distinguish single-player from multiplayer.
4. Replay both eyes from one checkpoint, initially with zero separation and per-eye dump to PNG; prove identical zero-offset images and complete dynamic coverage.
5. Feed the Underground per-eye camera into existing `PSXModRenderView` and projective GTE seam, not a screen-space shift. Prove positive-depth geometry exhibits depth-dependent parallax. Restore all state on success, failure and abort, and atomically publish complete pairs.
6. Preserve **stereo shedding OFF** by default. Overload holds complete last-known-good images according to current framework contract, not alternating empty XR submissions.

**Gate G3:** Gameplay true-stereo pairs with same frame ID; no-op/zero-eye comparisons, state-fingerprint rollback, watchdog injection and GL transaction tests pass; no left/right pair mixing or blank XR flashes from default overload policy.

## 6. Phase 4 — Exact 6DoF, projective precision and level visibility

This phase must use the **new v0.1.6 precision path at first acceptance**, not an old integer-based stereo then an optional later floor patch.

1. Read current `docs/reverse/VR_PROJECTIVE_RENDERING.md` and framework tests. Ensure `MOH_PGXP=ON`, host-exact eye transform, scoped provenance, signed facing and near-plane clipping remain active in the production path, restoring modes after every pass and abort.
2. Validate Underground's camera-space axes, handedness, rotation order, GTE registers, transform ownership and world-units-per-meter. Avoid double-applying exact and integer eye offsets.
3. Port the per-eye frustum/AABB selection only after discovering Underground's actual spatial tree; verify available sectors and portal masks independently. Increasing FOV cannot reveal geometry never submitted by native visibility selection.
4. Run zero/1 mm/10 mm/60 mm head-translation sweeps, fine pitch sweeps and fixed-pose stability tests. Compare to the original's `vr/check_world_stability.py` methodology, using matched world ROIs and annotated native/VR captures.
5. Test ground under feet, head pitch up/down, far corners, head turns through 180 degrees, wall-leaning, transitions between areas, dynamic enemies and effects.
6. Keep non-eye HUD and menu capture on ordinary paths without leaking PGXP/provenance into those draws.

**Gate G4:** Correct near-floor clipping without black wedges, smooth sub-pixel pose response, stable fixed camera, real 6DoF, no new head-turn holes in multiple Underground areas, no rollback differences.

## 7. Phase 5 — Inputs and locomotion

1. Port XR-to-native PSX pad plumbing and current input tests; check the **current** `ALPHA_README.md` and runtime source rather than older control handoffs.
2. Reverse-engineer Underground's true controller analog curve/action masks; only reuse original response factors after live measurement. Preserve native movement, collision, recoil and menu behavior.
3. Implement movement/strafe, body turn, firing, reload/use, weapon cycle, crouch, jump, pause and focus-loss behavior. Validate current reference default **jump left-stick click / crouch right-stick click**, subject to Underground's actual action mapping.
4. Recenter safely; revalidate world orientation after headset runtime recenter, headset disconnect/reconnect, and menu transitions. Preserve native controller fallback.

**Gate G5:** Full mission movement, menus, focus transitions and common interactions work in VR; input tests and human check pass.

## 8. Phase 6 — Weapons, physical aiming and combat

1. Inventory all Underground weapons per mission and multiplayer where supported. Capture actual weapon ID, first-person object, geometry pointer, node/vertex/face counts, animation and shot constructor.
2. Transfer the proven guarded gun/arm mesh filtering algorithm; **do not** copy original per-weapon face counts/node selections or IDs as if validated. Build `vr/underground/weapon_profiles.h` from captured assets.
3. Transfer pose math and gun-pivot transform with calibrated grip, units/metre and correct native weapon transform contract; validate scope, reload, animated subparts, held items, projectiles and knives/explosives separately.
4. Route shot direction/origin through verified Underground weapon constructor or game-compatible aim path. Measure hits against the rendered barrel/laser at near and far ranges and under controller-only vs head/body-only motion. A pretty tracked mesh is **not** evidence of physical shot correctness.
5. Apply guards for input/pose validity, mesh signature, overlay generation and player state. Unknown weapons fall back cleanly to native.
6. Test each weapon equip/fire/reload/switch/empty-ammo/hit/recoil/save-load, and native flat equivalent. Save per-weapon receipts and frame captures.

**Gate G6:** All designated weapons track and interact reliably, guard mismatches fail closed, projectile/spread logic remains native, real hits align with controller aim to documented tolerances.

## 9. Phase 7 — Native HUD, menus, movies

1. Reuse generic `psx_mod_render_capture_rgba`, `psx_mod_openxr_surface`, native matte extraction, one-readback/shared-checkpoint optimizations and head-facing left/right hand surfaces.
2. Find Underground's actual health, compass, weapon icon and ammo native producers, packet signatures, text buffers and screen rectangles. Do not reuse MOH's hardcoded addresses, cutout rects or packet count without inspection.
3. Suppress **only owned** native gameplay HUD packets during world draw; don't drop unrelated text/prompts. Keep normal menu/briefing/FMVs on a comfortable 2D surface.
4. Verify health damage, ammo discharge/reload, weapon switch, pause, death, save/reload, lost hand tracking and recenter; test both eye surfaces and fallback.
5. Keep accepted wrist positioning head-facing and clean native artwork; no new redrawn GUI fonts. Keep gamma/sRGB behavior inherited from tested OpenXR framework.

**Gate G7:** Native HUD updates match guest state, left/right surfaces are clear and stable, flat transitions work, no unrelated native content is removed, no readback/state leak.

## 10. Phase 8 — Performance: evidence before optimization

**Current source-game lesson:** With PGXP projective correctness accepted, do not trade it away for FPS. The first game's demanding scene traced most time to guest `game_traverse`, not its host frustum selector; debug-disabled/LLE production improved cadence 23–27% but did not make all scenes full-rate. The experimental compiled-overlay path had a **six-cycle fidelity divergence**, so leave it disabled until an exact timing fix is independently verified in Underground.

Track:

- Guest frame/VBlank and unique world-pair cadence **separately** from XR display refresh.
- `game_traverse` / guest interpreter or shard duration, individual eye replay, GTE/GPU OT submit, shared checkpoint, HUD readback, audio underruns, waiting, GC/memory faults.
- Pair p50/p95/p99, empty submissions, sheds, stale-pair age, tracking loss and XR failures.
- Rollback checks/mismatches, fingerprints, per-eye pixel stability and scene coverage.

Use reproducible Underground mission fixtures, fixed simulator/pose inputs, repeatable warmup and traces, identical settings and matching executable IDs. Compare diagnostic and production flags explicitly. A throughput change does **not** establish gameplay fidelity: use guest-cycle/state fingerprints and deterministic replay over changing scenes. Investigate overlay timing only after a source-level delta accounting test includes cycle counter and batch/deferred-charge sites.

**Gate G8:** No new visual regressions against PGXP-accurate baseline; no default-shedding black-frame flicker; stable known-good headset submissions; measured bottlenecks and limitations recorded, including demanding missions.

## 11. Phase 9 — Release engineering and validation matrix

- Port `RunFlat.bat`, `RunVR-VDXR.bat`, `RunVR-SteamVR.bat`, `RunVR-Oculus.bat`, `vr/run_vr.ps1`, using the target's game identity and unique archive/plugin metadata.
- Release CI must include the current framework flags, compiled generated game C, PGXP enabled, OpenXR present, debug tools disabled, tested LLE setting, projective enabled and stereo shedding disabled unless explicitly opted in.
- Check archive contains plugin manifest, configs, launchers, correct binary with provenance, and **no** unauthorized disc/BIOs/saves. Emitter/hash verification should follow current v0.1.6 release process.
- Test Windows flat with no headset, VDXR Quest 3/Virtual Desktop (primary acceptance), SteamVR, and Meta Quest Link where accessible (these latter runtimes are not already fully validated by the source project).
- Verify boot, menu, briefing, first missions, streaming areas, death, checkpoint, reload, movies, pause/resume, controller focus, each weapon and game exit; test native screen transitions and no blank XR output.
- Re-run watchdog and transactional restoration tests whenever new hook, new overlay path or state-mutating feature lands.

**Gate G9:** Reproducible versioned Underground VR release; documented supported environments, known limitations, source/build provenance and successful full regression runs.

## 12. Suggested implementation PRs

| PR | Delivery | Acceptance |
|---|---|---|
| 01 | **Pins already aligned**; verify flat build and establish baseline | Flat regression clean at shared gitlinks |
| 02 | MIPS/GTE and overlay engine-equivalence mapping | Render/camera signatures verified |
| 03 | Plugin scaffold, optional OpenXR launcher | Headset native-screen startup; flat unaffected |
| 04 | No-op render checkpoint and render replay | Pixel/fingerprint restoration, watchdog |
| 05 | Complete per-eye replay and atomic stereo | Same-state pairs; depth parallax |
| 06 | Exact PGXP projective head pose and visibility | Floor and stability sweeps; multi-sector tests |
| 07 | Controllers, menus and native locomotion | Action-by-action regressions |
| 08 | Weapon inventory and guarded tracked meshes | Per-weapon asset evidence |
| 09 | Weapon fire/shot basis and aim | Real impact correspondence |
| 10 | Native HUD surfaces and scene transitions | HUD consistency/fallback |
| 11 | Performance attribution and correctness | Trace/replay receipts; production comparison |
| 12 | Packaging, runtime/mission acceptance | Shippable opt-in VR release |

**PR discipline:** Each PR pins the relevant framework commit, includes updated diagnostic fixtures and build/runtime receipts, states what is unverified, avoids auto-committing/pushing unreviewed generated output, and does not rewrite source-game code or unrelated framework worktrees. Do not proceed to later gameplay systems until G3/G4 pass.

## 13. Immediate first tasks for an implementation agent

1. Verify both repositories are on `master` and their authoritative gitlinks are still `psxrecomp=31df2e1e...` and `recomp-ui=7c635c6b...`; if moved, record actual current state before acting.
2. Read reference `AGENTS_VR.MD`, `VR_HANDOFF.md`, `VR_PROJECTIVE_RENDERING.md`, `VR_SLOT2_PERFORMANCE.md`, `VR_OPTIMIZATION_STATUS.md`, `vr/psx_vr_stereo.c`, Underground `game.toml`/`CMakeLists.txt`, and framework `AGENTS.md`/`CLAUDE.md`.
3. Create Underground feature branch, snapshot flat behavior and isolated saves, and prove flat preservation **without changing the already-matched framework/UI pins**.
4. Generate a candidate MIPS function-equivalence report for the render wait, level RTPS projector and camera. Do **not** guess addresses; capture source and target disassembly, call-site evidence and overlay identity.
5. Port just the opt-in manifest/registration and native-screen OpenXR path. Add hooks one at a time and instrument failure points before trying stereo.
6. Obtain a matched no-op frame-state receipt, then a zero-IPD eye pair, then a real-parallax pair. These are the first three technical VR milestones.

## 14. References in the source trees

**Reference game's live implementation:**

- `AGENTS_VR.MD` — architecture, current production constraints and source ownership
- `docs/reverse/VR_HANDOFF.md` — v0.1.6 current baseline
- `docs/reverse/VR_PROJECTIVE_RENDERING.md` — accepted near-floor, head-motion and precise-eye fix
- `docs/reverse/VR_SLOT2_PERFORMANCE.md` — production defaults, overload flicker and measured performance
- `docs/reverse/VR_OPTIMIZATION_STATUS.md` — checkpoint, readback and traversal instrumentation; rejected overlay shortcut
- `docs/reverse/VR_ALPHA_TODO.md` — current remaining limitations
- `vr/psx_vr_stereo.c`, `vr/moh_vr_*.{c,h}` — VR hook and per-title implementation
- `vr/check_world_stability.py`, `vr/trace_frames.py`, `vr/hitch_report.py`, `vr/check_native_hud_gameplay.py`, `vr/check_weapon_aim.py` — regression methods

**Underground target:** `game.toml`, `CMakeLists.txt`, `generated/SLUS_012.70_*`, `seeds/ghidra_funcs.txt`, submodule pins and current working flat release.

**Accuracy statement:** This plan was updated against the repositories' publicly available tree/content and reference implementation notes as of 2026-10-23. No Underground game execution or matching Ghidra session was performed in this review. Addresses and timings in the source project's docs describe *the original game*, not confirmed Underground results.
