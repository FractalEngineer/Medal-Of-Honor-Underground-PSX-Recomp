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
it, the raw base words, the upper 16 bits of the second base word as
`record_index`, the extension word, winding and render flags. Bounds are
reported twice: referenced-vertex bounds and the accepted leaf-box union.
`record_index` is captured evidence (below), not a material and not resolved by
the decoder.

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
map them without re-walking guests. Textured output must refuse this mesh: the
packet/preflight/subdivision material fields have not been captured and mapped
yet. The 8-byte index words carry vertex indices and `record_index`, not a
material descriptor.

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

## Captured packet/face inputs (2026-10-30)

The earlier static lead was correct about the addressing but wrong about the
payload. Two real captures (slots 2 and 5, three draws and 32 faces each)
prove the following; the receipt is
[`vr/proof/sp-world-capture-receipt.json`](../../vr/proof/sp-world-capture-receipt.json).

Method: `MOHU_VR_WORLD_CAPTURE` is a default-OFF diagnostic link-wrap build,
because the generated CPS bodies only call `psx_mod_function_entry` for the
`game.toml` list. `MOHU_SP_WORLD_CAPTURE=<file>` arms a bounded dump of the
`0x80010CF0` entry (`ra=0x8009A51C`, `a0=begin`, `a1=limit`, `s2=level`) and
the `0x80011424` entry (`ra=0x80011008`, `s7=face+8`). Normal builds do not
contain the wrappers; the arm callback and flush command are inert without the
environment variable.

| Native read | Captured value | Proven meaning | Status |
|---|---|---|---|
| `ra` at `80010CF0` | `0x8009A51C` | real caller return | confirmed |
| `a0`, `a1` | `0x80138390`, `0x80144FA7` | packet range, identical on both scenes | confirmed |
| `s2` level `+8/+0x2C/+0x3C` | sub/table/count | same layout the decoder reads (slot 2 draw 0: root `0x8010BA48`, 1444 vertices, table `0x8010FE4C`) | confirmed |
| `half[face+6]` | upper 16 bits of base word 1 | record index (e.g. `207`) | confirmed |
| `word[0x1F8003E8]` | runtime pointer, e.g. `0x801259BC` | per-draw record-table base | confirmed |
| table `+ index*12` | six 16-bit fields | per-face parameter record; packet body writes the low halves at packet `+0x38/+0x3C/+0x40` and the high halves through other fields after adding a base | structure confirmed |
| `gpr[27]+0xD8/+0xDC` | `0x0B`, `0x0` | read before the 40-entry compare at `0x80010F7C` | value captured, meaning open |
| texture page / CLUT / shading / semi-transparency | absent | not in the 12-byte record | open |

A second capture dumped `gpr[4]` at the face entry after `80011424` returned.
In slot 2 the three record words appear verbatim in the face packet at word
offsets 3, 6 and 9 for **20 of 32** captured faces, interleaved with words such
as `0x007B00E2` that look like packed UVs. Slot 5 matches only **3 of 32** and
uses a different packet layout, so this is a captured relationship, not a
universal one. No GP0 `0xE1..0xE6` draw-mode word appeared in the 96-byte
window, so texture page/CLUT stay unmapped.

**Correction:** the 12-byte record is not a material descriptor. Whether each
half is a UV, a color or another parameter is still unproven, so it is
deliberately not named. Do not use these fields to select a texture.

Still open: the packet/preflight fields that carry texture page, CLUT, shading
and semi-transparency, and a native reference count for culling/subdivision.

## Real-arena census (2026-10-30)

When capture is armed, the decoder runs once on the live root/table/count from
the first packet entry, with masks bypassed so every resident leaf is decoded.
Both scenes returned `status=ok` with no rejection:

| Scene | Root | Vertices | Nodes | Leaves | Triangles | Bounds min..max |
|---|---|---:|---:|---:|---:|---|
| slot 2 | `0x8010BA48` | 1444 | 203 | 134 | 1756 | `-904,-1829,961..2887,518,9137` |
| slot 5 | `0x8010C788` | 1307 | 237 | 155 | 1932 | `-6245,-2428,-9468..1760,-1248,-3988` |

With the global masks at `0x800B7490/0x800B7494` applied, slot 2 prunes to
25 leaves / 324 triangles and slot 5 to zero leaves. The masks are
view-specific, so a complete census must bypass them; the per-eye selector is
the place to apply visibility.

This proves the tree/strip walk terminates and covers the resident leaves on
real data. It is **not** a native culling or subdivision comparison.

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
triangle order, extension winding and render flags, `record_index` from the
upper half of the second base word, mask selection, rendered bounds,
deterministic re-decode (including struct padding), every rejection class, and
the cache (same-snapshot hit, fingerprint revalidation, unrelated-byte
tolerance, content invalidation, generation change, reset).

`vr/tests/test_world_select.c` covers identity/rotated/translated eyes,
conservative UNKNOWN retention, capacity overflow and argument guards.

`vr/tests/test_world_project.c` covers the view adapter (Q16/Q12/precise and
fallbacks), exact screen coordinates, whole-triangle rejection, four-vertex
near clipping, draw-list triangulation of triangles and clipped quads,
non-finite/malformed polygons, capacity overflow and argument guards.

`vr/tests/test_world_capture_summary.py` covers the offline capture validator:
proven draw/face fields, six-half record layout, material fields staying null,
and refusals for a wrong record base, wrong index or missing header.

Not yet demonstrated: decoded triangle counts/winding/bounds against the real
arena, texture-page/CLUT mapping, subdivision decisions and textured output.

## Next

1. Map the packet/preflight fields that carry texture page, CLUT, shading and
   semi-transparency; the 12-byte record is not one of them.
2. Capture a native triangle/face count from the packet builder or OT and
   compare it with the 1756/1932 decoded triangles; the census proves the walk
   terminates, not that native culling/subdivision matches.
3. Wire the decoder into a default-OFF native census so the real arena root,
   record table and resource generation are recorded before the host renderer
   consumes it.
