# Weapon Mapping Handoff

Last updated: 2026-10-25

## Current source of truth

Weapon-position work uses one copied multiplayer fixture. The fixture already
contains a stationary P2 target, all 13 measured weapon IDs across source slots
1-4, and verified native damage writes. No single-player fixture is required
for the current weapon-pose or weapon-damage work.

Use one enemy and test one weapon at a time. Reload the copied slot after a kill
instead of chasing a moving target.

Single-player and multiplayer do not share one safe update hook:

| Mode | Player update | Size | FNV-1a |
| --- | --- | ---: | --- |
| Multiplayer | `0x800892E8` | `0xA70` | `0x39E56A35` |
| Single-player | `0x800892C8` | `0xF20` | `0xF4D6C439` |

The current task is the multiplayer first-person weapon transform. The
single-player shot-origin path is a later aim-validation task and must not block
the multiplayer model mapping.

## Measured multiplayer fixture

| Item | Value |
| --- | --- |
| P1 / P2 roots | `0x800A3604` / `0x800A3608` |
| Player input | `actor + 0x39C` |
| Inventory slot / weapon ID | `input + 92` / `input + 93` |
| First-person weapon object | `actor + 0x4AC` |
| Object magic | `0x00160024` |
| Node count | 22 |
| Common node-table SHA-256 | `9f8c7275b3e8a1d6c7765da25a02d78b23f0c3fa4b67483f28865191d2805e4f` |
| Weapon IDs | `0, 1, 4, 5, 8, 9, 10, 12, 13, 14, 15, 16, 17` |

The object fields around `+0x5C` and `+0x64` are animation/frame state, not a
stable weapon identity. Do not select a mesh from those words.

The source slots are:

| Slot | Starting weapon and native cycle |
| --- | --- |
| 1 | P38 pistol (0), MP40 (1), StG44 (17), stick grenade (10) |
| 2 | Colt .45 (8), Sten (16), shotgun (4), petrol bomb (15) |
| 3 | Silenced pistol (9), crossbow (14), scoped rifle (5), stick grenade (10) |
| 4 | M1 Garand (12), StG44 (17), Panzerfaust (13), petrol bomb (15) |

## Required mapping work

1. Copy source slot 1 into a fresh analysis directory and load it through the
   diagnostic build. Keep the source save and thumbnail unchanged.
2. Capture the complete `actor + 0x4AC` object, its 22-node table, and the
   per-node geometry data for each weapon after a native weapon switch.
3. Find the model affine or node transform consumed by the first-person vertex
   path. The transform must affect model geometry without changing the world
   camera.
4. Record the model-local axes, pivot, scale, and sign conventions for each
   weapon. Keep the shared node table as a layout guard, not as a mesh profile.
5. Add a tracked transform only at the measured model geometry seam. Preserve
   native animation, recoil, reload, muzzle handling, ammo, and fire logic.
6. Fail closed unless the full overlay function, P1 actor identity, weapon
   object magic, node-table hash, current weapon ID, and caller contract match.
7. Apply the transform inside each verified eye transaction and restore it
   before the next eye. The world view must remain unchanged.

## Acceptance matrix

Use the stationary P2 target and a fresh copied-save load for every case.

| Case | Required result |
| --- | --- |
| Native idle | First-person weapon remains native |
| Synthetic model translation | Weapon moves; world and HUD do not |
| Synthetic model rotation | Weapon rotates around one guarded pivot |
| Each weapon ID | Correct mesh and node guard |
| Fire and recoil | Native animation and ammo behavior remain |
| Reload/switch | No stale transform or mesh identity |
| P2 damage | Native health writer remains reachable |
| Eye replay | Equal eye cycles/hashes after rollback |
| Tracking loss | Native weapon path restored |

## Current validation

The P1 view is the top view. The accepted hit gate is a decrease at the exact
P2 health address (`actor + 0x108`) in the native write trace, not merely a
lower final health sample. This accepts kills that respawn later without
confusing the intervening restore write for damage.

Four fresh copied-save runs cover all 13 measured IDs:

| Alignment | X | Yaw | P2 damage |
| --- | ---: | ---: | --- |
| Native | 0 | 0 | 13/13 |
| Lateral | 96 | 0 | 13/13 |
| Yawed | 0 | 12000 mdeg | 13/13 |
| Forced tracking loss | 96 | 0 | 13/13 native fallback |

Every run used slots 1-4 as one copied fixture set, closed all four-entry weapon
cycles, kept source saves and preferences unchanged, and left no owned game
process. The scoped rifle uses its 60/720-frame zoomed control. The stick
grenade uses a 36/720-frame throw. The petrol bomb uses 180 approach frames and
60/720 fire/release frames. Exact hashes, paths, and per-ID results are in
[weapon-alignment-receipt.json](../../vr/proof/weapon-alignment-receipt.json).

The diagnostic also has an opt-in right-grip raycast pointer. Hold the right
squeeze with `PSX_VR_LASER=1`; the beam ends on the nearest visibility-tree
surface and draws an impact dot. `PSX_VR_LASER_DOT` sets the dot radius and
`PSX_VR_LASER_RANGE_M` bounds the cast. Its pure geometry test passes, but
runtime headset visual acceptance is still pending.

## Known constraints

- The first-person object uses the shared 22-node layout, but per-weapon
  geometry state must still be validated.
- The current diagnostic affine at the actor model path changes P1's
  world-body representation. It is not yet proven to be the visible top-view
  first-person mesh seam, and the behavior is not promoted to the release path.
- Native damage writes to P2 prove combat reachability, not barrel alignment.
- Multiplayer stereo for P1 is not yet accepted. Start with a single-view model
  transform while world stereo remains on its accepted path.
- Shot origin and direction are separate from the visible model transform.
  Validate them in the final aim pass after the multiplayer weapon pose is
  stable.

## Evidence

- [WEAPON_SET_EVIDENCE.md](WEAPON_SET_EVIDENCE.md)
- [weapon-set-receipt.json](../../vr/proof/weapon-set-receipt.json)
- [weapon-model-receipt.json](../../vr/proof/weapon-model-receipt.json)
- [weapon-alignment-receipt.json](../../vr/proof/weapon-alignment-receipt.json)
- `analysis/vr-baseline/weapon-mesh-mapping/models-20261025/`
- `analysis/vr-baseline/weapon-mesh-mapping/profiles-live.json`

## Resume prompt

```text
Continue the Medal of Honor Underground PSX Recomp VR port from
`docs/vr/WEAPON_MAPPING.md`.

Use one copied multiplayer fixture and the stationary P2 target. Do not use a
moving single-player target for weapon-position mapping. Start with one weapon,
capture P1's `actor + 0x4AC` object and 22-node geometry state across native
weapon switches, and identify the model affine/node transform or vertex
projection that owns the visible first-person weapon.

Implement a fail-closed, rollback-scoped tracked transform at that measured
model seam. Preserve native animation, recoil, reload, ammo, firing, HUD and the
world view. Validate native idle, synthetic translation, synthetic rotation,
fire/recoil, reload/switch, tracking loss, stereo restore, and native P2 damage
for all 13 measured weapon IDs.

Keep source saves unchanged, use fresh copied-save directories, close owned
processes, restore SteamVR preferences and the debug-off release build, update
the handoff and receipts, run the focused tests, commit, and push.
```
