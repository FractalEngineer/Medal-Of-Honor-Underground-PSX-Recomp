# Movement and save preparation

The operator confirmed the sky ghost fixed in the physical headset on
2026-10-24. Movement work began from `627b31d`, with local HEAD and live remote
matching. Physical movement acceptance and multiplayer weapon-set coverage
remain pending.

## Controls and saves

Normal VR launch enables movement. Left stick moves forward/back and strafes;
right stick X turns smoothly. Movement follows the native body direction.
Deadzone is `0.2`, turn gain `0.65`; WorldScale `3`, IPD calibration `67 mm`,
and `1080p` internal rendering (5x) are preserved.

| Headset control | Native input |
| --- | --- |
| Right trigger | Cross: fire / confirm |
| Right A or left X | Square: reload / action |
| Right B | Circle: change weapon |
| Left stick click | Triangle: jump |
| Right stick click | L2: crawl/crouch |
| Left Menu | Start: pause / skip |
| Left grip held | Also route right Y to native LY; optional one-hand input |
| Menu left stick | D-pad navigation |
| Menu A / right trigger | Cross: choose |
| Menu B | Triangle: back |

The game owns combat contexts and weapon availability. These mappings do not
establish damage, tracked aiming, mounted weapons, or every weapon. Menus use
the native surface/player-pointer routing. Unsupported gameplay code/control
tables deliver neutral. Multiplayer routing and overlay guards need the new
fixtures; the SP receipt does not establish full multiplayer stereo support.

Start at boot instead of loading slot 2 with your usual runtime launcher:

```powershell
.\RunVR-VDXR.bat -Slot -1
```

`-Slot -1` clears inherited `PSX_LOAD_SLOT` and accepts native menu presentation
without waiting for a gameplay stereo pair. Enter multiplayer and select a
weapon set in the game's menus. Open the desktop savestate panel with **F7**,
select an unused slot, and save after the level and desired inventory load.
Repeat for each set; record each slot's map, weapon set, equipped weapon, and
player count. Preserve slot 2 as the SP regression fixture.

The launcher defaults to the isolated `analysis/vr-baseline/saves/` tree;
confirm the printed writable-state directory. For fixtures created elsewhere,
wait for saving to finish, close the game, and copy only completed `.pst` and
matching `.thumb` files into that tree. Never alter headers, ABI, or execution
identity. On a failed load, **ask the operator for a fresh PGXP slot**. No save
migration was attempted during this work.

`-NoMovement` keeps ordinary host-controller input for a control run.
`-MoveDeadzone` and `-TurnGain` override the corresponding defaults. The launcher
restores their `PSX_VR_MOVEMENT`, `PSX_VR_MOVE_DEADZONE`, and
`PSX_VR_TURN_GAIN` environment values on exit. Flat mode stays inert even with
inherited movement settings.

## Native map and architecture

The source follows the reference port's `vr/moh_vr_input.c` design: pure input
mapping and one-time `psx_mod_set_controller_source` registration with a coherent
DualShock presentation policy. Actions are sampled at the framework's offline
input boundary. There are no guest input hooks, player-position writes,
synthetic body yaw, framework changes, or input polling during eye replay.
Debug-override priority and the framework's save/load input guard are retained.

| Item | Underground |
| --- | --- |
| Native converter | `0x80083C6C`, 324 bytes, FNV `0x9CA131D0` |
| Converter SHA-256 | `ca7e826960954d0afd2225ca35261cf05a5b3408e44abf0b2ba94c072e50e380` |
| Calibration dispatcher | `0x80083DB0`, 84 bytes, FNV `0x2D93CB1C` |
| Dispatcher SHA-256 | `65745755028d9351b2f748af1785c7035fadf73c1e31a4fbc0df7ad8edf61e60` |
| Axis records | `0x800C47C8`, four 40-byte records |
| Action masks / inversion words | `0x800C4AA8` / `0x800C4AD0` |
| Response curve | `0x800AB12C`, 128 bytes |
| Raw pad order at `0x800A04A0` | RX, RY, LX, LY; individually measured |

Both complete function hashes and the selected axis/action records are checked
per gameplay sample. The game rebuilds calibration after detecting DualShock:
turn/forward/strafe records change from `1/0/3` to `3/0/1`. Native axis IDs must
remain `2/3/0`, inversions zero, with the measured action masks (entry 7 changes
from `3` to `0x200`). Rebuilt scales are 15360/8960/8960; initial scales are
8960/8960/10240.

Unlike the reference converter, Underground tests the live center +/-37 and
clamps its lookup index to 127. Captured center/gains were 128/255/258. The
inverse mapper searches the actual curve for magnitudes reachable in both
directions, then applies radial movement deadzone and turn gain. Copying the
reference threshold math would have produced the wrong response.

Native-axis controls showed LX changing actor rotation fields without position
translation, LY translating, RX strafing, and RY changing pitch fields. The
synthetic receipt records adjacent pad/actor queries; it is not an atomic
per-update measurement or physical turn-speed calibration.

## Verification

The [compact receipt](../../vr/proof/movement-receipt.json) records synthetic
action delivery, actual actor-field changes, release, rollback, image checks,
the final release profile, and settings/process cleanup. The strict C fixture
checks every native pad byte, curve saturation, radial movement, turn symmetry,
invalid input, button activity, menu mapping, and optional grip merge.

The action run covered neutral, forward/back, both strafes, both turn signs,
partial turning, diagonal motion, focus loss, inactive sticks, simultaneous
fire/use/weapon-cycle pad bits, and release. Matching position/rotation fields
changed. Rollback checks had no mismatch, VRAM leak, watchdog, or nesting repair.
The boot control checked menu D-pad/confirm/back delivery without a loaded save;
it did not establish multiplayer selection or multiplayer gameplay.

The existing 13 Python tests and strict frustum/HUD/input C fixtures pass.
Fresh zero and +/-90-degree captures retain eye identity and world coverage.
Both synthetic look-up raw eyes and the SteamVR application layer were
inspected; the measured sky ROI remained empty. Bulk evidence is bounded and
ignored under `analysis/vr-baseline/movement/`; the original sky proof remains.

Rejected attempts, all cleaned up:

- A relative exploratory save path resolved under `build-release` and found no
  save. The absolute existing path loaded slot 2 normally; no migration occurred.
- The first null-HMD test lacked permission to update SteamVR settings. No game
  started and settings were unchanged; the authorized retry used the existing
  restore-protected launcher.
- An initial registration block was inserted into the render-entry callback.
  The test rejected neutral delivery and repeated logs. Registration was moved
  to one-time activation before accepting movement evidence.
- The next test caught the post-DualShock calibration rebuild. Strict guards
  returned neutral; both measured layouts are now supported.
- The flat check closed its wrapper before the child game exited. The final
  process check caught the owned child; it was explicitly stopped and cleanup
  rechecked before the receipt was accepted.
- An exploratory menu query outlived its bounded launcher and received
  connection refused. The launcher had exited and restored settings normally.

Next operator checks: stick direction/speed, release, pause/resume, and menu
transitions in the headset, followed by fresh multiplayer weapon-set fixtures.
Any invalid fixture requires asking for a fresh PGXP slot.
