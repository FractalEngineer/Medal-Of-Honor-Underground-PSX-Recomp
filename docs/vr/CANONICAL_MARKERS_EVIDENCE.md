# Canonical animated weapon markers

Updated: 2026-10-27. This W5.3c experiment measures animated model data available
to simulation. It adds no shot-pose writes, changes no native gameplay state and
does not promote all-weapon tracking or physical barrel alignment.

## Source and temporal contract

`vr/underground/weapon_markers.h` defines the title-owned marker groups, means
and usability guard. `weapon_marker_groups.inc` contains the existing measured
W3.4 grip/tip node-index groups. P38 also samples its rear barrel ring (node 11,
indices 11..17). Other profiles expose an explicitly provisional grip-to-tip
axis; these are not newly measured bore axes.

The read-only sampler runs at the existing `800894DC` instruction, after native
animated vertices are produced and before projection. A natural P1 entry at
`800892E8` establishes owner/object/stack/caller/H=133 identity. Eye replay is
rejected before it can establish a token or publish data. Natural P2 objects
are separately counted and rejected. The project callback checks the token,
live P1/model identity, source-geometry hash and bounded output pointers before
copying selected native vertices into host-owned storage.

The simulation sample is the **last completed natural P1 animated-model output
before the shot event**. It is not the following frame's recoil animation or an
eye's model buffer. Each sample has owner, fixed input/object, weapon ID, measured
source-geometry FNV, host load generation, monotonically increasing sample
sequence and guest cycle. Usability requires all key fields to match, a sample
cycle no later than the event and age no greater than 2,257,920 guest cycles
(four NTSC VBlanks). The receipt reports measured ages rather than assuming that
limit is the actual age.

The existing framework savestate callback increments host generation and clears
validity before restored execution resumes. Source data is also cleared on
activation/start/resume; owner, object, ID, source hash, generation or time
mismatches reject a sample. A diagnostic freeze keeps the last sample available
for a real stale-cache control. No guest save header or RAM value is edited.

At native shot construction, the observer copies the whole selected-vertex
sample into the bounded shot record. Paged reads then refer to that immutable
copy, even while later native drawing refreshes the cache. The pure helper
publishes grip, tip and axis-base means only after all selected vertices pass.
Host NumPy recomputes each mean independently from the retained integer vertices.
The C fixture also compares compiled node/index selections to the original
measured calibration groups, checks gun-component membership, malformed inputs,
owner/model/source/load changes, time reversal and freshness boundaries.

Final matrix: **13 IDs, 18 initial shot events and three final-origin events**.
All have fresh matching samples. Initial-event ages range from 989,809 to
1,128,671 cycles (about two NTSC VBlanks at most), below the declared four-VBlank
limit. The maximum independent mean error is `4.2857095650106203e-10` model units
against a `1e-8` tolerance. The old W3.4 moving-marker receipt remains the
animation-state characterization; this timing matrix does not replace
recoil/reload/scoped moving-shot acceptance.

## Final-origin observations

The initial [family map](SHOT_FAMILY_EVIDENCE.md) covers the common constructor
call, RA `800488D8`. The [origin-writer result](SHOT_LIFECYCLE_EVIDENCE.md)
proves that release/constructor code can change the position afterward. Three
additional read-only instruction callbacks measure cache availability at the
corresponding final-origin stages:

| ID | Observation PC / complete instruction | Stage |
| --- | --- | --- |
| 10 grenade | `80084CDC` / `0C0145ED` | After the second basis call returns, immediately before `800517B4` initialization. Shot is S1; S2 is P1 input. |
| 15 petrol bomb | `80084B74` / `AE2B026C` | After final position and the optional Y clamp, before history copying. Shot is S1; S2 is P1 input. |
| 13 rocket | `80048AAC` / `8E090220` | After the common constructor's position adjustment and helper calls, before final input-history copying. Shot is S0; S2 is P1 owner. |

Each callback requires its live expected instruction, measured type, P1 register
relationship, current model/ID/source and the full measured basis-builder hash.
It samples only; these observations are **not sufficient code/ownership guards
for new writes**. The candidate still needs complete family code units and a
decision about preserving native clearance, history and initialization.
`event_pc` identifies the instruction observation; `event_caller` retains RA.

The origin ring is separate from initial-constructor capture. Its three records
must name the corresponding constructed shot objects. Thus the existing family
and lifecycle collectors retain their meaning and do not mistake the grenade's
second basis construction for a second projectile lifetime.

All three final-origin events used the same completed marker sample as their
corresponding initial construction. Their later event deltas were 22,879 cycles
(grenade), 21,372 (petrol) and 3,650 (rocket). Final-event sample ages were
1,012,688, 1,036,893 and 1,015,629 cycles respectively. This proves availability
at those observed stages, not a future conversion's collision/history policy.

## Reproduction and retained evidence

```powershell
python -X utf8 vr/tools/probe_canonical_markers.py `
  analysis/vr-baseline/<fresh-directory> `
  --proof vr/proof/weapon-canonical-markers-receipt.json
```

The tool reuses the existing all-ID family controls, copied root MP slots 1-4,
native input, headless configuration and receipt finalizer. A focused `--ids`
run cannot publish the full proof. The complete run includes fresh, frozen/stale,
recovered, frozen-cache load invalidation, P2 firing and disabled controls.
Native ammunition changes prove each control actually fired. Native shot
overrides remain disabled during this measurement; render rollback is checked.

Six controls passed: fresh/recovered samples accepted; a frozen sample aged
14,661,880 cycles and was rejected; a frozen cache was rejected after load
generation changed from 14 to 15 and the guest clock went backwards; a fresh P1
sample could not authorize a P2 shot; disabled capture supplied no usable sample.
The all-ID portion counted at least 1,907 rejected natural P2 draws and 9,332
rejected eye-replay entries without publishing either as canonical data.

Validation: 77 Python tests (including the strict C marker fixture), strict
diagnostic syntax, Release rebuild and 33-case shared-math parity. The unchanged
P38 behavior passes five native plus 14 tracked controls on the new executable:
901 complete pairs, 1,802 rollback checks, zero failed pairs/mismatches.

The longer all-ID measurement reports 2,413 published pairs, 300 discarded eye
attempts and zero mismatches across 5,126 verification checks. This is **not** a
zero-discard stereo receipt. A focused petrol-bomb run reproduces all 300
discards; the same native fixture with the sampler disabled also reaches 300,
with zero rollback mismatches. A focused crossbow-death control has zero discards.
Do not attribute the petrol result to enabling this sampler, claim global stereo
acceptance from this matrix, or relax existing render guards to hide the count.
The retained build receipt links these controls and the sampler-disabled timeline.

- [Canonical marker receipt](../../vr/proof/weapon-canonical-markers-receipt.json)
- [Build and affected regression receipt](../../vr/proof/weapon-canonical-markers-build-receipt.json)
- `mohu.vr.marker start|stop|freeze|resume|status`
- `mohu.vr.marker shot=N`, `vertices=N:START` (four selected vertices per page)
- `mohu.vr.marker origins`, `origin=N`, `origin-vertices=N:START`

The sampler is disabled by default and consumes no tracking input. Normal
calibration/aim flags remain OFF; the framework pin remains `555e1eab` on
`vr/shared-development`. No framework, generated C, game config, source save,
preference, headset or XR runtime change is part of this experiment.

## Next: W5.3d (completed)

Use the measured source/timing contract when implementing an explicit default-OFF
family candidate. Keep the existing P38 flag/unsupported-ID controls intact.
Begin with complete native code/guard units at the already mapped family stages,
then adapt the current quantized affine/full-inverse conversion to the immutable
animated tip/declared axis. Retain the render affine's declared grip/basis policy;
do not silently substitute a different pivot while changing the shot origin.

Native pellet generation, RNG, speed, gravity, release, owner, collision and
damage stay native. The rocket clearance adjustment and grenade second basis/
initialization must be handled deliberately; writing a common pose once or
subtracting observed shifts is insufficient. Test P38, MP40 and six-pellet
shotgun controls first, then each projectile family with the retained native
baselines. Matched native/tracked preservation and impact tests are W5.3e.

Fresh cached geometry alone does not prove new shot conversion, same-event
render/shot agreement, moving bore alignment, zoom-fire, thrown explosion
damage, NPC/SP isolation or physical acceptance. Those gates remain explicit.

W5.3d subsequently passed the synthetic desktop matrix. See
[the all-family receipt](../../vr/proof/weapon-aim-all-receipt.json) and
[build/regressions](../../vr/proof/weapon-aim-all-build-receipt.json). All 13
IDs / 23 converted events used the immutable animated marker with zero shot
fallbacks. The current next desktop task is W5.3e paired native/tracked
preservation and impact; physical and NPC/SP gates remain open.
