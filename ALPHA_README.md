# Medal of Honor Underground Recompiled + Full 6dof VR + Mouse/Keyboard

This is the Windows x64 **v0.1.5** testing release. Flat play remains the
default; VR is optional. Quest 3 through Virtual Desktop with VDXR is the
primary tested headset setup. SteamVR and Oculus launchers are included, but
Meta Quest Link and broad runtime coverage are not yet accepted.

For project context, see the [project README](README.md),
[v0.1.5 release notes](docs/release/v0.1.5.md) and
[documentation map](docs/README.md). The release notes summarize the package;
this guide is the source of truth for player setup, controls and limitations.

## What is in v0.1.5

- Native OpenXR stereo rendering with motion-tracked head movement.
- Tracked first-person weapons with hand-derived aiming and a right-grip laser.
- A wrist-mounted health and compass HUD, including the native under-fire marker.
- Wrist placement for the objective camera and native rendering for the game's
  frontend, videos and menus.
- A held 2.5x sniper scope with native scope range and normal player movement.
- Shared memory cards and savestates between flat and VR launchers.
- Mouse and keyboard campaign gameplay with editable actions, independent
  sensitivity sliders, wheel weapon cycling and adjustable 1.00x-2.50x aim zoom
  for firearms, the crossbow and both throwables.
- Mouse aiming and left/right traversal for mounted guns, plus corrected weapon
  cycling past empty inventory slots in either direction.
- Native frontend screens use the menu profile, so gameplay bindings do not
  leak into mission-end Evaluation or codename/typewriter pages.
- Native objective-camera aiming and photo capture, with walking and strafing
  while the viewfinder is held.

This is an alpha. Weapon and damage alignment beyond the exercised P38, Sten,
Panzerfaust and petrol-bomb paths still needs broader validation. Demanding
scenes can fall below the target frame rate. Sniper scope comfort, long-range
alignment and some frontend transitions still need physical-headset checks.

## Install and play

1. Download `mohu-0.1.5-windows-x64.zip` and extract the entire archive to a
   writable folder. Keep the executable, assets, mods and overlay toolchain
   together.
2. Supply your own **Medal of Honor Underground SLUS-01270 (NTSC-U)** CUE/BIN
   image. No game data or retail BIOS dump is included. The package includes
   the redistributable MIT OpenBIOS.
3. For flat play, run `RunFlat.bat` and select your disc in the launcher.
4. For VR, connect your headset and run the launcher for the intended OpenXR
   runtime:

```powershell
.\RunVR-VDXR.bat
.\RunVR-SteamVR.bat
.\RunVR-Oculus.bat
```

The launchers remember the disc selected beside the executable. Normal VR boot
includes the game's videos, menus and briefing; gameplay switches to per-eye
rendering. No test save or development tools are required. A bundled overlay
toolchain compiles streamed game code from your own disc automatically, so the
first launch and some transitions can take longer.

Flat and VR use the same `saves/` directory. Keep that folder when updating.
Older savestates may be incompatible with this executable; memory-card saves
are separate from savestates.

For an explicit disc path:

```powershell
.\RunVR-VDXR.bat -DiscPath "C:\Games\Medal of Honor Underground\game.cue"
```

## Mouse and keyboard

For flat play, open **Mods** and enable **Mouse and keyboard**. Click the game
to capture the mouse; Escape releases it. Defaults are WASD movement, left
mouse fire, right mouse aim, R reload, E use and mouse wheel weapon cycling.
Menus use WASD/arrows, E to choose and Q to go back.

All actions can be rebound on the mod page. Global and aiming sensitivity have
independent 1-10 sliders (defaults 5 and 4). **Aimed zoom (x)** ranges from 1.00
to 2.50, default 1.25. The weapon stays visible; the native crosshair appears
only while aiming. The sniper retains its native scope and supports movement.
Number keys remain available for the framework's filter shortcuts.

## Touch controls

| Control | Gameplay |
| --- | --- |
| Left stick | Move / strafe |
| Right stick | Smooth turn |
| Right trigger | Fire |
| A | Reload / use, according to game context |
| B | Cycle weapon |
| Left stick click | Jump |
| Right stick click | Toggle crouch |
| Menu button | Pause / Start |
| Right grip | Hold for the weapon laser; on the sniper rifle, hold for scope |
| Left grip | Hold for one-stick mounted weapon or camera aiming |

Menus use the left stick to navigate, the trigger or A to confirm, and B to go
back. The normal right-grip laser remains active while the sniper scope is held.
Movement is not disabled by the scope.

## Known limitations

- Performance is not final. The target is 60 fresh application frames per
  second, with 90 preferred; heavy scenes can still slow down.
- Physical comfort, rifle/laser alignment and final long-range visibility for
  the sniper scope remain open.
- Broader NPC damage, impact and final-origin validation across every weapon
  and mission remains open.
- Some frontend transitions and headset reconnect/tracking-loss cases still
  need wider testing.
- Quest 3 with VDXR is the primary tested setup. SteamVR and Oculus are
  available but not broadly accepted.
- This release targets Windows OpenGL. Linux, macOS and Vulkan VR are not
  supported by this alpha package.

## Reporting issues

Report issues at
[FractalEngineer/Medal-Of-Honor-Underground-PSX-Recomp](https://github.com/FractalEngineer/Medal-Of-Honor-Underground-PSX-Recomp/issues).
Include the build version, headset and OpenXR runtime, connection method,
mission/location, reproduction steps and whether the problem also occurs in
flat mode. Do not attach disc images or BIOS dumps.

Package metadata records the exact source revisions and executable SHA-256.
Dependency licenses are included with the package. These binaries are unsigned.
