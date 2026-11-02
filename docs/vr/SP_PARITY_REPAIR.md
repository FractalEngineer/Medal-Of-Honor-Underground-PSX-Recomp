# SP parity repair and quality checkpoint

Updated: 2026-10-28. Desktop validation only; physical acceptance remains open.
[VR_PLAN.md](VR_PLAN.md) owns R1-R7 and [HANDOFF.md](HANDOFF.md) gives the next
experiment. Compact evidence: [sp-parity-repair-receipt.json](../../vr/proof/sp-parity-repair-receipt.json).

## Why the previous result was misleading

The owner was right to reopen this work. The previous game's scoped weapon draw,
post-animation placement, weapon-only selection and coordinate precision already
provided the architecture. Underground ported MP first but its later SP adapter
omitted important parts of that pattern. The handoff then called a physical pass
next while the checkbox plan still claimed there was no SP binding.

There were two separate flash errors:

1. SP bank 0's FT4 tag is `player+0x5FC`; `+0x600` is its color-source address.
   Bank 1's tag/color are `+0x624/+0x628`. The old code treated `+0x600` as a tag,
   so its shape guard silently declined that visible packet. Bank 1 still supplied
   successful alignment counters. These are 40-byte buffered native packets;
   the previous flat/stereo labels were incorrect.
2. The SP target used a fixed calibration point and treated `projection_h_ref=400`
   as a focal length. The renderer also uses per-eye focal/center parameters and
   the native H/reference ratio. Native H is 133 at the measured project seam.
   A hand-X delta or one selected image did not validate that second projection.

The reference's rendered-affine capture was reusable. Its reviewed plugin does
not contain a separate native-flash-packet relocation function to copy directly.
Underground still needed its own packet bindings, but it did not need a second
muzzle projection or a new weapon architecture.

## Implemented correction

- Keep ownership at SP `80091854`, caller `80091420`, with the measured model
  identity, player, code and hand guards. The existing P38 shot basis remains
  `80048604 -> 80076C28`, return `8004860C`, type `13F6`.
- Apply the calibrated transform at `80090954`, after native animation and
  RT/TR restoration. Use the reference precision principle: uniformly lift
  weapon camera coordinates and eye translation, selecting a safe power-of-two
  factor within Q12/TR bounds. Restore the world view and GTE state afterward.
- At `80090A78`, read the exact projected animated muzzle vertices consumed by
  the native triangles. The same reader now feeds SP and MP flash placement.
  Translate the existing guarded FT4 packets; preserve their native UV/color,
  shape, OT placement and lifetime. Recoil moves the visible muzzle/flash; it
  does not steer the hand-fixed shot/laser ray.
- A known owned muzzle outside/behind the eye degenerates only its guarded flash
  during replay. It cannot leave an authored centre-screen flash visible.
  Malformed/unknown packet shapes are still declined; unrelated effects remain native.
- Reuse the validated gun-island mask after projection. P38 keeps 96 vertices,
  including its 27-vertex node-11 barrel, and masks 142 arm vertices per eye.
  Tracking loss retains the native gun-only fallback instead of exposing arms.
- Parse explicitly requested physical units in desktop controls too. Earlier
  no-XR runs ignored that setting and used the 716.418 default; current focused
  SP controls request the same 238.806 units/metre as normal world-scale-3 VR.

## Slot 3: the disappearing gun was an allocation failure

The copied analysis SP slot 3, viewed at +60 degrees, reached `8009086C` with the
native primitive arena full. The held draw returned before its project seam.
This is separate from muzzle calibration and from a hand legitimately outside the FOV.

The native primitive pool uses `[800A5380]` as base and `[config+0x98]` as bank
size, with current cursor/end at `800A5358/800A535C`. The repair checks the exact
arena getter/setter code, both bank bounds/alignment and the current bank. Only
when space is insufficient, it scans the eye OT and source-model spans and
borrows an unreferenced 32 KiB tail of the other native bank for the held draw.
It restores both arena words immediately. Eye rollback owns all packet writes.
Invalid bounds, referenced packets or source overlap refuse borrowing.

The same-binary causal control (`870a4d5a...`) produced:

| Control | Arena-full refusals | Spare uses | Gun vertices per eye | Masked arms |
| --- | ---: | ---: | --- | --- |
| Spare disabled, head/hand +60 degrees | 141 | 0 | 0 / 0 | 0 / 0 |
| Spare enabled, same fixture/pose | 0 | 135 | 96 / 96 | 142 / 142 |

Final-source enabled/reload/out-of-view controls are recorded separately in the
receipt. Broader scene, streaming and non-P38 SP coverage remain open.

A trial persistent GPU-DMA allocation was removed: it changed the enhancement
memory-layout cookie and rejected the original save. Reducing only the native
reservation was also insufficient in the saturated view and was removed.
Do not repeat those approaches or modify personal save headers to hide rejection.

## Flash evidence is now checked against the visible copy

The corrected baseline captured bank 0 color source `player+0x600` at projected
centre `(350,217)`. The +150 mm hand-X control captured both sources `+0x600`
and `+0x628` at `(450,217)` in 512x240 eye coordinates. Its counters recorded
374 bank-0 and 400 bank-1 operations, 774 alignments and zero fallbacks.
The natural flat frame is retained separately and still has its native packet;
that is not the VR eye image.

Actual eye images show the flash at the barrel, including baseline
`sp-both-flash-banks-20261028/sp-eyes/p000028_{left,right}.png` and displaced
`sp-flash-shift-both-banks-20261028/sp-eyes/p000029_{left,right}.png` under
`analysis/vr-baseline/`. Their hashes and binary provenance are in the receipt.
The baseline precedes the additional out-of-view suppression guard; the displaced
capture uses the final diagnostic source. Current out-of-view control checks that
owned flashes are hidden, with the hand-fixed shot path still active.

The existing all-family shot and native recoil policy is unchanged. These tests
observe native P38 construction/aim events; they do not establish linked SP NPC
health decreases or physical impact alignment.

## Performance and native integration

Detailed debug recording was still enabled in the playable cache. The reference
already documented its cost. Normal `build-release` is now restored to
`PSX_DEBUG_TOOLS=OFF`. `run_vr.ps1 -Build` explicitly selects ON only when a debug
port is requested, and uses two build jobs.

Matched hidden-window runs use the copied SP slot 3, 1080p, unchanged rendering,
no XR, no synthetic hand input (native gun-only fallback), no screenshots and
VERIFY OFF. Unique pair cadence is derived from counter deltas over quiet
8-to-30-second windows. This measures build overhead, not headset display FPS or
tracked-hand performance. The receipt records exact binaries and source identity.

| Final-source build | Fresh world pairs/s | Cleanup |
| --- | ---: | --- |
| Detailed debug ON | 18.17 | Clean exit 0 |
| Production debug OFF | 29.19 | Clean exit 0 |

This is a 60.6% pair-throughput increase with the same final plugin source and rendering
configuration. An earlier checkpoint also measured 19.01 pairs/s with debug ON
versus 28.50 and 29.10 with OFF; those binaries predate the last flash-tag/hidden-
muzzle correction and are retained as supporting measurements, not relabeled.
The current production executable is `6c39318c2fb27c7574ab90417581beb32a9ff8987c0563a3e6c216f9a063cbf8`.
A common guest-frame 300-to-900 cross-check, interpolated from the once-per-
second framework logs, also supports the direction of the gain (approximately
36.3 versus 60.8 guest frames/s). This is an approximate cadence cross-check,
not a frame-latency distribution. Future comparisons should also enable the
existing `PSX_BENCH_WINDOW=300:900` report directly.
The performance campaign and physical performance gate remain open.

R4b is now complete. `game.toml` declares 24 entry hooks and 11 guarded
instruction sites derived from the plugin registration block and verified engine
map. The supported emitter regenerated the static forwarders and overlay codegen
identity. Native cached overlays produce real pairs and execute the SP weapon,
flash, arena, HUD, frame and focused MP callbacks. The SP
baseline/turned/close/lost/out-of-view controls and a P38 MP
stereo/fire/rollback/recovery regression pass with native-call evidence.

The matched production comparison used one debug-off binary, copied SP slot 3,
1080p, no XR, no tracked hand, VERIFY OFF and `PSX_BENCH_WINDOW=300:900`:

| Mode | Pair cadence | Wall | Guest work | Dirty instructions |
| --- | ---: | ---: | ---: | ---: |
| Native cache | 30.00/s | 9,943.5 ms | 7,979.9 ms | 379,200 |
| Interpreter config | 29.19/s | 9,897.8 ms | 9,760.2 ms | 133,806,583 |

This is a bounded scene result: wall time is effectively flat (0.46% slower in
the final native sample), while measured guest work falls 18.2%. It is not a
uniform FPS gain. The native path executed 2,807,918 overlay calls in the
window after a warm cache. `PSX_NATIVE_BLOCK` remains only a localization control.

## Verification and continuation

- 123 Python tests pass, including an exact `game.toml` hook-list and generated
  main-EXE forwarder regression. Strict weapon/MP C fixtures cover masks,
  precision bounds, spare-bank bounds and malformed cases. Strict diagnostic
  C syntax and Release builds pass.
- Changed SP paths exercise lateral eyes, translated hand, +60-degree head/hand,
  close hand, tracking loss, native firing, repeated load and out-of-view flashes.
  Receipts distinguish old scope tests from final-source tests. Recorded eye
  verification has nonzero checks, zero mismatches and no watchdog/discard errors.
- Focused MP flash transport retained a clean exit with a bounded 20-second
  shutdown allowance. This does not close the older physical MP cleanup issue.
- Source saves/preferences are unchanged. No first-game source, framework/UI pin,
  framework master or generated guest C changed. No headset was started.

Next independent desktop work is linked live SP NPC damage/isolation and family
coverage (R6). R5 fog remains open but is paused: the captured slot 0/2/3 states
do not match the operator's street-wall case. Do not tune distance/fog values
until a correct fixture is available. A later operator-requested MP/SP physical
batch ran; specific grenade orientation, scale, StG hand, high-shot and laser
failures reopen calibration/visual acceptance. The current alpha-first order and
runtime menu study are in [ALPHA_PLAYABILITY_AND_CALIBRATION.md](archive/ALPHA_PLAYABILITY_AND_CALIBRATION.md),
which supersedes the earlier physical-batch/W6 priority here.
