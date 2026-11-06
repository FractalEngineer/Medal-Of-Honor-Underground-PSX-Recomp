# Mouse and keyboard controls

Enable **Mouse and keyboard** in the Mods menu. The feature is experimental
and defaults off. Click once in campaign gameplay to capture the mouse; that
activation click does not fire. Escape releases it.

Use only `build-release` for builds and launches. The local release configuration
uses `MOHU_PGXP=ON` to retain compatibility with existing release saves; this is
independent of the VR plugin. Do not create extra build directories for testing.

**Mouse sensitivity** and **Scoped sensitivity** are editable in this mod's
options. The defaults are 50 (about 0.044 degrees per count) and 100% of the
zoom-adjusted rate. Fractional angles feed the view matrix directly; there is
no mouse acceleration or smoothing. Native camera and projectile fixed-point
precision still apply.

| Control | Gameplay | Menus |
| --- | --- | --- |
| Mouse motion | Direct look | — |
| W/A/S/D | Move / strafe | Navigate |
| Left mouse | Fire | Confirm |
| Right mouse | Native sniper scope only | — |
| R | Native reload/use | — |
| E | Native use/reload alias | Cross / confirm |
| Q | Next weapon | Triangle / back |
| Wheel up / down | Previous / next weapon while captured | — |
| 1–8 | Select owned inventory slot | — |
| Left Ctrl | Crouch | — |
| Space | Jump | — |
| P | Pause | Start / resume |
| Arrow keys | Native D-pad | Navigate |
| Enter / Backspace | Confirm / back aliases | Confirm / back |

Ordinary weapons keep the native crosshair and do not enter native aim mode,
which would prevent walking. While the mouse is captured, the sniper retains
its native scope view with direct mouse look and normal walking/strafe controls.
Weapon changes, ammunition, reload/use context and
collision remain native. Number keys address inventory slots, not fixed weapon
categories; unavailable slots are ignored.

Menu bindings are selected for the frontend and native pause menu. They do not
overwrite the player's saved keyboard/controller bindings. The current MKB
defaults are a temporary session profile; editable bindings are still pending.

This implementation targets local single-player campaign play. Sniper controls
are verified on the owner's slot 1. Other campaign contexts and remaining input
latency need further validation.
The handoff and regression receipts record the current test coverage.
