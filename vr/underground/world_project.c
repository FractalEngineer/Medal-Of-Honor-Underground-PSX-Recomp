#include "world_project.h"

#include "mod_plugins.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

static int finite_values(const double *values, unsigned count) {
    for (unsigned i = 0; i < count; ++i)
        if (!isfinite(values[i])) return 0;
    return 1;
}

int mohu_world_eye_from_view(const struct PSXModRenderView *view, double cx,
                             double cy, int width, int height,
                             MohuWorldEyeView *out) {
    if (!view || !out || width <= 0 || height <= 0 ||
        !isfinite(cx) || !isfinite(cy))
        return 0;

    MohuWorldEyeView result;
    memset(&result, 0, sizeof result);
    result.fx = view->projection ? view->fx_q16 / 65536.0 : 400.0;
    result.fy = view->projection ? view->fy_q16 / 65536.0 : 400.0;
    result.cx = cx + (view->projection ? view->cx_delta_q16 / 65536.0 : 0.0);
    result.cy = cy + (view->projection ? view->cy_delta_q16 / 65536.0 : 0.0);
    for (unsigned i = 0; i < 9; ++i)
        result.rotation[i] = view->precise ? view->rotation[i]
                                           : view->rotation_q12[i] / 4096.0;
    for (unsigned i = 0; i < 3; ++i)
        result.translation[i] = view->precise
            ? view->translation_precise[i] : (double)view->translation[i];
    result.width = width;
    result.height = height;

    if (!finite_values(result.rotation, 9) ||
        !finite_values(result.translation, 3) || !isfinite(result.fx) ||
        !isfinite(result.fy) || !isfinite(result.cx) || !isfinite(result.cy) ||
        result.fx <= 0.0 || result.fy <= 0.0)
        return 0;
    *out = result;
    return 1;
}

static void transform_vertex(const MohuWorldEyeView *view,
                             const MohuWorldVertex *vertex, double eye[3]) {
    const double world[3] = {vertex->x, vertex->y, vertex->z};
    for (unsigned row = 0; row < 3; ++row) {
        double value = view->translation[row];
        for (unsigned col = 0; col < 3; ++col)
            value += view->rotation[row * 3 + col] * world[col];
        eye[row] = value;
    }
}

static void intersect_near(const double *a, const double *b, double near_z,
                           double out[3]) {
    const double denominator = b[2] - a[2];
    double t = denominator != 0.0 ? (near_z - a[2]) / denominator : 0.0;
    if (!isfinite(t)) t = 0.0;
    if (t < 0.0) t = 0.0;
    if (t > 1.0) t = 1.0;
    for (unsigned i = 0; i < 3; ++i) out[i] = a[i] + (b[i] - a[i]) * t;
    out[2] = near_z;
}

static void project_vertex(const MohuWorldEyeView *view, const double eye[3],
                           MohuWorldProjectedVertex *out) {
    out->eye[0] = eye[0];
    out->eye[1] = eye[1];
    out->eye[2] = eye[2];
    out->screen[0] = view->cx + view->fx * eye[0] / eye[2];
    out->screen[1] = view->cy + view->fy * eye[1] / eye[2];
}

MohuWorldStatus mohu_world_project_eye(const MohuWorldMesh *mesh,
                                       const MohuWorldEyeView *view,
                                       double near_z,
                                       MohuWorldProjectedTriangle *out,
                                       uint32_t capacity,
                                       MohuWorldProjection *stats) {
    if (stats) memset(stats, 0, sizeof *stats);
    if (!mesh || !view || !stats || !isfinite(near_z) || near_z <= 0.0 ||
        !finite_values(view->rotation, 9) ||
        !finite_values(view->translation, 3) || !isfinite(view->fx) ||
        !isfinite(view->fy) || !isfinite(view->cx) || !isfinite(view->cy) ||
        view->fx <= 0.0 || view->fy <= 0.0 || view->width <= 0 ||
        view->height <= 0)
        return MOHU_WORLD_REJECT_ARGUMENT;
    if (mesh->triangle_count && (!mesh->vertices || !mesh->triangles))
        return MOHU_WORLD_REJECT_ARGUMENT;
    if (capacity && !out) return MOHU_WORLD_REJECT_ARGUMENT;

    for (uint32_t t = 0; t < mesh->triangle_count; ++t) {
        const MohuWorldTriangle *triangle = &mesh->triangles[t];
        double eye[3][3];
        unsigned inside = 0;
        for (unsigned k = 0; k < 3; ++k) {
            transform_vertex(view, &mesh->vertices[triangle->vertex[k]],
                             eye[k]);
            if (eye[k][2] > near_z) inside++;
        }
        stats->tested++;
        if (!inside) {
            stats->dropped++;
            continue;
        }

        double polygon[MOHU_WORLD_MAX_POLYGON][3];
        unsigned count = 0;
        if (inside == 3u) {
            for (unsigned k = 0; k < 3; ++k)
                for (unsigned i = 0; i < 3; ++i) polygon[k][i] = eye[k][i];
            count = 3;
        } else {
            for (unsigned k = 0; k < 3; ++k) {
                const double *a = eye[k];
                const double *b = eye[(k + 1u) % 3u];
                const int a_inside = a[2] > near_z;
                const int b_inside = b[2] > near_z;
                if (a_inside != b_inside) {
                    if (count == MOHU_WORLD_MAX_POLYGON) break;
                    intersect_near(a, b, near_z, polygon[count++]);
                }
                if (b_inside) {
                    if (count == MOHU_WORLD_MAX_POLYGON) break;
                    for (unsigned i = 0; i < 3; ++i) polygon[count][i] = b[i];
                    count++;
                }
            }
            stats->clipped++;
        }
        if (count < 3u) {
            stats->dropped++;
            continue;
        }
        if (stats->emitted == capacity)
            return MOHU_WORLD_REJECT_TRIANGLE_BUDGET;

        MohuWorldProjectedTriangle *result = &out[stats->emitted++];
        memset(result, 0, sizeof *result);
        result->triangle = t;
        result->count = (uint8_t)count;
        for (unsigned i = 0; i < count; ++i)
            project_vertex(view, polygon[i], &result->vertex[i]);
    }
    return MOHU_WORLD_OK;
}

MohuWorldStatus mohu_world_drawlist(const MohuWorldProjectedTriangle *projected,
                                    uint32_t count,
                                    MohuWorldScreenTriangle *out,
                                    uint32_t capacity,
                                    MohuWorldDrawList *stats) {
    if (stats) memset(stats, 0, sizeof *stats);
    if (!stats || (count && !projected) || (capacity && !out))
        return MOHU_WORLD_REJECT_ARGUMENT;

    for (uint32_t i = 0; i < count; ++i) {
        const MohuWorldProjectedTriangle *polygon = &projected[i];
        if (polygon->count < 3u || polygon->count > MOHU_WORLD_MAX_POLYGON) {
            stats->degenerate++;
            continue;
        }
        stats->polygons++;
        for (unsigned k = 1; k + 1u < polygon->count; ++k) {
            const MohuWorldProjectedVertex *a = &polygon->vertex[0];
            const MohuWorldProjectedVertex *b = &polygon->vertex[k];
            const MohuWorldProjectedVertex *c = &polygon->vertex[k + 1u];
            if (!isfinite(a->screen[0]) || !isfinite(a->screen[1]) ||
                !isfinite(b->screen[0]) || !isfinite(b->screen[1]) ||
                !isfinite(c->screen[0]) || !isfinite(c->screen[1])) {
                stats->degenerate++;
                continue;
            }
            if (stats->triangles == capacity)
                return MOHU_WORLD_REJECT_TRIANGLE_BUDGET;
            MohuWorldScreenTriangle *triangle = &out[stats->triangles++];
            triangle->source_triangle = polygon->triangle;
            const MohuWorldProjectedVertex *sources[3] = {a, b, c};
            for (unsigned v = 0; v < 3u; ++v) {
                triangle->screen[v][0] = sources[v]->screen[0];
                triangle->screen[v][1] = sources[v]->screen[1];
            }
        }
    }
    return MOHU_WORLD_OK;
}
