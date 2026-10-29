# Weapon Mapping Handoff

Last updated: 2026-10-29

Execution order and stop/recovery rules are in [HANDOFF.md](HANDOFF.md).
Checkbox status is in [VR_PLAN.md](VR_PLAN.md). **NEXT implementation: G7, all
existing MP weapon calibrations/control paths into SP first**, especially the
reported petrol bomb/Panzerfaust fixed aiming. Follow the
[SP parity runbook and 13-ID matrix](SP_WEAPON_PARITY.md). Native hand HUD is
already ported; do not port it again or treat MP all-ID controls as SP acceptance. See
[SP_PARITY_REPAIR.md](SP_PARITY_REPAIR.md) for the
current muzzle/arm/slot-3 fixes and
[ALPHA_WEAPON_REPAIRS.md](ALPHA_WEAPON_REPAIRS.md) for authored orientation,
scale, StG hand filtering and completed W6.2/W6.3 exact laser desktop evidence.
W3.4, W4 P38 native mapping, W5.1,
W5.3/W5.4 desktop gates and W6.1 hand-fixed ray capture pass;
physical acceptance remains open. All 13 IDs now have measured
complete-gun topology, animated captures, provisional calibration, passing
gun-only desktop controls and moving-marker animation evidence.
Read [P38_NATIVE_AIM_EVIDENCE.md](P38_NATIVE_AIM_EVIDENCE.md) for current
bindings and the corrected mixed-node barrel. Read
[WEAPON_COMPLETE_PROFILES.md](WEAPON_COMPLETE_PROFILES.md)
for the all-ID mask/calibration table and the dynamic-marker requirement.
Historical sections below remain measurement history, not instructions to
repeat completed gates.

Current operator contract: the laser shows the bullet's hand-fixed aim ray;
native recoil is visual. Fixed calibration/hand affine drives shots and the
future laser. Animated markers remain diagnostics. This supersedes older
moving-marker aiming requirements; see RENDERED_MUZZLE_EVIDENCE.md.

## Current result

The visible **top-view P1 first-person mesh seam is now located**. The guarded,
opt-in implementation projects the real first-person object's native animated
vertices with a temporary GTE rotation/translation, then restores all eight
RT/TR words before returning. The default path keeps native shots. The separate P38 diagnostic candidate
now uses a calibrated grip and rendered-muzzle native-shot override; see the
current evidence linked above. The world view remains independent.
The VR launcher enables calibrated gun-only SP/P38 control. The separate
`MOHU_VR_MP_CONTROL` bench remains opt-in. Native/flat launch is separate.

W1 is also complete for the P38 synthetic spatial contract. The real right-hand
path now supplies absolute placement for ID 0 only; the first-accepted neutral
pose and direct x/yaw controls are not used as acceptance. Independent head and
hand cases pass numerically and visibly in both eyes. This remains a desktop
coordinate test, not W3 physical grip or size calibration.

W2.1 is complete for the native MP selector trace. It is a flat scene-list and
per-object visibility path, not the SP `80099960` PVS queue. No MP frustum
override existed at W2.1; W2.2 now adds one behind `MOHU_VR_MP_FRUSTUM=1`.

Use the four copied multiplayer saves and stationary P2 target for this work.
Do not create, migrate, patch, or overwrite the operator's saves. Reload a copied
slot after a kill. No single-player target is needed for MP model mapping.

The adjacent reference game's `VR_WEAPON_TRACKING.md`, `VR_WEAPON_AIM_PLAN.md`,
and `VR_WEAPON_BATCH.md` distinguish first-person geometry from the held/body
object. Following that contract exposed Underground's separate viewmodel. The
reference's offsets, calibration, mesh profiles, and shot hooks were not copied.

## Measured native contract

| Item | Underground multiplayer |
| --- | --- |
| P1 / P2 actor roots | `0x800A3604` / `0x800A3608` |
| Input pointer field | `[actor + 0x39C]`, measured value `actor + 0x400` |
| Inventory slot / weapon ID | `input + 92` / `input + 93` |
| First-person object | `[actor + 0x114] == input + 0x9F0 == actor + 0xDF0` |
| Third-person body object | `actor + 0x4AC`; 22 nodes, magic `0x00160024` |
| First-person caller | `0x8008A3DC`, call `0x8008A53C`, return `0x8008A544` |
| Animated model geometry | `0x800892E8`, 0xA70 bytes, FNV32 `0x39E56A35` |
| Native animated vertex producer | `0x8008DB98`, 0xB4 bytes, FNV32 `0xFAE3646E` |
| Pose application | `0x800894DC`, after native vertices and RT/TR restoration |
| Scope restoration | `0x80089D30`, common epilogue for normal and early returns |
| Native weapon projection | `H = 133` |
| Mesh fields | magic `+0x70`, node header `+0x80`, face count `+0xB6`, faces `+0xB8` |

`0x800892E8` was historically labeled a multiplayer player update. Its captured
code and the measured `0x8008A544` call show that this instance is an animated
model geometry method: `a0` is a model object, not the actor. The engine-map name
is corrected; its historical role enum is retained. The single-player overlay
at `0x800892C8` (0xF20, FNV32 `0xF4D6C439`) is a separate generation and is not
covered by this MP hook.

Read actor globals at use time. The sample pistol object `0x801491C0` is a heap
observation, not a fixed address. Object `+0x5C/+0x64` fields are animation state.

The hook requires the exact caller instruction and return address, P1 identity,
input/object pointer relationship, H=133, full geometry/vertex-producer function
hashes, known weapon ID, exact magic, native face count, node counts, and a hash
of every source vertex record. Vertex hashes include counts and data, not heap
pointers, so repeated IDs in different source slots retain the same guard.
Unknown layouts, code, projection, or tracking return to native rendering.

## Shot-family map

All 13 IDs enter the native basis builder `0x8006C8B0` with caller
`0x800488D8`. `shot.h` maps the measured types and returns unknown IDs to native.

| Type | IDs | Family |
| --- | --- | --- |
| `0x13F1` | 13 | rocket |
| `0x13F3` | 10, 15 | thrown |
| `0x13F6` | 0, 5, 8, 9, 12 | single |
| `0x13F7` | 1, 4, 16, 17 | repeating/spread |
| `0x13FA` | 14 | bolt |

The shotgun constructed six native pellets in one trigger window. Read
[SHOT_FAMILY_EVIDENCE.md](SHOT_FAMILY_EVIDENCE.md) before changing family
behavior. The separate default-OFF W5.3d `MOHU_VR_WEAPON_AIM` candidate now
converts all five families from animated markers. W5.3e paired preservation and
P2 impact pass on the copied MP fixture; physical and NPC/SP acceptance remain
separate.

## P1-only multiplayer eye replay

The opt-in `MOHU_VR_MP_CONTROL=1` bench now reconstructs the native P1 view
inside each existing stereo rollback transaction. It uses the same real
first-person mesh hook in both eyes. Canonical two-player simulation continues
outside replay; source saves and native shot logic remain unchanged.

| Contract | Underground MP |
| --- | --- |
| Frame context | `0x800A0B08`, native source view 512x120, world H=400 |
| Natural frame entry / caller | `0x80054BC4` / `0x80063CF8` |
| P1 camera root | `0x800A35B0` |
| Current selected player | `0x800A35C4` |
| Scene-list root | `0x800A35CC` |
| Camera selector | `0x80054E68(camera, 0)` |
| Scene draw | `0x8006E9D8(context, list)` |
| OT | `[context+0x2218]`, 512 entries, native guest `DrawOTag` |

Full function guards cover frame entry (512 bytes, FNV `6CDFBB75`), camera
selection (332, `2BE15194`), scene draw (384, `04C21F46`), and native player
render callback (580, `8B9E349D`). The exact natural caller, 512x120/H=400
context, actor classes, input pointers, and camera handle resolving to P1 are
required before replay. Mode/ownership/pointer failures decline the bench.
The camera selector must actually select P1 before the scene is drawn.

Replay omits the enclosing two-view renderer, its waits, flip and P2 submission.
It rebuilds one native P1 OT per eye, uses the rollback-protected y=0 buffer,
and submits it once through guest `DrawOTag`. This retains PGXP packet source
addresses. It also omits the native split HUD; the MP laser is not drawn yet.

The eye view uses H=400 for the world. The native weapon uses H=133. Its
scoped `projection_h_ref=400` preserves the native 133/400 focal ratio while
retaining eye rotation/translation; the world view is restored at the common
geometry epilogue even for lost tracking. Using absolute world focal length,
or setting the reference to 133 without a calibrated replacement mesh pose,
makes the native gun too large and clips it out of the view. Those first trials
are rejected. This differs deliberately from the reference game's calibrated
mesh transform and does not copy its calibration.

The final desktop matrix covers all 13 IDs and closes all four native cycles.
Native, +24 translation, +12-degree yaw and lost tracking have complete 512x120
eye pairs. Zero eyes match byte-for-byte; both eyes apply the tracked transform
and both decline it during loss. Sampled world pixels stay fixed while the
visible gun moves. The last matrix snapshot has 1,215 pairs and 2,430 rollback
checks, zero mismatches/leaks/watchdogs/repairs, and matching eye state/cycles.
A lateral +/-24 eye control changes 52,136 pixels between complete eyes.

A native pistol shot while MP replay and +24 weapon pose are active reduces
P2 health from 32 to 31.25 and the clip from 8 to 7, with the native health-write
trace retained. Deliberately refusing render passes then clearing the refusal
recovers fresh pairs. Refusal/stale counters are historical: recovery is judged
by a newly captured pair ID after the last failed attempt, not by erasing those
counters. The accepted control has seven admission refusals and no failed eye.

Reproduce with the diagnostic build (debug tools ON):

```powershell
python vr/tools/check_mp_view.py analysis/vr-baseline/weapon-mesh-mapping/new-mp-eyes --all-weapons
python vr/tools/check_mp_view.py analysis/vr-baseline/weapon-mesh-mapping/new-mp-lateral --eye-offset 24
python vr/tools/check_mp_view.py analysis/vr-baseline/weapon-mesh-mapping/new-mp-fire --fire-pistol --reject-recover
```

Use `vr/tools/summarize_mp_view.py` to verify those three directories and retain
the compact receipt and proof sheet. Desktop MP eye rendering is accepted at
this fixture; physical headset tracking, independent head/hand calibration,
head-turn visibility and broad MP gameplay are still open. The native MP level
selector remains in use; the SP head-frustum hook is not an MP visibility fix.

## MP native level selection

The W2.1 capture used copied root MP slot 1, P38, zero switches, stationary P2
and no firing. Both natural scene callers executed: `80054CD4` and `80054D54`
call `8006E9D8(context,list)` with return addresses `80054CDC`/`80054D5C`.
The final frame had 592 scene calls across 296 frame-function samples.

Complete live function guards were captured for:

| Contract | Address | Bytes | FNV32 |
| --- | --- | ---: | --- |
| Native frame | `80054BC4` | `0x200` | `6CDFBB75` |
| Scene dispatch | `8006E9D8` | `0x180` | `04C21F46` |
| Level-node callback | `8006C61C` | `0x290` | `A2AAC71B` |
| Visibility selector | `80096EF4` | `0x90` | `273C8059` |
| Visibility helper | `80096AC8` | `0x428` | `77C2060F` |

`8006E9D8` walks the list at `[800A35CC]`. The fixture had 26 nodes: two
headers, 21 level nodes with callback `8006C61C`, one special node and two
player nodes. The 21 level nodes are the flat queue in traversal order. Every
level node had visibility mask `0x07020200` at `+0x0C`, render flags
`0x00400211` at `+0x10` and auxiliary flags `0x08000001` at `+0x14`.

The complete callback reads the `+0x0C` mask and invokes `80096EF4` from
`8006C664`/`8006C688`. The selector constructs the object AABB and calls
`80096AC8` from `80096F70` for the camera-space visibility result. There is no
separate PVS leaf queue write in the complete MP callback. The earlier SP
selector `80099960` and its `800B74B8` queue are not resident or executed in
this MP fixture and must not be transplanted.

The detailed contract is
[MP_LEVEL_SELECTOR_EVIDENCE.md](MP_LEVEL_SELECTOR_EVIDENCE.md); the compact
receipt is
[weapon-mp-level-selector-receipt.json](../../vr/proof/weapon-mp-level-selector-receipt.json).
The ignored raw receipt retains complete disassembly, both player snapshots,
source references and cleanup evidence.

## MP eye-frustum override

W2.2 measured the fields consumed by the native selector before enabling the
override. For each level node, `80096EF4` reads signed-short center coordinates
at `+0x2F4`, `+0x2F6`, `+0x2F8` and radius at `+0x2FC`, then forms a
center-minus/plus-radius cube. `80096AC8` transforms it using the live GTE
RT/TR, the camera input pointer at `+0x39C`, the view descriptor at
`input+0xC8`, and screen bounds `800A2D10/800A2D14`.

The retained 21-node capture measured screen bounds **540 x 120**, world H 400,
OFX 256.0 and OFY 60.0. The view descriptor was heap memory and is never
hardcoded. In that run three level nodes passed native P1 selection; the visible
set is live and is not a static allowlist.

The override replaces only `80096EF4` results while a valid P1 eye replay is
active. It composes the same node cube and RT/TR with the existing eye
`PSXModRenderView`, uses the measured 540x120 screen rectangle, and leaves every
non-level selector caller and malformed layout on the native path. Complete
frame/selector/callback/helper hashes, natural return addresses, selected P1
ownership, finite view values and non-wrapping short AABBs are required.
`MOHU_VR_MP_FRUSTUM=1` is explicit; the control defaults off.

The zero-angle P38 control used a fresh copied root MP slot 1 with zero
switches and no firing. Each eye applied 126-147 override decisions across its
four pose cases with zero fallback and zero rollback errors. Native zero-IPD
eyes matched at SHA-256
`de83c69d0a08f5933805c07dc86ac27f2310df3ef8eb1e920b12d0608d9b3c9e`;
the retained both-eye image is
[weapon-mp-frustum-controls.png](../../vr/proof/weapon-mp-frustum-controls.png).
W2.3 added zero, +/-90-degree and near-wall controls with native/override
selector comparison. Turned eye views correctly select different sets from the
native body view; equality at every pose is not the acceptance criterion.
The accepted evidence is
[weapon-mp-visibility-receipt.json](../../vr/proof/weapon-mp-visibility-receipt.json)
and [the control sheet](../../vr/proof/weapon-mp-visibility-controls.png).

Evidence:
[MP_EYE_FRUSTUM_EVIDENCE.md](MP_EYE_FRUSTUM_EVIDENCE.md),
[measurement receipt](../../vr/proof/weapon-mp-frustum-measurement.json) and
[build receipt](../../vr/proof/weapon-mp-frustum-build-receipt.json).

## W1 P38 absolute synthetic pose contract

The measured coordinate contract is
[WEAPON_CALIBRATION.md](WEAPON_CALIBRATION.md). The capture used the existing
guarded seam, not a mesh scan: copied root MP slot 1, P38 ID 0, zero switches,
stationary P2 and no firing. It records source and native animated vertices,
the 8-word GTE RT/TR, the P1 eye view, axes, handedness, authored placement and
every unit boundary.

The native model-to-camera affine is deliberately scaled and sheared: at the
capture its column scales were approximately `6.002`, `3.753` and `2.006`, and
its full 3x3 inverse exists. Code preserves the whole affine as
`hand_from_model`; it does not transpose it or treat it as orthonormal. The W1
synthetic hand transform uses the right grip and aim pose in tracking-origin
space, `48 / 0.067 = 716.4179104477612` game units/metre, and the provisional
native-camera marker `(98, 296, 193)`. The marker is a spatial-control pivot,
not a P38 grip or muzzle measurement. The desktop head path uses 1000
diagnostic units/metre, and the existing eye view is applied once after the
guest affine.

The runtime path is P38-only. Other real-hand weapon IDs stay native until the
per-ID calibration gates; direct `mohu.vr.weapon.pose x=/yaw=` controls remain
separate and are not evidence for the hand path. Native animation, recoil,
arms and mesh identity remain inputs, and invalid focus/activity/validity/age/
quaternion samples fall back without retaining a neutral anchor.

The independent harness ran 29 cases: both-eye controls, two fresh-load
absolute starts, hand-only translation and rotation, 10 head-only cases, a
combined pose, origin change, and five invalid controls followed by a fresh
valid recovery. Expected and observed GTE controls differed by zero RT/TR
steps. Recovered-hand maxima were `6.185436e-05` rotation and `0.492537`
translation unit; origin-anchor and translation limits were one integer GTE
unit. Both eye meshes were populated, zero-IPD eyes matched, and the sampled
world ROI stayed unchanged for hand-only motion. No shot was fired.

Evidence: [pose-space receipt](../../vr/proof/weapon-pose-space-receipt.json),
[both-eye proof](../../vr/proof/weapon-pose-space-controls.png) and
[build receipt](../../vr/proof/weapon-pose-build-receipt.json). The build
receipt also records the affected MP/flat/SP regressions, source hashes,
unchanged saves/preferences and the final debug-OFF release hash. Physical
recenter, MP visibility, grip/scale and tracked aim remain open.

## W3.1 P38 model-local calibration

The P38 calibration probe captures the complete node-13 source and animated
vertex arrays atomically at the existing W1 seam. It uses copied root MP slot 1,
ID 0, zero switches, stationary P2 and no fire. The animated-model grip block
centers at `(76.555555555556, 100.777777777778, 287.888888888889)`; the muzzle
cap centers at `(76.2, 109.8, 396.8)`. Their normalized direction is the
provisional forward axis.

| Field | Measured value | Units / status |
| --- | --- | --- |
| Grip pivot | `(76.555555555556, 100.777777777778, 287.888888888889)` | animated model units |
| Muzzle | `(76.2, 109.8, 396.8)` | animated model units |
| Right | `(0.999994671106, 0, 0.003264622472)` | dimensionless |
| Up | `(-0.000269517466, -0.996586343637, 0.082556568708)` | dimensionless |
| Forward | `(-0.003253478173, 0.082557008645, 0.996581032934)` | dimensionless |
| Forward span | `114.525481833051` | animated model units |
| Nominal scale | `530.210564041902` | model units/metre; provisional |

The scale uses a 216 mm nominal P38 overall length. It is a geometry-based
starting value, not operator acceptance. The old `(98,296,193)` camera marker
remains the W1 rotation diagnostic and is not the measured grip. The new data
is profile metadata; it does not yet alter the rendered pose, native shot or
normal defaults.

Evidence: [calibration receipt](../../vr/proof/weapon-p38-calibration-receipt.json),
[atomic capture](../../vr/proof/weapon-p38-calibration-capture-receipt.json) and
[build/regressions](../../vr/proof/weapon-p38-calibration-build-receipt.json).

## Captured first-person profiles

| ID | Weapon | Nodes | Native faces | Geometry FNV32 |
| ---: | --- | ---: | ---: | --- |
| 0 | P38 pistol | 14 | 354 | `8544F8B9` |
| 1 | MP40 | 32 | 316 | `8095CAFB` |
| 4 | Shotgun | 21 | 306 | `805BD649` |
| 5 | Scoped rifle | 26 | 383 | `9F7ADA24` |
| 8 | Colt .45 | 14 | 303 | `267E86AA` |
| 9 | Silenced pistol | 14 | 310 | `65F76C5D` |
| 10 | Stick grenade | 24 | 341 | `DDCE0989` |
| 12 | M1 Garand | 23 | 280 | `450F78DC` |
| 13 | Panzerfaust | 31 | 333 | `068CBD37` |
| 14 | Crossbow | 29 | 290 | `DFF185CA` |
| 15 | Petrol bomb | 28 | 397 | `7CA0DBEC` |
| 16 | Sten | 31 | 354 | `29D5BC18` |
| 17 | StG44 | 32 | 352 | `F467028B` |

All native nodes, arms, animation, recoil, reload, and muzzle handling remain
inputs to the projection. W3.1 measured P38 model-local grip and muzzle markers,
but no gun-only mesh extraction or physical grip acceptance is claimed. The
current renderer still rotates around its W1 camera-space diagnostic pivot;
nothing consumes the new calibration data yet. Operator review now requires
removing the attached arm geometry and carrying the gun from the measured grip
rather than rotating around that diagnostic pivot.

GTE TR registers use **integer camera units**. The older affine-composition
helper packs translation in Q12. `mohu_vr_weapon_compose_gte_control` cancels that
packing scale before using it for TR. Applying the affine's `*4096` unchanged
pushed the entire weapon offscreen; those early controls are rejected.

## Validation and reproduction

The flat mapping control matrix uses all four source-slot cycles:

| Slot | Native ID cycle |
| --- | --- |
| 1 | 0, 1, 17, 10 |
| 2 | 8, 16, 4, 15 |
| 3 | 9, 14, 5, 10 |
| 4 | 12, 17, 13, 15 |

Each equipped weapon receives native identity, lateral +24 integer units,
yaw +12 degrees, forced tracking loss, and identity-restored controls. The tool
checks nonzero apply/restore counters, zero pose applications during loss, native
fallback during loss, and exact apply/restore equality after the active calls
drain. A running-guest snapshot may catch one call between apply and restore;
that is not accepted as a persistent leak.

The proof compares explicitly named world, ammo-HUD, and other-panel-weapon
rectangles. All of those rectangles must be byte-identical to each weapon's
native image. Native target movement, timed weapon-name text, and weapon idle
animation continue between captures; no whole-image identity claim is made.
Inspect the top-panel native/translated/yawed proof sheet as well as counters.

With `build-release` configured for debug tools, reproduce with:

```powershell
python vr/tools/inspect_weapon_sets.py analysis/vr-baseline/weapon-mesh-mapping/new-fp-controls --cycle --first-person-models --pose-controls
python vr/tools/summarize_weapon_viewmodels.py analysis/vr-baseline/weapon-mesh-mapping/new-fp-controls vr/proof/weapon-viewmodel-receipt.json vr/proof/weapon-viewmodel-controls.png
```

The helper owns one hidden game on TCP 4372, copies source slots and thumbnails
into a fresh directory, uses ordinary PGXP load/identity checks, hashes source
saves and preferences, and closes its owned process. An invalid save requires
asking the operator for a fresh PGXP slot; never patch its ABI or identity.

Runtime code is `vr/underground/weapon.c`, `weapon.h`, and `vr_diagnostic.c`.
The pure C fixture covers known/incorrect mesh layouts, body/viewmodel
separation, Q12-affine versus integer-TR units, preserved control padding,
overflow with no writes, and stale/unfocused/bad tracking fallback.

## Combat and remaining work

The pre-existing native-hit matrices cover all 13 IDs, including delayed kills
followed by respawn. Accept damage only from a decrease at P2 `actor+0x108` in
the complete native write trace. A lower final sample is insufficient. The scoped
rifle, stick grenade, and petrol bomb require the recorded longer/approach
controls. A visible model delta does **not** redirect native shots.

The final +24 geometry build repeats the native P2-damage gate for all 13 IDs:
`fp-combat-final-20261025/inventory.json` under the same analysis tree. All four
cycles close, exit 0, source saves/preferences unchanged, and no owned process
remains. The compact receipt includes per-ID native health-decrease summaries.
The same diagnostic binary's SP zero-eye control has 18 complete pairs, equal
eye state/cycles and 37 rollback checks with zero mismatches, leaks, watchdogs
or repairs. This validates the existing SP path, not MP weapon stereo.

W2.4 is complete. The copied MP slot now selects the measured overlay's
converter `0x800799E4`, dispatcher `0x80079B28`, P1 actions `0x800C0ED0`,
axis records `0x800C0BF0` and curve `0x800A458C`; the SP tables remain a
separate checked path. W2.5 is also complete: both directions of every movement
axis, seven button masks, focus recovery and native Start pause/resume pass,
with zero render-time input samples. Isolated SP and OpenXR-off flat fallback
pass in their own fixtures. Follow the corrected dependencies: W3 desktop
profile preparation can progress without physical acceptance. W4 MP P38
shot binding and the W5.1 diagnostic candidate are now complete; remaining
W5/W6 work follows the measured contracts. Normal default enablement and physical accuracy claims
remain gated by hardware acceptance. Use [HANDOFF.md](HANDOFF.md) and the
[reference reuse audit](REFERENCE_REUSE_AUDIT.md) for exact code/tool entry points;
do not create another discovery effort or reimplement the reference algorithms.

The earlier `actor+0x4AC` affine and `0x80088C08` experiments moved the wrong
split-panel rendering and are superseded. Their dead runtime hooks/address
selector are removed. The session-start diff is retained locally under
`analysis/vr-baseline/weapon-mesh-mapping/session-start-20261025.patch`.

## Final build state

The active `build-release` is Release/OpenGL/OpenXR/PGXP with
`PSX_DEBUG_TOOLS=ON` for active desktop work, at SHA-256
`2fab9c257013832e9dde5aaddcb9e24a0c232d873514f5c48188c4d8e018e547`. The
[current build receipt](../../vr/proof/weapon-shot-families-build-receipt.json)
records all-ID shot families, strict fixtures, P38 native/tracked combat and
related regressions.
The last debug-off release was
`bae4f60f02f4bf70ce86ea85d201674df7157bafa4d6bea20c3086972f2ab71d`.
The OpenXR-off flat executable is
`18f4328bc9085f0a6a2322f940eea63516f07e93698010853cf3474cad94636c`.
Flat startup is inert even with weapon-pose, flat-probe, synthetic-pose,
all-ID calibration/gun-only, MP control and frustum flags inherited.
Fifty-seven Python tests and the strict C fixtures pass, including all 13
compiled calibration records. Saves,
controller preferences and SteamVR settings are unchanged; no owned game or
debug listener remains.
The flat smoke intentionally closes its hidden process and does not establish
interactive gameplay or new OpenXR acceptance.

## Evidence

- [P1-only MP eye receipt](../../vr/proof/weapon-mp-eye-receipt.json)
- [MP build and regressions](../../vr/proof/weapon-mp-build-receipt.json)
- [MP native / translation / yaw eyes](../../vr/proof/weapon-mp-eyes.png)
- [P38 coordinate contract](WEAPON_CALIBRATION.md)
- [P38 absolute spatial controls](../../vr/proof/weapon-pose-space-receipt.json)
- [P38 both-eye control sheet](../../vr/proof/weapon-pose-space-controls.png)
- [W1 build and regressions](../../vr/proof/weapon-pose-build-receipt.json)
- [MP selector receipt](../../vr/proof/weapon-mp-level-selector-receipt.json)
- [MP selector build receipt](../../vr/proof/weapon-mp-level-selector-build-receipt.json)
- [MP selector evidence](MP_LEVEL_SELECTOR_EVIDENCE.md)
- [MP eye-frustum evidence](MP_EYE_FRUSTUM_EVIDENCE.md)
- [MP eye-frustum measurement](../../vr/proof/weapon-mp-frustum-measurement.json)
- [MP eye-frustum build receipt](../../vr/proof/weapon-mp-frustum-build-receipt.json)
- [MP native input controls](../../vr/proof/weapon-mp-input-receipt.json)
- [MP input build and regressions](../../vr/proof/weapon-mp-input-build-receipt.json)
- [MP lifecycle controls](../../vr/proof/weapon-mp-lifecycle-receipt.json)
- [MP lifecycle build and regressions](../../vr/proof/weapon-mp-lifecycle-build-receipt.json)
- [First-person flat control receipt](../../vr/proof/weapon-viewmodel-receipt.json)
- [Final build and flat isolation](../../vr/proof/weapon-viewmodel-build-receipt.json)
- [Native / translation / yaw proof](../../vr/proof/weapon-viewmodel-controls.png)
- [Native inventory and damage](WEAPON_SET_EVIDENCE.md)
- [Historical body-object observations](../../vr/proof/weapon-model-receipt.json)
- [Historical damage-only pose matrix](../../vr/proof/weapon-alignment-receipt.json)
- [All-ID complete-gun topology](../../vr/proof/weapon-complete-gun-topology-receipt.json)
- [All-ID animated captures](../../vr/proof/weapon-profile-captures-receipt.json)
- [All-ID provisional calibration](../../vr/proof/weapon-provisional-calibrations-receipt.json)
- [All-ID calibrated controls](../../vr/proof/weapon-complete-gun-controls-receipt.json)
- [All-ID control sheet](../../vr/proof/weapon-complete-gun-controls.png)
- [All-ID moving-marker controls](../../vr/proof/weapon-moving-muzzle-receipt.json)
- [Moving-marker control sheet](../../vr/proof/weapon-moving-muzzle-controls.png)
- [All-ID shot-family receipt](../../vr/proof/weapon-shot-families-receipt.json)
- [Shot-family build/regressions](../../vr/proof/weapon-shot-families-build-receipt.json)
- `analysis/vr-baseline/weapon-mesh-mapping/first-person-geometry-20261025/inventory.json`
- `analysis/vr-baseline/weapon-mesh-mapping/fp-controls-final-20261025/inventory.json`
- `analysis/vr-baseline/weapon-mesh-mapping/fp-combat-final-20261025/inventory.json`
- `analysis/vr-baseline/weapon-mesh-mapping/fp-stereo-final-20261025/receipt.json`

## Resume prompt

```text
Read HANDOFF.md, VR_PLAN.md, WEAPON_COMPLETE_PROFILES.md,
P38_NATIVE_AIM_EVIDENCE.md and SHOT_FAMILY_EVIDENCE.md.
Continue W6.2 using the exact reader contract in HANDOFF section 1. W3.4 is complete;
all 13 IDs retain model-animation diagnostics; shot/laser aim is fixed to the hand. W4 P38
mapping, W5.1, W5.3d conversion, W5.3e paired preservation/impact and the W5.4
desktop combat-state pair and P1 death/native respawn/fresh-shot supplement pass.
Read DEATH_RESPAWN_EVIDENCE.md for the lifecycle scope (stereo inactive).
Physical W5.4d hand-aim/impact confirmation stays open. Do not repeat them or
the accepted W6.1 rendered-muzzle matrix (RENDERED_MUZZLE_EVIDENCE.md), nor
the all-ID topology, capture, calibration, 64-case controls or animation matrix.
Use the current weapon-hand-fixed-preservation-receipt.json and its stated
common-prefix tolerances. Older animated-reference receipts remain historical.
W5.2 remains
open until a compatible live NPC/SP fixture and guarded SP binding exist.
Preserve native fallback, normal defaults, source saves, historical proofs and
unrelated work. Leave physical W3.3/W3.5 open. No commit/push unless asked.
```
