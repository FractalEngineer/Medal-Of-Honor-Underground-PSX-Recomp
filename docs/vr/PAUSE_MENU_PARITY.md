# Native pause-menu port

Updated 2026-10-29. A7 implementation and desktop/null-HMD validation were
completed on 2026-10-28; the operator now confirms SP pause in the headset.

The operator personally tested the activated clean image and reports “pause
menu is ok.” SP pause functional headset smoke is accepted (A7a). This does
not assert instrumented performance, exhaustive menu/comfort cases or an MP
physical test. Do not repeat the pause port or make MP acceptance gate the SP
alpha. Current work is [performance](PERFORMANCE_NEXT_STEPS.md).

## Reference and local binding

Reused the first game's `vr_scene_entry` explicit native pause-state decision,
`vr_native_surface_mode`/native menu plane and `moh_vr_menu_input_map` behavior.
The existing Underground mapper already provides Start, D-pad, Cross confirm
and Triangle back. No new menu renderer, UI framework, guest pause system or
controller mapper was introduced.

| Mode | Native pause word | Enter writer | Native reader / branch |
| --- | --- | --- | --- |
| SP | `0x800A70F0` | `0x8006EA0C` | `0x8006E95C` / `0x8006E964` |
| MP | `0x800A0A84` | `0x80064AC4` | `0x800649C8` / `0x800649D0` |

Copied-fixture Start traces prove `0 -> 1 -> 0` through native code, rather
than a host button latch. Seven exact reader/writer instruction words guard
each overlay generation; unknown code or values outside 0/1 decline the override.
SP's other toggles at `+0x7134/+0x9780/+0x9784` and MP audio toggles at
`+0x31F0/+0x31F4` were observed but are not used as pause state.

## Presentation and input

While native pause is set, route controllers through the existing menu mapper,
stop P1/world eye replay and activate `psx_mod_openxr_native_surface`. The
existing framework captures the **fresh canonical native present** and submits
it to both eyes as a head-relative quad. XR tracking/submissions remain live.
No retained stereo gameplay image, hand transformation, HUD stripping or laser
replay obscures the menu. Native pause artwork/selection/simulation behavior is
unchanged. Resume disables the native plane and resumes fresh stereo gameplay.

This adapts the reference's existing native menu-plane path rather than copying
its SP-only `g_menu_flat` identity-eye replay verbatim. Underground's MP P1-only
scene replay excludes the enclosing native pause artwork. Using the full fresh
native present preserves it in both SP and MP with the already available quad
API. Default placement remains 2 m distance / 2 m width. No framework change,
codegen identity change, mod-memory allocation or save conversion is required.

`MOHU_VR_PAUSE_MENU=0` is a diagnostic opt-out. It is not the shipping default.
Flat mode without the VR plugin path retains native presentation.

## Validation

`vr/tools/probe_pause_menu.py` copies original saves, drives synthetic XR action
samples through the normal controller callback, and records native flag writes,
pad bytes, screenshots, restoration counters and XR submission metadata.

- Both SP slot 3 and MP slot 1 pass two pause/navigation/resume cycles, including
  Start resume and Cross/Continue resume.
- Right/left menu navigation yields D-pad bits with all analog axes centered;
  focus loss releases buttons and sticks. Screenshots confirm Continue/Quit
  selection changes. Gameplay stereo pairs stop while paused, as intended.
- Both modes pass loading the copied gameplay state while paused, returning to
  unpaused state and fresh stereo pairs without changing the source save.
- Null-HMD XR controls show fresh `native_submitted` growth while paused,
  `submitted_source=2`, `submitted_layer=2`; resume returns to stereo source/layer
  1. Zero XR failures and zero rollback mismatches are recorded during controls.
- No-XR controls exit the game with code 0. Null-HMD runs use the existing
  restore-protected `run_vr.ps1 -Headless` launcher and record its exit separately
  from the child; launcher exit 0 alone does not certify the child's exit code.
- 123 Python tests pass; the strict C menu fixture covers both mode contracts,
  wrong/stale overlay words, invalid state and the existing idle fallback.
  Diagnostic C compiles with strict warnings.

Source/fixture/binary/raw evidence hashes are retained in
[pause-menu-parity-receipt.json](../../vr/proof/pause-menu-parity-receipt.json).
Raw files remain under the corresponding `analysis/vr-baseline/pause-*` folders.

Reproduction (diagnostic build required; run outside the sandbox):

```powershell
python vr/tools/probe_pause_menu.py analysis/vr-baseline/<fresh-output> --mode sp
python vr/tools/probe_pause_menu.py analysis/vr-baseline/<different-output> --mode mp --headless-xr
```

The second form uses SteamVR's null HMD, restores original SteamVR settings and
owns its processes. `--xr` without `--headless-xr` is a physical-runtime option;
use it only for an authorized headset session. Desktop and null-HMD results do
not prove per-eye physical comfort or every native menu page's behavior.

## A1 exit triage

All six physical batch reports (MP1-4, SP laser off/on) record
`reason=atexit`, `exit_origin=sdl_window_close`. Their nonzero Windows exit codes
remain a teardown defect, but these reports do not show an active-play exception.
Do not hold all alpha ports behind a new broad crash hunt based only on those
codes. S5 stays open for a real production physical close returning 0.

## Continuation

Next implementation is A2: compare the first game's preserved authored animated
basis with Underground's normalized per-ID calibration at the known pose seams;
fix upright grenade grip and retained StG hand, then verify the reported high-shot
and scale cases. A4 exact laser and A5 native HUD remain direct ports. A short
operator SP pause check has now passed. The earlier SP/MP physical requirement
is superseded by the current SP-only release scope; exhaustive edge cases stay
separate from that accepted functional smoke.
