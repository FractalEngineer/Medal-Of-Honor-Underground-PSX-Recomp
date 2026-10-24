#include "input.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

static double finite_axis(double v) {
    return isfinite(v) ? fmax(-1, fmin(1, v)) : 0;
}
static double scalar_deadzone(double v, double deadzone) {
    v = finite_axis(v);
    if (fabs(v) <= deadzone) return 0;
    return copysign((fabs(v) - deadzone) / (1 - deadzone), v);
}
static uint32_t combat_buttons(const PSXModOpenXRInput *input) {
    uint32_t left = input->buttons[0] & input->buttons_active[0];
    uint32_t right = input->buttons[1] & input->buttons_active[1];
    uint32_t pressed = 0;
    /* Config. 2 native buttons, also documented in docs/DEFAULT_CONTROLS.md.
     * Feed ordinary PSX buttons so native press/hold/release logic owns combat.
     * Square's reload/interaction context is still the game's decision. */
    if (input->trigger_active[1] && isfinite(input->trigger[1]) &&
        input->trigger[1] >= .55f && input->trigger[1] <= 1) pressed |= 0x4000; /* Cross: fire/confirm */
    if (right & PSX_MOD_XR_PRIMARY) pressed |= 0x8000; /* A: Square/use */
    if (right & PSX_MOD_XR_SECONDARY) pressed |= 0x2000; /* B: Circle/next weapon/back */
    if (left & PSX_MOD_XR_PRIMARY) pressed |= 0x8000; /* X: Square/reload/use context */
    if (right & PSX_MOD_XR_STICK) pressed |= 0x0100; /* right click: L2/crouch toggle */
    if (left & PSX_MOD_XR_STICK) pressed |= 0x1000; /* left click: Triangle/jump */
    if (left & PSX_MOD_XR_MENU) pressed |= 0x0008; /* Menu: Start */
    return 0xffffu ^ pressed;
}
int mohu_vr_menu_input_map(const PSXModOpenXRInput *input,double deadzone,
                         PSXModControllerState *pad) {
    if(!pad)return 0;
    memset(pad,0,sizeof *pad);pad->struct_size=sizeof *pad;
    pad->buttons=0xffff;pad->lx=pad->ly=pad->rx=pad->ry=128;pad->analog=1;
    if(!input || input->struct_size!=sizeof *input || !input->focused)return 1;
    if(!isfinite(deadzone) || deadzone<0 || deadzone>=1)return 0;
    uint32_t left=input->buttons[0]&input->buttons_active[0];
    uint32_t right=input->buttons[1]&input->buttons_active[1],pressed=0;
    if(right&PSX_MOD_XR_PRIMARY)pressed|=0x4000; /* A: Cross/confirm */
    if(right&PSX_MOD_XR_SECONDARY)pressed|=0x1000; /* B: Triangle/back (menus use Triangle, not Circle) */
    if(left&PSX_MOD_XR_MENU)pressed|=8; /* Menu: Start/skip */
    if(input->trigger_active[1] && isfinite(input->trigger[1]) &&
       input->trigger[1]>=.55f && input->trigger[1]<=1)pressed|=0x4000;
    if(input->active[0]) {
        double threshold=fmax(.55,deadzone),x=finite_axis(input->stick[0][0]),y=finite_axis(input->stick[0][1]);
        if(x>threshold)pressed|=0x20;
        if(x< -threshold)pressed|=0x80;
        if(y>threshold)pressed|=0x10;
        if(y< -threshold)pressed|=0x40;
    }
    pad->buttons=0xffffu^pressed;return 1;
}
int32_t mohu_vr_analog_response(const MohuVRAnalogResponse *response,
                             unsigned axis, uint32_t byte) {
    if (!response || axis >= 3 || byte > 255) return 0;
    const MohuVRAnalogAxis *a = &response->axis[axis];
    unsigned index;
    int sign;
    /* Underground 80083C6C tests center +/- 37 and clamps the curve index.
     * The reference 80075E7C uses a different threshold and no clamp. */
    if ((int)byte < (int)a->center - 37) {
        index = ((a->center - byte) * a->negative_factor) >> 8;
        sign = -1;
    } else if (byte > a->center + 37) {
        index = ((byte - a->center) * a->positive_factor) >> 8;
        sign = 1;
    } else return 0;
    if (index >= sizeof response->curve) index = sizeof response->curve - 1;
    return sign * (int32_t)(response->curve[index] * a->scale);
}
static int valid_response(const MohuVRAnalogResponse *response) {
    if (!response) return 0;
    for (unsigned i = 0; i < 3; ++i) {
        const MohuVRAnalogAxis *a = &response->axis[i];
        if (a->center != 128 || !a->negative_factor ||
            a->negative_factor > 65535 || !a->positive_factor ||
            a->positive_factor > 65535 || !a->scale || a->scale > 65535)
            return 0;
    }
    return 1;
}
static uint32_t inverse_axis(const MohuVRAnalogResponse *response,
                             unsigned axis, double value) {
    value = finite_axis(value);
    if (!value) return 128;
    /* Use the common reachable magnitude: neither sign gets a faster maximum.
     * Search the actual curve rather than assuming centered linear pad bytes. */
    uint8_t reachable[2][256] = {{0}};
    uint32_t scale = response->axis[axis].scale;
    for (uint32_t byte = 0; byte <= 255; ++byte) {
        int32_t v = mohu_vr_analog_response(response, axis, byte);
        if (v) reachable[v > 0][(unsigned)abs(v) / scale] = 1;
    }
    unsigned full = 0;
    for (unsigned i = 1; i <= 255; ++i)
        if (reachable[0][i] && reachable[1][i]) full = i;
    double target = fabs(value) * full;
    double error = target;
    unsigned magnitude = 0;
    for (unsigned i = 1; i <= 255; ++i) {
        if (!reachable[0][i] || !reachable[1][i]) continue;
        double candidate = fabs(i - target);
        if (candidate < error) { error = candidate; magnitude = i; }
    }
    uint32_t best = 128;
    unsigned distance = 256;
    int32_t desired = (int32_t)(magnitude * scale) * (value < 0 ? -1 : 1);
    if (!magnitude) return 128;
    for (uint32_t byte = 0; byte <= 255; ++byte) {
        unsigned candidate = (unsigned)abs((int)byte - 128);
        if (mohu_vr_analog_response(response, axis, byte) == desired &&
            candidate < distance) { distance = candidate; best = byte; }
    }
    return best;
}
int mohu_vr_input_map(const PSXModOpenXRInput *input, double deadzone,
                    double turn_gain, const MohuVRAnalogResponse *response,
                    int merged_y, PSXModControllerState *pad) {
    if (!pad) return 0;
    memset(pad, 0, sizeof *pad); pad->struct_size = sizeof *pad;
    pad->buttons = 0xffff;
    pad->lx = pad->ly = pad->rx = pad->ry = 128; pad->analog = 1;
    if (!input || input->struct_size != sizeof *input || !input->focused) return 1;
    pad->buttons = combat_buttons(input);
    if (!isfinite(deadzone) || deadzone < 0 || deadzone >= 1 ||
        !isfinite(turn_gain) || turn_gain < 0 || turn_gain > 2 ||
        !valid_response(response)) return 0;
    /* The native left stick is LX (turn) + LY (move/aim). LX comes off the right
     * hand and LY off the left, so any mode that aims with the left stick - a
     * machine gun - splits its two axes across both hands. The right stick's Y
     * is otherwise unused (only its X turns), so in merged mode it drives LY as
     * well, larger magnitude winning: one hand then owns both axes. */
    double ly = 0;
    int have_ly = 0;
    if (input->active[0]) {
        double x = finite_axis(input->stick[0][0]);
        double y = finite_axis(input->stick[0][1]);
        double length = hypot(x, y);
        if (length > deadzone) {
            double magnitude = (fmin(1, length) - deadzone) / (1 - deadzone);
            ly = -y * magnitude / length;
            have_ly = 1;
            pad->rx = inverse_axis(response, 2, x * magnitude / length);
        }
    }
    if (input->active[1]) {
        pad->lx = inverse_axis(response, 0,
                              scalar_deadzone(input->stick[1][0], deadzone) * turn_gain);
        if (merged_y) {
            double right_y = -scalar_deadzone(input->stick[1][1], deadzone);
            if (fabs(right_y) > fabs(ly)) { ly = right_y; have_ly = 1; }
        }
    }
    if (have_ly) pad->ly = inverse_axis(response, 1, ly);
    return 1;
}
