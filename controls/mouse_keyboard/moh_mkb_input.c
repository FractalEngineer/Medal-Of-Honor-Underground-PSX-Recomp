#include "moh_mkb.h"
#include <math.h>

int mohu_mkb_firearm_zoom_supported(unsigned weapon) {
    switch (weapon) {
    case 0: case 1: case 4: case 8: case 9: case 11: case 12:
    case 13: case 14: case 16: case 17:
        return 1;
    default:
        return 0; /* Native sniper scope, camera and throwables. */
    }
}

double mohu_mkb_zoom_step(double amount, int held) {
    /* Three native campaign updates, about 100 ms, in either direction. */
    const double next = fmax(0, fmin(1, amount + (held ? 1.0 : -1.0) / 3.0));
    return next < 1e-9 ? 0 : next > 1 - 1e-9 ? 1 : next;
}

double mohu_mkb_zoom_ease(double amount) {
    amount = fmax(0, fmin(1, amount));
    return amount * amount * (3 - 2 * amount);
}

void mohu_mkb_mouse_reset(MohuMkbMouse* state) {
    if (!state) return;
    state->pending_x = state->pending_y = 0;
}

void mohu_mkb_mouse_take(MohuMkbMouse* state, int64_t* yaw, int64_t* pitch) {
    mohu_mkb_mouse_take_scaled(state, 1.0, yaw, pitch);
}

void mohu_mkb_mouse_take_scaled(MohuMkbMouse* state, double gain,
                                int64_t* yaw, int64_t* pitch) {
    if (!state || !yaw || !pitch || !isfinite(gain) || gain <= 0 || gain > 8) return;
    const double scale = gain * 65536.0;
    *yaw = (int64_t)(state->pending_x * scale);
    *pitch = -(int64_t)(state->pending_y * scale);
    state->pending_x -= (double)*yaw / scale;
    state->pending_y += (double)*pitch / scale;
}

void mohu_mkb_view_matrix(int32_t pitch, int32_t yaw, const int32_t eye[3],
                          int16_t rotation[9], int32_t translation[3]) {
    const double radians = 6.2831853071795864769 / (4096.0 * 65536.0);
    const double sp = sin(pitch * radians), cp = cos(pitch * radians);
    const double sy = sin(yaw * radians), cy = cos(yaw * radians);
    const double rows[9] = {cy, 0, -sy, sy * sp, cp, cy * sp,
                           sy * cp, -sp, cy * cp};
    for (unsigned row = 0; row < 3; ++row) {
        const double scale = row == 1 ? 5120.0 : 8192.0;
        double t = 0;
        for (unsigned col = 0; col < 3; ++col) {
            const unsigned at = 3 * row + col;
            rotation[at] = (int16_t)lround(rows[at] * scale);
            t -= (double)rotation[at] * eye[col] / (4096.0 * 65536.0);
        }
        translation[row] = (int32_t)lround(t);
    }
}

int mohu_mkb_shot_matrix(const int32_t origin[3], const int32_t target[3],
                         int16_t rotation[9]) {
    double f[3];
    for (unsigned i = 0; i < 3; ++i) f[i] = (double)target[i] - origin[i];
    const double length = hypot(hypot(f[0], f[1]), f[2]);
    if (length < 65536.0) return 0;
    for (unsigned i = 0; i < 3; ++i) f[i] /= length;
    const double horizontal = hypot(f[0], f[2]);
    if (horizontal < 0.001) return 0;
    const double right[3] = {f[2] / horizontal, 0, -f[0] / horizontal};
    const double up[3] = {-f[1] * f[0] / horizontal, horizontal,
                          -f[1] * f[2] / horizontal};
    for (unsigned row = 0; row < 3; ++row) {
        rotation[3 * row] = (int16_t)lround(right[row] * 4096);
        rotation[3 * row + 1] = (int16_t)lround(up[row] * 4096);
        rotation[3 * row + 2] = (int16_t)lround(f[row] * 4096);
    }
    return 1;
}

int mohu_mkb_mounted_pitch(int32_t center, int32_t x, int32_t z,
                           int narrow, int32_t pitch, int32_t* next_target, int32_t* applied) {
    const double distance = hypot((double)x, (double)z);
    if (distance < 1.0 || !next_target || !applied) return 0;
    const double units = 268435456.0 / (2.0 * 3.14159265358979323846);
    double angle = pitch / units;
    const double low = atan2(-(double)(narrow ? 27 : 110), distance);
    const double high = atan2((double)(narrow ? 15 : 60), distance);
    if (angle < low) angle = low;
    if (angle > high) angle = high;
    *next_target = (int32_t)llround(((double)center - tan(angle) * distance) * 65536.0);
    *applied = (int32_t)llround(angle * units);
    return 1;
}

int32_t mohu_mkb_mounted_yaw(int32_t current, int32_t anchor, int64_t delta, int limit) {
    const int64_t turn = 0x10000000LL, half = turn / 2;
    int64_t relative = ((int64_t)current - anchor + delta % turn) % turn;
    if (relative > half) relative -= turn;
    if (relative < -half) relative += turn;
    if (limit > 0) {
        const int64_t bound = (int64_t)limit * 65536;
        if (relative > bound) relative = bound;
        if (relative < -bound) relative = -bound;
    }
    int64_t result = ((int64_t)anchor + relative) % turn;
    if (result > half) result -= turn;
    if (result < -half) result += turn;
    return (int32_t)result;
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
