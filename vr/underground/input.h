#pragma once
#include "mod_plugins.h"
/* Native default scheme: left X turns, left Y moves, right X strafes.
 * Calibration is read from the live guest, including its nonlinear lookup. */
typedef struct MohuVRAnalogAxis {
    uint32_t center, negative_factor, positive_factor, scale;
} MohuVRAnalogAxis;
typedef struct MohuVRAnalogResponse {
    MohuVRAnalogAxis axis[3]; /* native LX, LY, RX */
    uint8_t curve[128];
} MohuVRAnalogResponse;
/* Mirrors Underground 80083C6C before native input-state gains. */
int32_t mohu_vr_analog_response(const MohuVRAnalogResponse *response,
                             unsigned axis, uint32_t byte);
/* merged_y: the right stick's otherwise-unused Y also drives LY (move/aim), so
 * one hand controls both axes of the native left stick - needed when a machine
 * gun aims with that stick. */
int mohu_vr_input_map(const PSXModOpenXRInput *input, double deadzone,
                    double turn_gain, const MohuVRAnalogResponse *response,
                    int merged_y, PSXModControllerState *pad);
/* Native menu buttons/D-pad, independent of gameplay calibration tables. */
int mohu_vr_menu_input_map(const PSXModOpenXRInput *input,double deadzone,
                         PSXModControllerState *pad);
