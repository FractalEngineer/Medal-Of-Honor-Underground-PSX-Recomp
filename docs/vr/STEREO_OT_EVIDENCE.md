# Stereo OT and Frame-Entry Evidence

Date: 2026-10-24

This note records the diagnostic work that followed the byte-identical
frame-driver replay. Its negative controls remain rejected; the later accepted
same-checkpoint parallax pair is recorded in
[STEREO_VIEW_EVIDENCE.md](STEREO_VIEW_EVIDENCE.md). It does not claim OpenXR
support.

## Correct natural frame entry

The earlier replay called `0x8006D66C`, which is four instructions into the
natural function. The real entry is `0x8006D65C`:

```text
0x8006D65C  lui  r4, 0x800A
0x8006D660  lui  r3, 0x800B
0x8006D664  lw   r2, 0x70E8(r4)
0x8006D668  lw   r3, 0x9784(r3)
0x8006D66C  addiu sp, sp, -80
```

The guarded binding now covers `0x8006D65C..0x8006DC44` (1,512 bytes):

```text
sha256 = bc1f06d66e91b9f93337fc0cba511cc112e0d2d2043427aa5d385a3911b77cc0
fnv1a  = 0x7F07744E
```

The live slot-0 run reported:

```text
verified role=frame driver address=0x8006D65C
ra=0x800705EC a0=0xFFFF0000 a1=0x00000800 a2=0x00000000 a3=0x00000001
```

## Draw environment and OT

The main-EXE `PutDrawEnv` match is `0x80018BB8`, guarded over 192 bytes:

```text
sha256 = b626d04e62c37f78773d5c0d23d5585446aa24e1c2ec21c57196725390ebcdcc
fnv1a  = 0x232CC04B
```

`PutDispEnv` is `0x80018C78`, with a 0.984 structural match to the reference.

The frame context is `0x800A7138`. Its current draw environment is:

```text
ctx + 16 + 184 * index
```

At `index = 1`, the live DRAWENV clip fields were:

```text
x = 0
y = 240
w = 512
h = 240
```

The context stores an OT base pointer at `[ctx + 0x2218]`. In the sampled scene:

```text
at frame-render entry: base = 0x800A72E0, head = 0x800A7ADC
after frame driver:    base = 0x800A82E0
```

The head is `base + 511 * 4`. The first tag at the frame-render entry was
`0x000A8AD8`, which led through two empty buckets and then into packet memory at
`0x0013DFF8`.

## Clear and submission controls

Clearing the eye rectangle through the measured GP0 fill packet was effective.
A clear-only run produced two pure-black images:

```text
left extrema  = ((0, 0), (0, 0), (0, 0))
right extrema = ((0, 0), (0, 0), (0, 0))
```

The OT-only control walks the prebuilt 512-entry list and writes each packet's
command words to GP0 through a bounded diagnostic walker. With
`MOHU_VR_STEREO_OT_ONLY=1` and zero eye offset it rendered the complete
courtyard, HUD, and weapon:

```text
stereo_ot base=0x800A72E0 head=0x800A7ADC tag=0x000A8AD8
attempt=1 pairs=1 rendered=1 level_hits=0/0 view_apps=1/1 ot_words=18090
```

The left/right PNGs were byte-identical, as expected for zero offset:

```text
sha256 = 10ad3e8fbebe500c0d665b2eab2d509ecd012d44c96e4a6ab6d009ecbb11ebd1
```

Retained images:

- [left](../../vr/proof/stereo-otonly-zero-left.png)
- [right](../../vr/proof/stereo-otonly-zero-right.png)
- [side by side](../../vr/proof/stereo-otonly-zero-sbs.png)

The measured natural GP0 state packet is:

```text
E3000000
E403BDFF
E5000000
E100060A
E2000000
E6000000
```

This packet is reproduced before the eye fill and submission.

## Why the earlier pair was misleading

The earlier driver replay submitted the same prebuilt scene and could therefore
produce a convincing, full-scene image pair while never regenerating the visible
world vertices. A full image pair is not evidence unless it is shown to originate
from a fresh eye-specific draw.

Current negative results:

- Host render-view offset plus full driver replay: full scene, byte-identical.
- Direct per-eye TRX offset plus post-driver OT base: black pair.
- Frame-render replay plus clear: incomplete or replaced list, not stereo proof.

## Correction: scoped view offset on frame-render replay

The earlier host-offset result above was produced before the current
frame-render replay controls and did not isolate zero and signed offsets on
that path. A later run replayed the guarded frame render at `0x80053BB4` and
called `psx_mod_render_view_offset()` inside each eye transaction:

- `MOHU_VR_EYE_OFFSET=0` reproduced the full courtyard with a byte-identical
  left/right pair;
- `MOHU_VR_EYE_OFFSET=24` produced signed `-24` / `+24` camera offsets, a full
  courtyard pair, 94,282 changed pixels, and depth-dependent world motion.

This supersedes the old statement that a host view offset always submits an
identical full-scene pair. The driver replay remains rejected; the accepted
seam is the frame-render replay. See
[STEREO_VIEW_EVIDENCE.md](STEREO_VIEW_EVIDENCE.md) for images, hashes, runtime
cycles, and the zero-offset control.

The black driver/TRX control hashes to:

```text
ffc1aaa604e5364b25926033bfdb5b792c1ce06597681358d212c8c386a72aa5
```

The new OT base is not yet proven to own the visible world list. Do not submit it
as a stereo result.

## Packet producer trace

The write trace was armed over `0x0013DFE0..0x0013E030`. It reported writes from
the following producer PCs:

```text
0x80090D68  ra=0x800908E4  scene draw bridge
0x80090E6C  ra=0x800908E4  scene draw bridge
0x80090E98  ra=0x800908E4  scene draw bridge
0x80090EA8  ra=0x800908E4  scene draw bridge
0x80090EB8  ra=0x800908E4  scene draw bridge
0x8009104C  ra=0x800908E4  scene draw bridge
0x800110C4..0x80011334  ra=0x80011008  packet command writer
0x800140B0  ra=0x80091AC4  secondary packet writer
```

This identifies the renderer output writer, not yet the high-level caller that
starts the visible world generation before `0x8006D65C`.

## Next measurement

The next session should trace upward from the two producer clusters:

1. `0x800908E4`: caller inside the verified scene draw bridge.
2. `0x80011008`: packet-command writer called by the bridge output path.

The required result is a guarded natural entry whose per-eye replay writes a new
visible OT with different packet vertices and whose left/right PNGs have
depth-dependent, non-zero differences.
