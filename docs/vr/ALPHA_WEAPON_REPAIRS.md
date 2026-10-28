# Authored weapon pose and exact laser repairs

Updated 2026-10-28. Implementation follows the operator's detailed MP/SP feedback.
Physical acceptance stays open; no headset was used for these changes.
[Receipt](../../vr/proof/weapon-alpha-repairs-receipt.json) records the actual
controls and their limits. Historical PCA/topology receipts describe older builds.

## Weapon defaults

The reference `vr/psx_vr_stereo.c::vr_weapon_geometry_filter`,
`vr/moh_vr_aim.c::moh_vr_weapon_transform` and
`vr/moh_vr_weapons.h::moh_vr_weapon_face` preserve authored animation and separate
hand filtering from the rigid attachment. Underground already sampled aim
orientation plus grip position. That sampler did not need replacement.

The old Underground candidate normalized every entire weapon to a PCA frame.
A magazine, stock or fused hand affects that frame: StG's PCA forward was tilted
4.62 degrees from authored +Z. Aligning that axis to the hand left its visible
barrel below the fixed firing direction. Grenade/bottle long axes were also mapped
to hand-forward, rotating upright props into a forward pose.

- Preserve authored X/right, -Y/up and +Z/launch axes in the calibration affine.
  Native recoil/reload still animates vertices and the projected muzzle flash.
- Use the reference's 850 model-units/metre firearm convention as the new
  provisional candidate. It replaces inferred real-world-length scaling;
  nominal lengths in historical receipts are not accepted display measurements.
  This reduces the earlier oversized defaults without changing world scale/IPD.
  The operator has not yet accepted each new size.
- Grenade and petrol bottle retain their measured size, stay upright in hand,
  and launch forward. Displaying the cap above the grip does not aim a throw up.
- Shot construction, velocities, spread, ammo, reload and release stages remain
  native. No extra per-ID pitch trims were added. Authored-axis parity does not
  certify physical sights/impact agreement at every distance.

`weapon.c` owns immutable defaults. `weapon_defaults.py` reads these numeric
initializers for diagnostic pose solvers, rejecting a changed schema. Solvers
must not keep reading the frozen PCA receipt after defaults change. Historical
rendered-muzzle tests explicitly use their historical calibration instead.

## StG hand, stock and grip

The reference has no StG asset; its filtering algorithm is reusable, its data is
not. Underground's hand is fused into node 27 and shares vertices with the stock.
Whole-node or connectivity-only acceptance was insufficient.

Native faces, animated coordinates and captured palette/UV assignments identify
30 hand faces. Reject node-27 private vertices
`0-4, 6-9, 11-15, 38, 53, 54, 110`. Preserve shared stock vertices `5`, `10`,
`109`, the barrel/muzzle, node-29 magazine and node-31 sight. Native negative-SZ
rejection removes mixed hand-boundary faces; their shared stock vertices remain.
The result retains **185 faces / 143 gun vertices**, versus 215/161 previously.
The unchanged source geometry identity remains `F467028B`.

StG's grip now uses the measured hand-region centre
`(83.388889, 132.111111, 37.666667)`. The preceding nearest-to-arm heuristic
placed it at Z=237.40625 near the receiver/fore-end. Source geometry, face streams
and animation tables are not modified persistently.

## Exact surface reader: two native layouts

Reuse reference `moh_vr_ray_tri` and its broad-phase/traversal strategy, including
full matrix inverses. Adapt the actual Underground index streams. Do not copy
the reference's fixed 16-byte-record assumption or skip an origin-inside leaf.

| Source | Verified binding | Actual geometry |
| --- | --- | --- |
| SP arena | `8009A478`, call `8009A4F8 -> 80099960`, return `8009A500`; live `s2` owns the level | Root `*(*(level+8)+14)`, vertices `*(level+2C)`, count `*(level+3C)`. Drawer `80010CF0`: 8-byte base triangle, 4-byte strip extensions. |
| MP arena | Class-3 callback `80057920`, drawer `80094680 -> 80012A90` | Count `[8009ECE4]`, level array `8009F13C`, stride `C4`; same root/table/count fields and 8-byte base streams. |
| MP scene props | Flat list `[800A35CC]`, next `+4`, ordinary callback `8006C61C` | Model `[actor+114]`, vertices `+2C`, count `+3C`, stream `+B0`, face count halfword `+B4`; `80089D5C -> 80015608` consumes 16-byte bases plus 4-byte extensions. |

Both strip formats mask indices with `1FFF`; `8000` selects strip winding and
`1FFF` terminates a strip. Bounds/child fields retain the existing visibility-tree
contract. Validate each pointer/span, count and index. Malformed/unsupported data,
cycles and exhausted budgets suppress the laser; boxes never become endpoints.

The **21 MP selector nodes are scene props**, not the main arena. The class-3
callback owns four independent arena trees in the fixture. An intermediate
prop-only reader matched an incomplete oracle but missed all walls/floor; it is
not accepted evidence. The final oracle includes both the arena and props.
Prop vertices use actor `+354` RT and `+368` TR to reach world space, as in
native `80095CB4`. Transform the ray by the full inverse without normalizing
away its world-distance parameter.

## Shared firing ray and display

`mohu_vr_weapon_model_ray` is shared by native shot construction and the laser.
The renderer retains the unscaled, quantized calibration affine before precision
lifting. The laser uses its constant calibrated muzzle/+Z axis and the same
validated canonical camera. It does not resample controllers or use animated
recoil vertices to steer the ray. Flash placement still uses projected animated
tip vertices.

Reuse the existing per-eye projection, clipping, line/dot emission and actual
OFX/OFY/H. MP now draws the laser after its final OT submission too. Hold right
grip at least 55%; throwables have no straight firearm laser. A valid range miss
has no impact dot. The ray covers verified static arena surfaces and supported
scene props, not NPC hit volumes or a prediction of ballistic drop/spread.

Read-only `mohu.vr.laser` diagnostics expose each eye's fixed affine, world ray,
surface count and nearest distance; `level=0..7` exposes SP reader bindings.
These are probe data, not a player settings menu. No framework/UI pin, native
hook registration, generated guest C or savestate layout changes were required.

## Validation and continuation

The compact receipt owns final binary/source hashes and complete run selection.
The tools refuse occupied processes/ports, copy saves and verify preferences.
All game launches run outside the sandbox.

- Actual SDK calibration captures verify each profile's applied quantized affine
  against an independent identity-hand calculation, rather than treating the
  older relative-delta matrix as evidence of absolute scale.
- Representative native firing covers P38, StG, shotgun and both throwables;
  linked damage is observed except the grenade release-only control. Shotgun
  retains six pellets and about 5.15-degree spread. MP P38 recovery is separate.
- SP and MP laser controls independently decode **7,251 / 8,039 triangles** and
  compare nearest hits in both eyes, at several hand angles and with head turn.
  Grip release/tracking loss suppress drawing. An actual MP projectile matches
  the previewed fixed ray while the affine stays fixed during recoil.
- Strict C tests cover exact versus box hits, both windings, both strip formats,
  range/miss, origin inside bounds, bad indices/pointers, missing terminators and
  traversal budgets. Python tests retain old receipt validation separately.

Do not repeat source mapping or unchanged combat inventories. Before alpha,
H1/A5a native HUD is now ported and SP desktop/null-HMD validated; see
[NATIVE_HAND_HUD.md](NATIVE_HAND_HUD.md). Continue R6 real SP NPC damage/isolation
and broader SP families without a headset. SP is the release target; MP is only
the quick all-weapon calibration fixture.
R5 fog still requires the matching street-wall save; current courtyard/slot-3
scenes cannot establish that report. S5 physical clean-close/performance and
operator weapon/menu/laser acceptance remain open. A3's optional calibration
editor is still a study, and the reference does not contain a finished editor.
The operator requested one headset batch after the remaining fixes, not now.
