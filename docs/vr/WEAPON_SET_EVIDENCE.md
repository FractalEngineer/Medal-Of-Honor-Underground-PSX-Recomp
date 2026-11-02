# Multiplayer weapon fixtures and native damage

On 2026-10-24 the operator completed source slots 1–4 with P1 facing P2 and
authorized native weapon cycling and damage logging. All four load through the
normal PGXP ABI/execution-identity checks. Each has four inventory entries and
returns to its original entry after four native Circle presses. Together they
cover 13 distinct weapon IDs.

| Source slot | P1 cycle, starting equipped; IDs in parentheses |
| --- | --- |
| 1 | P38 pistol (0), MP40 (1), StG44 (17), stick grenade (10) |
| 2 | Colt .45 (8), Sten (16), shotgun (4), petrol bomb (15) |
| 3 | Silenced pistol (9), crossbow (14), scoped rifle (5), stick grenade (10) |
| 4 | M1 Garand (12), StG44 (17), Panzerfaust (13), petrol bomb (15) |

Every distinct weapon has a recorded native damage write to P2. This establishes
native combat fixtures, not tracked aiming, weapon mesh tracking, general
multiplayer VR support, or all weapons available anywhere in the game.

## Procedure and provenance

The process follows the reference game's `vr/inspect_weapon_sets.py`,
`docs/reverse/VR_WEAPON_TRACKING.md`, and `VR_WEAPON_AIM_PLAN.md`: copy saves,
load normally, select weapons through native input, reload before each firing
control, and join health changes to their native writer. Underground addresses,
weapon IDs and fields were measured independently.

The reusable tool is [inspect_weapon_sets.py](../../vr/tools/inspect_weapon_sets.py).
It refuses an occupied port 4372 or an existing game, uses the one
`build-release` executable with debug tools temporarily ON, hidden OpenGL,
an explicit isolated memcard directory, and neutral overrides for both ports.
It copies only completed `.pst`/`.thumb` pairs. There are no save writes,
ammo edits, direct guest RAM writes, guest hooks, or production VR changes.

The diagnostic game configuration is the existing interpreter control
`analysis/vr-baseline/game-interp.toml`; its hash is in the final local receipt.
The execution identity remains
`8174a988661560c5297b4579eb11a9577ccd80a03ea5dfa794a84e21ca3c4361`.
The [compact receipt](../../vr/proof/weapon-set-receipt.json) records executable
and source-save hashes, all cycles, per-weapon damage writers, and controls.
Bulk evidence is bounded under `analysis/vr-baseline/weapon-sets/`:

- `final-inventory/`: all four closed cycles; saves, controller preferences and
  SteamVR settings unchanged; exit 0 and no remaining game.
- `native-damage/`: fresh-load native firing for every entry, 24-frame hold
  followed by at least 240 frames of observation; one local inventory sheet.
- `special-controls/`: longer scoped/grenade/petrol controls.
- `petrol-near/`: closer-range native movement and petrol-bomb damage.
- `idle-control/`, `away-control/`: negative pistol controls.

Original files under `saves/openbios/` are unchanged. Source slot 2 is now an
operator-created multiplayer fixture; the separate SP regression slot 2 under
`analysis/vr-baseline/saves/` remains untouched. Do not overwrite that tree's SP
fixture with the new multiplayer slot 2. The tool creates its own save tree.

## Measured native layout

| Item | Underground multiplayer |
| --- | --- |
| P1 / P2 roots | `0x800A3604` / `0x800A3608` |
| Input pointer | `actor + 0x39C`; points to `actor + 0x400` in these fixtures |
| Inventory slot / equipped ID | `input + 92` / `input + 93` |
| Reserve / clip | signed halfwords at `input + 94 + 2*slot` / `input + 110 + 2*slot` |
| Current health | signed 16.16 at `actor + 0x108` |
| Maximum health | `actor + 0x104`; unchanged by ordinary hits |
| Damage function | `0x8004EAB4`, complete 532-byte span through `0x8004ECC8` exclusive |
| Damage subtraction / store | `0x8004EB78` / `0x8004EB80` |
| Death clamp / respawn store | `0x8004EC44` / `0x80063E8C` |

All four captured RAM images have the same complete damage-function SHA-256:
`5ee9683eb0646d46a39e0b552f214fe90be010d2d41cebbe45fadc2db2a1b9e5`.
The final tool verifies it after each load. The writer loads health at +264,
subtracts `a1`, then stores to the same field. Trace `s0` identifies the damaged
actor; `a2`/`s1` retain the native source object. A nonlethal pistol hit records
32 -> 31.25. P1's input and ammo respond to port 1, independently of P2.

Weapon labels combine the native equipped IDs, ammo category strings around
`0x800A55CC..0x800A5EBC`, clip/reserve behavior, and inspected first-person
images. The scoped rifle remains generically named; its precise historical
model name is not established by these controls. No reference mesh face/node
profile is transplanted.

## Damage interpretation and special controls

Idle and turned-away P38 controls retain P2 health 32 with zero health writes.
The turned-away image shows P1 facing a wall; the pistol still consumes a round.
The forward control consumes a round and records the native subtraction.

Automatic weapons can fire several shots during one hold, and shotgun pellets
can create several damage writes. These windows do not measure per-bullet
damage. All accepted health traces are complete (`total = available = emitted`),
with only the two health fields armed. Frame polling is not exact replay.

The short plain scoped-rifle control did not consume ammo. The accepted scoped
control holds native R2 for 60 frames, then Cross+R2 for 60 and observes another
720. It consumes ammo and records lethal P2 damage. This comparison does not
isolate zoom from the longer hold. Stick grenades also have a longer release
control. In both cases, P2 can die and respawn to 32 before the final sample;
the writer trace preserves the hit, death clamp and respawn separately.

Stationary petrol-bomb controls consume the sole bomb and auto-switch weapons
but record no P2 hit, including the longer window. A fresh slot-2 control uses
180 native forward-input frames to close the distance, then holds fire 60 and
observes another 720. P2 receives native splash/burn damage and dies; P1 also
dies. Both respawn. This proves native petrol-bomb damage at closer range and
does not establish safe distance or direct barrel/trajectory alignment.

Reproduce after enabling debug tools in `build-release`:

```powershell
python vr/tools/inspect_weapon_sets.py analysis/vr-baseline/weapon-sets/new-native --cycle --damage
python vr/tools/inspect_weapon_sets.py analysis/vr-baseline/weapon-sets/new-special --slots 3 --cycle --damage --only-damage-ids 5 10 --scoped-zoom --fire-frames 60 --release-frames 720
python vr/tools/inspect_weapon_sets.py analysis/vr-baseline/weapon-sets/new-petrol --slots 2 --cycle --damage --only-damage-ids 15 --approach-frames 180 --fire-frames 60 --release-frames 720
```

Use a fresh output directory. Restore debug tools OFF and rebuild the same
directory afterward; the handoff contains the configure/build commands.

## First-person model mapping

The read-only mapping pass used the same copied slots and native Circle input:

```powershell
python vr/tools/inspect_weapon_sets.py analysis/vr-baseline/weapon-mesh-mapping/models-new --slots 1 2 3 4 --cycle --models
```

For P1, the weapon object is `actor + 0x4AC`. Every one of the 13 weapon IDs
returned magic `0x00160024`, a 22-node table, and the same node-table SHA-256
`9f8c7275b3e8a1d6c7765da25a02d78b23f0c3fa4b67483f28865191d2805e4f`.
The object's per-frame fields at `+0x5C/+0x64` are not a stable mesh ID: they
also change after cycling back to the same weapon. The tool retains those
bounded state words for later correlation rather than treating them as a
profile.

Weapon-position work is multiplayer-first. The fixed P2 target and all measured
weapon IDs make the same shot repeatable without target movement. Start from one
copied slot, one weapon, and one frame-local object snapshot.

The missing seam is the multiplayer first-person model affine/node transform or
the later vertex projection. Tracked controls must be applied inside the
rollback-scoped model path while preserving native animation, recoil, reload,
ammo and fire behavior.

The full implementation order, guards, and acceptance matrix are in
[WEAPON_MAPPING.md](WEAPON_MAPPING.md). The compact mapping receipt is
[weapon-model-receipt.json](../../vr/proof/weapon-model-receipt.json).

## Verification and limits

Thirteen Python tests and strict frustum, HUD-packet, input, and weapon C
fixtures pass.
The shared release target compiles; the normal debug-off profile is restored.
Two bounded hidden flat auto-load smokes staged slot 4 but did not attempt the
load within 30 seconds. One used the interpreter config; the second used normal
`game.toml` with vsync disabled. Both logged inert VR startup and the unchanged
execution identity, reported no invalid save, and were terminated/cleaned up.
Production headless flat auto-load is therefore unverified; successful state
loads and combat evidence above belong to the diagnostic executable. This
startup limitation was not addressed by changing framework or save data.
No OpenXR session is needed for this flat inventory task, so this session adds
no stereo or headset acceptance claim. Existing sky/movement receipts remain
the rendering evidence. No framework, generated output, `game.toml`, or VR
runtime behavior changed.

Rejected discovery runs initially watched maximum health +0x104, treated the
linked-list player order as port order, and used a numeric `set_input` mask
where that command expects hexadecimal text. They are excluded from the damage
receipt. A broad actor trace was truncated for discovery; the accepted controls
use complete narrow health traces. Missing include paths in the first fixture
compile invocation were corrected before accepting the strict C results.

No save migration failed or was attempted. Any future invalid ABI or execution
identity means **ask the operator for a fresh PGXP slot**; never edit headers.
Next work is locating the model affine/node transform inside the verified
first-person draw, then mapping projectile constructor/motion seams and adding
guarded tracked mesh/aim controls. Multiplayer rendering/visibility needs its
own measured contract.
