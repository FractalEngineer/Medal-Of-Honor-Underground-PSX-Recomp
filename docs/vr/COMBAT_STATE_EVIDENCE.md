# Combat-state desktop evidence

Updated: 2026-10-27. This document records the W5.4 desktop matrix. It does not
close physical acceptance, W5.2 live NPC/SP, or the operator's barrel-to-impact
confirmation.

The later [P1 death/respawn supplement](DEATH_RESPAWN_EVIDENCE.md) closes W5.4c
without repeating this six-case matrix. Physical barrel-to-impact confirmation
is now W5.4d; W6.1 desktop rendered-muzzle capture is the next task.

## Result

The paired native/tracked run passed all six state controls on copied root MP
slots 1-4. Both modes used the same executable, source saves and preferences.
All owned processes closed cleanly, and no headset or XR runtime was launched.

| Control | Native result | Tracked result | Evidence |
| --- | --- | --- | --- |
| Reload tail, P38 | 1 shot, type `0x13F6`, clip 8->7, linked P2 damage | Same; fresh marker origin and first motion agreed | A fire 2 frames after reload refill produced no shot/damage in both modes. The post-tail shot then passed. |
| Empty fire, P38 | Final round consumed clip 1->0; immediate second press added no shot/damage | Same; no candidate constructed | P38 auto-reload began after the empty attempt. The transition is recorded separately from shot construction. |
| Switch during reload, P38 | 0 shots, 0 damage; slot/ID 0->1 | Same | The reload was interrupted by a native switch without creating a candidate. |
| Scoped fire, ID 5 | 2 shots, type `0x13F6`, clip 5->3, linked P2 damage | Same native behavior | Both tracked samples stayed native because the ordinary family guard rejected the hidden-scope state. |
| Recoil follow-up, P38 | 1 shot after recoil, no P2 damage | Same; marker sequence advanced and converted origin/first motion agreed | The view was turned away so the recoil-specific projectile did not merge with a P2 hit. |
| Load recovery, P38 | 1 shot, clip 8->7, linked P2 damage | Same | Tracked load generation advanced 6->7 and `loads` advanced 6->7 before the recovered shot. |

The non-fallback tracked rows reported zero rendered-origin error and zero
first-motion origin error at the recorded precision. Normalized axis cosines
were `1.0`. Reload-tail and load-recovery target-ray misses were `0.43` and
`0.51` world units. Recoil follow-up intentionally used no target ray because
the native view was turned away.

## Dependencies

The all-13 damage gate is the completed W5.3e desktop receipt rather than a
repeated conversion matrix:

- [preservation receipt](../../vr/proof/weapon-preservation-receipt.json)
- [preservation evidence](WEAPON_PRESERVATION_EVIDENCE.md)
- [shot-family receipt](../../vr/proof/weapon-shot-families-receipt.json)

That receipt covers all 13 IDs, native types, per-shot ammunition, shotgun
spread/RNG, linked damage and the five ownership/freshness controls. W5.4 adds
state-transition behavior on top of that accepted contract.

## Reproduction

```powershell
python vr/tools/probe_weapon_combat_states.py `
  analysis/vr-baseline/combat-states-final-20261027d `
  --proof vr/proof/weapon-combat-states-receipt.json
python -m unittest discover -s vr/tests -p 'test_*.py'
```

Focused runs use `--mode native|tracked --cases <name>`. A focused run cannot
publish a full W5.4 proof.

## Limits

- The scoped state has no fresh animated viewmodel marker and therefore remains
  a recorded native fallback. Do not treat it as a converted scoped shot.
- The recoil follow-up validates moving-tip conversion and first integration
  while turned away; P2 impact is covered by reload-tail and scoped-fire.
- This is synthetic copied-MP desktop evidence. Live NPC/SP isolation, physical
  attachment, headset use and operator-confirmed barrel-to-impact alignment
  remain open.
- No runtime C source changed for W5.4. The proof uses executable
  `8d0db60626bd516e91a342f648b22579e07b7ad3339ac104637774e1a71bc20d`.
