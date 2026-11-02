#include "scope.h"

#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <string.h>

int main(void) {
    assert(mohu_vr_scope_final_depth_h(2447) == 2463);
    assert(mohu_vr_scope_final_depth_h(400) == 400);
    assert(mohu_vr_scope_final_depth_h(401) == 403);
    assert(!mohu_vr_scope_final_depth_h(0));
    assert(!mohu_vr_scope_final_depth_h(UINT32_MAX));
    assert(mohu_vr_scope_fog_start(5700,2447,400,250) == 9252);
    assert(mohu_vr_scope_fog_start(5700,2447,2463,2313) == 9252);
    assert(mohu_vr_scope_fog_start(12000,2447,400,250) == 12000);
    assert(mohu_vr_scope_fog_start(5700,0,400,250) == 5700);
    assert(mohu_vr_scope_fog_start(5700,2447,0,250) == 5700);
    assert(mohu_vr_scope_fog_start(5700,2447,2500,250) == 5700);
    assert(mohu_vr_scope_fog_start(5700,2447,400,UINT32_MAX) == 5700);
    PSXModRenderView view = {0};
    view.struct_size = sizeof view;
    view.fx_q16 = 50000;
    view.fy_q16 = 60000;
    view.cx_delta_q16 = 1234;
    view.cy_delta_q16 = -567;
    view.precise = 1;
    const double rotation[9] = {1,0,0,0,1,0,0,0,1};
    memcpy(view.rotation, rotation, sizeof rotation);
    assert(mohu_vr_scope_apply_zoom(&view, 2.5));
    assert(view.fx_q16 == 125000 && view.fy_q16 == 150000);
    assert(view.cx_delta_q16 == 1234 && view.cy_delta_q16 == -567);
    assert(!mohu_vr_scope_apply_zoom(NULL, 2.5));
    assert(!mohu_vr_scope_apply_zoom(&view, 0.5));
    return 0;
}
