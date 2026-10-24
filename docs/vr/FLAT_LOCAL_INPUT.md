# Flat multiplayer input for save preparation

The operator creates all weapon-set savestates. Launch `RunFlat.bat` from the
repository root for ordinary flat play using the one `build-release` target.

Local setup on 2026-10-24:

- P1: the selected Steam Controller, analog mode. Every `[player1]` keyboard
  and mouse binding is `None`.
- P2: keyboard, digital mode, with the separate layout below.
- Multitap disabled: this is a normal two-port game.
- `RunFlat.bat` explicitly disables `PSX_DEV_INPUT`, the diagnostic P1
  keyboard/all-controller merge, and clears the existing VR activation flags.

| P2 key | Native button / action |
| --- | --- |
| I / K | D-pad up/down: forward/back |
| J / L | D-pad left/right: turn |
| U / O | L1/R1: strafe left/right |
| 1 | Cross: fire / menu confirm |
| 2 | Square: reload/action |
| 3 | Circle: change weapon |
| 4 | Triangle: jump / menu back |
| 5 / 6 | L2/R2: crawl / aim-look |
| 7 / 8 | L3/R3 |
| P / M | Start / Select |
| F7 | Desktop savestate panel |

Runtime settings live in `build-release/settings.toml`; keyboard bindings live
in `build-release/keybinds.ini`. Both are local ignored user preferences. The
original files are backed up under
`analysis/vr-baseline/flat-local-input-backup/`. No savestates were created,
modified, or migrated by this setup.

The inspected runtime always includes each player's keyboard bindings even
when that port is assigned a gamepad (`main.cpp`, `pad_sources_for`). Both
players previously used the same default keys. Clearing P1's keys prevents P2
keyboard input from also driving P1. Separate P2 keys avoid the default desktop
keyboard mappings commonly emitted by Steam Controller layouts. The reported
controller-to-P2 movement was not captured live, so its exact physical-event
source remains unconfirmed. Steam settings were not changed; the operator
stopped the Steam UI inspection.

The resulting TOML/INI files were parsed and checked for the intended device
assignment, empty P1 keyboard bindings, exact P2 layout and disabled multitap.
The executable and framework were unchanged; physical separation still needs
the operator's controller/keyboard check. If rebinding through the launcher,
keep P1 keyboard entries empty and P2 on its own keys.
