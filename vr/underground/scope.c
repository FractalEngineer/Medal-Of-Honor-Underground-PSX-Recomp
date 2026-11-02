#include "scope.h"

#include <math.h>

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
