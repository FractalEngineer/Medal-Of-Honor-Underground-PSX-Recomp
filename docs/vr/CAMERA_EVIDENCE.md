# Camera Evidence

Measured from the diagnostic build at slot 0 on 2026-10-23. This is
discovery evidence, not a camera hook design.

## Motion probe

The session was loaded from an isolated save copy, then given right-stick
rotation input through the debug input override.

| Check | Before | After |
| --- | --- | --- |
| Frame | 367 | 605 |
| GTE RT (control words 0-4) | changed | changed |
| GTE TR words 5-7 | zero | zero |
| GTE OFX/OFY/H | unchanged | unchanged |
| Scratchpad `0x1F800014..0x1F80004A` | baseline | changed |

The rotation changed the view matrix while translation registers remained
zero. This agrees with the reference game's camera-relative storage model.

## Write trace

A write trace over scratchpad `0x1F800000..0x1F800100` reported sampled writers
in the range `0x80090B98..0x8009115C`, with return address `0x800908E4`. The
producer is in the overlay loaded at base `0x8008C000`. Its owning function
boundary and caller contract still need disassembly before any hook is proposed.

The trace also exposed stable pointer-like arguments:

- `s4 = 0x800F130C`
- `s3`/`a2` pointed into the current scene matrix area near `0x80157D90`; the
  exact pointer varied with allocation and camera motion.

## GTE projection observation

At the sampled gameplay point:

```text
OFX = 0x01000000  (256.0 in 16.16)
OFY = 0x00780000  (120.0 in 16.16)
H   = 0x00000190  (400)
```

This is consistent with a 512x240 PSX display and the reference world
projection. It does not yet prove which guest function owns the camera.

## Open work

- Identify the camera matrix source and owner, rather than the scratch copy.
- Separate camera translation from player and entity transforms with a forward
  movement trace.
- Record the exact active overlay hash for `0x800908E4` before considering a
  hook.
- Do not register camera hooks from the pointer values above; they are runtime
  heap addresses and are not stable identifiers.
