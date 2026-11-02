#include "scope.h"

#include <math.h>

uint32_t mohu_vr_scope_final_depth_h(uint32_t target) {
    if (target < 400u || target > 8000u) return 0u;
    uint32_t h = 400u, step = 1u;
    while (h < target) {
        if (step < 64u) step += 2u;
        h += step;
    }
    return h;
}

uint16_t mohu_vr_scope_fog_start(uint16_t original, uint32_t target,
                                uint32_t current_h, uint32_t cutoff) {
    const uint32_t h = mohu_vr_scope_final_depth_h(target);
    if (!h || current_h < 400u || current_h > h || cutoff > 8000u)
        return original;
    const uint32_t distance = 4u * (cutoff + h - current_h);
    return distance > original && distance <= UINT16_MAX
        ? (uint16_t)distance : original;
}

int mohu_vr_scope_apply_zoom(PSXModRenderView* view, double zoom) {
    if (!view || view->struct_size != sizeof *view ||
        !isfinite(zoom) || zoom < 1.0 || zoom > 8.0 ||
        view->fx_q16 <= 0 || view->fy_q16 <= 0) return 0;
    const double fx = view->fx_q16 * zoom;
    const double fy = view->fy_q16 * zoom;
    if (!isfinite(fx) || !isfinite(fy) ||
        fx > INT32_MAX || fy > INT32_MAX) return 0;
    view->fx_q16 = (int32_t)lround(fx);
    view->fy_q16 = (int32_t)lround(fy);
    return 1;
}
