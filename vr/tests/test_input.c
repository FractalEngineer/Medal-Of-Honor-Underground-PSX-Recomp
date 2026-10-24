#include "input.h"
#include <assert.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>
/* Underground slot-2 live calibration; converter is 80083C6C. */
static const uint8_t measured_curve[128] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,10,10,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,52,54,56,58,60,62,64,66,68,70,72,74,76,78,80,82,84,86,88,90,94,98,102,106,110,114,118,122,126,130,134,138,142,146,150,160,170,180,190,200,210,220,230,240,250,255,255};
int main(void) {
    MohuVRAnalogResponse response = {0};
    for (unsigned i = 0; i < 3; ++i)
        response.axis[i] = (MohuVRAnalogAxis){128, 255, 258, i == 2 ? 10240 : 8960};
    memcpy(response.curve, measured_curve, sizeof measured_curve);
    assert(mohu_vr_analog_response(&response, 0, 45) == -(int)measured_curve[82] * 8960);
    assert(mohu_vr_analog_response(&response, 0, 211) == measured_curve[83] * 8960);
    /* Center +/-37 are inclusive neutral; the native converter saturates
     * its lookup index. Check all pad bytes against that measured contract. */
    for (unsigned byte = 0; byte < 256; ++byte) {
        int expected = 0;
        if (byte < 91 || byte > 165) {
            unsigned distance = byte < 128 ? 128 - byte : byte - 128;
            unsigned index = distance * (byte < 128 ? 255 : 258) / 256;
            if (index > 127) index = 127;
            expected = measured_curve[index] * 8960 * (byte < 128 ? -1 : 1);
        }
        assert(mohu_vr_analog_response(&response, 0, byte) == expected);
    }
    MohuVRAnalogResponse saturated = response;
    saturated.axis[0].negative_factor = saturated.axis[0].positive_factor = 65535;
    assert(mohu_vr_analog_response(&saturated, 0, 0) == -255 * 8960);
    assert(mohu_vr_analog_response(&saturated, 0, 255) == 255 * 8960);
    PSXModOpenXRInput input = {0}; PSXModControllerState pad;
    input.struct_size = sizeof input; input.focused = 1;
    input.active[0] = input.active[1] = 1;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad));
    assert(pad.buttons == 0xffff && pad.lx == 128 && pad.ly == 128 && pad.rx == 128);
    for (int i = 0; i <= 100; ++i) {
        input.stick[1][0] = i / 100.f;
        assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad));
        int positive = mohu_vr_analog_response(&response, 0, pad.lx);
        input.stick[1][0] = -i / 100.f;
        assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad));
        int negative = mohu_vr_analog_response(&response, 0, pad.lx);
        assert(abs(positive + negative) <= 2 * 8960);
    }
    input.stick[1][0] = 0;
    for (int degrees = 0; degrees < 360; degrees += 15) {
        double angle = degrees * 3.141592653589793 / 180;
        input.stick[0][0] = (float)cos(angle);
        input.stick[0][1] = (float)sin(angle);
        assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad));
        double x = mohu_vr_analog_response(&response, 2, pad.rx) / (255. * 10240);
        double y = -mohu_vr_analog_response(&response, 1, pad.ly) / (255. * 8960);
        assert(fabs(hypot(x, y) - 1) < .03);
        assert(fabs(x - cos(angle)) < .025 && fabs(y - sin(angle)) < .025);
    }
    input.stick[0][0] = input.stick[0][1] = .1f;
    input.stick[1][0] = .15f;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad));
    assert(pad.lx == 128 && pad.ly == 128 && pad.rx == 128);
    input.stick[0][0] = input.stick[0][1] = input.stick[1][0] = 1;
    input.focused = 0;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad));
    assert(pad.lx == 128 && pad.ly == 128 && pad.rx == 128);
    input.focused = 1; input.active[0] = input.active[1] = 0;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad));
    assert(pad.lx == 128 && pad.ly == 128 && pad.rx == 128);
    input.active[0] = input.active[1] = 0;
    input.trigger_active[1] = input.squeeze_active[1] = 1;
    input.trigger[1] = .55f; input.squeeze[1] = .8f;
    input.buttons_active[0] = input.buttons_active[1] = PSX_MOD_XR_CLICKS;
    input.buttons[0] = PSX_MOD_XR_PRIMARY | PSX_MOD_XR_SECONDARY | PSX_MOD_XR_STICK | PSX_MOD_XR_MENU;
    input.buttons[1] = PSX_MOD_XR_PRIMARY | PSX_MOD_XR_SECONDARY | PSX_MOD_XR_STICK;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad));
    /* No R2: the right-grip aim mapping was removed, so nothing drives it. */
    assert(pad.buttons == (0xffffu ^ 0xf108u)); /* buttons don't depend on stick activity */
    assert(pad.lx == 128 && pad.ly == 128 && pad.rx == 128);
    input.focused = 0;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad) && pad.buttons == 0xffff);
    input.focused = 1; input.buttons_active[0] = input.buttons_active[1] = 0;
    input.trigger_active[1] = input.squeeze_active[1] = 0;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad) && pad.buttons == 0xffff);
    input.buttons[0] = PSX_MOD_XR_SECONDARY; input.buttons_active[0] = PSX_MOD_XR_CLICKS;
    input.buttons[1] = PSX_MOD_XR_STICK; input.buttons_active[1] = PSX_MOD_XR_CLICKS;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad) && pad.buttons == 0xfeff);
    input.buttons[1] = 0;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad) && pad.buttons == 0xffff);
    input.buttons[1] = PSX_MOD_XR_STICK; input.buttons_active[1] = 0;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad) && pad.buttons == 0xffff);
    assert(mohu_vr_menu_input_map(&input, .2, &pad) && pad.buttons == 0xffff);
    input.trigger_active[1] = 1; input.trigger[1] = NAN;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad) && pad.buttons == 0xffff);
    input.trigger[1] = .54f;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad) && pad.buttons == 0xffff);
    input.trigger[1] = .8f; input.active[0] = input.active[1] = 1;
    input.stick[0][0] = input.stick[0][1] = 1; input.stick[1][0] = 1;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad));
    assert(pad.buttons == 0xbfff && pad.lx != 128 && pad.ly != 128 && pad.rx != 128);
    input.active[0] = 1; input.stick[0][0] = NAN; input.stick[0][1] = .19f;
    assert(mohu_vr_input_map(&input, .2, .65, &response, 0, &pad) && pad.rx == 128 && pad.ly == 128);
    assert(!mohu_vr_input_map(&input, 1, .65, &response, 0, &pad));
    response.axis[0].negative_factor = 0;
    assert(!mohu_vr_input_map(&input, .2, .65, &response, 0, &pad));
    /* Menu input works before the gameplay response table is initialized. */
    memset(&input,0,sizeof input);input.struct_size=sizeof input;input.focused=1;
    input.buttons_active[1]=PSX_MOD_XR_CLICKS;input.buttons[1]=PSX_MOD_XR_PRIMARY;
    assert(mohu_vr_menu_input_map(&input,.2,&pad) && pad.buttons==0xbfff);
    input.buttons[1]=PSX_MOD_XR_SECONDARY;
    assert(mohu_vr_menu_input_map(&input,.2,&pad) && pad.buttons==0xefff);
    input.buttons[1]=0;input.active[0]=1;input.stick[0][0]=-1;input.stick[0][1]=1;
    assert(mohu_vr_menu_input_map(&input,.2,&pad) && pad.buttons==0xff6f);
    input.stick[0][0]=NAN;input.stick[0][1]=.2f;
    assert(mohu_vr_menu_input_map(&input,.2,&pad) && pad.buttons==0xffff);
    input.trigger_active[1]=1;input.trigger[1]=.9f;input.active[0]=0;
    assert(mohu_vr_menu_input_map(&input,.2,&pad) && pad.buttons==0xbfff);
    input.focused=0;
    assert(mohu_vr_menu_input_map(&input,.2,&pad) && pad.buttons==0xffff && pad.lx==128);
    input.focused=1;input.trigger[1]=NAN;input.buttons_active[1]=0;
    assert(mohu_vr_menu_input_map(&input,.2,&pad) && pad.buttons==0xffff);
    assert(!mohu_vr_menu_input_map(&input,1,&pad));
    response.axis[0].negative_factor = 255; /* restore after the invalid-input probe */
    /* Optional left-grip merge: right Y also drives LY, so one stick owns both
     * axes of the native left stick. It must leave the left hand's own Y alone. */
    memset(&input,0,sizeof input);input.struct_size=sizeof input;input.focused=1;
    input.active[0]=input.active[1]=1;
    input.stick[1][0]=0;input.stick[1][1]=1.f;
    assert(mohu_vr_input_map(&input,.2,.65,&response,0,&pad) && pad.ly==128);
    assert(mohu_vr_input_map(&input,.2,.65,&response,1,&pad) && pad.ly!=128 && pad.lx==128);
    int right_up=mohu_vr_analog_response(&response,1,pad.ly);
    input.stick[1][1]=-1.f;
    assert(mohu_vr_input_map(&input,.2,.65,&response,1,&pad));
    assert(right_up+mohu_vr_analog_response(&response,1,pad.ly)==0);
    input.stick[0][1]=.3f;input.stick[1][1]=1.f;
    assert(mohu_vr_input_map(&input,.2,.65,&response,1,&pad));
    uint32_t right_wins=pad.ly;
    input.stick[1][1]=.05f; /* inside the deadzone: the left hand's push stands */
    assert(mohu_vr_input_map(&input,.2,.65,&response,1,&pad) && pad.ly!=right_wins);
    return 0;
}
