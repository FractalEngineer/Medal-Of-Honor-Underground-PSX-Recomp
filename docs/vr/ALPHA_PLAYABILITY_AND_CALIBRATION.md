# Playable alpha priorities and runtime weapon calibration study

Date: 2026-10-28. **Study/documentation only. No feature implementation, game
launch, build, new framework branch or dependency update is authorized by this task.**
This document supersedes the earlier blanket visual-acceptance wording and the
strict R5 -> R6 -> W6 ordering where those conflict with the operator's alpha goal.

## Operator clarification: port working first-game behavior first

The operator explicitly asked to use the already solved first-game behavior.
**Default approach: port/adapt its current source; the runtime editor is optional
follow-up, not a prerequisite for corrected weapons, laser or essential HUD.**
The menu proposal below remains a study, not a new architecture to build before
restoring parity. Current implementation priority is A1 triage, A7 native pause,
A2 weapon parity,
A4 laser parity, A5 HUD parity, A6 focused alpha validation/package; A3 can follow
those ports or move earlier only if live calibration is still the actual blocker.

### Concrete source-to-source port work

Reference checkout inspected at `d82a5d0024570d7477db38d3cea5dfc59dd22035`.
Both projects already use aim orientation + grip position for hand tracking
(`mohu_vr_weapon_track_delta` locally). **Do not rediscover or replace that working
input convention.** The relevant difference is subsequent model composition:
reference preserves its authored animated basis with a full native inverse;
Underground maps each asset through normalized per-ID grip/right/up/forward data.
Compare that difference at the known seams before assuming the hand sampler is wrong.

| Problem | Previous-game implementation to start from | Underground adaptation only |
| --- | --- | --- |
| Pause menu missing/broken | `vr/psx_vr_stereo.c:vr_scene_entry` pause flag / `g_menu_flat`, `vr_native_surface_mode`, quad presentation and controller source; `moh_vr_input.c:moh_vr_menu_input_map` | Reuse native pause-state -> flat menu plane -> menu-input transition. Local menu mapper already exists. Verify Underground's native pause-state producer; do not copy the first-game address. SP source explicitly excludes MP, so validate MP presentation separately. |
| Held orientation / high fire | `vr/psx_vr_stereo.c:vr_weapon_geometry_filter`, `vr_shot_basis_entry`, `vr_cache_camera`; `vr/moh_vr_aim.c:moh_vr_weapon_transform`, `moh_vr_aim_shot`; `vr/check_weapon_aim.py` | Compare its **aim orientation + grip position**, native animated basis and full inverse with local per-ID normalized calibration and fixed-ray composition. Determine the divergence before adding offsets. Preserve this project's requested fixed shot/laser ray and native recoil. |
| Model size / pivot | `vr/run_vr.ps1` `WeaponModelUnitsPerMeter`/`WeaponPivot`; `moh_vr_weapons.h:moh_vr_weapon_model_scale`; the geometry filter's local model scaling | Port the established local-size/pivot control path. Verify equivalent assets before carrying values; `850` and `(80,150,100)` are not universal Underground constants. Projection precision is not physical size. |
| Attached hand | `moh_vr_weapons.h:moh_vr_weapon_face`, including partial-node suppressor selection; geometry filter's retained-face compaction; `check_weapon_profiles.py` | Apply the same face-selection principle to ID 17 using local vertices/triangles and update its guard/expected counts. The reference profile table has no StG44, so no valid StG-specific mask can simply be copied. Do not remap all meshes. |
| Floating laser | `moh_vr_raycast.h:moh_vr_ray_tri`, `moh_vr_ray_tree_tris`, `test_moh_vr_raycast.c`; `psx_vr_stereo.c:vr_laser_capture/project/clip/draw` | Port the complete surface-hit path and known tests. Bind local SP geometry and MP callback data. Feed the local shared fixed shot ray; do not copy the reference's animation-following laser policy. Check origin-inside leaves rather than inherit the reference shortcut blindly. |
| Health / ammo HUD | `moh_vr_hud.c/.h`, `test_native_hud.c`, `verify_native_hud.py`, `check_native_hud_gameplay.py`, stereo file's HUD capture/submission sites | Port existing dual-matte extraction, hand surfaces and fallback. Replace native ownership/regions/values; reuse current framework APIs. No new HUD renderer or hand-surface backend. |

These are existing solutions, not new discovery work. For each port, record the
source function, local counterpart and exact missing target binding. If a binding
is already in WEAPON_MAPPING/HANDOFF, reuse it. If an asset is byte-identical,
carry its data with provenance; otherwise measure only its differing data.
The reference has different weapon IDs and no Underground StG44/crossbow/petrol
profile. It also documents its in-game VR options menu as pending in
`ALPHA_README.md`; that one feature needs integration rather than a finished-menu
copy. Do not turn that limited gap into a new implementation plan for solved work.

First future implementation slice: compare the known grenade/P38 pose and firing
paths against the functions above, restore the chosen reference behavior where
it diverged, and fix only the StG's retained-hand selection. Then port its exact
laser path and native HUD. Keep the runtime menu study available without letting
it delay a playable alpha. No code or games are changed by this clarification.

## Latest operator findings

The operator additionally reports that the native pause menu is not working.
This is required alpha functionality and an existing first-game port, separate
from the new VR calibration/options editor. A native Start input or frozen actor
position alone does not establish a readable, navigable menu in the headset.

The four MP sets and SP slot-3 smoke established usable tracking and access to
the weapon set. Subsequent specific feedback withdraws blanket calibration and
gun-only acceptance. Preserve the original "Looks good" answers as history.

| Report | Required correction / remaining measurement |
| --- | --- |
| Grenades point forward instead of upright | Correct the held prop's display/grip orientation. Do not rotate its throw velocity upward merely because its long axis should be upright. Check petrol bomb separately. |
| Some weapons are too large | Per-ID model scale about the grip, independent of world scale/IPD. IDs and preferred values are not yet supplied; do not invent them. |
| StG44 still has an attached hand | Reopen ID 17's gun/hand classification and rendered face selection. Existing connectivity/whole-node tests did not prove semantic separation of a hand inside a retained component. Keep the gun/barrel intact. |
| Several weapons fire too high | Reproduce at known near/far targets; compare visible sights/barrel, shared hand-fixed ray, native launch direction and actual impact. IDs and angular errors remain unmeasured. |
| Laser stops in mid-air | Replace visibility-box endpoints with real surface intersections, and replace the controller-aim ray with the same calibrated ray used for shots. A calibration slider cannot correct false hit geometry. |

The reports do not invalidate every prior topology/math/combat result. Reopen the
affected calibration, asset mask, physical aim and laser scopes; reuse the measured
ownership, native hooks and copied fixtures. No complete rediscovery or unchanged
13-ID combat rerun is needed.

## What can be reused

Inspected current sources; these are implementation entry points, not claims that
a VR calibration menu already exists:

| Source | Existing capability | Needed integration |
| --- | --- | --- |
| `vr/underground/weapon.h`, `weapon.c` | `MohuVrWeaponCalibration`, per-ID immutable profiles, grip/muzzle/basis/physical size; `mohu_vr_weapon_calibrated_control` | Validated effective profile from shipped defaults plus runtime overrides. Keep original asset guards/masks separate. |
| `vr/underground/vr_diagnostic.c` | Owned SP/MP draw scopes, fixed shot candidate, projected animated flash; `vr_weapon_control_command` and generation handoff | Publish one effective calibration generation to rendering and firing. The current pose command exposes diagnostic X/yaw/loss, not a complete production calibration API. |
| `recomp-ui/src/recomp_runtime_ui.h` | Integer/choice/action rows, navigation, get/set/save/visibility callbacks, custom items and row views | Title-owned calibration page and callbacks. Fixed-point UI values can represent percent, degrees and millimetres. |
| Same UI, `recomp_runtime_ui_render_argb8888` | Software menu image without a new GPU UI renderer | Convert BGRA/ARGB layout to the RGBA8 OpenXR surface contract; verify alpha and channel order. |
| `psxrecomp/runtime/include/psx_menu_host.h`, `host_overlay.h` | Menu-provider lifecycle, main-thread requests, pause policy and local input capture | A title adapter if using host-menu services; confirm installed linkage and controller-source capture. Host SDL capture alone does not prove synthetic/OpenXR input is neutralized. |
| `mod_plugins.h`: `psx_mod_openxr_surface`, `PSX_MOD_OPENXR_SURFACE_FACE_HEAD` | Existing RGBA LOCAL-space surface submitted between XR begin/end | Comfortable in-headset options plane. Select a non-conflicting surface ID and preserve native menus/HUD ownership. |
| First game `vr/moh_vr_raycast.h`, `vr/psx_vr_stereo.c` | Triangle math/traversal patterns, surface presentation and beam projection | Reuse algorithms, verify Underground geometry bindings; never copy addresses or calibrations. |

The default recomp-ui PSX menu may decline single-disc titles
(`psx_menu_provider.cpp`, `default_selection` check). Its provider's ImGui draw
targets the desktop framebuffer. **Enabling that menu does not automatically
make it appear in the headset.** The native OpenXR menu surface copies content
before host overlays. Prefer the existing software menu image + explicit XR
surface for an initial title-owned page, with shared UI navigation retained.
Verify the software backend is linked before choosing exact source/CMake changes.

The reference `docs/reverse/VR_ALPHA_TODO.md` section 5 still lists VR options,
calibration, persistence and activation as unfinished. Reuse the current shared
UI/model/surface APIs, not an assumed finished first-game calibration editor.
Generic missing capabilities, if actually needed, belong on `vr/shared-development`
and its tracker; title weapon fields/data stay in Underground. Do not update pins
or grow a generic settings framework to start this feature.

## Proposed minimum runtime menu

### Required native pause port comes first (A7)

Reference `vr_scene_entry` reads its measured SP pause flag at `0x8009A61C`
(writer `0x80062760`), sets `g_menu_flat`, calls `psx_mod_openxr_quad` at the
configured distance/size, and supplies identity eye views for the native menu.
Its controller source chooses `moh_vr_menu_input_map` when either native-surface
or flat-menu mode is active. Weapon pose/laser/HUD replacement must not obscure
this menu. The first game's documented accepted menu distance/width is 2 m.
These are reusable behavior/defaults; the guest pause address is title-specific.

Underground already has `mohu_vr_menu_input_map`, Start mapping,
`set_openxr_native_surface` and `mohu_vr_native_surface_due` (four idle vblanks).
Current menu input selection is tied to the native-surface mode or absent player;
the inspected scene entry does not contain the reference's explicit native-pause
flag/flat-plane branch. A pause may keep drawing the scene, so an idle-scene
heuristic is insufficient. This is the concrete port gap to verify at runtime,
not proof that every possible pause failure has that cause.

Next authorized pause implementation: trace the Underground native pause-state
producer using one Start press/release and resume, bind that state in the existing
scene/input paths, and adapt the reference quad/identity-view transition. Preserve
fresh XR submissions and native menu art, selection, audio/simulation pause and
resume policy. Do not replace guest pause with host process suspension, a new UI
renderer or an options-page mockup. No native pause flag writes for normal use.

Acceptance: from normal SP gameplay, left Menu opens a stable readable native
menu in both eyes; stick/D-pad navigation, confirm, back and resume work; gameplay
movement/fire/laser stays neutral; resuming restores fresh world pairs, hand pose
and input without an accidental shot. Test repeated pause/resume, head turns,
focus/recenter and save/load/quit entries only where the native menu supports them.
The first game's `g_menu_flat` branch is SP-only: adapt MP independently using
the existing measured MP Start/lifecycle fixture; do not claim automatic MP parity.
Keep W2.5's historical input test scope; native menu visibility/operation is open.

### Optional weapon-calibration page

One readable head-facing **VR > Current weapon** page, available during play and
usable without removing the headset. No wrist placement, mouse ray, virtual
keyboard or arbitrary rebinding is needed for this first increment.

| Player control | Proposed initial range/step (validate during implementation) | Meaning |
| --- | --- | --- |
| Weapon | Current native ID/name, locked while editing | Prevent a switch/save load from silently editing a different profile. Unknown IDs show unavailable. |
| Size | 50-150%, 1% | Uniform local scale around grip. Advanced range only if measured assets need it. |
| Grip position | Each axis +/-150 mm, 1 mm | Hand-local left/right, up/down, forward/back; show player-friendly axis labels. |
| Grip angle | Pitch/yaw/roll +/-45 degrees, 0.5 degree | Common firearm attachment alignment; rotate model and derived fixed ray coherently. |
| Upright prop orientation | Per-prop shipped preset; fine adjustment | Display/grip orientation independent of the native throw basis. No mandatory 90-degree fine-slider workaround. |
| Aim elevation / left-right | Advanced +/-15 degrees, 0.25 degree, zero default | Explicit residual sight/shot alignment only after coordinate/trajectory errors are excluded. Shared by firing and laser; never a separate laser offset. |
| Laser | Off / hold right grip | Offer only the corrected surface-aware laser for normal alpha use. Existing diagnostic pointer stays clearly experimental/off by default. |
| Preview / Save / Cancel / Reset this weapon | Actions | Immediate session preview, explicit disk save, undo to entry snapshot and restore shipped defaults. No automatic save on every increment. |

Ranges are design proposals, not measured accepted calibration values. Add fine
and coarse stepping if needed; do not overwhelm the first page with all axes at once.
Keep full developer details/marker editing out of the player page.

Proposed activation: long left Menu press (~600 ms), short press retains native
pause. Verify the actual action is exposed on supported runtimes before adopting
it. Defer the native Start press until gesture classification so a long press
does not also pause or navigate the game. Right grip is already the laser gate;
do not reuse it as the options trigger. F10 can be a desktop companion, not the
only means of opening a VR menu.

Navigation: left stick chooses/adjusts, A accepts, B backs out. Opening must release
fire/reload/movement/weapon-cycle and suppress gameplay input until closing. Require
buttons/sticks released before resuming to avoid an accidental shot or switch.
Use edge/debounce handling rather than repeating actions each eye draw.

Default menu mode keeps the existing fresh XR/stereo loop running and neutralizes
player controls. Freeze the editable weapon ID and use a known safe spot for
preview; SP enemies may still move. Do not promise a paused live preview until the
host-pause path is proven to keep XR begin/end, hand tracking and surface updates
running. Offline MP fixtures are not networked MP: refuse unsupported online editing.

## Calibration and persistence contract

Keep shipped profiles immutable. A title-owned per-ID override structure holds
scale, local position, local rotation, optional fine aim trim and a generation.
Compose one effective calibration snapshot outside eye replay and reuse it for
both eyes, simulation shot construction and laser. Do not mutate globals halfway
through a stereo pair or recompute a different profile on a render thread.

For firearms, the default relation is:

`origin_from_model = origin_from_hand * hand_from_calibration * calibration_from_model`

Scale in `calibration_from_model` about the grip, then derive the fixed calibrated
muzzle origin and forward axis from the same composition. Scaling must move the
muzzle consistently while leaving native bullet speed/spread/damage untouched.
Native recoil/reload still animate the model and flash; they never steer the fixed
shot/laser ray. The flash continues using the actual projected animated tip, not a
new adjustable screen offset. Recheck its marker selection if the StG mask changes.

Separate the held visual basis and throw-launch basis for grenade/bottle families.
The current general profile maps its declared forward to hand forward; the grenade
and petrol profiles use grip-to-tip axes. That is a plausible explanation for the
reported orientation, **not a measured runtime root cause**. Preserve constructor,
release, secondary initialization and native launch dynamics while fixing the
display pose. Do not implement physical velocity-based throwing for this alpha.

Treat high shots as a diagnosis first: a shared error across weapons may be a
controller grip/aim convention or camera transform error. A constant near-target
offset can be muzzle parallax; distance-growing error suggests angle/basis. Native
spread and ballistic drop also matter. Verify the reference conversion and current
camera contract; avoid hiding a systemic bug with 13 unrelated pitch trims.

Persist host-only settings in a versioned title-local file (proposed
`vr_weapon_overrides.toml` in the writable settings location), separate from guest
saves and built game assets. Key by title, native weapon ID and profile schema or
asset fingerprint. SP/MP share values only when the validated profile is the same;
unsupported SP assets retain native fallback. Unknown/mismatched schema or assets
must not silently apply stale offsets. Save via temporary-file replacement, keep
last valid state on I/O failure, and validate finite values/ranges before publish.

Precedence: shipped defaults < valid saved user override < current unsaved preview;
explicit diagnostic overrides are for isolated tools and visibly disable/override
the menu rather than silently fighting it. Environment variables are startup input,
not a live settings store. Saving a guest state must not embed UI host pointers or
change the enhancement-memory-layout cookie. A save/load or weapon switch cancels
the old edit snapshot and invalidates stale shot candidates until current data is
fresh. No persistent emulated GPU allocation or save-header patching.

## Alpha-first completion order

| Priority | Concrete deliverable | Existing gates / stop condition |
| --- | --- | --- |
| 1 | Classify the `0xC0000409` / MP2 process exits using timestamps, close requests and available crash evidence | S5/Q1. If any are mid-game, fix before a public alpha. If close-only, bound the shutdown fix and proceed with calibration; do not rebuild the renderer or repeat weapon inventories. Current receipts do not prove every exit was caused by closing. |
| Immediately after stability triage | Port the previous game's native pause presentation and menu routing | A7 / B9/H2. A usable native pause/resume menu is required before alpha; the optional A3 calibration editor is unrelated. |
| 2 | Correct shipped grenade grip, StG hand mask and bad scale defaults; establish shared shot/sight alignment and real SP damage on a small representative set | W3.3/W3.5, W5.2/R6, W5.4d. Start P38, StG44 and grenade; add one rifle/shotgun and each changed launch family. Validate native SP NPC health ownership/damage and unchanged spread/release behavior. Extend only changed paths. |
| 3 | Port the first game's surface-triangle laser and projection/clip path, consuming the local fixed shot ray | A4 / W6.2-W6.4. Verify only target geometry bindings and any guard gaps. If it delays alpha, ship laser OFF/omit it rather than present box hits as walls. |
| 4 | Port the first game's working native hand HUD and fallback | A5 / H1/H2. Adapt native HUD producers/ROIs and existing surface calls. Do not invent a replacement HUD architecture or leave all information suppressed. |
| 5 | One practical SP mission/route, representative weapon families, death/load, pause/recenter/focus and a bounded play session; measure worst-scene cadence and package | A6 / B9/B10/Q1-Q4/S4. Reuse the first game's reporting and release tooling; keep production debug OFF and separate world-pair cadence from headset refresh. |
| Optional follow-up | Minimal persistent calibration menu if adjustments are still needed after reference parity | A3. Use the shared UI/XR APIs studied above; this is the one menu integration the first game also still lists as pending. It does not block porting solved features. |

R5 fog: obtain the correct street/wall fixture while doing the SP route, then fix
if it materially harms visibility. Do not block all other work on a missing fixture
or retune unrelated scenes. Campaign-wide perfection, elaborate wrist HUD,
universal headset matrices, room-scale collision, virtual hands, physical throwing,
two-handed weapons and advanced menus can follow the alpha. Native progression,
save/load, usable aiming, essential HUD and no active-play crashes cannot.

## Implementation slices for a later authorized session

- [ ] A1. Exit classification and bounded stability correction (S5); record close
  cause separately from visual feedback and mid-play crashes.
- [ ] A7. Port native pause presentation/input routing from the reference;
  bind Underground pause state, then verify both-eye navigation/resume in SP and MP.
- [ ] A2. Correct default profiles/masks and align the firearm shot contract;
  validate P38/StG/grenade and live SP NPC impact before cosmetic expansion.
- [ ] A3. Implement effective calibration state + persistence, then the minimal
  existing-UI/XR-surface menu. First prove production display/input before adding
  every adjustment. Do not assume desktop ImGui appears in XR.
- [ ] A4. Shared-ray actual-surface laser, or explicitly remove it from alpha.
- [ ] A5. Essential native HUD/mission information with tracking-loss fallback.
- [ ] A6. Focused end-to-end route, recovery/performance evidence and alpha package.

Validation should target failure modes: scale around a fixed grip, consistent muzzle
translation, rotation signs, same ray after save/reload, no mixed generations between
eyes or fire, upright held grenade with preserved launch, StG gun-only triangles,
menu input release/Cancel, malformed config handling and concrete wall-versus-empty
space laser tests. Run shared parity only if shared math/wrappers change. Reuse
existing probes; do not add tests that merely mirror every UI row.

The next prompt should authorize **A1/A7 first**, then A2 and direct A4/A5 ports.
A3 is optional follow-up; the previous menu-first ordering is superseded.
This study does not start those implementations and implies no commit/push.
