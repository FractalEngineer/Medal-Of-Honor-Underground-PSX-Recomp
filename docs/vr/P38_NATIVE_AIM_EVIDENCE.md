# P38 complete model and native combat candidate

Updated: 2026-10-27. No headset was used. W4 and W5.1 are complete; W5.2 has
desktop P38/P2 evidence and remains open for live NPC/SP isolation. All 13 IDs
now have complete-gun topology, animated captures and provisional calibration;
only P38 has an accepted rendered-muzzle shot override. W3.3/W3.5 physical
acceptance and W3.4 moving-animation checks remain open.

## Results and corrections

The native shot contract is now measured, and an explicitly enabled P38
candidate renders the complete gun at the controller grip and fires native
shots from its declared barrel tip. Native constructor, basis, history, motion,
collision, ammunition and damage logic remain in charge after the six pose
fields are supplied. Unsupported weapons and invalid hands retain native fire.

The W3.2 comparison runner left `inspect_weapon_sets.load()`'s absolute neutral
debug-pad override active. That override wins over the normal controller source.
The runner now calls `clear_input` and supplies a neutral **host-layer** pad,
which allows XR mapping to reach native gameplay. It also sets
`PSX_DITHERING=0`, matching the ordinary VR launcher. Both are measured in the
new desktop run; W3.2's historical transport receipt is unchanged.

The new `MOHU_VR_P38_CALIBRATED=1` candidate replaces the old camera-space pivot
with the measured model grip. It keeps the native animated vertex producer,
packs the calibrated affine into the existing scoped GTE RT/TR and restores it
at the existing common return. For this calibrated path `projection_h_ref=133`
matches native weapon H=133; the authored W1 control continues to use ref=400.
The candidate's model and shot consumers use the same quantized affine.

## Barrel correction: do not filter by whole node

The first candidate mistakenly retained only node 13. The operator correctly
identified the missing barrel. Node 11 contains a disconnected barrel/sight
island alongside hands/arms. The final filter retains this island as well.

| Native vertices | Final policy |
| --- | --- |
| Node 13, indices 0..68 | All 69 receiver/grip vertices retained |
| Node 11, indices 6..32 | All 27 barrel/sight vertices retained |
| Node 11, all other indices | 122 hand/arm vertices hidden |
| Node 9, indices 0..19 | 20 arm vertices hidden |

The decoded 354-triangle native stream contains 91 receiver/grip triangles and
37 barrel triangles: **128 complete-gun triangles**, using all 96 selected
vertices. The 226 other triangles are excluded by setting only their projected
non-gun vertex depth negative before the native face reader. Both eyes retain
96 valid gun vertices and mask 142 non-gun vertices. Source vertices, face/strip
records and animation data are unchanged; the eye transaction restores outputs.

Underground uses 28-byte base triangles, 8-byte strip extensions and a
four-byte `0x1FFF` terminator. The reference's fixed-face compaction cannot be
copied onto this stream. `check_p38_mesh.py` validates every decoded index, the
complete asset identity and exact retained topology. The source geometry FNV
is `8544F8B9`; the 4,320-byte triangle stream FNV is `1F000741`, SHA-256
`4882e095af5e99e5a36dfda8add3249d9ab2a31ee13639e12dc5451c990bd37c`.
Runtime guards check both before calibrated rendering/aim.

The earlier node-13 W3.1 capture remains valid for the receiver/grip alone.
Its supposed muzzle `(76.2,109.8,396.8)` is a receiver cap. The current complete
gun uses node-11 vertices 24..28 for the true barrel tip and 11..17 for the
barrel-axis base. Do not aim from the old cap or infer a barrel direction from
the grip-to-cap vector.

| Current animated-model marker | Value |
| --- | --- |
| Grip, node 13 indices 47..64 | `(76.555555555556,100.777777777778,287.888888888889)` |
| Barrel tip, node 11 indices 24..28 | `(81.8,110.6,447.6)` |
| Barrel-axis base, node 11 indices 11..17 | `(80,109.428571428571,367.857142857143)` |
| Forward unit axis | `(0.022564372944,0.014684750646,0.999637537897)` |
| Complete-gun forward span | `164.265769717169` model units |
| Provisional 216 mm overall-length scale | `760.489674616524` model units/metre |

The [complete calibration receipt](../../vr/proof/weapon-p38-complete-calibration-receipt.json)
supersedes the old markers for the candidate. Physical size remains provisional.
Native recoil/reload still animate the model; moving animated muzzle markers
during those actions are not yet calibrated or accepted.

## Native P38 contract

| Meaning | Underground MP binding |
| --- | --- |
| Constructor | `800486D0`, 1,052 bytes, FNV `5F58030B` |
| Pose selection before basis | `80048528`, 424 bytes |
| Native basis builder | `8006C8B0`, 260 bytes, FNV `82E385D7` |
| Constructor call / delay / return | `800488D0=0C01B22C`, `800488D4=AE200048`, RA `800488D8` |
| Shot / owner at basis entry | `A0 == S0` shot, `S2` owner; shot type `13F6` (5110) |
| World position | Shot `+220/+224/+228`, signed 16.16 |
| Pitch / yaw / roll | Shot `+23C/+240/+244`, signed 16.16, 4096 units/turn |
| Native basis storage | Shot `+354` |
| Native position history | Constructor copies to shot `+26C..+274`, then shot-input `+88..+90` |
| First motion stores | `8006F0CC`, `8006F0E8`, `8006F104`; shot in S0 |
| Motion/collision routine | `8006EB8C`, 3,140 bytes |
| Shot-to-target hit resolver | `800503F4`, 1,340 bytes |
| Damage call | `800508F8=0C013AAD`, RA `80050900` |
| Exact health decrease | `8004EB80`, P2 `actor+108`; A2/S1 identify the observed shot |

Complete function hashes, actual arguments, native versus overridden fields,
first motion and exact linked health writes are in the
[native contract receipt](../../vr/proof/weapon-native-shot-receipt.json) and
[tracked combat receipt](../../vr/proof/weapon-p38-aim-receipt.json).
Bulk complete bytes and streaming traces stay in their named ignored directories.

The canonical camera is **the eight RT/TR words at `800A2CEC`**, explicitly
loaded by the native visibility helper `80096AC8`. GTE state at callback
`8006C61C` entry can belong to the previous object and is not canonical.
The off-replay P1 callback caches the guarded global, its owner and guest cycle.
Inverting it recovers the simultaneously captured native camera actor's position
within the two-world-unit Q12/integer tolerance. Head-only rendering leaves it
unchanged. Never use the eye-only laser cache for simulation shots.

The override requires the exact MP code, full P38 asset/stream identity,
`A0==S0`, expected caller, live P1 owner/class/input/weapon ID and a P1 camera
at most 2,257,920 guest cycles old (four NTSC VBlanks). Clock reversal, replay,
P2/NPC ownership, unknown IDs and invalid tracking reject it. Host fixtures
exercise these predicates; real P2 shots and MP40 shots retain native behavior.
No live NPC/SP fixture is claimed.

## Repeatable checks and continuation

Use a fresh child directory for every run, no existing game or listener on
4372. These commands need the existing diagnostic build with debug tools ON;
they use headless OpenGL and copied root MP slot 1, without a headset/runtime.

```powershell
python vr/tools/probe_native_shot.py analysis/vr-baseline/<fresh-native>
python vr/tools/probe_native_shot.py analysis/vr-baseline/<fresh-tracked> --tracked
```

Add `--case tracked-body` for a single focused diagnosis. That mode cannot
publish a full-suite proof. Add `--proof <new-receipt.json>` only to a complete
suite; do not overwrite historical evidence. The committed current receipts
identify the tested binary and source hashes.

The tracked matrix covers toward/away, +100 mm translated hand, independent
head/body turns, nearer/farther positions, P2, MP40, unfocused/inactive/partial/
stale tracking and valid recovery. Hits require the exact P2 health writer to
name the constructed shot, not just changed health. First motion starts at the
declared muzzle with at most one 16.16 quantization step of origin error and
axis cosine at least `.999995`. Both-eye mesh/projection/restoration, unchanged
world ROI and changed gun pixels are checked separately from damage.

The `--tracked` diagnostic explicitly enables `PSX_VR_WEAPON_POSE`,
`MOHU_VR_P38_CALIBRATED` and `MOHU_VR_P38_AIM`. Normal defaults remain OFF;
`RunFlat.bat` clears the new flags. The prepared tracked headset comparison
selects this corrected candidate, but no new headset run was requested or done.

**NEXT desktop milestone: W3.4 moving-muzzle/special-animation controls.**
Use the all-ID profile evidence; do not repeat topology, capture or fixed-pose
controls. Add recoil, reload, switch and prop-specific animation samples, then
check whether each provisional muzzle marker remains valid. Other IDs have
provisional pose calibration but retain native shots. W5.2's remaining live
NPC/SP isolation needs its own
measured SP binding and copied fixture; W5.3/W5.4 retain constructor-family,
special animation and all-weapon combat work. W3.3/W3.5 remain operator gates.
