#include "moh_mkb.h"
#include <math.h>

void mohu_mkb_mouse_reset(MohuMkbMouse* state) {
    if (!state) return;
    state->pending_x = state->pending_y = 0;
}

void mohu_mkb_mouse_take(MohuMkbMouse* state, int64_t* yaw, int64_t* pitch) {
    if (!state || !yaw || !pitch) return;
    *yaw = (int64_t)(state->pending_x * 65536.0);
    *pitch = -(int64_t)(state->pending_y * 65536.0);
    state->pending_x -= (double)*yaw / 65536.0;
    state->pending_y += (double)*pitch / 65536.0;
}

void mohu_mkb_angles(int32_t pitch, int32_t yaw, int64_t dp, int64_t dy,
                     int32_t* next_pitch, int32_t* next_yaw) {
    int64_t p = (int64_t)pitch + dp;
    int64_t y = ((int64_t)yaw + dy) % 0x10000000LL;
    if (p > 0x02AA0000) p = 0x02AA0000;
    if (p < -0x02AA0000) p = -0x02AA0000;
    if (y < 0) y += 0x10000000LL;
    *next_pitch = (int32_t)p;
    *next_yaw = (int32_t)y;
}

void mohu_mkb_mouse_motion(MohuMkbMouse* state, double dx, double dy) {
    if (!state) return;
    if (!isfinite(dx) || !isfinite(dy)) {
        mohu_mkb_mouse_reset(state);
        return;
    }
    if (dx < -1000000.0) dx = -1000000.0;
    if (dx > 1000000.0) dx = 1000000.0;
    if (dy < -1000000.0) dy = -1000000.0;
    if (dy > 1000000.0) dy = 1000000.0;
    state->pending_x = fmax(-1000000.0, fmin(1000000.0, state->pending_x + dx));
    state->pending_y = fmax(-1000000.0, fmin(1000000.0, state->pending_y + dy));
}

void mohu_mkb_stick_pair(int left, int right, int up, int down,
                         uint8_t* lx, uint8_t* ly) {
    if (!lx || !ly) return;
    const int x = !!right - !!left;
    const int y = !!down - !!up;
    /* Feed each digital direction at full native deflection. Scaling diagonal
     * bytes before the game's nonlinear analog curve causes a second speed
     * reduction. The native movement code owns diagonal velocity handling. */
    *lx = !x ? 128 : x < 0 ? 0 : 255;
    *ly = !y ? 128 : y < 0 ? 0 : 255;
}

uint16_t mohu_mkb_action_aliases(uint16_t buttons, int enter, int backspace,
                                 int alternate_square) {
    uint16_t out = buttons;
    if (enter) out &= (uint16_t)~0x4000u;
    if (backspace) out &= (uint16_t)~0x1000u;
    if (alternate_square) out &= (uint16_t)~0x8000u;
    return out;
}

int mohu_mkb_weapon_slot(const int16_t* reserve, unsigned count, unsigned current,
                         int direction, int requested) {
    if (!reserve || !count || count > 8 || current >= count) return -1;
    if (requested >= 0)
        return (unsigned)requested < count && reserve[requested] != -1 ? requested : -1;
    if (!direction) return -1;
    for (unsigned step = 1; step < count; ++step) {
        unsigned slot = direction > 0 ? (current + step) % count :
                                        (current + count - step) % count;
        if (reserve[slot] != -1) return (int)slot;
    }
    return -1;
}

uint16_t mohu_mkb_menu_buttons(uint16_t buttons, int left, int right, int up,
                               int down, int confirm, int back) {
    if (up && !down) buttons &= (uint16_t)~0x0010u;
    if (right && !left) buttons &= (uint16_t)~0x0020u;
    if (down && !up) buttons &= (uint16_t)~0x0040u;
    if (left && !right) buttons &= (uint16_t)~0x0080u;
    return mohu_mkb_action_aliases(buttons, confirm, back, 0);
}
