# Static-world decoder (M1)

Created: 2026-10-30. Status: **geometry/topology decoder landed; materials and
reference captures remain open.** This is the first M1 deliverable for
[PERFORMANCE_ARCHITECTURE_PLAN](PERFORMANCE_ARCHITECTURE_PLAN.md).

## Inputs

The decoder reads the same arena layout the raycast reader uses, from the real
SP packet-builder inputs:

| Field | Source | Use |
|---|---|---|
| Visibility tree root | level / arena (caller of `80010CF0`) | depth-first leaf walk |
| Node AABB | `+0..+10` int16 | bounds only; no culling |
| Leaf face count | `+12` int32 | `0` = interior, `>0` = leaf strip count |
| Visibility masks | `+16`, `+20` | optional, caller-supplied |
| Child / face-list word | `+24`, `+32`, `+28` | interior children or leaf strip |
| Vertex table | level `+0x2C` | 8-byte `int16 x,y,z` vertices |
| Vertex count | level `+0x3C` | bounded to 8192 |

Strip list: 8-byte base triangles, 4-byte extensions, `0x1fff` terminator.
Base/index masking and extension winding (`bit 15`) match
`vr/underground/raycast.h`. Extension bits 13–14 are retained as render flags.

## Output

`MohuWorldMesh` owns a copied vertex table and a deterministic triangle array.
Each triangle carries its three vertex indices, the guest word that introduced
it, the raw base words, the extension word, winding and render flags. Bounds are
reported twice: referenced-vertex bounds and the accepted leaf-box union.

Decoding is complete for a root: leaves beyond the native camera view are
included, nothing is projected or culled, and no GPU/VRAM state is touched.

## Resource cache

`MohuWorldMesh` records the contiguous source range it consulted
(`source_start`/`source_end`) and an FNV-1a fingerprint of that range.
`mohu_world_cache_acquire` keys on the request fields plus generation — pose
and screen coordinates are absent — and behaves as follows:

| Case | Result |
|---|---|
| Same request, same `snapshot_serial` | reuse, no reads (`hits`) |
| Same request, new snapshot, fingerprint matches | reuse after one span hash (`validations`) |
| Same request, new snapshot, fingerprint differs | free, re-decode (`stale`) |
| Different generation/identity | decode into another slot (`misses`) |
| Decode rejects | entry stays invalid; status returned |

The fingerprint range is the bounding range of consulted bytes, so bytes in
gaps between scattered reads also participate. That is conservative: unrelated
changes can force a re-decode but never a stale reuse. It is revalidated at
most once per native snapshot, never per eye. `*mesh` is borrowed until the
next acquire/reset/free.

## Materials are not decoded

`materials_decoded` is always `0`. Raw tokens are retained so the next step can
map them without re-walking guests. Textured output must refuse this mesh:
the packet/preflight/subdivision material fields have not been captured and
mapped yet. Do not infer materials from the 8-byte index words — they contain
no material fields.

## Per-eye selection

`vr/underground/world_select.{h,c}` runs the framework's conservative
`psx_vr_box_visible` over each triangle's world AABB, with an identity model
transform and the caller's eye rotation/translation (`+Z` forward). It returns
candidate triangle indices in decode order, plus `tested`/`outside`/`unknown`
counts.

- OUTSIDE is only returned when all eight corners are outside one plane, so a
  potentially visible face is never dropped.
- UNKNOWN (non-finite, saturated view, malformed box) is **kept** and counted.
- A candidate count above the caller's capacity returns
  `triangle_budget` with `count == capacity`; it does not silently truncate.

Selection is a host-side reference/fallback for the eventual shader path, not
a claim of native per-face culling equivalence.

## Per-eye projection (M2 groundwork)

`vr/underground/world_project.{h,c}` transforms each vertex with the eye
rotation/translation, clips wholly-behind triangles, clips crossing triangles
to at most four vertices, and projects with `sx = cx + fx*x/z`,
`sy = cy + fy*y/z` (`+Z` forward). `mohu_world_eye_from_view` adapts the real
`PSXModRenderView` using the same Q16 focal/centre-delta and Q12/precise rules
as `frustum.h`, so there is one convention.

`mohu_world_drawlist` then fan-triangulates the projected 3/4-vertex polygons
into screen-space triangles, preserving polygon order and flagging non-finite
points as degenerate. The full CPU chain is therefore
decode -> cache -> select -> project -> draw list.

This is a deterministic CPU reference/comparison path. It is not the GPU
renderer and does not yet carry textures, ordering, subdivision or PGXP
precision.

## Material leads (unverified — do not implement from this alone)

A static read of `80010CF0` shows a per-face loop that reads `half[face+6]`,
scales it by 12, adds a table base loaded from scratch `0x1F8003E8`, then
reads `word[+0]`, `word[+4]` and `half[+8]` into `gpr[20]`, `gpr[21]`, `gpr[1]`.
That is a plausible 12-byte face/material record. `gpr[23] = face + 8` is
established just before the `80011424` call, matching the documented `$s7`
face pointer. A second table at `gpr[27]+0xD8`/`+0xDC` and a 40-entry compare
at `0x80010F7C` are still unmapped.

None of this has been tied to packet output or verified against a capture, so
it is a lead for the next session, not a decoder field. The material mapping
still requires the captured fixture the plan demands.

## Rejections (atomic, named)

`argument`, `vertex_table`, `tree_root`, `node_bounds`, `leaf_count`,
`leaf_budget`, `strip_span`, `strip_terminator`, `strip_budget`,
`vertex_index`, `tree_budget`, `triangle_budget`, `allocation`.

Every rejection frees the partial mesh and records the node/leaf, offending
word and detail. Faces are never silently dropped, and a cycle is stopped by
the 8192-node budget.

## Validation

`vr/tests/test_world_decode.c` (compiled and run by
`vr/tests/test_world_decode_fixture.py`) covers a two-leaf synthetic arena:
triangle order, extension winding and render flags, mask selection, rendered
bounds, deterministic re-decode, every rejection class, and the cache
(same-snapshot hit, fingerprint revalidation, unrelated-byte tolerance,
content invalidation, generation change, reset).

`vr/tests/test_world_select.c` covers identity/rotated/translated eyes,
conservative UNKNOWN retention, capacity overflow and argument guards.

`vr/tests/test_world_project.c` covers the view adapter (Q16/Q12/precise and
fallbacks), exact screen coordinates, whole-triangle rejection, four-vertex
near clipping, draw-list triangulation of triangles and clipped quads,
non-finite/malformed polygons, capacity overflow and argument guards.

Not yet demonstrated: a real captured arena, material mapping, subdivision
decisions and reference triangle counts.

## Next

1. Capture the real `80010CF0` material fields (packet/preflight/subdivision
   reads) into a mapping table and extend the decoder.
2. Compare decoded triangle counts/winding/bounds against a reference capture
   from the frozen slot-2 fixture.
3. Wire the decoder into a default-OFF native census so the real arena root and
   resource generation are recorded before the host renderer consumes it.
