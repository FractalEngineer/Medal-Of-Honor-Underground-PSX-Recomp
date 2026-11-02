#pragma once

#include "mod_plugins.h"
#include "vr_geometry_math.h"

#include <math.h>
#include <stdint.h>

/*
 * Underground's level selector uses the same visibility-tree layout as the
 * accepted reference implementation. Keep this test independent from the
 * diagnostic globals so the tree and frustum rules can be compiled directly.
 */
static inline int mohu_vr_box_visible(const int16_t bounds[6],
                                      const double matrix[9],
                                      const double tr[3],
                                      const PSXModRenderView* view,
                                      double cx, double cy,
                                      int width, int height) {
    if (!view || !bounds || !matrix || !tr) {
        return 1;
    }
    const double fx = view->projection ? view->fx_q16 / 65536.0 : 400.0;
    const double fy = view->projection ? view->fy_q16 / 65536.0 : 400.0;
    const double center_x =
        cx + (view->projection ? view->cx_delta_q16 / 65536.0 : 0.0);
    const double center_y =
        cy + (view->projection ? view->cy_delta_q16 / 65536.0 : 0.0);
    double eye_rotation[9];
    for (int i = 0; i < 9; ++i) {
        eye_rotation[i] = view->precise
            ? view->rotation[i]
            : view->rotation_q12[i] / 4096.0;
    }
    double eye_translation[3];
    for (int i = 0; i < 3; ++i) {
        eye_translation[i] = view->precise
            ? view->translation_precise[i]
            : view->translation[i];
    }
    const int visible = psx_vr_box_visible(
        bounds, matrix, tr, eye_rotation, eye_translation,
        fx, fy, center_x, center_y, width, height);
    if (visible == PSX_VR_GEOMETRY_UNKNOWN) {
        return 1;
    }
    return visible;
}

/*
 * The MP selector expands each node's short center and radius into a cube.
 * Reject wrapped or negative input so the caller can execute the untouched
 * native selector instead of testing a different object.
 */
static inline int mohu_vr_mp_aabb_from_sphere(
    const int16_t center[3], int16_t radius, int16_t bounds[6]) {
    if (!center || !bounds || radius < 0) {
        return 0;
    }
    for (int axis = 0; axis < 3; ++axis) {
        const int32_t low = (int32_t)center[axis] - radius;
        const int32_t high = (int32_t)center[axis] + radius;
        if (low < INT16_MIN || low > INT16_MAX ||
            high < INT16_MIN || high > INT16_MAX) {
            return 0;
        }
        bounds[axis] = (int16_t)low;
        bounds[axis + 3] = (int16_t)high;
    }
    return 1;
}

/* -1 means malformed input; 0/1 are the normal invisible/visible results. */
static inline int mohu_vr_mp_box_visible(
    const int16_t center[3], int16_t radius, const double matrix[9],
    const double tr[3], const PSXModRenderView* view, double cx, double cy,
    int width, int height) {
    int16_t bounds[6];
    if (!mohu_vr_mp_aabb_from_sphere(center, radius, bounds)) {
        return -1;
    }
    return mohu_vr_box_visible(
        bounds, matrix, tr, view, cx, cy, width, height);
}

static inline int mohu_vr_mp_view_valid(const PSXModRenderView* view,
                                        int width, int height) {
    if (!view || width <= 0 || height <= 0 || width > 2048 ||
        height > 512 || !view->projection || view->fx_q16 <= 0 ||
        view->fy_q16 <= 0) {
        return 0;
    }
    if (view->precise) {
        for (int i = 0; i < 9; ++i) {
            if (!isfinite(view->rotation[i])) {
                return 0;
            }
        }
        for (int i = 0; i < 3; ++i) {
            if (!isfinite(view->translation_precise[i])) {
                return 0;
            }
        }
    }
    return 1;
}

/*
 * Collect a complete queue before the caller writes guest RAM. Any malformed
 * node, cycle/visit overflow or full output queue rejects the override so the
 * native selector can run unchanged.
 */
/* Native 8009A174 compares camera-space MAC3 against view+40 (16.16).
 * Reject only boxes wholly beyond that plane after the same eye transform
 * used for angular visibility. One unit retains the native integer boundary. */
static inline int mohu_vr_box_within_far(
    const int16_t bounds[6], const double matrix[9], const double tr[3],
    const PSXModRenderView* view, double far_depth) {
    if (!bounds || !matrix || !tr || !view ||
        !isfinite(far_depth) || far_depth <= 0.0) return -1;
    double minimum = INFINITY;
    for (unsigned corner = 0; corner < 8u; ++corner) {
        double world[3];
        for (unsigned row = 0; row < 3u; ++row) {
            world[row] = tr[row];
            for (unsigned col = 0; col < 3u; ++col)
                world[row] += matrix[row * 3u + col] *
                    bounds[col + ((corner >> col) & 1u) * 3u];
        }
        double depth = view->precise ? view->translation_precise[2]
                                     : view->translation[2];
        for (unsigned col = 0; col < 3u; ++col)
            depth += (view->precise ? view->rotation[6u + col]
                                   : view->rotation_q12[6u + col] / 4096.0) * world[col];
        if (!isfinite(depth)) return -1;
        if (depth < minimum) minimum = depth;
    }
    return minimum <= far_depth + 1.0;
}

static inline int mohu_vr_collect_tree(uint32_t root, uint32_t queue[1000],
                                       unsigned* count,
                                       const double matrix[9],
                                       const double tr[3],
                                       const PSXModRenderView* view,
                                       double cx, double cy,
                                       const uint32_t masks[2],
                                       int bypass_masks,
                                       int keep_all, double far_depth) {
    uint32_t stack[256];
    unsigned top = 1;
    unsigned visited = 0;
    *count = 0;
    stack[0] = root;

    while (top) {
        const uint32_t node = stack[--top];
        const uint32_t off = node & 0x1fffffffu;
        if (!node || (node & 3u) || off > 0x200000u - 36u ||
            ++visited > 8192u) {
            return 0;
        }
        if (!bypass_masks && !keep_all &&
            (!(psx_mod_read_word(node + 16u) & masks[0]) ||
             !(psx_mod_read_word(node + 20u) & masks[1]))) {
            continue;
        }

        int16_t bounds[6];
        for (int i = 0; i < 6; ++i) {
            bounds[i] = (int16_t)psx_mod_read_half(node + (uint32_t)i * 2u);
        }
        for (int i = 0; i < 3; ++i) {
            if (bounds[i] > bounds[i + 3]) {
                return 0;
            }
        }
        if (!keep_all) {
            const int within_far = mohu_vr_box_within_far(bounds, matrix, tr, view, far_depth);
            if (within_far < 0) return 0;
            if (!within_far || !mohu_vr_box_visible(
                    bounds, matrix, tr, view, cx, cy, 512, 240)) continue;
        }

        if ((int32_t)psx_mod_read_word(node + 12u) > 0) {
            if (*count == 1000u) {
                return 0;
            }
            queue[(*count)++] = node;
        } else {
            static const unsigned offsets[3] = {24u, 32u, 28u};
            for (int i = 0; i < 3; ++i) {
                const uint32_t child =
                    psx_mod_read_word(node + offsets[i]);
                if (child) {
                    if (top == 256u) {
                        return 0;
                    }
                    stack[top++] = child;
                }
            }
        }
    }
    return 1;
}
