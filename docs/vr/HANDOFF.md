# Underground VR execution handoff

Updated 2026-10-29 after native profiling and compiler controls. **P3b complete;
next task: P3c2–P3c6 preflight implementation and qualification, then the budget
decision and P4/P5.** Follow
[PERFORMANCE_NEXT_STEPS.md](PERFORMANCE_NEXT_STEPS.md) in order. Do not resume a
NEXT pointer from an archived report. [VR_PLAN.md](VR_PLAN.md) owns status;
[IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) owns history.

## 1. Accepted checkpoint — do not reopen without a new regression

The operator reports: “smoke test passed, looking good no more missing level
and music,” then “pause menu is ok, sten is ok, performance still meh.” Record
these as human headset observations, not instrumented timing or all-ID tests.

| Scope | Current acceptance |
|---|---|
| Clean image activation / existing launchers | Complete; operator launched it personally |
| SP missing world, including the reported slot-5 symptom | Resolved; desktop proof plus operator headset pass |
| Stuck repeating music | Resolved; stream/refill proof plus operator headset pass |
| SP Sten hand aiming | Native construction/motion/loss controls pass; operator headset pass |
| SP pause menu | Native desktop/null-HMD controls pass; operator now confirms headset behavior |
| SP petrol model / laser | Exact model repair and eight-direction/loss/release desktop checks pass |
| Performance | Still unsatisfactory; 60 fresh application frames/s minimum, 90 preferred; OPEN |
| All-SP-ID native damage / grenade / rocket acceptance | Not implied by this smoke; still open behind performance |

Human report and its limits:
[clean-disc-headset-smoke-receipt.json](../../vr/proof/clean-disc-headset-smoke-receipt.json).
Do not ask for another general headset smoke now. Finish independent desktop
work; request a focused physical check only when its candidate is ready.

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
- Current SP fixtures: `analysis/vr-baseline/saves/openbios/`:
  `state_8001F844_slot03.pst/.thumb`, slot04 (Sten), slot05 (indoor/old world-loss
  repro). Root `saves/` is not the current SP fixture tree.
- Existing probes copy fixtures to a unique analysis directory. Preserve source
  states/thumbnails, personal saves, keybinds/settings and XR runtime settings.
  Never edit health/ammo/inventory, fabricate compatible saves or patch headers.
- A real execution/layout-cookie mismatch stops dependent gameplay tests.
  Inspect diagnostics and preserve the source. Do not remove identity guards,
  create another build merely to hide the mismatch, or claim a failed load passed.
- SP is the alpha target. MP is only a quick weapon calibration fixture.
  Do not implement MP features or make another MP matrix gate the SP alpha.

## 4. The next implementation, with evidence boundaries

Read the performance runbook and execute its first unchecked step. In brief:

**The next agent starts at [runbook section 3.1](PERFORMANCE_NEXT_STEPS.md#31-ordered-execution-checklist--start-at-p3c2),
not at its historical baseline/profile reproduction commands.** Read the
complete `80011424` helper, caller and dispatch entries; begin the standalone
caller-contract harness and proceed into implementation. Capture alone is not
the requested deliverable. P3c2–P3c6 need no physical headset.

1. Preserve the accepted clean-image checkpoint. The current clean production
   baseline and completed P3b evidence are in [NATIVE_REPLAY_PROFILE.md](NATIVE_REPLAY_PROFILE.md).
   Do not restart attribution or compiler sweeps. For a genuinely new candidate,
   obtain one current clean
   production baseline with the existing tool. Do not rerun disc audits, all-ID
   matrices or old render-clip experiments. No physical HMD launch.
2. **P3b is complete:** exclusive packet/preflight/GPU-command segments cost
   5.729/3.805/1.143 ms per pair; full visibility hook only 0.068 ms. Loaded
   native DLL samples resolve against their own PE tables. Timings are
   diagnostic; raw host top-400 covers 1,881/3,085 samples. See the report for
   canonical/eye separation, resolved callers and limitations.
3. **P3c:** target `80011424` (668 bytes, FNV `C38CDCC1`), called by the packet
   builder at `80011000`, return `80011008`. Read the report's exact five-step
   implementation contract first. Capture its custom register/scratchpad/GTE/
   PGXP inputs/results before replacement; `$v0` alone is insufficient. Start
   with the standalone caller harness, then obtain valid per-execution game
   fixtures for integration; never bypass existing state identity guards.
   Optimize through the real caller
   interface, reusing the reference/shared services. Verify unchanged image/FOV,
   aiming, audio/simulation timing, pause/loss/load and original save contracts.
   Run three alternating production A/Bs before promoting an improvement.
4. **Budget decision after the preflight result:** if still too expensive,
   continue the larger packet builder P3d through the same qualification gates.
   P3e HUD work is conditional on a measured remaining stall. Read the existing
   dirty/change detection and shared capture first; do not port checkpoint or
   paired readback again. Use the [decision table](PERFORMANCE_NEXT_STEPS.md#33-what-follows-preflight--choose-by-measured-full-path-budget).
5. **P4/P5:** remove the native ~30-Hz fresh-view ceiling safely, retaining native
   simulation/audio timing. A cheaper pair alone does not produce 60/90 fresh
   views. No turbo, VBlank-rate change or compositor-repeat substitution.
6. Only then request a bounded SP headset performance check (P6). The last smoke
   accepted functionality; it did not certify FPS or every gameplay scope.

| Ordered task | Done only when |
|---|---|
| P3c2 — caller contract/fixtures | Real input/output cases, supported entry/resume contract and valid harness/fixture strategy exist |
| P3c3 — implementation | A build-selected faster helper exists, original reference runs, paired caller-result tests pass |
| P3c4 — correctness | Relevant world/FOV/PGXP/weapon/laser/timing and pause/loss/refusal/load controls pass separately from timing |
| P3c5 — production desktop A/B | Three alternating windows plus the second workload show a useful consistent gain, with exact binary/fixture/flags |
| P3c6 — full path/decision | Actual HUD/weapon/laser/XR work is measured, failures retained, candidate qualified or explicitly rejected; a desktop gain is insufficient |

**Fixture/tool trap:** a new execution family changes identity. Current probes
assume the fixed source-save tree and `build-release`; sibling `--exe` selection
only served same-identity compiler controls. Before cross-profile game timing,
extend the existing probes to select separate valid fixture roots and complete
build/assets/config/cache directories. Those selectors do not exist yet. See
[section 3.2](PERFORMANCE_NEXT_STEPS.md#32-execution-identity-and-fixture-handling--resolve-before-integration).
Never fake compatible states, overwrite shared fixtures, copy a candidate into
another profile's cache, or count a refused load as a pass. Continue independent
harness/implementation work if an integration fixture is unavailable.

**Larger fallback:** cached scene geometry may support fresh-pose rendering if
targeted replay work cannot meet the budget/cadence. It is a conditional design
decision, not the next task or a required alpha feature. Preserve the replay
reference and validate moving geometry/weapon/controller poses and FOV before
claiming success. Record one exact next task after each retain/reject/defer
decision; do not start helper, HUD, scheduler and renderer redesign in parallel.

Known measurements are leads, not a new matched-HMD benchmark:

- Older desktop A/B: pair work 17.668 → 17.608 ms, cadence 28.378 → 29.768/s.
  `MOHU_VR_SKIP_NATIVE_WORLD_COPY=1` skips only an unused canonical world draw.
  It passes Sten/pause/refusal/reload/hitch controls but stays OFF; it does not
  materially reduce stereo replay cost or close 60/90 acceptance.
- Traversal about 15.65 ms; submit 0.65 ms; tree collection 0.056 ms per pair.
  720p/native resolution still about 17.96/17.76 ms. Do not start by reducing
  resolution, caching tree collection or retuning frustum bounds.
- These desktop records have no XR copy/hand-HUD capture cost; full XR/HUD is
  additional. Use current clean image for new A/Bs. Historical two-title scenes
  differ; 65–69% more primitives is workload attribution, not a speed ratio.
- Clean-default slot-5 smoke: 17.391-ms desktop pair work, no HMD cost included.
  No minimum/steady 60-Hz or 90-Hz pass exists.
- Three inlining variants are rejected/removed. Shared IPO reduces desktop
  pair work about 4.3%, but one unchanged-binary null-HMD run regresses badly.
  Full-path gain is unqualified; **PSX_RUNTIME_IPO remains OFF**. Do not average
  away that run or repeat tuning sweeps. Native timers are diagnostic-only;
  restore `MOHU_VR_NATIVE_PROFILE=OFF` alongside debug OFF after their use.

## 5. Closed investigations and separate open scopes

Do not reopen these without new contrary evidence:

- Slot-5 missing world/music: damaged image stalled at raw sector 9469 and
  blocked a native arena load. Replacement passes all 318,028 sector checks;
  operator confirms resolution. No rendering/fog/CD timing bypass is needed.
- Queue terminator is `800B8458 = 800B74B8 + 1000*4`, not `800C8458` (signed
  displacement). Corrected/asserted; this alone was not the world fix.
- Common SP shot seam: `80048604 → 80076C28`, RA `8004860C`; exact firearm
  ID/type guard. Native SP motion stores `800793E4/80079400/8007941C` differ
  from MP's. Do not rediscover the Sten/P38 basis or move aim with recoil.
- Entry-hook config is now **25 entries / 11 instruction sites**. The extra
  arena-wrapper entry supports the default-OFF native-copy candidate. No
  temporary clipping/triangle trace hook remains; generated game C is unchanged.
- SP petrol uses an exact known metadata variant, 99 visible bottle / 97 masked
  arm vertices. Do not weaken all model guards or repeat PCA calibration.
- Checkpoint reuse and paired native HUD readback are already shared. Do not
  port them again or update the framework merely because master moved.

Still open after performance: real SP NPC damage/isolation; broader live SP
weapon/final-origin coverage (especially thrown/rocket); focused HUD/transition
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
- Run focused checks appropriate to changes and `git diff --check`. Current
  baseline: 132 Python tests; strict plugin/native-timer syntax and 480 focused
  slot-5 rollback checks pass. Earlier shot/weapon C controls remain unchanged.
- Update stable IDs in VR_PLAN, the current handoff and compact receipts with
  actual source/binary/fixture provenance. Preserve failed controls and scope.
- Keep dumps, disc/BIOS data, saves and generated screenshots in ignored local
  directories. Do not stage `.commandcode/`, unrelated work or disc assets.
- Commit/push when requested; no PR creation or framework pin change is implied.

Detailed bindings remain in [WEAPON_MAPPING.md](WEAPON_MAPPING.md),
[SP_GAMEPLAY_REPAIRS.md](SP_GAMEPLAY_REPAIRS.md),
[PAUSE_MENU_PARITY.md](PAUSE_MENU_PARITY.md) and their receipts. The superseded
[old handoff](HANDOFF_HISTORY_20261029.md) is evidence only, not a task queue.
