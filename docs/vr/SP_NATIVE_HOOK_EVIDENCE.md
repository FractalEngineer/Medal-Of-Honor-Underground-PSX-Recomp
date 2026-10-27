# Native hook and SP cadence result

Date: 2026-10-28. Scope: desktop only.

This closes R4/R4b. Cached native overlays now execute the existing VR callbacks
and pass stereo/weapon parity before any throughput comparison. It does not close
R4 performance as a headset claim or change R5-R7.

## Instrumentation

`game.toml` declares 24 entry hooks and 11 guarded instruction sites derived from
`vr/underground/vr_diagnostic.c` and the verified engine map. The generated
main-EXE C now contains the four static entry forwarders:

- `0x80013B40`
- `0x80013EB4`
- `0x80018B48`
- `0x80018BB8`

The remaining callbacks are emitted into the native overlay codegen. At runtime
the plugin reports `function=24 instruction=11`. The diagnostic
`PSX_NATIVE_BLOCK` path is not the shipping solution.

## Desktop controls

The copied SP slot 3 and copied MP slot 1 were used. All controls required
`--production-config --require-native`; the probes record native-call deltas
from `overlay_native_ring` rather than treating counters or FPS as proof.

| Control | Result |
| --- | --- |
| SP baseline | Pass; 96/96 gun vertices, 142/142 arm masks, 2 flash banks, clean rollback |
| SP turned head/hand + reload | Pass; 96/96 gun vertices, source state unchanged |
| SP close hand | Pass; 96/96 gun vertices, 142/142 arm masks |
| SP tracking loss | Pass; native gun-only fallback, no aimed shot, clean shutdown |
| SP out of view | Pass; 0/0 visible gun and hidden owned flash |
| Focused MP P38 | Pass; both-eye pairs, clip 8 to 7, P2 health 32 to 31.25, recovery pair 263 |

The SP controls used executable
`ed6f2664880ddc7fc2df057c9439aeb4e35aec2d0ac571ab720f863de78f145c`
with debug tools on. All reported zero eye failures and zero rollback mismatches.
The MP run used the native resolution surface and 1,106 rollback checks.

## Matched cadence

The production comparison uses one release binary
(`6c39318c2fb27c7574ab90417581beb32a9ff8987c0563a3e6c216f9a063cbf8`),
copied SP slot 3, hidden SDL, 1080p, no XR, no trackable hand, no screenshots,
VERIFY off and the common guest-frame window `300:900`.

| Metric | Native cached | Interpreter config |
| --- | ---: | ---: |
| Guest frames in window | 600 | 600 |
| World-pair cadence | 30.00/s | 29.19/s |
| Wall time | 9,943.5 ms | 9,897.8 ms |
| Guest work | 7,979.9 ms | 9,760.2 ms |
| Dirty instructions | 379,200 | 133,806,583 |
| Overlay native calls | 2,807,918 | 0 |
| Overlay interpreted calls | 18,600 | 0 |

The direct `[BENCH]` window is effectively unchanged in wall time (0.46%
slower in this native sample) and uses 18.2% less measured guest work. The
quiet-window pair cadence shows a 2.78% increase, but both modes are close to
the same 30-pair pacing limit. These are bounded scene results, not a uniform
FPS gain.

The native path requires a warm overlay cache. A cold run may spend its opening
seconds interpreting and compiling; `--require-native` prevents that run from
being accepted as a native result. The check is intentionally stricter than
looking only at flat FPS or stereo counters.

## Verification

Final sources/tools and raw hashes are in
[sp-native-hooks-receipt.json](../../vr/proof/sp-native-hooks-receipt.json).
The production build is restored to `PSX_DEBUG_TOOLS=OFF`. Source saves and
preferences remained unchanged. No headset was started.

R5 remains open but is paused on fixture selection. The available slot 0/2/3
captures do not reproduce the operator's street-wall/fog case, so they cannot
validate a producer or correction. Do not tune draw distance or FOV constants.
The next independent desktop task is R6 linked live SP NPC impact.
