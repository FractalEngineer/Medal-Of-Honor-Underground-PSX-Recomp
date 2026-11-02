# Native MP shot lifecycle baseline

Updated: 2026-10-27. W5.3a/b are native measurements. Family-aware conversion
and matched tracked preservation/impact later passed in W5.3d/e. No headset
or XR runtime was used; no game runtime code or framework pin changed.

## What this adds to the family map

The [family map](SHOT_FAMILY_EVIDENCE.md) identifies 13 IDs, five types and one
basis caller. The lifecycle probe follows those objects through native position
history, XYZ integration and linked native health writes. It uses copied root MP
slots 1-4, native fire/release/movement and the existing read-only capture command.
All shot overrides are disabled in this run. Source saves/preferences stay intact.

The [compact receipt](../../vr/proof/weapon-shot-lifecycle-receipt.json) contains
per-ID controls, actual trigger/release frame bounds, each construction, first
motion, bounded trajectory samples and linked native damage. Full streams remain
in its ignored raw receipt and per-ID `id-XX-traces.json` files. The
[validation receipt](../../vr/proof/weapon-shot-lifecycle-validation-receipt.json)
records the executable, sources, checks and remaining limits.

Final result: **13 IDs, 22 shot lifetimes, 147 complete XYZ integration groups,
19 linked native damage writes, no override writes**. Sten reused one address;
constructor sequence bounds kept the two lifetimes separate. The final shotgun
spread was `5.252537956386305` degrees between the most separated first-motion
directions, with one basis-angle variant and six direction variants.

| ID / native family | Lifetimes | XYZ groups | Linked damage writes |
| --- | --- | --- | --- |
| 0 P38 / single | 1 | 2 | 1 |
| 1 MP40 / repeating | 2 | 4 | 2 |
| 17 StG44 / repeating | 2 | 4 | 2 |
| 10 stick grenade / thrown | 1 | 90 | 0 |
| 8 Colt .45 / single | 1 | 2 | 1 |
| 16 Sten / repeating | 3 | 6 | 3 |
| 4 shotgun / repeating | 6 | 16 | 5 |
| 15 petrol bomb / thrown | 1 | 1 | 0 |
| 9 silenced pistol / single | 1 | 2 | 1 |
| 14 crossbow / bolt | 1 | 6 | 1 |
| 5 scoped rifle / ordinary single fire | 1 | 2 | 1 |
| 12 M1 / single | 1 | 2 | 1 |
| 13 Panzerfaust / rocket | 1 | 10 | 1 |

Each row is a native control, not a tracked-aim result. The two thrown items
were constructed after the measured release interval. Scoped fire here is
ordinary fire, not zoom-plus-fire. A third Sten birth after input release reflects
native action timing; no controller-release bug is inferred from birth timing.

Measured world-unit differences between basis position and first sampled
integration start are stick grenade `(9,0,332)`, petrol bomb `(8,0,149)` and
Panzerfaust `(27,0,431)`. Other IDs are `(0,0,0)` in this fixture. These are
observations, not constants to subtract in a future override.

## Findings that constrain conversion

- The shotgun constructs six objects with the same initial basis angles. Their
  first motion directions differ: native spread is not established by counting
  basis-angle variants. Compare six trajectories, pairwise angular spread and
  native speeds after the candidate basis. Do not implement another spread RNG.
- Thrown/rocket first-integration starts differ from their captured basis
  positions. The ordinary firearms and crossbow have zero difference in this
  fixture. The focused follow-up below resolves their actual writers; the common
  basis-entry observation alone did not identify final origins or the grenade's
  second basis/init call.
- A stick-grenade sample contains changing vertical increments and later resting
  integration records. The petrol-bomb sample reaches one integration before
  this fixture stops producing that object's sampled motion. Neither control
  establishes tracked throw accuracy, detonation timing or explosion damage.
- Rocket and crossbow motion and linked native damage provide real projectile
  baselines. Native hits do not certify tracked collision/impact alignment.
- Automatic fire can destroy and reuse a shot address inside one trigger window.
  Match basis samples to ordered constructor events and split at the next birth's
  global write sequence. Address alone, or address plus guest frame, is not a
  lifetime identity. The same-frame shotgun also requires separate objects.
- The all-ID animation evidence already proves idle markers are insufficient.
  This probe does not create a canonical animated-marker cache. Existing eye
  capture arrays and the eye-only laser camera must not be promoted to simulation
  sources without measuring their ownership, ordering and freshness.

## Trace contract and rejection

The collector adapts the first game's bounded PC-filtered streaming method,
retaining Underground's measured bindings. `TraceCollector` now accepts an
optional filter map; the existing P38 probe retains its original defaults.
Lifecycle capture additionally retains the full measured motion function
`8006EB8C..8006F7D0` and shot update `80047720..80047C80` as context.

Each lifetime requires one `80048790` native type store per basis sample,
correct type, one XYZ history sequence at `800488EC/F0/F4`, and complete ordered
XYZ integration groups. Every integration address must name this object's actual
position field. Constructor sequence bounds also apply to motion and damage;
the probe refuses missing/ambiguous constructions, incomplete XYZ groups and
trace-ring loss/truncation. Damage is claimed only for `8004EB80`, caller RA
`80050900`, with both `S1` and `A2` naming that lifetime's shot.

The actual clear-input command is bracketed by guest-frame queries. Births
strictly before that interval are `held`, strictly after are `released`, and
inside it are `release-boundary`. Do not turn a boundary observation into an
exact trigger-edge claim. Requested hold frames and elapsed guest frames differ
because the game advances while TCP queries are handled.

The compact proof hashes the final raw receipt bytes. Its raw hash is external
to those bytes, avoiding the previous family probe's self-referential digest
finalization. Historical family receipts are not rewritten by this correction.
Tests exercise real failure contracts, including recycled addresses, missing
constructors, wrong fields/history, truncated motion, false spread and final
receipt hashing.

## Reproduction and next task

```powershell
python -X utf8 vr/tools/probe_shot_families.py `
  analysis/vr-baseline/<fresh-directory> --lifecycle `
  --proof vr/proof/weapon-shot-lifecycle-receipt.json
```

Do not repeat the 13-ID baseline until a change affects it.

## Focused final-origin writer result

The [origin-writer receipt](../../vr/proof/weapon-projectile-origin-writers-receipt.json)
resolves the missing writes using `probe_projectile_origins.py`. It records a
broad ring only briefly, identifies the actual shot through existing P1 capture,
then asks `wtrace_dump addr_lo/addr_hi` to filter the **full retained ring** by
that object. It does not predict an allocation address. A retained native birth
anchor, complete position history and equality between last-writer values and
first integration's old values guard against ring loss or misassociation.

| ID | Last XYZ origin writers | Focused shift (world units) | Observed policy |
| --- | --- | --- | --- |
| 10 grenade | `80084CC0`, `80084CCC`, `80084CD8` | `(9,0,332)` | Release code copies a stack position into shot `S1`, then calls basis `8006C8B0` at `80084CD4` (RA `80084CDC`) and initialization `800517B4` at `80084CDC`. |
| 15 petrol bomb | `80084AF0`, `80084B18`, `80084B40` | `(8,0,150)` | Release code computes shot `S1` position from stack coordinates and scaled basis components. The captured window also shows a conditional Y clamp and subsequent history writes. |
| 13 rocket | `80048A20`, `80048A48`, `80048A70` | `(27,0,432)` | Common constructor applies a basis-derived positional adjustment after basis construction and before final input-history copies. |

The one-unit petrol/rocket differences from the broader baseline are additional
evidence that the shifts are not correction constants. Complete live code
windows and exact store words are retained. These windows establish the observed
stores; they are not complete function hashes or ownership guards for new writes.
The petrol Y clamp was visible in code but was not taken in this control.

At the grenade's second basis call, `A0 == S1` is the shot and `S2` is P1 input,
not the owner actor. The existing observer/override requires `A0 == S0` and
`S2 == owner`, so it intentionally does not capture or override that call. This
corrects an easy overreading of the common-caller family map: it maps initial
construction, not every later basis rebuild. Reusing the common constructor
guard at the grenade release call would silently retain native behavior there.

```powershell
python -X utf8 vr/tools/probe_projectile_origins.py `
  analysis/vr-baseline/<fresh-directory> `
  --proof vr/proof/weapon-projectile-origin-writers-receipt.json
```

This three-control probe uses the accepted eight-frame trigger window. An earlier
four-frame attempt did not construct the grenade; do not repeat that shorter
window. The final run closed cleanly with source saves/preferences unchanged.

Follow-up W5.3c is complete in
[CANONICAL_MARKERS_EVIDENCE.md](CANONICAL_MARKERS_EVIDENCE.md), including natural
P1 source ownership, freshness/load controls and all three final-origin stages.
W5.3d implemented the opt-in family-aware candidate, and W5.3e supplies the
matched preservation/impact controls in
[WEAPON_PRESERVATION_EVIDENCE.md](WEAPON_PRESERVATION_EVIDENCE.md).
Native model/reload/recoil controls remain accepted
within W3.4; they do not close moving-shot alignment. NPC/SP and physical gates
remain separate.
