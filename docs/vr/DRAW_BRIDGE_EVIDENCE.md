# Scene Draw Bridge Evidence

Source capture:

```text
build-vr-diagnostic/overlay_captures.json.d/536B5A9970274FF3.json
base     = 0x8008C000
entry    = 0x80090760
end      = 0x800911D4
size     = 0x00000A74 (2676 bytes)
sha256   = eef90ff046d1d666d7e1564e8c20635b45d15f4bb391aae2d3e43feb2b40ce9c
fnv1a    = 0x65089EA3
```

This is a static and live-capture classification, not a camera-structure
result. The runtime guard hashes all 669 instructions before registering the
read-only diagnostic entry hook.

Live entry confirmation:

```text
role = scene draw bridge
entry = 0x80090760
ra    = 0x800919BC
a0    = 0x800F130C
a1    = 0x801FBD20
a2    = 0x00000000
a3    = 0x00000000
```

The caller is `0x80091854`. The call site is `0x800919B4`, with the return
address in the following branch instruction. The dispatcher body is 840 bytes
and has its own byte guard:

```text
entry    = 0x80091854
end      = 0x80091B9C
sha256   = 2db16d3a7990988d5f6424e39643ad22bd73724063094542d1a6ccedecdb5beb
fnv1a    = 0x248E3C95
```

The dispatcher is live-confirmed with:

```text
entry = 0x80091854
ra    = 0x80091420
a0    = 0x800F130C
a1    = 0x800A82E0
a2    = 0x00000000
a3    = 0x000000C0
```

Its caller is the 1,204-byte entity render entry at `0x800913A0`, which calls
the dispatcher at `0x80091418`. That function also has alternate dispatch paths,
so its caller trace is needed before treating it as the frame-level replay
entry.

```text
entry    = 0x800913A0
end      = 0x80091854
sha256   = 241c6c6cfbcf041f8f79d6bc3bc61ccf366976304edc63ea8a0321fe942cd21c
fnv1a    = 0x64BAD0BB
```

The entity render entry is live-confirmed from a 180-byte wrapper at
`0x80079AF8`, with return address `0x80079B50`. The wrapper calls the entity
entry at `0x80079B48` and also has a second call site at `0x80079CD4` from a
different terminal block, so it is a render-list wrapper rather than the frame
root.

```text
entry    = 0x80079AF8
end      = 0x80079BAC
overlay  = 0x80079000
sha256   = 6b72ff1166aae1c14992f3cd63e60c756bc462b190dd43e9c0989c0d0ec49ea5
fnv1a    = 0xB77A81DB
```

The wrapper is live-confirmed from `0x80076A50`, with return address
`0x80076B90`. The call at `0x80076B88` passes the player pointer and a render
context. The parent function inspects actor flags before selecting this render
path, so it is classified as an actor render entry rather than a scene root.

```text
entry    = 0x80076A50
end      = 0x80076C28
overlay  = 0x80076000
sha256   = 0ed8b6873354f331c0e723d5548107fec12bb0edaf587507e782868e144b63c0
fnv1a    = 0xD06C70C5
```

The actor render entry is live-confirmed from `0x8008AB84`
(`$ra=0x8008AC60`). This wrapper reads `object+0x39C`, matching the verified
player input offset, and calls the actor render entry at `0x8008AC58`.

```text
entry    = 0x8008AB84
end      = 0x8008ACE4
overlay  = 0x8008A000
sha256   = f30566c203a64d8da1a36409d1ebf9e5c74c9c2d7a747e2d32aee5f441a46c5b
fnv1a    = 0xED5849B4
```

The return address `0x8008AC60` follows an indirect `jalr` in `0x80078E08`.
The object supplies its callback through `object+0x384`, so the apparent caller
chain is a vtable dispatch, not a direct call. The 436-byte dispatcher is the next
trace boundary:

```text
entry    = 0x80078E08
end      = 0x80078FBC
overlay  = 0x80078000
sha256   = ccc88e83a8993e95d7237f2a93398dff1c897566315a0c4e097bde413e94c2bc
fnv1a    = 0x36AC70BA
```

The actor update dispatcher is live-confirmed from `0x80053BB4`
(`$ra=0x80053C70`). That function performs the frame render sequence:

```text
0x80053D4C   scene render setup
0x800976D0   conditional world pass
0x8009865C   conditional world pass
0x80070898   render environment
0x8006B64C   display projection setup
0x80078E08   actor update dispatcher (scene pointer)
0x8008F9F4   player render entry
0x80053CFC   render wait helper
```

This is the first measured whole-frame boundary, but the wait helper is inside
the function's normal return path. A stereo callback must reproduce the draw
calls and omit `0x80053CFC`, rather than replaying the enclosing function
unchanged.

```text
entry    = 0x80053BB4
end      = 0x80053CA4
overlay  = 0x80053000
sha256   = fe5a91df89f151ce6c369fee46339f6462baee3b3af9bb8f9fec6940c8173ead
fnv1a    = 0xA2BCF1A9
```

The replay callback must finish with the game's `DrawOTag` submission. The
reference `0x800172D8` matched Underground `0x80018B50` at 0.932 normalized
similarity. The target body is 26 instructions and is guarded by its exact
104-byte hash:

```text
entry    = 0x80018B50
end      = 0x80018BB8
container = main EXE 5c4566b7...
sha256   = 748ee5eec31244e850fb16fc7e893a00ef7a8213e83af433fc93ad782f8ca12c
fnv1a    = 0x4DDF2EE0
```

Without this call the replay executed about 500k guest cycles per eye but
submitted zero GPU primitives, so the captured eyes were identical.

The first replay callback reproduced the frame-render calls plus `DrawOTag`.
That submitted about 1,000 primitives per eye, but the ordering table had already
been built before the callback, so the two images were still identical. This
established that the eye transaction must start above the frame-render function.

The next opt-in experiment replays the guarded frame driver at `0x8006D66C`.
Its call to the frame renderer is at `0x8006DB04`, and its 1,496-byte body is
guarded by:

```text
entry    = 0x8006D66C
end      = 0x8006DC44
sha256   = 2df855c8a87f31014db7c5f2f58fd4e088a46794d6cacb8b3d821de708caa582
fnv1a    = 0x7C33671C
```

This replay is intentionally opt-in (`MOHU_VR_REPLAY_FRAME_DRIVER=1`).

The first driver replay reached the verified wait and was aborted there. The
wait is now completed through the trusted entry hook only while an eye is
active. A subsequent run reached `0x8004356C`, a 1,588-byte post-render update
that reads timer device `0x1F801C0C`; that function is likewise skipped inside
the replay because its work is not part of the draw image.

```text
entry    = 0x8004356C
end      = 0x80043BA0
sha256   = 8ac1ec6e9c97de99cd3bfab4642ac67058153ec939e33bbce61cbf3c09c0f703
fnv1a    = 0x5B83DE00
```

## Driver replay result

With `0x8009D828` completed early and `0x8004356C` skipped only inside the eye
transaction, the frame-driver replay completed without watchdog or device-read
aborts. It published 180 pairs in the sampled run and recorded four
level-transformer entries per eye.

The resulting left and right PNGs were nevertheless byte-identical. This is a
negative result for the current injection location:

- Geometry generation before the frame driver is outside the eye transaction.
- The driver replay submits a prebuilt ordering table rather than regenerating
  the visible level packets.
- Applying `TRX +/- 24` at the level transformer during this late replay does
  not change the submitted image.

The runtime stereo transaction, wait bypass, `DrawOTag` path, and per-eye GPU
submission are therefore proven. Parallax is not yet proven in the simultaneous
pair. The next required boundary is the function that generates the visible
level geometry before `0x8006D66C`.

## What the function does

The function receives a scene-like object in `$a0` and a geometry table in
`$a1`. It:

1. Saves the complete GTE RT/TR control state into its scratch allocation.
2. Calls the verified entity transform at `0x80093830` from `0x800908DC`.
   The observed return address is `0x800908E4`.
3. Loads a composed 3x3 matrix from the scratch block into GTE RT1..RT3 at
   `0x80090910..0x80090950`.
4. Runs three RTPS operations per draw pass.
5. Builds packet data over `0x80090B98..0x8009115C` and restores its saved GTE
   state before returning.

The write trace's `$ra = 0x800908E4` therefore identifies the verified entity
transform call site. It does not identify the camera simulation that produced
the matrix. The scratch writes are renderer output.

## Current boundary

The function is a useful renderer/draw bridge and a source of caller evidence,
but it is not yet the whole-scene replay callback required by simultaneous
stereo. A two-eye implementation must first identify the frame-level caller and
prove that replaying that caller reproduces the draw transaction without
advancing guest time.

The known `MOHU_VR_LEVEL_OFFSET_X` path remains preferable for a first
camera-space stereo proof because it is already bounded by the verified level
transformer and render wait.
