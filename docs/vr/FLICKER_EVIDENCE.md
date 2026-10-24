# Alternating Black-Pair Flicker Evidence

Date: 2026-10-24

This note records the cause and correction of the black flashing visible in
both the game window and the headset window after the world-scale correction.
The operator confirmed the corrected build no longer flashes.

## Symptom and counter control

Head tracking and world scale were correct, but the image alternated with pure
black. The runtime counters initially rejected the same hypothesis used for the
reference game's overload flicker:

- 622 complete pairs;
- zero stereo sheds;
- zero empty OpenXR submissions;
- zero XR failures;
- stable 238.806 effective game units per metre.

A second six-second null-HMD run produced 241 pairs and 482 render-pass
verification checks with zero mismatches, still with zero empty submissions.
The problem was therefore the content of individual complete pairs.

## Pair-level isolation

The diagnostic build can write a bounded stereo-pair sequence when
`MOHU_VR_STEREO_DUMP_DIR` names an existing directory. The first capture wrote
60 pairs and gave an exact alternating result:

- odd pairs: complete courtyard with eye mean RGB about `53.7, 52.8, 62.1`;
- even pairs: pure black, exactly `0, 0, 0`.

That is 30 black pairs out of 60. Both alternating OT bases contained non-empty
lists, and the OT-only control showed the same alternation. This ruled out frame
render regeneration and scene-list production as the cause.

The game alternates its native display origin between `y=0` and `y=240`. The
eye replay followed that display origin. The replayed packet coordinates are
rooted at the `y=0` scratch surface, so the `y=240` transaction cleared a
rectangle that the eye geometry did not draw. The captured result was a valid,
complete, pure-black pair.

## Correction

Both eyes now replay into the same `y=0` scratch buffer regardless of which
native display buffer is current. The stereo render transaction backs up and
restores that rectangle, so the guest's visible VRAM content is unchanged.

This does not copy, advance, or rewrite guest state. It only selects the
rollback-protected eye-render target.

## Final receipts

Final 60-pair sequence:

- 60 left images and 60 right images;
- zero black left images and zero black right images;
- left mean minima and maxima identical across the sequence;
- right mean minima and maxima identical apart from render rounding;
- 93,415 changed pixels between the first left/right pair, confirming the
  runtime IPD view was still applied.

Final verification run:

- 241 complete pairs;
- 482 render-pass checks;
- zero verification mismatches;
- zero sheds, empty submissions, or failures.

Final compositor series:

- eight consecutive SteamVR null-HMD dumps;
- eight nonblank compositor images;
- eight nonblank application-layer images;
- zero rejected dumps;
- `clean: true` in `capture-series.json`.

The PGXP slot-2 fixture still loads under the unchanged execution identity.
No guest state, savestate header, disc, or original save was modified.
