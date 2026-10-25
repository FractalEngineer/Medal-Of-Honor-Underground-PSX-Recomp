# Underground VR implementation handoff

Updated: 2026-10-26. This file is the execution contract for the next session.
[VR_PLAN.md](VR_PLAN.md) owns checkbox status. [WEAPON_MAPPING.md](WEAPON_MAPPING.md)
owns the detailed measured weapon layout. [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md)
owns history. History is not a queue of tasks to repeat.

## 1. Start here - one next task

**NEXT: W2.3 - pass zero, +/-90-degree and near-wall MP visibility controls.**
Use the completed flat scene-list/per-object selector and the opt-in eye-frustum
override; do not transplant the SP PVS selector or queue.

The visible weapon seam and P1-only MP eye renderer are already found and
working in desktop controls. W1 is complete for the P38 synthetic spatial
contract: the first-accepted-hand neutral delta has been replaced by an
absolute hand path, and independent head/hand controls pass in both eyes with
numeric residual checks. Do not rediscover the seam or rerun unchanged W1
controls. Physical grip/scale, MP head-turn visibility and tracked shots remain
open in W2-W5.

W2.1 is complete. Copied root MP slot 1 calls the native frame `80054BC4`,
scene `8006E9D8`, per-node callback `8006C61C`, visibility selector `80096EF4`
and helper `80096AC8`. The 21 level nodes are a flat scene-list queue gated by
`+0x0C` visibility masks. No separate MP PVS leaf queue was found at this seam.

W2.2 is also complete for its guarded override. The selector consumes node
center `+0x2F4..+0x2F8`, radius `+0x2FC`, the live GTE RT/TR, a heap view
descriptor at `camera_input+0xC8`, and an observed 540x120 screen rectangle.
`MOHU_VR_MP_FRUSTUM=1` replaces only level-node selection inside a valid P1 eye
replay; non-level nodes and every malformed or unknown path remain native. The
zero-angle P38 control passed in both eyes with zero fallbacks and clean
rollback. Head-turn and near-wall acceptance is W2.3 and is not claimed here.

## 2. Current state - facts, not work to restart

| Item | Current observation |
| --- | --- |
| Repository | `C:/Users/titan/Desktop/Github_Projects/Mine/Medal-Of-Honor-Underground-PSX-Recomp` |
| Branch / current HEAD | `feature/vr-port`; read current HEAD during preflight. W1/W2.1 predecessor is `afda5082...` |
| Checkpoint scope | W2.2 VR implementation, tools, proofs and execution docs; inspect current Git status and preserve `.commandcode/` |
| Framework gitlink | `b982e66e2536eaf738fbe3021db4d8f6c0feb90b` |
| UI gitlink | `7c635c6b366a6e0d5d3c913a7fce6ec04dd9f256` |
| Title / version | `SLUS-01270` / `0.1.0` |
| One active build | `build-release`, Release/OpenGL/OpenXR/PGXP |
| Game executable | `build-release/Medal_of_Honor_Underground_Recompiled.exe`; `psx-runtime` is the CMake target, not the executable filename |
| Current debug tools | OFF; TCP tools require an explicit diagnostic rebuild ON |
| CMake VR option | `MOHU_VR_DIAGNOSTICS` defaults OFF; local build currently ON |
| Normal launcher | Native menus, `-Slot -1`; no implicit savestate load |
| Experimental defaults | `PSX_VR_WEAPON_POSE`, `MOHU_VR_MP_CONTROL` and `MOHU_VR_MP_FRUSTUM` remain off |
| PGXP save ABI | `131106`; base flavor ABI `34` is incompatible |
| Unrelated work | `.commandcode/` is unrelated; do not add, change or clean it |

Read current Git state at session start. These are observations, not instructions
to reset HEAD, switch to master, restore an old binary or force old gitlinks.
`BASELINE.md` records the 2026-10-23 starting tree, including old `31df2e1e`;
it is historical and must not override the current framework pin above.

Accepted evidence:

| Scope | Receipt / practical limit |
| --- | --- |
| Flat first-person meshes | [weapon-viewmodel-receipt.json](../../vr/proof/weapon-viewmodel-receipt.json): all 13 IDs; visible pose controls; not physical calibration |
| P1-only MP eyes | [weapon-mp-eye-receipt.json](../../vr/proof/weapon-mp-eye-receipt.json): 1,215 pairs, 2,430 rollback checks, zero errors; both eyes and all 13 IDs |
| MP lateral / native fire | Same MP receipt: 52,136 differing pixels; pistol clip 8->7 and P2 health 32->31.25; not tracked-shot alignment |
| W1 P38 absolute spatial controls | [weapon-pose-space-receipt.json](../../vr/proof/weapon-pose-space-receipt.json): 29 cases, 10 head-only, five invalid; both eyes populated; no fire |
| W1 build / regressions | [weapon-pose-build-receipt.json](../../vr/proof/weapon-pose-build-receipt.json): source/binary hashes, 18 Python tests, strict fixtures, MP/flat/SP regressions, debug OFF |
| W2.1 native MP selector | [weapon-mp-level-selector-receipt.json](../../vr/proof/weapon-mp-level-selector-receipt.json) and [build receipt](../../vr/proof/weapon-mp-level-selector-build-receipt.json): five complete functions, both natural callers, 21-node flat queue/masks; no fire |
| W2.2 MP eye frustum | [frustum measurement](../../vr/proof/weapon-mp-frustum-measurement.json), [zero control](../../vr/proof/weapon-mp-frustum-controls.png) and [build receipt](../../vr/proof/weapon-mp-frustum-build-receipt.json): 21 live samples, guarded both-eye override, zero fallback/rollback errors; W2.3 controls remain open |
| Current build/regressions | [weapon-mp-build-receipt.json](../../vr/proof/weapon-mp-build-receipt.json): debug OFF, 18 Python tests, MP guard/syntax checks, flat isolation, SP 19 pairs / 38 rollback checks |
| Earlier native damage | [WEAPON_SET_EVIDENCE.md](WEAPON_SET_EVIDENCE.md), [weapon-alignment-receipt.json](../../vr/proof/weapon-alignment-receipt.json): all 13 IDs, damage-only pose reachability |
| Current eye images | [weapon-mp-eyes.png](../../vr/proof/weapon-mp-eyes.png) |
| SP world / visibility | [PGXP_RENDER_VIEW_EVIDENCE.md](PGXP_RENDER_VIEW_EVIDENCE.md), [HEAD_TURN_HUD_EVIDENCE.md](HEAD_TURN_HUD_EVIDENCE.md), [SKY_GHOST_EVIDENCE.md](SKY_GHOST_EVIDENCE.md) |
| Native input | [MOVEMENT_EVIDENCE.md](MOVEMENT_EVIDENCE.md): synthetic SP controls; physical/MP coverage remains open |

The current release executable SHA-256 is
`d13aa6496ea4a690e2018cf8ed5e44668ad4c47e4af9919342ea2ce9deca955a`.
The tested W2.2 diagnostic executable SHA-256 is
`5fe5c4dd1c7b52ffa552b0ec6af662ea51efbff9441666da791a7402aec68984`.
They differ because debug tools differ. Earlier W1 and MP hashes remain
historical. Do not swap them or relabel a historical receipt. Source hashes are
in the current build receipt; a new implementation needs new provenance and
affected checks, not fabricated matching hashes.

## 3. Fixture selection - slot numbers alone are ambiguous

| Purpose | Source | Selection |
| --- | --- | --- |
| W1 P38 / stationary P2 | `saves/openbios/state_8001F844_slot01.pst` plus `.thumb` | MP slot 1, weapon ID 0, zero switches |
| Full MP matrix | Root `saves/openbios/`, slots 1-4 plus thumbnails | 13 unique IDs across four native cycles |
| SP regression only | `analysis/vr-baseline/saves/openbios/state_8001F844_slot02.pst` plus `.thumb` | Isolated SP slot 2 |
| Stale-identity control | Slot 1 in that isolated SP tree | Not the valid root MP slot 1; do not use as W1 fixture |

**Root slot 2 is MP; isolated slot 2 is SP. Never choose by slot number without
its save root.** A new empty analysis directory is not a new compatible save.

The existing tools copy the selected `.pst` and `.thumb` into a fresh output
subtree and pass its absolute `--memcard-dir`. Use that ownership/cleanup pattern.
Never save into, overwrite, migrate, patch or replace an operator source slot.
Do not change clip/reserve, health or enemy placement to make a test pass.
Do not chase a moving SP enemy for weapon-position work. Reload the MP copy.

Cycles: slot 1 = `0,1,17,10`; slot 2 = `8,16,4,15`;
slot 3 = `9,14,5,10`; slot 4 = `12,17,13,15`.
Unique IDs: `0,1,4,5,8,9,10,12,13,14,15,16,17`.

## 4. Locked native contracts - use these exact seams

| Meaning | Underground MP contract |
| --- | --- |
| P1 / P2 roots | `[800A3604]` / `[800A3608]`; read at use time |
| Input | `[actor+39C] == actor+400` |
| Slot / weapon ID | `input+92` / `input+93` (decimal offsets) |
| Current health | `actor+108` (hex offset); trace the exact P2 address |
| Native damage function | `8004EAB4`, 532 bytes, SHA-256 `5ee9683eb0646d46a39e0b552f214fe90be010d2d41cebbe45fadc2db2a1b9e5` |
| Native health subtract / store | `8004EB78` / `8004EB80`; damage evidence, not a shot-constructor seam |
| Real first-person object | `[actor+114] == input+9F0 == actor+DF0` (hex offsets) |
| Body object - rejected as viewmodel | `actor+4AC`, magic `00160024`, 22 nodes |
| First-person entry | `800892E8`, 0xA70 bytes, FNV32 `39E56A35` |
| Required first-person caller | Call `8008A53C`, return `8008A544` |
| Native animated vertex producer | `8008DB98`, 0xB4 bytes, FNV32 `FAE3646E` |
| Pose application | `800894DC`, after native animated vertices / RT/TR restoration |
| Shared epilogue / restore | `80089D30`; eight RT/TR words plus world render view |
| Native world / weapon focal | H=400 / H=133 |
| MP eye context | `800A0B08`, 512x120 P1 source view |
| Natural MP frame / caller | `80054BC4` / `80063CF8`; call word guarded at `80063CF0` |
| P1 camera / selected player / scene list roots | `800A35B0` / `800A35C4` / `800A35CC` |
| Native MP camera / scene calls | `80054E68(camera,0)` / `8006E9D8(context,list)` |
| Submission | `[context+2218]` OT, 512 buckets, guest DrawOTag `80018B48` |

Addresses in this table are hex guest addresses, usually shown without `0x`.
Offsets explicitly labeled decimal are decimal. Heap sample `801491C0` is not
an address to hardcode. Function hashes identify the overlay generation; the
same address in SP is not the same method. Full guards live in source.

Source ownership:

| File / function | Change here for |
| --- | --- |
| `vr/underground/weapon.c`: `mohu_vr_weapon_track_delta`, `mohu_vr_weapon_relative_delta`, `mohu_vr_weapon_compose_gte_control` | Pure pose math / captured per-ID profiles |
| `vr/underground/vr_diagnostic.c`: `vr_weapon_prepare_delta` | W1 P38 absolute placement; other real-hand IDs remain native until their calibration gates |
| Same file: `vr_weapon_fp_enter`, `vr_weapon_viewmodel_project`, `vr_weapon_viewmodel_restore` | Existing guarded model scope; keep native animation, caller/mesh guards and common restore |
| Same file: `vr_mp_snapshot`, `vr_mp_code_valid`, `vr_mp_frame_entry`, MP branch of `vr_stereo_eye_draw` | Existing MP replay; reuse, do not replace to fix a weapon pose |
| `vr/underground/mp_view.h`, `vr/tests/test_mp_view.c` | MP mode, ownership, input/pointer and 512x120/H=400 guard |
| `vr/underground/frustum.h`, `vr/tests/test_frustum.c` | Host AABB/tree fixture plus the W2.2 center/radius cube and render-view overflow guards |
| `vr/tools/check_mp_view.py` | Owned copied-save process, both-eye controls, native pistol fire, refusal/recovery |
| `vr/tools/probe_mp_level_selector.py` | W2.1 selector trace plus W2.2 live AABB/RT/TR/view measurement |
| `vr/tools/inspect_weapon_sets.py` | Native inventory, actual first-person mesh capture, exact native damage trace |
| `vr/underground/input.c` | Existing mapper; MP converter/dispatcher still needs independent validation |
| `vr/underground/raycast.h` | Current visibility-node-extents pointer, not an exact triangle/barrel solution |

GTE TR uses integer camera units. The old affine helper packs translation in
Q12; `compose_gte_control` cancels that packing. Do not reintroduce `*4096` for
TR. RT coefficients are Q12; translation and rotation do not share units.

For the current authored mesh pose, temporarily use
`weapon_view.projection_h_ref=400`, preserving 133/400 of the world focal.
Restore the world view even for native/lost tracking. Absolute H=400 projection
or ref=133 without replacing the authored pose clipped the gun out of view.
Do not change this ratio independently of a measured new placement/projection
contract. A future calibrated placement may justify a different contract, but
requires a fresh same-run native/changed A/B with a visible gun and fixed world.

## 5. W1 - completed implementation and reproduction contract

### W1.1: first bounded experiment - P38 space capture

1. Perform the read-only session preflight in section 7. Open these functions:
   `vr_weapon_prepare_delta`, `mohu_vr_weapon_track_delta`,
   `mohu_vr_weapon_relative_delta`, `vr_weapon_viewmodel_project`,
   `build_stereo_render_view`, and the native producer at `8008DB98`.
2. Use copied root MP slot 1, ID 0, zero switches. Keep P2 stationary; do not
   fire. Run a single-weapon MP control only if the preflight or new change
   needs a fresh baseline; an intact prior receipt is not a reason to rerun it.
3. Capture the native animated affine/vertex representation, GTE RT/TR,
   selected P1 camera and complete eye view at the already measured seam.
   Take samples before and after application and at restore. Record function
   bytes/caller/ID/object identity with the samples. Do not scan all RAM again
   for an alternative first-person object.
4. The W1 deliverable is `docs/vr/WEAPON_CALIBRATION.md`. It must:
   name model/animated-model, native base-camera, tracking-origin, hand and eye
   spaces. For every transform, specify source->destination, units, axis signs,
   handedness, matrix storage, authored root placement and native animation.
   Measure whether the native basis is scaled; use its full inverse if needed.
5. State the intended composed result in named spaces. The target relation is
   `point_eye = eye_from_origin * origin_from_hand * hand_from_model * point_animated`.
   Define all scale/conversion factors and where native authored placement is
   removed. Derive how this fits the existing guest GTE plus host eye transform;
   never apply the eye transform twice or assume it has already been removed.
   W1 may use explicitly labeled provisional test pivot/scale and analytic
   markers to validate spaces. Physical grip/size acceptance is W3; do not
   block W1 by trying to calibrate all 13 weapons or requiring a headset first.

**W1.1 exit:** a captured P38 contract sufficient to compute an expected point
and forward axis, with one explicit unit conversion at each boundary. If a
space or unit is unknown, capture that missing producer/consumer next; do not
"tune until it looks right" or move to another weapon.

### W1.2: add the missing independent pose harness

Harness: `vr/tools/check_weapon_pose_spaces.py`. It reuses
`check_mp_view.py` process/save/PNG/rollback code and must not create a new
build, save format, OpenXR backend or renderer.

- Feed genuine synthetic right grip and aim samples through the existing
  debug command `openxr_hands_override`. Set both poses, focus, activity and
  validity. Its positions are `px_mm/py_mm/pz_mm`; quaternion components
  `qx/qy/qz/qw` are integer millionths, not floats. Clear overrides afterward.
- Refresh samples during a valid control so age stays <=150 ms. Test staleness
  by deliberately stopping refresh using host time; guest frame count is not
  a host pose age. Record `openxr_hands` output with each case.
- Do not leave `MOHU_VR_WEAPON_SYNTHETIC_X/YAW_MDEG` or the flat-probe flag
  active: those select direct deltas and bypass the real hand-pose path.
  Existing `mohu.vr.weapon.pose x=/yaw=` controls prove only direct deltas.
- Independently vary the existing eye-view head pose. The debug head override
  currently exposes translation and pitch, not a generic yaw argument. For a
  desktop-only yaw control, deliberately expose/use the existing diagnostic
  view yaw path; do not invent an unsupported debug command or require a new
  headset just to test the math. The current hand override also does not expose
  arbitrary origin-pose fields. Cover origin changes with explicit pure-math
  inputs or a narrowly scoped test extension, then verify physical recenter
  later; unsupported JSON fields are not a recenter test.
- Record effective units/metre for both hand conversion and eye view. The
  desktop view helper uses 1000 diagnostic units/metre; the hand converter
  currently uses `g_openxr_units_per_meter` (default `48/0.067`, and normally
  `238.806` with launcher WorldScale=3). Its environment override is parsed in
  the OpenXR activation branch, so setting that variable in a non-XR process
  does not prove it took effect. Make test units explicit and measured.
- `MOHU_VR_EYE_HEAD_*_MILLI` means milli-GTE camera units, not millimetres.
  Convert a requested physical pose using the declared unit scale; retain
  requested and effective values. Do not conflate diagnostic and headset scale.

Required independent cases, all with source slot 1 / P38:

| Case | What changes | Required invariant |
| --- | --- | --- |
| Absolute starts | Two different valid hand poses on fresh loads | First pose must affect placement; both must not silently become the same neutral/native placement |
| Hand only | +/-100 mm on each axis; +/-15-degree yaw/pitch/roll | Measured points/axis follow the composed transform; world ROI unchanged |
| Head only | Hand fixed in tracking-origin space; head +/-100 mm and +/-15-degree yaw/pitch | Reconstruct weapon anchor in origin space: it stays fixed; eye-space/screen motion agrees with head motion, not frozen pixels |
| Combined | Independently chosen head and hand changes | Same composed result, not the sum of two head transforms |
| Origin/recenter | Transform origin, head and hand consistently | Physical relation preserved; no retained stale neutral basis |
| Invalid/recovery | Unfocused, inactive, missing validity, stale and bad quaternion, then valid | Native fallback/no pose write on invalid samples; no jump from an old unintended anchor on recovery |

Use declared analytic points/axis in addition to images. Set tolerances before
judging output: float math <=1e-6 in its declared units, using recorded effective
inputs after SDK float conversion; final storage error no
more than one documented quantization step; zero-pose eyes identical; fixed
world ROI unchanged for hand-only cases. If the measured representation needs
a different tolerance, derive and record it before the run, not after a failure.
A clipped/disappearing gun is not a successful visible translation control.

### W1.3-W1.5: implement and close only this gate

Change the pure pose math and existing guarded geometry scope to meet the
captured contract. Preserve native animation/recoil/reload as input. Keep
unknown-ID, code/mesh/caller/ownership/focus/age failure paths native, and restore
RT/TR plus render view before another draw/eye. Do not hook firing or remove
arms as a shortcut. Per-weapon physical calibration comes later.

Save a compact pose-space receipt under `vr/proof/`, raw captures under a fresh
ignored analysis subtree, paired PNG IDs/hashes, effective parameters and
numeric expected/observed residuals. Run only the affected regression tier in
section 8. Check W1 boxes only after that evidence passes, then set NEXT=W2.1.

## 6. Later gates - deterministic order, not interchangeable experiments

| Task | Prerequisite / first action | Exit / allowed continuation |
| --- | --- | --- |
| W2 MP visibility/input | W1-W2.2 complete; validate the eye-frustum override, then trace the native pad converter | Full MP signatures/layouts plus zero/side/near-wall/input controls; SP addresses/queues are not substitutes |
| W3 calibration/hardware | W1+W2; P38 first, then per-ID pivots/axes/scale/muzzle markers and a bounded copied-save headset comparison | Operator acceptance per weapon; desktop receipts never check physical boxes |
| W4 native shot discovery | W1+W2; fresh MP P38 idle/fire/turned-away controls; start from P1 fire call chain and exact native P2 damage writer | MP constructor/basis/history/first-motion/ownership/units captured, read-only first |
| W5 tracked aim | W3 physical visual acceptance + W4 measured MP shot contract | Native trajectory/impact matches calibrated rendered barrel; P2/NPC and invalid tracking remain native |
| W6 exact laser | Calibrated rendered affine/muzzle/axis and independently mapped Underground triangles | First exact triangle hit, matching both-eye beam/dot; no node-box shortcut claim |
| H/Q HUD/coverage/performance/release | Relevant weapon gates pass | See explicit remaining boxes in VR_PLAN; do not substitute these for blocked W1 work |

If hardware is unavailable at W3, complete test preparation and leave physical
boxes open. After W1+W2, **read-only W4 mapping** may proceed while waiting;
tracked-shot writes/default promotion may not. This is the only planned branch
around the physical gate. Do not silently jump to HUD, optimization, SP targets
or remapping a completed renderer because a calibration experiment failed.

For W4, the original game's `VR_WEAPON_AIM_PLAN.md` is methodology, not a list
of Underground addresses or shot IDs. Local `analysis/vr-baseline/weapon-shot-mapping/`
contains historical SP scripts with hardcoded slot 0/run names: read them as
leads, do not execute them unchanged for MP or adopt their fields as measured MP.
Keep native speed/spread/ammo/reload/collision/damage/throw behavior.

## 7. Session preflight and bounded diagnostic commands

Read only, before editing:

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git submodule status
Get-Content vr/proof/weapon-mp-build-receipt.json -Encoding utf8
Get-FileHash -LiteralPath build-release/Medal_of_Honor_Underground_Recompiled.exe -Algorithm SHA256
Select-String -LiteralPath build-release/CMakeCache.txt -Pattern '^(PSX_DEBUG_TOOLS|MOHU_VR_DIAGNOSTICS|PSX_OPENXR):'
```

Compare the current source/build flags to that receipt. Differences require
inspecting the current diff, not resetting it. Do not create a branch/worktree,
change framework pins, regenerate C or launch a game merely to redo preflight.
All implementation/tools/tests remain under `vr/`; retained docs under
`docs/vr/`. Existing launcher/CMake integration may be narrowly edited when
required, with flat-mode checks. `game.toml`, `generated/`, framework/UI source
and original saves remain unchanged unless a separately justified task needs
it. Do not use broad `git add -A` with unrelated `.commandcode/` present.

Use the current CMake dependency cache; do not invent a new build directory.
Only when TCP/live diagnostics are needed:

```powershell
cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release -DMOHU_VR_DIAGNOSTICS=ON -DPSX_OPENXR=ON -DPSXRECOMP_REQUIRE_GAME_C=ON -DPSX_DEBUG_TOOLS=ON
if ($LASTEXITCODE -ne 0) { throw 'Diagnostic configure failed' }
cmake --build build-release --target psx-runtime --parallel 2
if ($LASTEXITCODE -ne 0) { throw 'Diagnostic build failed' }
$runRoot = Join-Path 'analysis/vr-baseline/weapon-mesh-mapping' ('resume-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $runRoot | Out-Null
```

The parent `$runRoot` may exist; **each tool's output child must not exist**.
Do not pre-create the child paths below. The tools own copying and cleanup.
Run one game at a time. Refuse occupied TCP 4372/existing games; do not attach
these controls to or terminate an operator's game. Do not pass `-Build` to a
VR launcher during a TCP run: it configures debug tools OFF.

Small existing control, if needed for W1:

```powershell
python vr/tools/check_mp_view.py (Join-Path $runRoot 'p38')
if ($LASTEXITCODE -ne 0) { throw 'P38 MP eye control failed' }
```

Full affected-path regression, once after a meaningful pose/replay change:

```powershell
python vr/tools/check_mp_view.py (Join-Path $runRoot 'mp-matrix') --all-weapons
if ($LASTEXITCODE -ne 0) { throw 'MP matrix failed' }
python vr/tools/check_mp_view.py (Join-Path $runRoot 'mp-lateral') --eye-offset 24
if ($LASTEXITCODE -ne 0) { throw 'MP lateral control failed' }
python vr/tools/check_mp_view.py (Join-Path $runRoot 'mp-fire') --fire-pistol --reject-recover
if ($LASTEXITCODE -ne 0) { throw 'MP native fire/recovery failed' }
python vr/tools/inspect_weapon_sets.py (Join-Path $runRoot 'flat-poses') --cycle --first-person-models --pose-controls
if ($LASTEXITCODE -ne 0) { throw 'Flat pose regression failed' }
python vr/tools/sky_ghost_control.py (Join-Path $runRoot 'sp-zero') --case zero
if ($LASTEXITCODE -ne 0) { throw 'SP regression failed' }
```

The old tool's `--native-projection` is an A/B discovery control; do not use it
as accepted projected/headset evidence. The W1 harness exercises the real hand
path separately from these existing direct-delta controls.

## 8. Verification, exit codes, recovery and session close

| Change | Required checks |
| --- | --- |
| Documentation only | Link/checkbox/task-ID consistency, source/receipt facts, diff whitespace; no game/build required |
| Pure weapon math / new spaces | Weapon fixture + new analytic space tests, P38 independent both-eye cases; then full affected pose/MP/flat/SP suite before accepting the implementation |
| MP mode/view/projection code | MP guard fixture, full MP matrix/lateral/fire/recovery, flat pose and SP zero regression |
| Shot state writes | New native/redirected shot traces + negative ownership/focus/ID cases, native damage suite, frame-state rollback and native fire/animation regressions |
| Launcher/input changes | Launcher tests, inherited-flag flat startup, relevant native input/boot/menu controls |

Existing focused commands (run once when affected):

```powershell
python -m unittest discover -s vr/tests -p 'test_*.py'
if ($LASTEXITCODE -ne 0) { throw 'Python tests failed' }
$cc = ((Select-String -LiteralPath build-release/CMakeCache.txt -Pattern '^CMAKE_C_COMPILER:.*=').Line -split '=',2)[1]
& $cc -std=c11 -Wall -Wextra -Werror -Ivr/underground vr/tests/test_mp_view.c -o (Join-Path $runRoot 'test_mp_view.exe')
if ($LASTEXITCODE -ne 0) { throw 'MP guard compile failed' }
& (Join-Path $runRoot 'test_mp_view.exe')
if ($LASTEXITCODE -ne 0) { throw 'MP guard fixture failed' }
& $cc -std=c11 -Wall -Wextra -Werror -Ivr/underground -Ipsxrecomp/runtime/include vr/tests/test_weapon.c vr/underground/weapon.c psxrecomp/runtime/src/vr_pose_math.c -o (Join-Path $runRoot 'test_weapon.exe')
if ($LASTEXITCODE -ne 0) { throw 'Weapon fixture compile failed' }
& (Join-Path $runRoot 'test_weapon.exe')
if ($LASTEXITCODE -ne 0) { throw 'Weapon fixture failed' }
& $cc -std=c11 -Wall -Wextra -Werror -fsyntax-only -Ivr/underground -Ipsxrecomp/runtime/include vr/underground/vr_diagnostic.c
if ($LASTEXITCODE -ne 0) { throw 'Diagnostic syntax failed' }
```

Interpret results correctly:

- MP/flat weapon inventories need `complete=true`, exit 0, unchanged sources/
  preferences and no remaining owned game. A receipt written during failure
  is not accepted just because some early cases passed.
- Both zero eye images must finish decoding, be populated and have identical
  hashes. Counters without a visible weapon do not prove a model seam.
- Native damage means a decrease in the complete trace at the exact current
  P2 health address. A kill can respawn to 32; final health alone is insufficient.
- A live counter read may catch one apply between restore calls. Verify exact
  equality after loss/drain; do not weaken the no-persistent-leak gate.
- Backend admission refusal increments `refused`; an interrupted eye may also
  increment `failed`. Retained/stale/last-failure fields are historical. For an
  intentional refusal control, require newer published/captured pair IDs after
  the last failed attempt, no new failures after recovery and zero state errors.
  Do not erase counters or accept a frozen retained picture as recovery.
- The established SP `sky_ghost_control.py` intentionally terminates its hidden
  child and may record child exit 1 with `intentional_termination=true`; its own
  command exits 0 when accepted. This exception does not excuse a crashed MP
  matrix or a save-load failure. The production flat startup smoke is also an
  explicit intentional termination, not interactive gameplay acceptance.

Failure handling is deterministic:

| Observation | Next action / stop condition |
| --- | --- |
| Debug port absent | Check build has debug tools ON, exact exe path, startup stderr and port 4372; no second game/build directory |
| `last_ok=0`, `state_load_failed`, ABI/identity mismatch | Stop dependent gameplay; ask operator for a fresh compatible PGXP source slot. Never patch ABI/identity or create a replacement save yourself |
| Occupied port / existing game | Recover/close it only if this session has a recorded ownership chain. Otherwise leave it alone; ask the operator only when it blocks dependent work, and continue independent code/docs |
| `emu busy or frozen` | Existing MP helper retries bounded busy responses; inspect advancing frames/logs after the bound. Do not invent pause/step/continue/run-to: removed APIs |
| Guard mismatch | Record actual bytes/contract and stay native. Do not weaken guards or reinterpret another overlay as the same function |
| Gun missing but apply counters rise | Compare the known native-projection control and focal/pose/near clipping at the same seam; do not reopen body-object discovery |
| World changes in hand-only control | Inspect eye/view restoration, transform order and double application; do not fix it with world offsets or widened FOV |
| Shutdown hangs | Stop admitting new eye transactions before TCP quit, as current MP helper does. Use bounded wait, then terminate only the recorded owned child; record forced cleanup as a limitation/failure, not exit 0 |
| Same hypothesis fails twice | Record both parameter sets and evidence; do not rerun it unchanged. Identify the missing fact or change one measured hypothesis; remain on this task |
| Hardware absent | Leave physical acceptance open, finish bounded batch preparation; only the explicitly allowed read-only W4 branch may advance |

Before ending an implementation session:

- [ ] Restore the same build to debug OFF and build successfully:

```powershell
cmake -S . -B build-release -DPSX_DEBUG_TOOLS=OFF
if ($LASTEXITCODE -ne 0) { throw 'Release configure failed' }
cmake --build build-release --target psx-runtime --parallel 2
if ($LASTEXITCODE -ne 0) { throw 'Release build failed' }
```

- [ ] If runtime/launcher changed, check hidden flat startup through RunFlat with
  inherited VR/weapon/MP flags; require pose/probe/stereo/OpenXR inactive and
  no MP frame replay. Do not require TCP from this debug-off smoke.
- [ ] Recheck source-save/thumbnail, settings/keybind and SteamVR hashes against
  this session's recorded baseline. Clear synthetic overrides and close only
  owned processes. No headset/runtime settings should silently remain changed.
- [ ] Keep bulk RAM/assets/images in ignored `analysis/`; retain compact receipts
  and selected proof under `vr/proof/`, with actual source/binary hashes.
- [ ] Check `git diff --check` and affected doc links. Review the diff; preserve
  unrelated work. No commit/push is implied unless the user requests it.
- [ ] Update checkbox IDs in VR_PLAN and the continuation record below; do not
  change earlier receipts to claim a new binary was tested.

## 9. Dead ends - do not repeat without new contrary evidence

| Rejected path / mistaken claim | Use instead / evidence needed to reopen |
| --- | --- |
| `actor+4AC` / shared 22-node table as first-person mesh | Measured `[actor+114] == input+9F0`; old candidate moved another panel |
| `80088C08` as the top-view weapon | Existing `800892E8` from `8008A544`; new viewport-specific evidence required to reopen |
| `8008DB98` is always the wrong function | It is the real native vertex producer when owned by the measured first-person caller; the old wrong body ownership was the error |
| `800892E8` as a simulation/player-update hook | This MP generation is animated model geometry; use measured mode-specific contracts |
| Generic frame-driver replay / all-span TRX experiments | Accepted SP frame-render slice and separate MP P1 reconstruction; black pairs were rejected |
| Manual GP0 OT walk as PGXP proof | Guest DrawOTag preserves packet source addresses |
| Following native y=240 flip for eye scratch | Accepted rollback-protected y=0 buffer; alternating black pairs were measured |
| Affine `*4096` applied to GTE TR | Integer TR helper and Q12 RT are deliberately different |
| Reference `ref=133`, pivot `(80,150,100)` or scale 850 copied as calibration | Existing authored pose uses ref=400; measure Underground spaces/mesh before changing placement |
| Native P2 hits prove tracked aim | Native shots are still native; require construction, trajectory and calibrated barrel-to-impact evidence |
| SP frustum/movement addresses applied to MP | W2.1/W2.2 measured the flat MP selector and eye frustum; MP converter remains W2.4 |
| Current right-aim/node-box laser called exact barrel/triangle laser | W6 rendered affine/muzzle plus independently mapped exact triangles |
| New build folder or patched state header repairs a save | Ordinary PGXP checks and operator-provided compatible slot only |
| Historical run-11 SP script executed for MP | Read it as a lead; use root MP copied slot 1 and current ownership/layout |
| Old plan says create branch, align `31df2e1e`, scaffold VR | Completed; current branch/pins/receipts above are authoritative |

## 10. Continuation record - replace these fields at session end

- Completed through: W2.2 (native MP selector layout plus guarded eye-frustum
  override and zero-angle control); W2.3-W6 and physical acceptance remain open.
- Current task: W2.2 complete. Stop before W2.3.
- Last accepted evidence: weapon-mp-frustum-measurement.json /
  weapon-mp-frustum-build-receipt.json / MP_EYE_FRUSTUM_EVIDENCE.md.
- Next action: W2.3 - run copied-slot-1 P38 zero, +/-90-degree and near-wall
  both-eye controls comparing native and overridden selector output with populated
  geometry and zero rollback errors. Do not reuse SP visibility addresses.
- Open physical gate: no grip/scale/size, physical recenter or tracked-shot
  acceptance is claimed. W1 control motion is synthetic.
- Current build: debug OFF at release SHA `d13aa649...`; W2.2 source/save/
  preference hashes match the build receipt; no owned game/debug listener or
  smoke wrapper remains.
- Checkpoint: W1/W2.1 predecessor is `afda508`; W2.2 source/tools/proofs/docs are
  included in this checkpoint. Unrelated `.commandcode/` remains excluded and
  untouched.

If a session stops mid-W2, replace the current task with the exact completed
substep, source diff, failing/passing case, output path, missing fact and one
next experiment. Do not reset this pointer to M1/W1 or generic discovery.
