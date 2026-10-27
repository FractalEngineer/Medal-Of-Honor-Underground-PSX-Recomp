# P1 death and native respawn evidence

Updated: 2026-10-27. W5.4c passes for the copied MP desktop fixture. Physical
barrel-to-impact confirmation stays open in W5.4d. The next desktop task is
W6.1 rendered animated muzzle capture, as specified in [HANDOFF.md](HANDOFF.md).

## Accepted result

The native and tracked modes ran in separate owned headless OpenGL processes,
using identical root MP slot-1 copies, preferences and executable
`8d0db60626bd516e91a342f648b22579e07b7ad3339ac104637774e1a71bc20d`.
No runtime C, framework pin, configuration default, source save or preference
changed. No headset or XR runtime was used.

| Control | Native | Tracked |
| --- | --- | --- |
| P1 health | 32 -> 0 -> 32 | 32 -> 0 -> 32 |
| Native P2 attack | 34 MP40/StG44 shots | 29 MP40 shots |
| P2 candidate eligibility / aim writes | None | None |
| P1 actor/input | Preserved | Preserved |
| P1 shots from respawn input | 0 | 0 |
| Death/respawn P1 clip/reserve changes | 0 / 0 | 0 / 0 |
| Load generation | 1 throughout | 1 throughout |
| Separate post-respawn P38 shot | 1, type `0x13F6`, clip 8 -> 7 | Same, converted with fresh markers |
| Clean child exit | 0 | 0 |

Each death is linked to the actual current P1 health address, native damage
store `8004EB80` and P2 shot identity in both S1 and A2. Lethal MP40 damage
subtracts positive Q16 health to a negative value before `8004EC44` clamps it
to zero. The checker requires that same-frame, later-sequence, same-victim and
same-shot clamp; it cannot accept unsigned wraparound or final health alone.
Both accepted traces have 14 damage subtractions plus the zero clamp.

The tracked marker was valid before death, invalid when dead and valid again
after native respawn. Its sequence advanced 146 -> 836 -> 866. The recovered
shot used sequence 948, generation 1 and a source captured after the recorded
death, aged 1,040,735 guest cycles. The conversion independently reconstructed
from copied marker/control data had origin error `0.000007295364781612079`
world units, within one Q16 step. Its first-motion origin error was `0` and
normalized axis cosine `0.999999190424552`.

The recovered tracked shot deliberately aims upward to expose its first native
integration without requiring a target at the random respawn location. It
claims no post-respawn P2 damage. The accepted all-13 damage gate remains the
[W5.3e pair](WEAPON_PRESERVATION_EVIDENCE.md).

## Scope and limits

- Both modes have stereo inactive: zero eye attempts, render passes and rollback
  verification checks. This is a new shot/marker lifecycle result, not fresh
  stereo death/replay acceptance. Broader stereo/scene transitions remain in Q1.
- Native attack counts differ with hit timing. This supplement requires native
  P2 ownership/type and actual lethal damage, not equal RNG sequences or equal
  shot counts. Matched spread/RNG preservation remains the W5.3e result.
- The all-family flag is enabled in the tracked process, and the separate
  recovered shot supplies a valid synthetic hand. No live hand is claimed
  during the lethal attack. The observer records marker validity through death.
- P1 is P38 in copied MP slot 1. This does not certify every weapon at death,
  live NPC/SP isolation, physical attachment or headset barrel alignment.

## Reproduction and stop conditions

```powershell
python -X utf8 vr/tools/probe_weapon_death.py `
  analysis/vr-baseline/<fresh-death-directory> `
  --proof vr/proof/<new-death-receipt>.json
python -m unittest discover -s vr/tests -p 'test_*.py'
```

The tool reuses `probe_weapon_combat_states.run_mode` for save copies, explicit
environment, occupied-port/process refusal and bounded cleanup. Its separate
case registry leaves the accepted six-case matrix intact. Focused
`--mode native|tracked` runs cannot publish a paired proof.

1. Switch P2 to native MP40; after the switch tail, use short digital left
   presses and read the actual angle until the measured slot-1 range is reached.
   P2 debug injection supports digital buttons only. Do not write actor angles.
2. Fire native 8-frame bursts with 90 frames for recoil to settle. Allow native
   ammunition exhaustion/switching to StG44; reject unsupported weapons. Stop
   by 40 bursts and the 56-sample capture bound. No manufactured ammo or health.
3. Require a linked lethal subtraction/clamp and observed dead P1. Distinct
   fire presses wait out the native death timer and request respawn, bounded
   to eight attempts. Observe restored health before naming any later input a
   recovered shot. Require zero P1 constructions from the respawn presses.
4. Drain the respawn tail, arm the valid tracked hand only in tracked mode,
   and require a separate P38 shot, native clip consumption and fresh marker
   conversion/first integration. Preserve generation and P1 ownership.
5. Any failed fixture, incomplete trace, ring overflow, wrong native type,
   source change or forced/nonzero exit fails the run. Raw checkpoints survive
   analysis failures. Do not rerun an unchanged hypothesis twice.

Rejected setup leads are retained under ignored `analysis/vr-baseline/`:
fixed-turn crossbow shots can kill P1 but are sensitive to native input phase
and aiming; continuous digital turns overshoot between TCP reads. A continuous
MP40 salvo raises native recoil out of the hit volume; short bursts preserve
useful aim. These are test-fixture limitations, not reasons to edit native shot
logic. Do not rediscover or repeatedly tune those discarded recipes.

An earlier attempted recovered shot actually performed respawn after the native
death timer. The final tool observes health restoration before proceeding.
Another rejected receipt treated lethal health as unsigned/exact zero at the
subtraction; the signed subtraction plus native clamp is now explicitly tested.
Failed runs are not accepted evidence.

## Receipts

- [Paired proof](../../vr/proof/weapon-death-respawn-receipt.json).
- [Validation/provenance](../../vr/proof/weapon-death-respawn-validation-receipt.json).
- Raw final pair: `analysis/vr-baseline/weapon-death-pair-20261027i/receipt.json`,
  with native/tracked receipts, complete traces, phase checkpoints and logs.
- The [six-case matrix](COMBAT_STATE_EVIDENCE.md) and its historical hashes
  remain unchanged. This supplement adds the death transition rather than
  relabeling those older receipts.
