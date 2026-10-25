#pragma once

#include "mod_plugins.h"
#include "vr_geometry_math.h"

#include <math.h>
#include <stdint.h>

/*
 * Underground level visibility tree layout measured by the frustum probe:
 * int16 AABB at +0..+10, leaf count at +12, masks at +16/+20, and children at
 * +24/+32/+28. Bounds are in camera-relative world space.
 */
static inline int mohu_vr_ray_box(const double origin[3],
                                  const double direction[3],
                                  const int16_t bounds[6],
                                  double tmin, double tmax,
                                  double* t_enter) {
    return psx_vr_ray_box(origin, direction, bounds, tmin, tmax, t_enter);
}
static inline int mohu_vr_ray_tree(uint32_t root,
                                   const double origin[3],
                                   const double direction[3],
                                   const uint32_t masks[2],
                                   int bypass_masks,
                                   double tmax,
                                   double* t_hit,
                                   uint32_t* leaf) {
    if (!root || (root & 3u) || !origin || !direction || !isfinite(tmax) ||
        tmax <= 0.0) {
        return 0;
    }
    uint32_t stack[256];
    unsigned top = 1;
    unsigned visited = 0;
    double best = tmax;
    uint32_t best_leaf = 0;
    stack[0] = root;

    while (top) {
        const uint32_t node = stack[--top];
        const uint32_t offset = node & 0x1fffffffu;
        if (!node || (node & 3u) || offset > 0x200000u - 36u ||
            ++visited > 8192u) {
            return 0;
        }
        if (!bypass_masks && masks &&
            (!(psx_mod_read_word(node + 16u) & masks[0]) ||
             !(psx_mod_read_word(node + 20u) & masks[1]))) {
            continue;
        }

        int16_t bounds[6];
        for (int i = 0; i < 6; ++i) {
            bounds[i] = (int16_t)psx_mod_read_half(node + (uint32_t)i * 2u);
        }
        for (int axis = 0; axis < 3; ++axis) {
            if (bounds[axis] > bounds[axis + 3]) {
                return 0;
            }
        }

        double t_enter = 0.0;
        if (!mohu_vr_ray_box(origin, direction, bounds, 0.0, best, &t_enter)) {
            continue;
        }
        if ((int32_t)psx_mod_read_word(node + 12u) > 0) {
            if (t_enter > 1e-3) {
                best = t_enter;
                best_leaf = node;
            }
            continue;
        }
        static const unsigned child_offsets[3] = {24u, 32u, 28u};
        for (int i = 0; i < 3; ++i) {
            const uint32_t child = psx_mod_read_word(node + child_offsets[i]);
            if (child) {
                if (top == 256u) {
                    return 0;
                }
                stack[top++] = child;
            }
        }
    }

    if (!best_leaf) {
        return 0;
    }
    if (t_hit) {
        *t_hit = best;
    }
    if (leaf) {
        *leaf = best_leaf;
    }
    return 1;
}
