# SP slot 4/5, music and performance repair work

Updated 2026-10-29. Operator priorities: repair Sten/SP aiming, missing
world, music after lag and performance; enable thrown-weapon lasers. Music and
missing world were **separate incidents**, explicitly confirmed by the operator.
SP remains the alpha target. Agent probes were desktop-only; the operator
subsequently ran the headset personally and reports world/music fixed, pause
OK, Sten OK, performance still unsatisfactory. This closes those functional
smokes and does not certify 60/90 FPS or all-SP-weapon gameplay.

**Next execution queue:** [PERFORMANCE_NEXT_STEPS.md](PERFORMANCE_NEXT_STEPS.md).
Sections below retain diagnostic history; do not treat an old “next control”
sentence as current instructions. No more disc/culling/music/Sten/pause hunt
is needed without a new regression. [Operator report](../../vr/proof/clean-disc-headset-smoke-receipt.json).

## Current result — supersedes the investigation notes below

**Image follow-up:** the operator supplied two new images; both are identical
and pass all sector checks, including the missing music payload. See
[DISC_IMAGE_COMPARISON.md](DISC_IMAGE_COMPARISON.md). A copied slot-5 smoke passes
with recovery disabled, then original mod state is restored. The operator then
requested permanent activation after deleting the old/duplicate images; the
remaining clean image is now active for existing RunVR batch files, and the
historical repair is disabled. The earlier request for another dump is closed.

**G1:** `sten-final-rotated`, `sten-final-native`, `sten-final-loss` and
`p38-final` pass. The common SP firearm seam accepts exact ID/type pairs.
Three rotated Sten shots start at the laser muzzle within 1/65536 guest unit;
native first-motion cosines against the ray are 0.9999256, 0.9999957 and
0.9999178, including native spread. SP motion stores are
`800793E4/80079400/8007941C`, NOT the MP addresses. Loss rejects the adapter and
restores native motion. P38 still aims correctly. All these VERIFY controls
have zero mismatches. This does not certify all-ID SP damage, props or rockets.

**G2/G3 cause:** the music retry also blocks a native world-section load.
The libDS header-position check fails at LBA 9469: all 2352 raw bytes are zero,
so its decoded position is -150. The driver retries from 9453 indefinitely.
`indoor-music-native`/`indoor-music-dma` reproduce in native flat mode: unchanged
40-KiB SPU ring, recurring SPU IRQs, completed SPU DMA copying stale halves, CD
DMA reading only 12-byte headers and no 2048-byte payloads. The incidents were
reported separately; this does not attribute both to the same lag spike.
`cd_read_log.lba` records Setloc, NOT delivered LBA; use CD sector trace events.

Read-only `audit_sp_disc.py` finds 64 wholly zero raw sectors. LBA 9469 belongs
to `DATA/MSN2/LVL2/M2_2_1.VB;1`, starting at 9013. The original BIN matches the
project's recorded MD5 `8a2e3361e8272ce09e9a4ea7bd0403ad`; that recorded hash is
not an independent integrity oracle. Exact original SHA-256:
`0951683ffd1bc2db1094ef3b0e142df6741efe2a5f95ad13bb5f2813a6c252d9`.

The game-owned declarative package `mohu.repair.music-sector` restores only
that sector's 24-byte sync/MSF/mode/subheader during reads. Exact source image
SHA-256 and expected zero bytes guard it. It does not modify the BIN/CUE or
change shared CD timing, IRQs or guest driver code. Missing audio payload stays
zero: roughly 0.163 s of silence at the observed half rate. It cannot recover
original music, and other zero sectors are not blindly patched. Another
independently verified dump remains desirable; the operator will find another
after the next run. Do not ask again now. No download or source-image rewrite
was performed.

`music-header-control` and `music-header-hitch-tail` first prove recovery on a
disposable image copy. The latter survives a one-second main-thread hitch:
ring bytes change, full payload reads resume, last-five-second repeat
correlation is -0.03187 instead of the stale loop's approximately 0.994, and
VERIFY has zero mismatches. Then `world-recovery-package` proves the package
on the ORIGINAL source image/copied slot 5: complete/exit 0, player position
unchanged, zero VERIFY mismatches, four arena roots, both stereo eyes show the
restored corridor. Arena 0 finishes loading (1470 -> 1230 vertices). The laser
now hits its wall at 3330.23274606 units; independent triangle intersection
agrees below 1e-5. Before recovery there were three roots and no forward hit.
Final packaged `sten-copy-controller-fallback` also passes the hitch: ring
changes, tail correlation 0.02590, native payload reads resume, no VERIFY
mismatches, clean exit, original saves/preferences unchanged.

Also fixed a signed-displacement error: native `lui 800C; sw -31656` addresses
**800B8458**, not 800C8458. The queue terminator is derived from
`800B74B8 + 1000*4` with a compile-time assertion. This correction alone did
NOT restore the corridor. Do not reopen culling bypasses for this fixture.

The later `world-full-interpreter` additionally disables static native text
(`PSX_FORCE_INTERP=1`); it fails identically. The earlier overlay-only
interpreter control did not exclude static codegen. A temporary trace proves
the floor triangle at `800E97D0` passes backface culling and has subdivided
packets; its hook/generated edit was removed. Missing geometry was in the
uncompleted arena load, not that triangle's projection.

**G4:** prop ID exclusions are removed. `petrol-laser-final` passes eight
directions, both eyes/independent hits against 7,251 SP triangles, grip release
and tracking loss with zero VERIFY mismatches. MP grenade calibration reaches
all eight matching ray cases, but its longer run reports two VRAM-only restore
failures (CPU state hashes agree). A shorter RAM-snapshot control also fails
with three VRAM mismatches. Preserve BOTH failed receipts; changing query
duration does not fix the restore failure. MP remains calibration; do not
expand this into unrelated MP feature work or claim SP grenade acceptance.

Tool corrections: `audio_wav start=-1` means OLDEST samples, not the tail;
earlier five-second correlations refer to the prefix. Tail captures now use
an explicit absolute sample index. Laser working caches clear during replay;
geometry now reads native SP arena records and a captured RAM image, and eye
queries require a coherent valid pair. Do not treat an in-flight zero cache
count as unloaded geometry, or a failed tool export as a passed probe.

The historical notes below preserve rejected controls and partial evidence;
they are not the current task queue.

## Fixtures and current work

- Fresh states are `analysis/vr-baseline/saves/openbios/state_8001F844_slot04.*`
  and `slot05.*`, saved 2026-10-28 20:27 local. Copy fixtures before running.
  The root `saves` tree has older/different states.
- `probe_sp_issues.py` owns copied fixtures/process, synthetic hands, native
  input, stage/host/phase/GCP evidence, stereo images, SPU/CD/IRQ/audio captures
  and source/preference hashes. Run it **outside the sandbox**. Raw evidence:
  `analysis/vr-baseline/sp-issues-20261028/`.
- Default hidden-GL controls have no audio and are unpaced throughput probes;
  they are not 60/90-Hz acceptance. `--audio` uses a hidden SDL window and dummy
  audio sink with the normal pacer. VERIFY is a separate correctness control.
- An initial `world-software` request still used `--headless-opengl`, which
  overrides backend selection. It is NOT software-renderer evidence. The
  corrected `world-software-actual` uses `--headless --renderer software` and
  native VRAM screenshot capture; the missing world persists there.

## G1 — common SP firearm aiming

The old SP adapter explicitly accepted only ID 0/type `13F6`, despite all-ID MP
calibration and tracked SP models. Slot 4 Sten is ID 16/type `13F7` at the same
guarded native `80048604 -> 80076C28`, return `8004860C`, P1 owner/input layout.
The baseline `sten-before` shows native shots and no `mohu.vr.shot.sp.aimed`.

The retained change uses the held ID's calibration and exact ID/type pairing
for single, repeating and bolt families at this SP seam. All owner, caller,
code, camera-age and tracking checks remain. Thrown and rocket final-origin
adapters remain separate; this does not claim their SP conversion is complete.

`sten-after`: a +35-degree synthetic hand receives two native Sten constructions
with the same hand-fixed output pose; the direction agrees with the concrete
surface laser. 272 VERIFY checks, zero mismatches/eye failures, unchanged sources
and preferences, clean exit. Further fallback, pose/motion and P38 controls are
still required before final acceptance. Unit tests reject wrong type/unknown IDs
and keep props/rockets out of this common firearm seam. All-ID SP live damage
acceptance is not implied by those pure guards.

## G2 — historical missing-world investigation (resolved above)

`world-before` reproduces the broad black gap with an NPC visible. The gap also
persists with native frustum (`world-native-frustum`), all leaves collected
(`world-all-leaves`), native flat (`world-flat`), full interpreter flat
(`world-flat-interp`, actual native exec/call count 0) and actual software
rendering (`world-software-actual`). Precision-disabled native flat also fails.

Two bounded replay-only triangle preflight experiments were rejected:

- clearing the aggregate RTPT error before helper `80011424`;
- retaining front-facing projective triangles at continuation `80011008`.

Counters proved execution and rollback passed, but neither repaired the visible
gap. **Both were removed**, including their generated hooks/config changes.
Do not reinstate them or relax all culling as a shipping fix.

The native SP arena array is at `800A57DC`, stride `C4`, count `[800A5384]`.
Slot 5 has four records; the normal caller `80057D60` skips index `[800B749C]`.
The three observed draws are records `800A58A0`, `800A5964`, `800A5A28`.
The skipped record 0 has a valid root far behind this player; skipping it alone
is not proof of this defect. The source maps contain 6,284 decoded triangles in
these three roots; `world-ray` independently finds no forward wall hit and does
find nearby floor/ceiling intersections. Native packet cursors retain ample
space (around 60 KiB), so primitive-arena exhaustion is not established.

Relevant functions: arena wrapper `8009A478` (208 bytes, FNV `981FD4DF`),
drawer `80010CF0`, preflight helper `80011424` (668 bytes, FNV `C38CDCC1`),
leaf queue selector `80099960`. No cause/fix is claimed yet.

## G3 — historical music investigation (resolved above)

The controlled one-second main-thread stall leaves SDL's audio thread running.
Audio resumes non-silent output, but that alone does not prove music advances.
The indoor SPU recording has high correlation at a **143,360-sample / 3.250794 s**
period, consistent with a 40-KiB ADPCM ring at voice 0's half-rate pitch. The
indoor no-injected-hitch `world-ray` recording shows the same period; outdoor
slot-3 controls do not. This is evidence to inspect the stream refill chain,
not yet proof of its failure mechanism or a complete reproduction of the
operator's original lag event.

The first `indoor-audio-hitch` tool run failed while exporting empty CD-in audio:
this music uses SPU output, and CD-in had zero frames. That run is not accepted
as a complete probe. Its recorded SPU PCM remains useful diagnostic data. The
tool now exports only nonempty taps and captures voice-0 ADPCM RAM, IRQ state,
SPU events and CD traces. Next control: native flat versus stereo on the same
slot-4 copy; compare ring hashes and IRQ/DMA/CD progression before/after 12 s.

## G4 — thrown laser

Removed the ID-10/15 suppression in the calibrated hand-fixed ray path. The
existing native prop calibration keeps the held model upright and its ray
forward. This is a straight surface aiming ray; gravity/flight stay native.
`petrol-laser` shows ID 15, valid concrete hit at distance 1726.02684 guest units,
both-eye drawing/99 bottle vertices, and zero VERIFY mismatches. Grenade and
tracking-loss/release controls remain to be completed.

## Performance: current candidate, not a promoted gain

Existing profilers now retain host-module attribution and static/native guest
function histograms. PGXP CPU arithmetic/load/store/journaling is significant;
guest-cycle counts alone do not measure host cost. The static clip helper is
also visible in the sampled workload. Do not restart the already-fixed native
overlay-cache diagnosis.

An opt-in `MOHU_VR_SKIP_NATIVE_WORLD_COPY=1` candidate filters only the draw-only
SP arena wrapper after a successful stereo publication. It refreshes the
unposed canonical shot-camera cache at the same GTE state, returns the native
allocator cursor, and keeps canonical actor/input/audio/menu execution. It is
off by default and refuses stale/failed-pair/menu cases. No framework change.
The final debug-ON `sten-copy-controller-fallback` passes native Sten motion,
music hitch recovery, pause/resume, forced render refusal and save reload with
zero VERIFY mismatches. Counter stops while paused/refused and resumes after
recovery; the canonical shot camera remains valid. Two earlier harnesses failed
because raw debug input either missed the native poll window or prevented the
VR menu route. The corrected tool clears that layer and uses the existing
`probe_pause_menu.py` controller route. Those earlier runs remain incomplete.

`profile_sp_production.py` measures Release/debug-OFF without TCP or an XR
session, using copied states, one opt-in 120-pair stage export and normal close
of its own hidden window. **No synthetic hands, XR copy, or hand-HUD capture
cost is present. These are desktop-work controls, NOT headset FPS.**
Three alternating slot-3 A/B runs:

| Policy | Pair cadence, runs 1/2/3 | Mean pair work | Mean native interval |
|---|---|---|---|
| Baseline | 28.159 / 27.649 / 29.325 per s | 17.668 ms | 35.239 ms |
| Skip unused native world copy | 29.945 / 29.661 / 29.698 per s | 17.608 ms | 33.589 ms |

Mean cadence rises 28.378 -> 29.768 (+4.9%); individual gain ranges 1.3–7.3%.
This removes canonical work but does NOT materially speed the stereo pair.
Restored slot 5 gives 17.242 -> 17.200 ms pair work in one A/B, not a repeatable
60-Hz result. Keep the candidate OFF pending fuller visual/canonical acceptance.

Resolution isolation with the candidate gives 17.962 ms at 720p and 17.759 ms
at native resolution, versus about 17.608 ms at 1080p. Lowering resolution does
not remove this CPU replay cost. Per pair, traversal is about 15.65 ms, submit
0.65 ms, tree collection 0.056 ms. Do not spend the next turn tightening the
frustum or lowering resolution as the presumed main fix. Full XR/HUD cost is
additional, and native draw cadence still caps fresh pairs near 30.

## Investigation-era continuation (superseded by performance runbook)

1. Keep the original image plus the guarded recovery for the next run. When the
   operator supplies another dump, run the read-only audit; compare ISO file
   bytes and raw headers. Do not overwrite the original or fabricate other lost
   asset sectors. Do not repeat the slot-5 culling hunt.
2. Performance P3b/P3c: attribute the 15.65-ms native replay using existing
   host/phase profilers, adding bounded title spans around arena draw
   `80010CF0`, subdivision `80010000/80010508`, preflight `80011424` and entity
   work. Trace spans must distinguish canonical execution from each eye. Only
   then implement the dominant operation behind its measured caller interface,
   following `psxrecomp/AGENTS.md` and `docs/HLE_EXECUTION.md`; preserve a runnable
   reference and save compatibility contracts. Do not disable PGXP for a number.
3. P4: once the work fits the budget INCLUDING XR/HUD, decouple fresh view
   publication from the native 30-Hz draw loop. Preserve native simulation,
   audio, input and streaming cadence; compositor repeats or double-speed
   gameplay are not a 60/90 pass. Require three production A/B repeats and
   pause/loss/load/streaming controls before promoting any policy.
4. R6 remains: real SP NPC damage, broader live SP IDs and separate thrown/rocket
   final-origin adapters. Grenade rays are enabled, but its long MP calibration
   restore failure remains a named issue, not a clean pass. Do not turn MP into
   the alpha acceptance target.

Production Release/debug-OFF is restored. No framework changes or source-save,
disc, headset/runtime preference changes were made. 127 Python tests, strict
shot/weapon fixtures and strict plugin syntax pass. No physical headset launch,
commit or push occurred in this turn. The compact
[receipt](../../vr/proof/sp-gameplay-repairs-receipt.json) retains source/binary
hashes, partial/failed controls and quantitative evidence. Alpha/60/90 remain open.
