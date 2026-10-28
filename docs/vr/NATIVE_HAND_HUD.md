# Native hand HUD parity

Updated 2026-10-28. **SP is the alpha release target. MP is only the quick
all-weapon calibration fixture; MP feature completeness does not gate release.**

The reference `vr/moh_vr_hud.c` and `psx_vr_stereo.c::vr_capture_native_hud`
already solve native artwork extraction and hand surfaces. Underground now ports
that implementation through the existing framework APIs. No replacement health
bars, fonts, framework changes, generated guest C or save-layout changes.

## Implemented contract

- Two rollback-only native HUD draws over black/white mattes, one paired
  readback. No world traversal or simulation update is run for capture.
- Left hand: native health/compass artwork; right hand: native ammo icon and
  formatted clip/reserve strings. Regions are `(8,8,112,112)` and
  `(368,8,136,40)` in the isolated 512x240 capture.
- Reuse straight-alpha dual-matte extraction, 12 cm hand-position attachment,
  +6 cm vertical offset and `PSX_MOD_OPENXR_SURFACE_FACE_HEAD`. Controller roll
  cannot rotate the text. Fresh focus/origin, valid active grips and age <=100 ms
  are required. Artwork and replacement ownership reset every frame.
- Suppress each native HUD component only after its own hand surface succeeds.
  Capture failure, hand loss, focus loss, stale pose or upload rejection leaves
  that native component visible. Opaque black artwork stays opaque.
- Preserve non-ammo native text. The old blanket text-producer skip also hid
  unrelated objectives/notifications. Only strings owned by the current player's
  native clip/reserve pointers are moved to the right hand.
- Native pause uses its existing complete menu plane with no hand HUD requests.
  Save load/resume recaptures fresh native values. Normal flat play is untouched;
  desktop stereo does not pay HUD readback cost unless explicitly requested.
- `PSX_VR_WRIST_HUD=0` disables hand HUD capture and retains native components.
  Normal XR defaults to the hand HUD. `-KeepFlatHud` remains a comparison switch.

## Underground bindings

| SP source | Verified binding |
| --- | --- |
| Frame context / player | `800A7138` / `[800AA17C]` |
| OT / native packet bank | Context `+2218` / `+221C`; bank must be 0 or 1 |
| Health/compass producer | `8006C874`, size `4CC`, FNV `3ACE0C9A` |
| Text producer | `8006B64C`, 692 bytes, FNV `7E13324D` |
| Text count / entries | `[800A69E0]` / `800A6A5C`, 32-byte entries, flags `+18` |
| Player input / ammo strings | `[player+39C] == player+3FC`; clip `input+110`, reserve `input+114` |
| Ammo icon producer | `8008F9F4`, size `A4`, FNV `B142D786` |
| Icon ownership | `input+C0+40*bank`, native nine-word FT4. No absolute fixture actor or fixed weapon UV assumption. |
| Health/compass packet blocks | `800B8C88` / `800BA488`. The former constant `800C8C88` missed the signed `ADDIU` relocation. |
| Draw environment / OT submit | Existing guarded `80018BB8` / `80018B48` |

Native white reads back as **248** under this renderer's RGB5 GP0 fill, rather
than 255. The extractor validates the isolated empty corner and uses its measured
white level. Copying the reference's literal 255 left alpha 7 over transparent
backgrounds. Final native reconstruction error is <=1 channel value, with zero
opaque content outside the owned regions.

The MP calibration fixture uses native producers `80063244`, `80061E64`,
`80087BC4`, text table `800A0394` and input strings `+720/+724`. Its P1-only
fallback excludes P2 ammo. These bindings are retained as calibration support;
do not expand MP into a release project or an additional acceptance checklist.

## Evidence and limits

[Compact receipt](../../vr/proof/native-hand-hud-receipt.json) identifies source
hashes, diagnostic/production binaries, raw controls and their exact scopes.

`probe_native_hud.py <fresh-directory>` uses copied SP slot 3 and native input.
`--headless-xr` uses the existing restore-protected SteamVR **null HMD** launcher;
it does not use a physical headset. All game launches run outside the sandbox.
The accepted SP run checks:

- Native clip `8 -> 7 -> 8` and reserve `24 -> 23`, with corresponding captured
  native artwork; pause clears requests and Continue recovers them.
- Save reload restores original values and fresh artwork.
- Both hand surfaces upload through the actual XR backend; left grip loss leaves
  right replacement, both lost leave neither, recovery restores both, focus loss
  removes both. Per-eye rollback checks have zero mismatches.
- Strict C coverage includes 248/255 mattes, opaque black, independent invalid
  captures, stale/focus/hand loss, nonfinite position and upload rejection.

Physical placement/readability, briefing/movie transitions, native mission-text
scenarios and sustained production headset performance remain open. H1 is an
implementation/desktop/null-HMD result; H2 and full A5 are not blanket acceptance.

## Next: SP combat and playability, not another MP campaign

1. R6: use a real live SP NPC, arm narrow health tracing **before** firing, and
   compare native/fallback, tracked-toward and tracked-away controls from the same
   copied state. Link the native damage writer's target and source to that shot;
   record NPC-owned constructors separately to prove isolation.
2. **SP damage differs from MP:** offline slot-3 code has native health subtraction
   at `8004E13C`, store at `8004E144`, function entry `8004E0C0`. Verify the complete
   live function before tracing. MP's `8004EB80` is not the SP writer.
   `mohu.vr.shot sp-camera` exposes the existing canonical SP cache read-only;
   do not reuse `camera`, which reports the MP cache.
3. A bounded slot-3 discovery observed four class-65 actor candidates and native
   tracked shots, but did not establish clear sight or linked damage. Its first
   trace used the wrong MP damage span and is **not damage absence evidence**.
   Current analysis slot 0 failed ABI load; do not retry it unchanged. The old
   `weapon-shot-mapping/probe.py` guessed `8009DF70` as enemy health; that is not
   a verified actor health binding. Do not rerun that script unchanged.
4. Establish an engaged, unobstructed NPC using native movement in compatible
   slot 3, or a verified compatible combat fixture. Do not edit health/ammo or
   derive an acceptance claim from flashes, counters or MP P2 health.
5. Expand the SP shot adapter beyond its current P38-only guarded binding, using
   the existing all-family MP measurements as leads and native SP constructors
   as the actual authority. Then run the focused SP alpha route/performance/
   recovery checks. R5 fog still waits for its matching street-wall fixture.

The operator deferred physical testing until the remaining fixes are ready.
