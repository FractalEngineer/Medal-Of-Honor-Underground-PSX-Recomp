#pragma once

#include <stdint.h>

/* Pure achievement state machine for Medal of Honor Underground.
 *
 * Kept free of the runtime API so the event conditions can be unit-tested
 * without a disc, a host, or RecompLauncher. The plugin glue samples the
 * verified guest addresses once per VBlank and forwards events to
 * Recomp Achievements. */

typedef void (*MohuAchEventFn)(const char* event, void* user);

typedef struct MohuAchievementsState {
    int gameplay_prev;
    int weapon_prev;
    int low_health;
    uint32_t gameplay_frames;
    unsigned fired;
} MohuAchievementsState;

/* 10 minutes of emulated VBlank time (~60 Hz). */
#define MOHU_ACH_LONG_HAUL_FRAMES 36000u

void mohu_achievements_state_reset(MohuAchievementsState* state);

/* gameplay_active: SP_GAMEPLAY_ACTIVE != 0.
 * health: player+0x10A as int16, or -1 when no player is available.
 * weapon: input+93, or -1 when no player is available. */
void mohu_achievements_state_sample(MohuAchievementsState* state,
                                    int gameplay_active, int health, int weapon,
                                    MohuAchEventFn emit, void* user);
