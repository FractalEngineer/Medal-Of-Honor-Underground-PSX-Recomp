#ifndef MOHU_WORLD_SELECT_H
#define MOHU_WORLD_SELECT_H

#include "world_decode.h"

#include <stdint.h>

/*
 * Conservative per-eye candidate selection over a decoded static mesh.
 *
 * It keeps a triangle when its world AABB is not provably outside the eye
 * frustum. The framework's `psx_vr_box_visible` only rejects a box when all
 * eight corners are outside one plane, so the result never drops a possibly
 * visible face. Malformed/saturated input is reported as UNKNOWN and KEPT.
 *
 * This is a host-side reference/fallback, not the eventual shader path. The
 * caller supplies the same eye rotation/translation it gives
 * `psx_vr_box_visible`: row-major, +Z forward in eye space. Vertices are the
 * level's camera-relative coordinates, so the model transform is identity.
 */

typedef struct {
    double rotation[9];     /* world -> eye, row-major */
    double translation[3];
    double fx, fy, cx, cy;
    int width, height;
} MohuWorldEyeView;

typedef struct {
    uint32_t count;         /* indices written, in decode order */
    uint32_t tested;
    uint32_t outside;
    uint32_t unknown;       /* UNKNOWN results are kept, never dropped */
} MohuWorldSelection;

/* Fills `indices` up to `capacity`. Returns MOHU_WORLD_REJECT_ARGUMENT for an
 * invalid mesh/view and MOHU_WORLD_REJECT_TRIANGLE_BUDGET when more candidates
 * exist than `capacity`; `count` then equals `capacity` rather than silently
 * truncating a count. */
MohuWorldStatus mohu_world_select_eye(const MohuWorldMesh *mesh,
                                      const MohuWorldEyeView *view,
                                      uint32_t *indices, uint32_t capacity,
                                      MohuWorldSelection *selection);

#endif
