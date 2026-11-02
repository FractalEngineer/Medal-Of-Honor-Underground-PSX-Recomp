#include "scope.h"

#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <string.h>

int main(void) {
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
