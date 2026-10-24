#pragma once

#include <stdbool.h>
#include <stdint.h>

/*
 * Native UI takes over after two missed 30 Hz scene intervals, matching the
 * reference game. Any claimed scene frame restarts the idle count.
 */
#define MOHU_VR_NATIVE_SURFACE_IDLE_VBLANKS 4u

static inline bool mohu_vr_native_surface_due(
    uint32_t scene_attempts, uint32_t* seen_attempts,
    uint32_t* idle_vblanks, int surface_enabled) {
    if (!seen_attempts || !idle_vblanks) {
        return false;
    }
    if (*seen_attempts != scene_attempts) {
        *seen_attempts = scene_attempts;
        *idle_vblanks = 0u;
        return false;
    }
    if (*idle_vblanks < MOHU_VR_NATIVE_SURFACE_IDLE_VBLANKS) {
        ++*idle_vblanks;
    }
    return *idle_vblanks >= MOHU_VR_NATIVE_SURFACE_IDLE_VBLANKS &&
           surface_enabled != 1;
}
