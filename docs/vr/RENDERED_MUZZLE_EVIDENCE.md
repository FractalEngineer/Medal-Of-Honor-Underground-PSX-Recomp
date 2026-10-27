# Hand-fixed shot/laser ray and native weapon animation

Updated: 2026-10-27. Current operator policy is explicit: the laser indicates
where the bullet goes, fixed to the hand. Native recoil/reload animation plays
normally and does not steer this ray. This supersedes earlier W5/W6 plans that
required aim to follow the animated barrel. W6.1 is complete; W6.2 verified
triangle/vertex bindings is next under [HANDOFF.md](HANDOFF.md).

## Shared aim contract

The opt-in all-family shot candidate now passes the fixed profile calibration
(`muzzle`, `forward`) and the tracked hand affine to the existing
`mohu_vr_weapon_muzzle_shot` helper. The per-eye ray capture uses that same
helper and calibration. It retains native model animation as diagnostic data;
those copied animated vertices do not supply the shot/laser coordinates.

```text
base_origin = applied_quantized_RT * fixed_calibration.muzzle + applied_integer_TR
base_axis   = normalize(applied_quantized_RT * fixed_calibration.forward)
world_ray   = existing full canonical-camera inverse applied to that base ray
eye_ray     = actual scoped eye view applied once to the same base ray
```

The applied affine is already built from the controller grip position, aim
orientation and measured model calibration. It remains fixed when the hand
stays fixed, including through native recoil/reload. No native animation,
recoil, ammo, spread, gravity, release, collision or damage function was replaced.
The canonical model cache still guards owner/profile/load/freshness; it no
longer supplies aim coordinates. Legacy P38-only aim remains unchanged.

`MOHU_VR_WEAPON_AIM` still requires the calibrated render path and stays OFF by
default. Shot/event records expose `hand_fixed=1` for this policy. Older
receipts without that field retain their original animated-reference meaning;
the verifier supports both without changing historical receipts. The existing
probe's animated-marker name refers to its guard/capture lineage, not a
requirement that current aim follows animation.

The future firearm laser is the common aim centerline. Native shotgun spread
still fans pellets around it. Native thrown/rocket/bolt physics remain native;
a straight laser is not a claim to predict gravity or every pellet. W6.2/W6.3
still own target geometry, eligibility and actual beam/dot drawing. The legacy
right-aim/box pointer has not been relabeled as an exact shared-ray laser.

## P38 hand/ray and per-eye controls

Ten complete snapshots / 20 eyes passed on executable
`4204a6f3e2ca2037cfc1e7bc2987399f524e1e12156511eb8501c57d1e3a74d6`:

| Control | Result |
| --- | --- |
| Baseline, +/-24 eye offsets | One hand-fixed base ray; separate correct eye views |
| Head yaw +15 degrees / translation +100 units | Base ray unchanged; head affects each eye view once |
| Hand translation +100 mm / yaw +15 degrees | Calibrated ray follows the supplied hand |
| Native recoil | Visible markers move; fixed ray is identical to baseline |
| Native reload | Visible markers move and clip/reserve transfer; ray remains fixed |
| Tracking recovery | Unfocused hand rejects snapshot; focused recovery succeeds |
| Load recovery | Generation changes; old snapshot is invalid; fresh pair succeeds |
| Refusal recovery | Failed admission invalidates snapshot; a newer complete pair succeeds |

Changing to MP40 also rejected the retained P38 snapshot by identity. An actual
P38 shot had exactly the same recorded position and angles as the captured
fixed-ray prediction. Thus the laser reference and the native shot override
agree without following the recoil vertices.

The run published 268 pairs with 536 rollback checks, zero mismatches, failed
eyes, watchdogs or VRAM leaks. Six intentional admission refusals were recorded
separately. Stored snapshot validity became false, sequence 9 did not advance,
and reads were rejected until recovery produced the next complete snapshot.

Independent NumPy reconstruction from copied controls, calibration and actual
SDK-rounded hand samples had maximum eye-point error `2.37e-10` camera units,
fixed base-origin error `5.69e-14`, fixed axis-component error `4.58e-13`, and
W5 world-tip error `0.000007150948` world units. The actual P38 shot agreed
exactly at recorded precision. Point tolerance `1e-8` was declared before the
run for 12-decimal diagnostics; it reconstructs the quantized affine rather
than claiming physical accuracy at that precision. RT is Q12, TR integer,
world position/native angles Q16; the W5 numeric bound is one Q16 step.

Animated marker copies remain useful diagnostics. The recoil tip moved by up
to 45 model-coordinate units from idle; reload changed marker coordinates by
up to 60.444444. Their tip differences from the last natural sample were 31 and
43 units. These differences do not move the fixed ray and are not aiming errors
under the operator-selected policy.

## All-family native preservation and real damage

The fresh native/tracked pair used the same executable and source saves. All
13 IDs passed guarded construction/final-origin, first motion, ammo, release,
RNG, speed, ownership and impact controls. Native/tracked lifetimes were 21/21;
the tracked run retained 22 linked native P2 health decreases. Every ID produced
real linked P2 damage, including grenade and petrol under the redirected aim.

The shotgun retained six pellets, exactly 21 construction-scoped RNG updates,
and native spread: maximum pair angles were 5.257088 / 5.186966 degrees, with
median pair-angle delta 0.043845 degrees. The existing speed tolerances pass.
Missing/stale markers, unfocused hands and P2 fire stayed native; the recovered
P1 control became tracked. Marker replay/P2 rejection totals were 384/97.

The original comparison rejected the new grenade/petrol hits because the
native baseline missed in its fixed observation window. The current comparison
allows only **additional** linked hits for hand-fixed redirected `0x13F3`
weapons 10/15 and records them explicitly (four grenade, one petrol). Losing
native damage, extra hits from other families, wrong type or missing hand-fixed
policy still fails. RNG, ammo, release, speeds, trajectory/history and ownership
checks were not relaxed. Tests cover this narrow outcome difference.

The longer tracked run reproduced 300 known petrol-fixture eye discards and
recovered to pair 3296 after failed attempt 1844 with zero rollback mismatches.
This is not a zero-discard/global scene-stability claim. The standalone P38
ray run above had zero failed eyes. Broader transition stability remains Q1.

## Capture ownership and reproduction

The capture extends the existing `800894DC` P1 projection seam after the actual
tracked GTE control is applied. It owns copies of native/applied controls,
calibration-based ray, scoped view, source identity, generation and cycles.
It additionally copies the measured native animated marker vertices for debug
comparison. No second guest producer or renderer is introduced.

Both eye records stay pending until native weapon scopes restore and the
stereo transaction succeeds. A failed pair invalidates public usability without
advancing the frozen sequence. Load, invalid hands and model/context changes
also reject it. These are diagnostic frozen snapshots, not live beam pointers;
W6.3 must consume the current ray within the current eye/pair lifetime.

```text
mohu.vr.muzzle capture              request one complete pair
mohu.vr.muzzle status               validity/request/generation/sequence
mohu.vr.muzzle read=0|1             frozen eye metadata, including hand_fixed
mohu.vr.muzzle data=EYE:0..3         controls, diagnostics, view and fixed ray
mohu.vr.muzzle vertices=EYE:START    four diagnostic vertices per page
mohu.vr.muzzle stop                 disable and invalidate
```

Replies fit the existing 1 KB cap; every page carries its frozen sequence.
The capture is OFF at activation and has no new default-enabled environment
flag. The harness uses owned hidden processes, copied saves, bounded cleanup
and explicit per-process diagnostic flags. Intentional refusal counts must
exactly match the verified control delta; default callers still require zero.

```powershell
python -X utf8 vr/tools/probe_rendered_muzzle.py analysis/vr-baseline/<fresh-ray> --proof vr/proof/<new-ray>.json
python -X utf8 vr/tools/probe_shot_families.py analysis/vr-baseline/<fresh-native> --lifecycle --pair-settle-frames 8
python -X utf8 vr/tools/probe_weapon_aim.py analysis/vr-baseline/<fresh-tracked> --proof vr/proof/<new-aim>.json
python -X utf8 vr/tools/check_weapon_preservation.py analysis/vr-baseline/<fresh-native> analysis/vr-baseline/<fresh-tracked> --proof vr/proof/<new-pair>.json
```

## Validation and remaining scope

115 Python tests pass, including strict C affine/pair publication controls,
static-ray/recoil independence, actual-shot agreement, wrong source, double eye
application, false epoch equality and native damage-preservation checks. Strict
C syntax and the active Release/OpenXR/diagnostics/debug-tools build pass.
On the current binary, legacy P38 recovery and MP40-native fallback pass.

Before the operator policy change, the capture-only binary `fecd002a...` passed
five native / 14 legacy P38 controls, the 64-case MP matrix, MP lateral/native
fire/refusal recovery, all-ID flat poses and SP zero. These receipts retain
that binary; they are not relabeled as current-binary tests. The subsequent
change affects the explicit all-family aim branch and fixed-ray diagnostics;
its current ray and 13-family pair are validated above.

Source saves, thumbnails, preferences and SteamVR settings remain unchanged;
owned processes are closed. No headset, XR runtime, new build directory,
framework pin or shared math change was needed. Historical W5 state/death
receipts remain historical. The live rejection test is admission refusal;
failed-render publication is also covered by the C fixture, not a new live
mid-eye watchdog test.

W6.2 target triangles and W6.3 beam/dot submission remain open. Before W6.3
projection, also retain actual guest OFX/OFY/H; the current snapshot records the
affine and scoped view. Physical hand-aim/impact acceptance and live NPC/SP
isolation remain separate gates. Other-ID per-eye visualization is not claimed
by the P38 ray fixture, although all 13 shot families pass the current pair.

Evidence: [ray snapshots](../../vr/proof/weapon-rendered-muzzle-receipt.json),
[all-ID hand-fixed aim](../../vr/proof/weapon-hand-fixed-aim-receipt.json),
[paired preservation](../../vr/proof/weapon-hand-fixed-preservation-receipt.json),
[build/provenance](../../vr/proof/weapon-rendered-muzzle-build-receipt.json).
Raw current ray: `analysis/vr-baseline/hand-fixed-ray-20261027a/receipt.json`.
The pre-policy animated-capture exploration remains in ignored analysis and
is not the current aim contract.
