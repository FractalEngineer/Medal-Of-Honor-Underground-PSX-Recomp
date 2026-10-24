#pragma once

#include "mod_plugins.h"

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
    if (width <= 0 || height <= 0) {
        return 1;
    }
    double fx = view->projection ? view->fx_q16 / 65536.0 : 400.0;
    double fy = view->projection ? view->fy_q16 / 65536.0 : 400.0;
    cx += view->projection ? view->cx_delta_q16 / 65536.0 : 0.0;
    cy += view->projection ? view->cy_delta_q16 / 65536.0 : 0.0;
    if (!isfinite(fx) || !isfinite(fy) || fx <= 0.0 || fy <= 0.0) {
        return 1;
    }

    unsigned inside = 0;
    for (int corner = 0; corner < 8; ++corner) {
        double p[3];
        double eye[3];
        for (int row = 0; row < 3; ++row) {
            p[row] = tr[row];
            for (int col = 0; col < 3; ++col) {
                p[row] += matrix[row * 3 + col] *
                    bounds[col + ((corner >> col) & 1) * 3];
            }
        }
        for (int row = 0; row < 3; ++row) {
            eye[row] = view->precise ? view->translation_precise[row]
                                     : view->translation[row];
            for (int col = 0; col < 3; ++col) {
                const double rotation = view->precise
                    ? view->rotation[row * 3 + col]
                    : view->rotation_q12[row * 3 + col] / 4096.0;
                eye[row] += rotation * p[col];
            }
            if (!isfinite(eye[row])) {
                return 1;
            }
        }

        /* A saturated coordinate is not evidence that the whole node is
         * outside. Keep it and let the native triangle clipper decide. */
        if (fabs(eye[0]) >= 32760.0 || fabs(eye[1]) >= 32760.0 ||
            fabs(eye[2]) >= 65530.0) {
            return 1;
        }
        if (eye[2] >= -1.0) {
            inside |= 1u;
        }
        if (fx * eye[0] + (cx + 2.0) * eye[2] >= -2.0) {
            inside |= 2u;
        }
        if ((width - cx + 2.0) * eye[2] - fx * eye[0] >= -2.0) {
            inside |= 4u;
        }
        if (fy * eye[1] + (cy + 2.0) * eye[2] >= -2.0) {
            inside |= 8u;
        }
        if ((height - cy + 2.0) * eye[2] - fy * eye[1] >= -2.0) {
            inside |= 16u;
        }
    }
    return inside == 31u;
}

/*
 * Collect a complete queue before the caller writes guest RAM. Any malformed
 * node, cycle/visit overflow or full output queue rejects the override so the
 * native selector can run unchanged.
 */
static inline int mohu_vr_collect_tree(uint32_t root, uint32_t queue[1000],
                                       unsigned* count,
                                       const double matrix[9],
                                       const double tr[3],
                                       const PSXModRenderView* view,
                                       double cx, double cy,
                                       const uint32_t masks[2],
                                       int bypass_masks,
                                       int keep_all) {
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
        if (!keep_all && !mohu_vr_box_visible(
                bounds, matrix, tr, view, cx, cy, 512, 240)) {
            continue;
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
