# Stick grenade SP release evidence

Updated 2026-11-01. This is bounded synthetic-controller desktop evidence, not
a physical headset acceptance run.

## Implemented behavior

- SP stick grenade ID `10` now shares the measured SP thrown-release correction
  already used by petrol bomb ID `15`.
- The guard accepts only thrown type `0x13F3`, release ID `10` or `15`, a
  matching live viewmodel ID, fresh camera state, valid SP owner/input layout
  and exact throw/basis code hashes.
- The correction runs after the final native origin write and rebuilds the
  native angle, basis and collision geometry from the tracked controller.
- Multiplayer shot-family behavior is unchanged.

## Headless controls

The probe copied the operator's new slot 2 into a disposable directory and
loaded it in the diagnostic build. Source saves and preferences remained
unchanged. Each run consumed disposable-copy ammunition only.

| Controller yaw | Aimed releases | Tracking/other fallbacks | First native-motion delta |
| ---: | ---: | ---: | --- |
| -30 deg | 2 | 0 / 0 | `[38.25, 5.6875, -69.0625]` |
| 0 deg | 2 | 0 / 0 | `[67.625, 5.8125, -40.75]` |
| +30 deg | 2 | 0 / 0 | `[76.875, 5.6875, -1.4375]` |

The changing first-motion vectors exercise the controller-dependent release
path. They do not establish physical throw feel or collision outcomes.

Receipts:

- `analysis/runtime/stick-grenade-yawm30-20261101/receipt.json`
- `analysis/runtime/stick-grenade-yaw0-20261101/receipt.json`
- `analysis/runtime/stick-grenade-yaw30-20261101b/receipt.json`

## Remaining physical checks

- [ ] Throw the stick grenade through the normal launcher in a physical
  headset and confirm travel follows the controller/laser.
- [ ] Confirm collisions, fuse timing, explosion placement and comfort.
