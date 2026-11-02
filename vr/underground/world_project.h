#ifndef MOHU_WORLD_PROJECT_H
#define MOHU_WORLD_PROJECT_H

#include "world_decode.h"
#include "world_select.h"

#include <stdint.h>

struct PSXModRenderView;

#define MOHU_WORLD_MAX_POLYGON 4u

typedef struct {
    double eye[3];       /* +Z forward */
    double screen[2];
} MohuWorldProjectedVertex;

typedef struct {
    uint32_t triangle;   /* source triangle index */
    uint8_t count;       /* 3, or 4 after one near-plane clip */
    MohuWorldProjectedVertex vertex[MOHU_WORLD_MAX_POLYGON];
} MohuWorldProjectedTriangle;

typedef struct {
    uint32_t tested;
    uint32_t dropped;    /* wholly behind the near plane */
    uint32_t clipped;    /* crossed the near plane */
    uint32_t emitted;
} MohuWorldProjection;

typedef struct {
    uint32_t source_triangle;
    double screen[3][2];
} MohuWorldScreenTriangle;

typedef struct {
    uint32_t polygons;
    uint32_t triangles;
    uint32_t degenerate;   /* malformed polygon or non-finite screen point */
} MohuWorldDrawList;

/* Adapts the plugin's per-eye view with the same rules the existing frustum
 * selector uses: Q16 focal/centre deltas, Q12 or precise rotation/translation.
 * Returns 0 for an invalid view. */
int mohu_world_eye_from_view(const struct PSXModRenderView *view, double cx,
                             double cy, int width, int height,
                             MohuWorldEyeView *out);

/* Host reference transform/projection. Vertices are camera-relative level
 * coordinates, so world -> eye is the view rotation/translation only. A
 * triangle wholly behind `near_z` (> 0) is dropped; one crossing it is clipped
 * to a polygon of at most four vertices, then projected with
 * sx = cx + fx*x/z, sy = cy + fy*y/z. The eventual GPU path uses shaders; this
 * is the deterministic comparison/fallback. */
MohuWorldStatus mohu_world_project_eye(const MohuWorldMesh *mesh,
                                       const MohuWorldEyeView *view,
                                       double near_z,
                                       MohuWorldProjectedTriangle *out,
                                       uint32_t capacity,
                                       MohuWorldProjection *stats);

/* Fan-triangulates 3/4-vertex projected polygons into screen-space triangles,
 * preserving polygon order. Non-finite points are counted as degenerate and
 * dropped; capacity overflow returns triangle_budget. */
MohuWorldStatus mohu_world_drawlist(const MohuWorldProjectedTriangle *projected,
                                    uint32_t count,
                                    MohuWorldScreenTriangle *out,
                                    uint32_t capacity,
                                    MohuWorldDrawList *stats);

#endif
