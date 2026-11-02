#pragma once

#include <stdbool.h>
#include <stdint.h>

/*
 * Native UI takes over after two missed 30 Hz scene intervals, matching the
 * reference game. Any claimed scene frame restarts the idle count.
 */
#define MOHU_VR_NATIVE_SURFACE_IDLE_VBLANKS 4u

/* Measured Start writers and pause consumers, separately owned by the SP/MP
 * overlay generations. Never infer pause from the last host button press. */
typedef struct {
    uint32_t state_address;
    uint32_t read_address;
    uint32_t enter_address;
    uint32_t read_words[4];
    uint32_t enter_words[3];
} MohuVrPauseBinding;

static inline const MohuVrPauseBinding* mohu_vr_pause_binding(bool multiplayer) {
    static const MohuVrPauseBinding bindings[2] = {
        {0x800A70F0u, 0x8006E958u, 0x8006EA04u,
         {0x3C02800Au, 0x8C4270F0u, 0u, 0x1440017Bu},
         {0x3C02800Au, 0x24030001u, 0xAC4370F0u}},
        {0x800A0A84u, 0x800649C4u, 0x80064ABCu,
         {0x3C02800Au, 0x8C420A84u, 0u, 0x14400107u},
         {0x3C02800Au, 0x24030001u, 0xAC430A84u}},
    };
    return &bindings[multiplayer ? 1u : 0u];
}

/* -1: unknown overlay/state, 0: gameplay, 1: native pause. */
static inline int mohu_vr_pause_state(
    const MohuVrPauseBinding* binding, const uint32_t read_words[4],
    const uint32_t enter_words[3], uint32_t state) {
    if (!binding || !read_words || !enter_words || state > 1u) return -1;
    for (unsigned i = 0; i < 4u; ++i)
        if (read_words[i] != binding->read_words[i]) return -1;
    for (unsigned i = 0; i < 3u; ++i)
        if (enter_words[i] != binding->enter_words[i]) return -1;
    return (int)state;
}

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
