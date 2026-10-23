# Same-Checkpoint Stereo View Evidence

Date: 2026-10-24

This note records the first full-scene Underground pair with depth-dependent
motion from one frozen guest checkpoint. It is diagnostic evidence for the
frame-render replay and does not claim OpenXR support or 6DoF acceptance.

The fixed integer offset described here is retained as historical evidence.
The later full `PSXModRenderView` and PGXP projective path supersedes it; see
[PGXP_RENDER_VIEW_EVIDENCE.md](PGXP_RENDER_VIEW_EVIDENCE.md).

## Result

The accepted path replays the guarded frame render at `0x80053BB4` inside
`psx_mod_render_stereo()` and installs a scoped camera-space offset with
`psx_mod_render_view_offset()`:

- zero offset: complete courtyard, byte-identical left/right images;
- `X = -24` for the left eye and `X = +24` for the right eye: complete
  courtyard, non-identical images, visible world parallax;
- the runtime reports the same guest cycle for both eyes of each pair;
- comparison of fixed scene regions shows more motion near the camera than in
  the distant background.

The production runtime still does not enable this path by default. It is gated
by `MOHU_VR_STEREO_PROOF=1` and `MOHU_VR_EYE_VIEW_OFFSET=1`.

## Reproduction

The run uses the isolated slot-0 save and an OpenGL diagnostic build:

```powershell
$env:PSX_LOAD_SLOT = '0'
$env:MOHU_VR_STEREO_PROOF = '1'
$env:MOHU_VR_EYE_VIEW_OFFSET = '1'
$env:MOHU_VR_EYE_OFFSET = '0'   # zero control

.\build-vr-diagnostic\Medal_of_Honor_Underground_Recompiled.exe `
  --game (Resolve-Path 'analysis\vr-baseline\game-interp.toml').Path `
  --headless-opengl --no-launcher --debug-port 4392 `
  --memcard-dir (Resolve-Path 'analysis\vr-baseline\saves').Path
```

Capture the next complete pair through the debug server:

```text
stereo_dump path=C:\Users\titan\Desktop\Github_Projects\Mine\Medal-Of-Honor-Underground-PSX-Recomp\analysis\vr-baseline\view-offset count=1
```

Repeat the launch with `MOHU_VR_EYE_OFFSET = '24'` for the stereo pair.
The save passes through a black load transition. The first capture in the
verified run was black and was rejected; arm the retained capture only after
the courtyard is visible.

## Retained images

| Image | SHA-256 |
| --- | --- |
| [zero left](../../vr/proof/stereo-view-zero-left.png) | `10ad3e8fbebe500c0d665b2eab2d509ecd012d44c96e4a6ab6d009ecbb11ebd1` |
| [zero right](../../vr/proof/stereo-view-zero-right.png) | `10ad3e8fbebe500c0d665b2eab2d509ecd012d44c96e4a6ab6d009ecbb11ebd1` |
| [offset-24 left](../../vr/proof/stereo-view-offset24-left.png) | `2b343437145eafbb5c83fc80fa2606d7068ed7ac5b8708508ef40ee722b8136b` |
| [offset-24 right](../../vr/proof/stereo-view-offset24-right.png) | `2a851f38d0849b0f2717f15dcde0535c39f85c66b89c0f97af8d210197dbfa11` |

Side-by-side receipts:

- [zero control](../../vr/proof/stereo-view-zero-sbs.png)
- [offset-24 stereo](../../vr/proof/stereo-view-offset24-sbs.png)

The zero control has zero differing RGB pixels out of 122,880. The offset pair
has 94,282 differing pixels (76.7% of the frame), with per-channel mean absolute
differences of `15.88`, `14.83`, and `15.58`.

## Depth-dependent motion

Horizontal block matching used the same left/right image pair. Positive values
are the shift of the right image relative to the left:

| Region | Frame ROI `(x0,y0,x1,y1)` | Best horizontal shift |
| --- | --- | --- |
| Far left/middle architecture | `(80,24,470,72)` | 5 px |
| Mid courtyard | `(130,74,500,132)` | 4 px |
| Near floor | `(70,140,390,205)` | 8 px |
| Right wall | `(250,55,500,120)` | 5 px |

These measurements are block-matching observations, not a continuous depth map.
They establish that the motion is scene-depth dependent rather than a uniform
screen-space translation. The nearby floor moves three pixels more than the
sampled far architecture.

## Runtime receipts

Zero-offset run:

```text
attempts=9299 pairs=1036 failed=0 status=0
eye_cycles=[11883049628,11883049628]
eye_view=[[0,0,0],[0,0,0]]
capture pair_id=5739 guest_cycle=7872983521
```

Offset-24 run:

```text
attempts=15819 pairs=1771 failed=0 status=0
eye_cycles=[19244997734,19244997734]
eye_hashes=[b92f3e6cca112616,b92f3e6cca112616]
eye_view=[[-24,0,0],[24,0,0]]
capture pair_id=11729 guest_cycle=14635454116
```

The offset-24 run used `PSX_RENDER_PASS_VERIFY=1`. `render_pass_stats` reported
3,542 completed passes, 3,542 verification checks, zero mismatches, zero
aborts, zero watchdogs, zero VRAM leaks, and zero dropped device stores. The two
eyes report equal guest cycles and equal state hashes.

## Rejected controls

- Replaying the frame driver at `0x8006D65C` still does not reveal a usable
  visible list.
- Applying the TRX offset at every level-transformer entry with
  `MOHU_VR_EYE_OFFSET_ALL_SPANS=1` produced a black pair.
- Submitting the prebuilt OT without regenerating geometry remains
  byte-identical and is only a submission/clear control.

The successful seam is the frame-render replay, not the frame driver or the
OT-only walker.
