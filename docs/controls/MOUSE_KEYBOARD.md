# Mouse and keyboard controls

Enable **Mouse and keyboard** in the Mods menu. The feature is experimental
and defaults off. Click once in campaign gameplay to capture the mouse; that
activation click does not fire. Escape releases it.

Use only `build-release` for builds and launches. The local release configuration
uses `MOHU_PGXP=ON` to retain compatibility with existing release saves; this is
independent of the VR plugin. Do not create extra build directories for testing.

**Global mouse sensitivity** and **Aiming sensitivity** are editable in this
mod's options as **1-10 sliders**. Defaults are **5 global** (about 0.044 degrees
per count) and **4 aiming** for more precise aiming. Each uses the same base
scale independently: changing global does not change the aiming rate. Zoom
compensation keeps equal slider values at equal screen movement. Fractional
angles feed the view matrix directly; there is
no mouse acceleration or smoothing. Native camera and projectile fixed-point
precision still apply.

| Control | Gameplay | Menus |
| --- | --- | --- |
| Mouse motion | Direct look | — |
| W/A/S/D | Move / strafe | Navigate |
| Left mouse | Fire | Confirm |
| Right mouse | Quick, eased 1.25× firearm zoom / native sniper scope | — |
| R | Native reload/use | — |
| E | Native use/reload alias | Cross / confirm |
| Q | Next weapon | Triangle / back |
| Wheel up / down | Previous / next weapon while captured | — |
| Left Ctrl | Crouch | — |
| Space | Jump | — |
| P | Pause | Start / resume |
| Tab | Objectives / select | — |
| Arrow keys | — | Navigate |
| Enter / Backspace | Fire / jump alternatives | Confirm / back |

The crosshair is hidden in normal view and appears only while right-click
aiming. Ordinary firearms and the crossbow zoom 1.25× in about 100 ms, with reduced mouse
sensitivity and a tighter native crosshair. Releasing right click hides the
crosshair immediately and eases back out. The held weapon stays visible and
weapon accuracy is unchanged. Number keys are reserved for PSXRecomp's filter
shortcuts; use the wheel to cycle weapons.
Walking and strafing remain available. While the mouse is captured, the sniper retains
its native scope view with direct mouse look and normal walking/strafe controls.
Weapon changes, ammunition, reload/use context and
collision remain native.

All gameplay and menu actions are editable under **Mods > Mouse and keyboard**.
Click a binding button, then press a key or mouse button. Weapon cycling also
accepts wheel up/down. Each action supports three alternatives; right-click a
slot to clear it, or use its **Reset** button to restore the defaults. Escape
cancels a pending rebind. Changes save automatically and apply live when edited
in the running mod UI. The table above lists defaults, including alternatives.
Click-to-capture and Escape-to-release remain fixed framework controls.
Menu bindings apply to the game's frontend and native pause menu. The player's
ordinary saved keyboard/controller profiles remain unchanged.

This implementation targets local single-player campaign play. Sniper controls
are verified on the owner's slot 1. Other campaign contexts and remaining input
latency need further validation.
The handoff and regression receipts record the current test coverage.
