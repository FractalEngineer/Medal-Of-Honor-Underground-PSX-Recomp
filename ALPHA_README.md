# Medal of Honor Underground Recompiled + Full 6dof VR + Mouse/Keyboard

This is the **v0.1.7** testing release. Windows x64 ships flat and optional VR;
Linux x64 and arm64 ship flat. Quest 3 through Virtual Desktop with VDXR is the
primary tested headset setup. SteamVR and Oculus launchers are included, but
Meta Quest Link and broad runtime coverage are not yet accepted.

For project context, see the [project README](README.md),
[v0.1.7 release notes](docs/release/v0.1.7.md) and
[documentation map](docs/README.md). The release notes summarize the package;
this guide is the source of truth for player setup, controls and limitations.

## What is in v0.1.7

- RecompLauncher one-click setup, with the game's settings, VR mode and mods on
  its page.
- Recomp Achievements: five starter unlocks for the USA disc (gameplay start,
  sniper, weapon switch, a low-health recovery and a ten-minute session).
- Linux x64 and arm64 flat builds as `.tar.gz` archives.
- VR from RecompLauncher: VDXR, SteamVR, Meta/Oculus or the current OpenXR
  runtime, without editing environment variables.
- Mouse and keyboard enable, sensitivity, aimed zoom and bindings from the
  game's RecompLauncher page, plus CRT/scanline/internal-resolution choices.
- Specific startup messages for a missing, damaged or wrong-region disc.

It keeps the VR and flat feature set from v0.1.6: native OpenXR stereo rendering
with motion-tracked head movement, tracked first-person weapons with a
right-grip laser, a wrist HUD and damage marker, native frontend screens, a held
2.5x sniper scope, shared flat/VR saves, mouse and keyboard campaign gameplay,
centred reticles and shot targets, and corrected weapon cycling.

This is an alpha. Weapon and damage alignment beyond the exercised P38, Sten,
Panzerfaust and petrol-bomb paths still needs broader validation. Demanding
scenes can fall below the target frame rate. Sniper scope comfort, long-range
alignment and some frontend transitions still need physical-headset checks.

## Install and play

1. Download the archive for your PC: `mohu-0.1.7-windows-x64.zip` (flat and VR)
   or `mohu-0.1.7-linux-x64.tar.gz` / `mohu-0.1.7-linux-arm64.tar.gz` (flat).
   Extract the entire archive to a writable folder. Keep the executable,
   assets, mods and overlay toolchain together.
2. Supply your own **Medal of Honor Underground SLUS-01270 (NTSC-U)** CUE/BIN,
   ISO or CHD image. No game data or retail BIOS dump is included. The package
   includes the redistributable MIT OpenBIOS.
3. On Windows, run `RunFlat.bat` and select your disc in the launcher. On Linux,
   run `./run-flat.sh`. RecompLauncher can do this setup for you.
4. For VR, connect your headset and either choose the runtime on the game's
   RecompLauncher page or run the matching launcher:

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

For flat play, open **Mods** and enable **Mouse and keyboard**, or use the
**Mouse and keyboard** section on the game's RecompLauncher page. Click the game
to capture the mouse; Escape releases it. Defaults are WASD movement, left
mouse fire, right mouse aim, R reload, E use and mouse wheel weapon cycling.
Menus use WASD/arrows, E to choose and Q to go back.

All actions can be rebound on the mod page, or in RecompLauncher's Bindings
section. Global and aiming sensitivity have independent 1-10 sliders (defaults
5 and 4). **Aimed zoom (x)** ranges from 1.00 to 2.50, default 1.25. Launcher
values win over the stored Mods-page values for that launch; the game's Mods
page remains the place for direct launches.

## Achievements

Recomp Achievements is provided through RecompLauncher. The starter set covers
entering gameplay, equipping the sniper rifle, switching weapons, recovering
from 10 health or less, and ten minutes in gameplay. It does nothing when the
game is started outside RecompLauncher. A full mission-complete set is still
being researched.

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
- Linux is flat only in this release; Linux VR is not supported. The Linux
  builds need a working OpenGL 4.x driver.
- The achievements set is a starter set; mission-complete achievements and a
  full Beaten/Mastered path still need research.
- Launcher-provided mouse/keyboard and graphics-mod settings are session
  overrides; the game's own Mods page remains the stored choice for direct
  launches.

## Reporting issues

Report issues at
[FractalEngineer/Medal-Of-Honor-Underground-PSX-Recomp](https://github.com/FractalEngineer/Medal-Of-Honor-Underground-PSX-Recomp/issues).
Include the build version, headset and OpenXR runtime, connection method,
mission/location, reproduction steps and whether the problem also occurs in
flat mode. Do not attach disc images or BIOS dumps.

Package metadata records the exact source revisions and executable SHA-256.
Dependency licenses are included with the package. These binaries are unsigned.
