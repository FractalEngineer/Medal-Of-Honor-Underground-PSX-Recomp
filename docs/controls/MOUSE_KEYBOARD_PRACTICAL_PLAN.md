# Practical mouse and keyboard implementation plan

## Decision

Build a playable, feature-flagged direct-mouse mod. The owner rejected native
analog mouse emulation after playtesting it as sluggish and laggy, and explicitly
requested direct control like VR. Reuse native movement/action machinery. Ordinary
native R2 aim is excluded: it repurposes movement as pitch/lean and prevents
walking. This owner correction supersedes the initial native-aim proposal.

First-playable decisions:

- Mouse motion directly changes owned player pitch/yaw and targets at the
  measured camera-before-player boundary. Consume displacement once per native
  update, without stick curves, VBlank pulses or a turn-rate cap. Native ray
  construction still executes; only audited angular correction stores are
  suppressed during captured direct look.
- W/S drive native LY movement; A/D drive native RX strafe. A/D never turn.
- Left mouse maps to native Cross: fire/confirm.
- Right mouse maps to native R2 only for the scoped rifle (weapon ID 5).
  Release R2 for ordinary weapons after physical and plugin input are merged.
- Do not add a new ADS, FOV, weapon transform, or camera mode.
- Show the native crosshair for all normal weapons, including when R2 is not
  held.
- Leave the sniper scope native. Holding right mouse uses native R2 to enter
  the scope; the normal crosshair is hidden while the scope overlay is active.
- Use the existing `keybinds.ini`/PSX controls store. No new binding file and
  no full custom launcher screen in the first playable.
- Package defaults OFF until the input path and lifecycle checks pass.

The earlier native-stick route failed the owner's usability check. The direct
route uses the already measured actor/camera/ray hooks; the old stick-emulation
reducer has been removed. Default sensitivity is one native angle unit per mouse
count, yaw wraps at 4096 units, pitch retains the native +/-682-unit limit.

## Non-negotiable behavior

- The activation click captures the mouse and never fires.
- Escape releases capture.
- Focus loss, minimize, pause, menu, loading, savestate transitions and mod
  disable clear queued motion and held actions.
- No stale motion is replayed after return.
- No stuck fire, aim, movement or capture state.
- Mouse displacement is not multiplied by frame time or refresh rate.
- Netplay, split-screen and active VR are refused rather than mixed with this
  input mode.
- Native recoil, spread, ammo, reload, weapon switching, damage, collision and
  projectile behavior remain untouched unless a measured compatibility fix is
  required.

## Step 0: bounded native behavior check

Purpose: remove the remaining uncertainty about the existing aim button and
crosshair before adding production hooks.

Measure in the isolated copied-save fixture:

1. P38 idle, R2 held and Cross pressed:
   - capture idle and aimed frames;
   - record whether R2 changes FOV, camera anchoring or movement response;
   - verify whether the crosshair appears only while R2 is held.
2. Scoped sniper idle, R2 held and Cross pressed:
   - capture the scope transition and crosshair visibility;
   - record the native scope state and weapon identity.
3. Locate the crosshair producer or its visibility predicate. Prefer a
   read-only instruction gate or a render-only visibility flag over drawing a
   replacement crosshair.

Acceptance:

- P38 R2 behavior is understood and does not require an invented ADS state.
- The crosshair visibility gate is identified.
- The sniper scope gate is distinguishable from the normal crosshair.
- No save, preference or gameplay state changes survive the run.

Ordinary R2 does prevent walking (confirmed in the P38 fixture). Do not enter
that mode. Isolate crosshair visibility in the renderer instead.

## Step 1: production plugin skeleton

Add a normal, non-debug plugin and preloaded package:

- `controls/mouse_keyboard/moh_mkb.c`
- `controls/mouse_keyboard/moh_mkb.h` only if a separate test surface is needed
- `mods/preloaded/packages/mohu.input.mouse-keyboard/0.1.0/manifest.toml`
- `CMakeLists.txt`: compile the plugin into normal `psx-runtime` builds while
  leaving `MOHU_MKB_RESEARCH` separate and OFF for release builds

Initial package behavior:

- feature ID: `mohu.input.mouse-keyboard`
- default enabled: false
- channel: stable/experimental as appropriate
- no debug command required for normal use
- no disc, save, generated C or personal preference is included

The plugin must register activation/reset hooks and uninstall or neutralize all
host input policy on disable.

## Step 2: mouse capture and native look

Use the framework's existing local mouse policy instead of adding another SDL
polling path:

- `psx_mod_set_local_mouse_policy`
- `psx_mod_set_local_mouse_persistent_capture(1)`
- optionally `psx_mod_set_local_mouse_capture_across_transitions(1)` after its
  lifecycle behavior is verified

Implementation contract:

- One click captures; the capture click is suppressed.
- Escape releases.
- Motion accumulates as counts and applies directly to pitch/yaw at the owned
  camera update. Mouse Y positive maps to negative native pitch (look down).
- The pad transform preserves native sticks when no keyboard/mouse override
  applies. During capture it presents keyboard strafe through the mouse policy's
  RX output, preventing A/D from triggering the generic right-stick takeover
  gate. It never interprets RX strafe as horizontal look.
- Clear motion, axes and activation state on every reset or ineligibility.
- Do not modify native right-stick input when the plugin is OFF.
- Keep the reducer independent enough for direct unit tests.

Acceptance:

- capture click does not fire;
- mouse motion changes the native camera and a same-update P38 shot;
- Escape, alt-tab, focus loss and pause leave no stuck capture or motion;
- OFF behavior is byte-identical to the current ordinary input path.

## Step 3: keyboard movement and native actions

Use the existing PSX binding store and launcher Controls path.

First-playable defaults:

| Action | Binding |
| --- | --- |
| Forward/back | W / S |
| Strafe left/right | A / D |
| Fire/confirm | Left mouse / Enter |
| Sniper scope only | Right mouse |
| Reload/use | R / E |
| Next weapon | Q |
| Previous / next weapon | Wheel up / wheel down, while captured |
| Quick weapon selection | 1 through 8: owned inventory slots |
| Crouch | Left Ctrl |
| Jump | Space |
| Pause/Start | P |
| Menu directions | W/A/S/D / Arrow keys |
| Menu confirm | E / Enter / Left mouse (Cross) |
| Menu back | Q / Backspace (Triangle) |
| Release capture | Escape, fixed host action |

Implementation notes:

- Bind W/S through LY and A/D through RX rather than keyboard turning (LX).
- Merge opposite directions to neutral. Send full native deflection on each
  held axis, including diagonals: pre-scaling diagonal bytes makes the game's
  nonlinear analog response abnormally slow. Leave velocity handling native.
- Preserve native press/hold/release and menu-context behavior.
- Do not let gameplay bindings trigger menu actions or vice versa.
- Do not overwrite ordinary P1/P2 controller bindings.

If the current generic Controls page can edit these through the existing PSX
24-input store, use it. Add a title-specific semantic page only if the generic
page cannot expose movement, fire, aim and actions clearly.

## Step 4: sniper scope and always-on crosshair

Right mouse must inject native R2 only for the scoped rifle.

- Add or reuse the `R2` binding.
- For normal weapons, release R2 in the final pad transform. Releasing it in
  a controller source is insufficient: the physical button word is ANDed in
  afterward and can assert it again.
- Do not create a new FOV, zoom, camera pin, model pose or spread path.
- For sniper weapons, native R2 remains responsible for scope entry/exit.

Crosshair behavior:

- Force the native crosshair visible for normal weapons regardless of R2.
- Do not replace art or draw a host overlay unless the native sprite cannot be
  isolated safely.
- Hide/leave the normal crosshair when the sniper scope overlay is active.
- Crosshair visibility must not alter aim assist, shot direction, movement or
  weapon state.

Acceptance:

- P38 shows the crosshair while idle and while firing.
- Aiming does not introduce an unintended ADS or zoom.
- Sniper RMB enters the native scope and does not show the normal crosshair
  over the scope mask.
- Turning the feature OFF restores stock crosshair behavior.

## Step 5: integration gates and tests

Add focused tests rather than re-running the entire research matrix:

- local mouse policy lifecycle tests already present in the framework;
- pure reducer tests for count accumulation, reset and fractional remainder;
- keyboard-to-left-stick tests for opposite keys, diagonals and release;
- P38 capture/fire test in the copied-save fixture;
- one scoped sniper transition test;
- one automatic/rapid-fire and one reload/switch test;
- one pause/focus-loss/stale-input test;
- screenshot checks for normal crosshair and sniper scope;
- proof that source saves and ordinary preferences are unchanged.

Required builds:

- normal production build with the new package;
- research build remains independent;
- strict warning/error syntax check;
- Python test/verifier compilation;
- no remaining game process after each run.

## First-playable exit criteria

The first playable checkpoint is complete when:

1. The mod can be enabled and disabled from the existing package/UI path.
2. Mouse capture and release are reliable.
3. Mouse-look changes the view and P38 impacts.
4. WASD moves and strafes without keyboard turning.
5. Fire, aim, reload/use, cycle, crouch, jump and pause work.
6. Native crosshair is visible for ordinary weapons.
7. Sniper scope remains native and hides the normal crosshair.
8. No acquisition shot or stale input occurs.
9. Feature-OFF behavior remains stock.
10. The copied fixture and ordinary preferences remain unchanged.

## Deferred until after first playable

- Full target-present aim-assist matrix.
- Exhaustive recoil, moving, mounted and every-weapon research.
- Per-weapon ADS tuning. There is no custom ADS in this design.
- Wheel weapon selection and advanced rebinding UX.
- Full packaged release, public playtest and marketing claims.

## Known risks

- The direct look still needs owner feel/latency testing, scoped contexts and
  broad weapon/recoil/impact coverage. Native game rendering cadence remains.
- Crosshair visibility may share state with aim logic; isolate display from
  gameplay before forcing it.
- Non-sniper R2 prevents movement. The final pad transform must suppress it;
  the crosshair hook must never set the player's actual aim flag.
- Existing launcher binding UI may need a small bridge, but not a separate
  settings system.

## Verification starting point

Existing evidence:

- `docs/controls/MOUSE_KEYBOARD_HANDOFF.md`
- `docs/controls/MOUSE_KEYBOARD_HOOKS.md`
- `docs/controls/MOUSE_KEYBOARD_PROJECTION_RECEIPT.json`
- `tools/probe_mkb_native.py`
- `tools/check_mkb_research.py`
- `psxrecomp/runtime/src/local_mouse_policy.cpp`
- `psxrecomp/runtime/src/local_mouse_sdl.cpp`
- `psxrecomp/runtime/src/psx_keybinds.c`
- `docs/vr/FLAT_LOCAL_INPUT.md`
- `vr/underground/input.c` for the measured R2 mapping

Do not reopen completed camera/ray research unless the chosen native analog path
fails one of the first-playable acceptance checks.
