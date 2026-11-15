#include "mohu_achievements_state.h"

#include <string.h>

enum {
    MOHU_ACH_FIRED_GAMEPLAY = 1u << 0,
    MOHU_ACH_FIRED_SNIPER = 1u << 1,
    MOHU_ACH_FIRED_SWITCH = 1u << 2,
    MOHU_ACH_FIRED_CLOSE = 1u << 3,
    MOHU_ACH_FIRED_LONG = 1u << 4,
};

#define MOHU_SNIPER_WEAPON_ID 5

static void emit_once(MohuAchievementsState* state, unsigned flag,
                      const char* event, MohuAchEventFn emit, void* user) {
    if ((state->fired & flag) || !emit) return;
    state->fired |= flag;
    emit(event, user);
}

void mohu_achievements_state_reset(MohuAchievementsState* state) {
    if (!state) return;
    memset(state, 0, sizeof(*state));
}

void mohu_achievements_state_sample(MohuAchievementsState* state,
                                    int gameplay_active, int health, int weapon,
                                    MohuAchEventFn emit, void* user) {
    if (!state) return;

    if (!gameplay_active) {
        state->gameplay_prev = 0;
        state->weapon_prev = 0;
        state->low_health = 0;
        return;
    }

    if (!state->gameplay_prev) {
        state->gameplay_prev = 1;
        emit_once(state, MOHU_ACH_FIRED_GAMEPLAY, "gameplay_started", emit, user);
    }

    if (state->gameplay_frames < MOHU_ACH_LONG_HAUL_FRAMES) {
        ++state->gameplay_frames;
        if (state->gameplay_frames >= MOHU_ACH_LONG_HAUL_FRAMES)
            emit_once(state, MOHU_ACH_FIRED_LONG, "long_haul", emit, user);
    }

    if (weapon >= 0) {
        if (weapon == MOHU_SNIPER_WEAPON_ID)
            emit_once(state, MOHU_ACH_FIRED_SNIPER, "sniper_equipped", emit, user);
        if (state->weapon_prev > 0 && weapon > 0 &&
            weapon != state->weapon_prev)
            emit_once(state, MOHU_ACH_FIRED_SWITCH, "weapon_switched", emit, user);
        state->weapon_prev = weapon;
    }

    if (health <= 0) {
        state->low_health = 0;
    } else if (health <= 10) {
        state->low_health = 1;
    } else if (state->low_health && health >= 50) {
        state->low_health = 0;
        emit_once(state, MOHU_ACH_FIRED_CLOSE, "close_call", emit, user);
    }
}
