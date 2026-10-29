# Underground VR execution handoff

Updated 2026-10-30 after render-kernel implementation and stereo cache controls.
**Latest physical performance trial FAILED.** Operator reports unplayable
motion despite VDXR panel 90 FPS / 45-ms latency / 15-ms game rendering. Its
trace measures 44.139 fresh pairs/s, 22.081 native scene draws/s and 44.139
native VBlank counts/s. VDXR supplies a 22.222-ms application period (~45 Hz).
Pair work is 12.264 ms, native HUD capture 2.407 ms, mean pose age 15.420 ms.
The synchronous extra-view prototype slows the native wall-time clock; this
fails native-real-time and 60-FPS gates. All 120 captured pairs were fresh, so
successful submission/restoration does not certify playable throughput.

Existing RunVR BATs are restored to the normal production build/personal saves.
The opt-in `-PerformanceTest` route remains diagnostic and rejected for normal
play; do not suggest another trial of this unchanged candidate. Isolated test
progress and timestamped logs remain preserved. No game is left running.
143 Python tests and diff checks pass; no new game was launched for diagnosis.
[Physical failure receipt](../../vr/proof/sp-performance-headset-rejection-receipt.json)
supersedes the earlier launcher-ready checkpoint for acceptance.

**NEXT: G6/P4 — implement reusable world-space geometry, projected for each
current eye/head pose, with render deadlines that cannot slow native simulation.
60 fresh application FPS first; 90 later.** Preflight
and packet kernels exist with passing bounded comparisons. Exact-pose packet
reuse is rejected as the VR solution: coincident-eye desktop gains disappear
with separated eyes. All experiments remain OFF in normal play.
[Current results and one next implementation](RENDER_KERNEL_CHECKPOINT.md).

**The independent renderer plan now owns the work:**
[PERFORMANCE_ARCHITECTURE_PLAN](PERFORMANCE_ARCHITECTURE_PLAN.md) M0–M6. M0
tooling landed: `vr/tools/analyze_vr_measurement.py` classifies
simulation-bound versus presentation-bound runs from the existing frame trace
plus opt-in `PSX_RUNTIME_PERF_DIAG` lines
([contract](MEASUREMENT_CONTRACT.md)); `profile_sp_production.py
--runtime-perf` embeds it. The first real baseline is recorded below. Next: add
canonical, snapshot-extract/publish and asynchronous GPU-query spans, then take
a second workload. Do not restart cache-pose, compiler or calibration sweeps.

**M0 baseline measured:** three production slot-2 windows
(`--runtime-perf --eye-offset 8`, frozen slot02 copied, debug OFF, no
XR/HUD/hands) give 21.95–23.41 fresh pairs/s, pair_total 19.79–20.86 ms, p95
pair+hud 20.87–24.06 ms and native VBlank 43.9–46.8 Hz. The classifier reports
both simulation and presentation failure, but it is compute-bound: pacer waits
are only ~8 ms/s while the inter-frame work interval is ~96% of wall time.
A canonical-only control on the same scene
(`profile_sp_runtime.py --canonical-only`) is real-time: **60.00 Hz, 41% work
interval, 58% pacer**, versus 44–49 Hz at ~96% work and ~0.8% pacer with stereo.
The added per-eye work — not native execution or pacing — causes the slowdown.
Second scene (slot 5, indoor/streaming) matches: stereo 27.68 pairs/s at
16.99 ms, canonical steady 59.99 Hz at ~41% work; one streaming hitch is
recorded, not averaged away. [Receipt](../../vr/proof/m0-baseline-receipt.json).
Not a headset pass; the snapshot/async-GPU spans and alternating matched
windows remain open.

**M1 started:** `vr/underground/world_decode.{h,c}` decodes the measured SP
arena tree and strip lists into an owned, deterministic mesh with named,
atomic rejections and raw material tokens. A bounded snapshot cache keys on
request identity plus generation (never pose) and revalidates a source-span
fingerprint at most once per native snapshot. `world_select.{h,c}` adds a
conservative per-eye candidate list over the retained triangles using the
framework's `psx_vr_box_visible` (UNKNOWN kept, capacity overflow explicit).
`world_project.{h,c}` adds the host reference transform, near-plane clipping,
screen projection and a fan-triangulated screen draw list, plus an adapter from
the real `PSXModRenderView`.
Materials are **not** decoded
(`materials_decoded == 0`); textured rendering must refuse the mesh. A real
slot-2/slot-5 capture (`MOHU_VR_WORLD_CAPTURE`, default OFF) confirms the
`0x8009A51C` caller, the packet range, the level root/vertex table/count, and
that `record_index` is the upper half of base word 1; its 12-byte table entry
is six 16-bit parameter halves, **not** a material descriptor. A per-face
packet dump finds those words at packet offsets 3/6/9 for 20/32 slot-2 faces
but only 3/32 slot-5 faces, so the relationship is real but not universal.
The decoder also runs once on each live arena with masks bypassed and returns
`status=ok`: slot 2 decodes 203 nodes / 134 leaves / 1756 triangles, slot 5
237 / 155 / 1932. The global masks prune slot 2 to 25 leaves and slot 5 to
zero, so they are view-specific, not a resource filter.
Native face parity is exact on both captured views. With `face_tag` (base
address for a base, `extension_word - 4` for an extension), the root walk
matches 16/16 on slot 2 and 91/91 on slot 5 with zero missing; the earlier
11/16 and 70/91 result was an extension-address tag mismatch, not an
unreachable leaf. The visible-entry array at `0x800B74B8` is the submitted set,
and `mohu_world_decode_visible` reproduces it exactly: slot 2 1 entry/16
triangles, slot 5 7 entries/91 triangles, zero decoded-only, `status=ok`. Full
resident-world geometry parity is **not** claimed.
Texture page/CLUT fields remain unmapped. A default-OFF GP0 ring probe now
captures in-range `0x34` commands under `PSX_DEBUG_TOOLS=ON`; per-face
texpage/CLUT attribution is not established, so do not treat those words as a
material.
[Receipt](../../vr/proof/sp-world-capture-receipt.json).
Strict fixture `vr/tests/test_world_decode.c`; contract in
[STATIC_WORLD_DECODER](STATIC_WORLD_DECODER.md). Next: map texpage/CLUT; capture
a world-complete native reference for full geometry parity.

Petrol now follows the shared hand ray in both measured SP release branches.
Slot 1's missing street is reproduced and repaired in both eyes: the VR selector
omitted the native camera's far-depth plane and admitted 116 distant leaves from
a region that native rejected. The corrected selector preserves head-turn FOV;
zero/90-degree captures show actual world geometry. HUD/pause stress still has
one intermittent VRAM restoration mismatch, so broad G5c acceptance stays open.

Slot 2's world is verified. Current Release/debug-OFF desktop baseline is
20.139 ms/pair, 16.710 ms traversal and 25.011 fresh pairs/s, excluding XR/hand
surfaces/laser execution. This is not a 60/90 pass. Do not restart weapon
calibration, inventory, MP discovery or the completed P3b/compiler sweeps.
[Current cases](SP_CURRENT_REGRESSIONS.md), [parity runbook](SP_WEAPON_PARITY.md),
[performance implementation](PERFORMANCE_NEXT_STEPS.md).

**Workspace cleanup checkpoint:** read [WORKSPACE_LAYOUT](WORKSPACE_LAYOUT.md)
before launching or creating a build. Both normal launchers now use the same
standard `build-release` executable and absolute root `saves/`. Current operator
VR slots 0–6/cards are there; all original Flat/VR files and retired executables
are preserved in `analysis/archive/workspace-cleanup-20261029`. No performance
implementation was done during cleanup. Historical paths below remain evidence.

## 1. Accepted checkpoint — do not reopen without a new regression

The operator reports: “smoke test passed, looking good no more missing level
and music,” then “pause menu is ok, sten is ok, performance still meh.” Record
these as human headset observations, not instrumented timing or all-ID tests.

| Scope | Current acceptance |
|---|---|
| Clean image activation / existing launchers | Complete; operator launched it personally |
| Historical SP slot-5 loading failure | Resolved for that case; desktop proof plus earlier operator headset pass |
| Current SP slot 1 / file slot01 visibility — G5 | Desktop cause repaired: native far plane restored; street and 90-degree view populated in both eyes. HUD/pause VRAM mismatch remains open |
| Current SP slot 2 / file slot02 performance — G6 | OPEN: world verified; production desktop 20.139 ms/pair, 25.011 pairs/s; XR/hand work additional |
| Stuck repeating music | Resolved; stream/refill proof plus operator headset pass |
| SP Sten hand aiming | Native construction/motion/loss controls pass; operator headset pass |
| SP pause menu | Native desktop/null-HMD controls pass; operator now confirms headset behavior |
| SP petrol | Both measured SP release branches now use shared hand ray; hand/loss/native-motion controls pass. Fuse/impact/physical and missing grenade fixture remain open |
| Panzerfaust SP aim | Desktop synthetic candidate passes 30-degree hand rotation, head independence and tracking-loss fallback; physical/impact/final-origin controls remain open |
| Full MP-to-SP weapon calibration/control parity — G7 | OPEN: G7a complete; live SP fixtures cover IDs 0, 13, 15 and 16 only |
| Performance | Still unsatisfactory; 60 fresh application frames/s minimum, 90 preferred; OPEN |
| All-SP-ID live NPC damage/isolation | Not implied by smoke or G7 direction checks; R6 retains its separate scope |

Human report and its limits:
[clean-disc-headset-smoke-receipt.json](../../vr/proof/clean-disc-headset-smoke-receipt.json).
Do not ask for another general headset smoke now. Finish independent desktop
work; request a focused physical check only when its candidate is ready.

The latest report reopens overall world-visibility acceptance. Preserve the
historical slot-5/music fix without assuming it explains slot 1. Two reported
cases and their exact current source/fixture hashes are in the
[new receipt](../../vr/proof/sp-current-regressions-receipt.json). No new game
launch or performance measurement was done while recording this report.

Latest operator steering: finish the narrow petrol integration and return to
world/performance promptly. Both measured petrol branches now pass desktop
controls, using existing MP values without recalibration. G7's absent fixtures,
exact rocket-origin/impact and physical gates remain recorded, not prerequisites
for G6. G7a and earlier P38/Sten/Panzerfaust direction controls remain complete.

## 2. Active checkout, disc and launch

- Repository: `C:/Users/titan/Desktop/Github_Projects/Mine/Medal-Of-Honor-Underground-PSX-Recomp`.
  Game branch `feature/vr-port`. Use the existing checkout/build; no new task,
  worktree, dependency update or code regeneration is needed for orientation.
- Reference, read first only where relevant:
  `C:/Users/titan/Desktop/Github_Projects/Mine/Medal-Of-Honor-PSX-Recomp`.
  [REFERENCE_REUSE_AUDIT.md](REFERENCE_REUSE_AUDIT.md) lists existing ports.
- Framework remains pinned to `555e1eabccc59b9b6ff0d9fca48aca783513dc86` in both
  games. No framework changes in this checkpoint. Generic work belongs on
  `vr/shared-development`/feature branches, never master; both affected games
  must pass before changing pins. [Upstream tracker](FRAMEWORK_UPSTREAM_TRACKER.md).
- Production executable: `build-release/Medal_of_Honor_Underground_Recompiled.exe`.
  Release, PGXP, OpenXR, diagnostics plugin ON, TCP debug tools OFF.
- Active image: `Medal of Honor - Underground/Medal of Honor - Underground (USA).cue`.
  BIN SHA-256 `2aed19d588f69274f8be70001eaa9b6400240b62088da72bace815ab902d56ed`.
  The old image and duplicate were deleted by the operator. Do not search for them.
- Source/staged `game.toml`, preparation/catalog digests, launcher selection and
  disc cache were updated. TOC fingerprint remains `5abe13ac...`, recomputed
  from unchanged layout; data hashes differ. Executable/SP/MP overlay payloads
  are identical, so existing hook mappings and native caches remain applicable.
- `mohu.repair.music-sector` is historical, default-OFF and locally disabled.
  **Never enable it or add the clean image to its target.** Clean data needs
  no synthesized header/silence. [Disc report](DISC_IMAGE_COMPARISON.md).
- Operator uses existing `RunVR-VDXR.bat` (Virtual Desktop); Oculus/SteamVR
  variants also remain. Do not create `LaunchVR.bat` or another wrapper.
  Defaults: normal boot, native HUD, laser, tracked gun-only weapons, movement.
  The laser follows hand-fixed bullet aim; native recoil remains visual.

## 3. Fixtures, ownership and mandatory boundaries

- **Every game launch is outside the sandbox**, including hidden, software,
  desktop and null-HMD probes. In execution tools use `require_escalated`.
- One game at a time, two compile jobs. Inspect existing processes; never kill
  the operator's game/runtime. Close/terminate only a child this session owns.
- Work solo. Read applicable `AGENTS.md`; new HLE must follow
  `psxrecomp/docs/HLE_EXECUTION.md`. Do not create a local Beads DB if the
  configured central DB/path is unavailable; record that fact once.
- Frozen SP fixtures: `analysis/fixtures/sp/openbios/`:
  new slot01 (missing world), new slot02 (severe performance),
  slot03 (P38/petrol), slot04 (Sten), slot05 (indoor/old world-loss
  repro). Frozen MP calibration inputs: `analysis/fixtures/mp/openbios/`.
  Root `saves/` is the personal shared Flat/VR store; never use it as an
  implicit test fixture. Probes must copy fixtures into disposable outputs.
  Headless RunVR requires an explicit `-MemcardDirectory`.
- Existing probes copy fixtures to a unique analysis directory. Preserve source
  states/thumbnails, personal saves, keybinds/settings and XR runtime settings.
  Never edit health/ammo/inventory, fabricate compatible saves or patch headers.
- A real execution/layout-cookie mismatch stops dependent gameplay tests.
  Inspect diagnostics and preserve the source. Do not remove identity guards,
  create another build merely to hide the mismatch, or claim a failed load passed.
- SP is the alpha target. MP is only a quick weapon calibration fixture.
  Do not implement MP features or make another MP matrix gate the SP alpha.

## 4. The next implementation, with evidence boundaries

Read [RENDER_KERNEL_CHECKPOINT](RENDER_KERNEL_CHECKPOINT.md) and
[PREFLIGHT_KERNEL_CONTRACT](PREFLIGHT_KERNEL_CONTRACT.md). The first target is
60 fresh application frames/s. Do not reopen weapon calibration, inventory,
compiler sweeps or the completed preflight caller capture.

- P3c2/P3c3 implementation scope is complete: structured `80011424` host core,
  runnable original, 100,000 standalone comparisons, live 128/1,024-call
  captures with zero numeric/precision differences. Canonical/internal resume
  calls retain the original. Three alternating preflight-only mission-start
  A/Bs reduce desktop pair work about 9%; second workload/full XR promotion
  remains open.
- P3d has a build-selected batched `80010CF0` packet core retaining every native
  math/PGXP operation and CPS continuation. A live 512-call comparison covers
  entry/resumes and 8,091 writes without differences. REFERENCE builds. No
  full-path or heavy-slot-2 packet qualification is implied.
- P4 has a default-OFF one-extra-view SP VSync prototype. It does not advance
  native time. Latest traces alternate 60 native/60 extra pairs with distinct
  native counter/cycle stamps, but CPU saturation still slows wall-time guest
  cadence. Native-entry projection is retained for desktop intermediate views.
- Exact-pose world packet cache has 1,176 VERIFY checks with zero mismatches,
  HUD/laser, pause/refusal/load recovery. Its 56.3–57.0 desktop pairs/s depend on
  coincident eyes. Separated eyes yield 47.62 with cache versus 48.69 without,
  so keep it OFF and do not tune its pose keys again. No 60-FPS pass exists.

**One next task:** replace repeated world packet interpretation with reusable
source geometry/material/topology at the real `80010CF0` caller, before camera
culling/projection. Reuse the existing strip/vertex readers and shared GPU,
precision, clipping and transaction services. Start with one bounded arena
family and retain native fallback; preserve texture/CLUT/tpage, ordering/depth,
near clipping, fog, subdivision, separated eyes and 0/90-degree world views.
Keep moving entities/weapon/laser/HUD on their existing paths initially. Measure
separated-eye cadence before extending coverage. Final screen packets are not
a complete mesh and cannot provide fresh-pose unseen geometry.

Tool selectors now exist: `--build-dir` chooses a complete isolated runtime,
`--fixtures` a genuine per-execution fixture root. Production profiler also has
`--eye-offset`; zero is the historical coincident-eye desktop baseline. The
current experimental build is `analysis/builds/preflight-enhanced`; its matching
fixture root is `analysis/fixtures/sp-cache-view-key`. This is a newly saved
mission-start scene, **not the operator's heavier frozen slot 2**. Obtain states
through copied-card normal boot/input; never convert cookies/headers. No new
user save is needed for this work. Do not repeat refused fixture loads or spend
manual time in menus. Native boot receipts/input sequences remain ignored in
`analysis/runtime/`.

Normal `build-release` remains Release/debug OFF, PGXP flavor 2/OpenXR ON,
IPO/timers/harnesses/host kernels OFF, unchanged execution identity and normal
saves. Final copied heavy slot-2 production smoke passes at 19.994 ms/pair and
23.848 pairs/s; this is a smoke, not a matched candidate speed comparison.
Actual XR/hand surfaces, second-scene equivalence, timing/audio and physical
acceptance remain open. Request a targeted headset check only after a candidate
meets independent desktop gates. Preserve the historical HUD/pause VRAM failure.

## 5. Closed investigations and separate open scopes

Do not reopen these without new contrary evidence:

- Historical slot-5 missing world/music: damaged image stalled at raw sector 9469 and
  blocked a native arena load. Replacement passes all 318,028 sector checks;
  operator confirms resolution. No rendering/fog/CD timing bypass is needed.
  New slot-1 G5 was a separate omitted far-plane check, now repaired in desktop
  views; its HUD/pause restoration scope remains open.
- Queue terminator is `800B8458 = 800B74B8 + 1000*4`, not `800C8458` (signed
  displacement). Corrected/asserted; this alone was not the world fix.
- Common SP shot seam: `80048604 → 80076C28`, RA `8004860C`; exact ID/type guard
  admits firearms plus rocket ID 13, while thrown IDs 10/15 remain native.
  Panzerfaust final origin is written at `8004874C/80048774/8004879C`; native
  first motion stores are `800793E4/80079400/8007941C`. Do not rediscover the
  Sten/P38 basis or move aim with recoil.
- Entry-hook config is now **27 entries / 11 instruction sites**. The arena-wrapper
  entry supports the default-OFF native-copy candidate; the petrol completion
  entry is restricted to its verified SP release caller. The extra VSync entry supports the default-OFF cadence prototype. No
  temporary clipping/triangle trace hook remains; supported generation adds
  only that callback to shard 02; original packet/preflight bodies are unchanged.
- SP petrol uses an exact known metadata variant, 99 visible bottle / 97 masked
  arm vertices. Do not weaken all model guards or repeat PCA calibration.
- Checkpoint reuse and paired native HUD readback are already shared. Do not
  port them again or update the framework merely because master moved.

G7 retains broader live SP weapon/final-origin coverage, especially rocket
origin/impact and unavailable fixtures, deferred behind current performance work. Still separate: real SP NPC damage/isolation; focused HUD/transition
and clean-close acceptance; matching-fixture fog investigation only if still
reported. Pause and Sten physical smoke are now accepted. Do not require an MP
physical pause pass for the SP release.

Grenade ray calibration matches eight MP directions but two runs fail VRAM
restoration (2/3 mismatches, CPU hashes equal). Preserve failures. Full SP
grenade acceptance is unproven; only investigate that failure when it affects
the SP work/fixture, without expanding MP scope.

## 6. Required end-of-session checkpoint

- Restore/rebuild production debug-OFF after diagnostic builds. End with no
  owned game process/overrides left behind and no persistent XR settings change.
  Current production executable is
  `49936ea2ce270c8066738513d58dcca0cf23c9ba3df648fb069880b640c93753`.
- Run focused checks appropriate to changes and `git diff --check`. Current
  baseline: 140 Python tests, including shared save-route and SP weapon-tool coverage.
  Strict shot/weapon/raycast/frustum/cadence/cache-key C fixtures and 100,000
  preflight comparisons pass. Current production smoke and both profile builds
  pass; exact provenance is in the render-kernel receipt.
- Update stable IDs in VR_PLAN, the current handoff and compact receipts with
  actual source/binary/fixture provenance. Preserve failed controls and scope.
- Keep dumps, disc/BIOS data, saves and generated screenshots in ignored local
  directories. Do not stage `.commandcode/`, unrelated work or disc assets.
- Commit/push when requested; no PR creation or framework pin change is implied.

Detailed bindings remain in [WEAPON_MAPPING.md](WEAPON_MAPPING.md),
[SP_GAMEPLAY_REPAIRS.md](SP_GAMEPLAY_REPAIRS.md),
[PAUSE_MENU_PARITY.md](PAUSE_MENU_PARITY.md) and their receipts. The superseded
[old handoff](archive/HANDOFF_HISTORY_20261029.md) is evidence only, not a task queue.
