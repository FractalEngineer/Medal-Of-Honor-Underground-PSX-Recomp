#include "world_select.h"

#include "vr_geometry_math.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

static int finite_values(const double *values, unsigned count) {
    for (unsigned i = 0; i < count; ++i)
        if (!isfinite(values[i])) return 0;
    return 1;
}

static int view_valid(const MohuWorldEyeView *view) {
    return view && finite_values(view->rotation, 9) &&
           finite_values(view->translation, 3) && isfinite(view->fx) &&
           isfinite(view->fy) && isfinite(view->cx) && isfinite(view->cy) &&
           view->fx > 0.0 && view->fy > 0.0 && view->width > 0 &&
           view->height > 0 && isfinite(view->far_plane) &&
           view->far_plane >= 0.0;
}

MohuWorldStatus mohu_world_select_eye(const MohuWorldMesh *mesh,
                                      const MohuWorldEyeView *view,
                                      uint32_t *indices, uint32_t capacity,
                                      MohuWorldSelection *selection) {
    if (selection) memset(selection, 0, sizeof *selection);
    if (!mesh || !selection || !view_valid(view))
        return MOHU_WORLD_REJECT_ARGUMENT;
    if (mesh->triangle_count && (!mesh->vertices || !mesh->triangles))
        return MOHU_WORLD_REJECT_ARGUMENT;
    if (capacity && !indices) return MOHU_WORLD_REJECT_ARGUMENT;

    static const double identity[9] = {1.0, 0.0, 0.0, 0.0, 1.0, 0.0,
                                       0.0, 0.0, 1.0};
    static const double origin[3] = {0.0, 0.0, 0.0};

    for (uint32_t t = 0; t < mesh->triangle_count; ++t) {
        const MohuWorldTriangle *triangle = &mesh->triangles[t];
        int16_t bounds[6];
        for (unsigned axis = 0; axis < 3; ++axis) {
            int16_t low = INT16_MAX, high = INT16_MIN;
            for (unsigned corner = 0; corner < 3; ++corner) {
                const MohuWorldVertex *vertex =
                    &mesh->vertices[triangle->vertex[corner]];
                const int16_t value =
                    axis == 0 ? vertex->x : (axis == 1 ? vertex->y : vertex->z);
                if (value < low) low = value;
                if (value > high) high = value;
            }
            bounds[axis] = low;
            bounds[axis + 3] = high;
        }

        const int visible = psx_vr_box_visible(
            bounds, identity, origin, view->rotation, view->translation,
            view->fx, view->fy, view->cx, view->cy, view->width, view->height);
        selection->tested++;
        if (visible == PSX_VR_GEOMETRY_OUTSIDE) {
            selection->outside++;
            continue;
        }
        if (view->far_plane > 0.0) {
            int beyond = 1;
            for (unsigned corner = 0; corner < 3 && beyond; ++corner) {
                const MohuWorldVertex *vertex =
                    &mesh->vertices[triangle->vertex[corner]];
                const double z =
                    view->rotation[6] * vertex->x +
                    view->rotation[7] * vertex->y +
                    view->rotation[8] * vertex->z + view->translation[2];
                if (!isfinite(z)) {
                    beyond = 0;
                    break;
                }
                if (z <= view->far_plane) beyond = 0;
            }
            if (beyond) {
                selection->outside++;
                continue;
            }
        }
        if (visible == PSX_VR_GEOMETRY_UNKNOWN) selection->unknown++;
        if (selection->count == capacity)
            return MOHU_WORLD_REJECT_TRIANGLE_BUDGET;
        indices[selection->count++] = t;
    }
    return MOHU_WORLD_OK;
}
