#include "parity_adapter.h"

#include "moh_vr_frustum.h"
#include "moh_vr_raycast.h"

#include <math.h>
#include <string.h>

int reference_parity_inverse(const double matrix[9], double inverse[9]) {
    /* Provided by the reference game's moh_vr_aim.c. */
    extern int moh_vr_matrix_inverse(const double matrix[9],
                                     double inverse[9]);
    return moh_vr_matrix_inverse(matrix, inverse);
}

static PSXModRenderView make_view(const ParityView* parity) {
    PSXModRenderView view = {0};
    view.struct_size = sizeof view;
    view.projection = parity->projection;
    view.precise = parity->precise;
    view.fx_q16 = parity->fx_q16;
    view.fy_q16 = parity->fy_q16;
    view.cx_delta_q16 = parity->cx_delta_q16;
    view.cy_delta_q16 = parity->cy_delta_q16;
    memcpy(view.rotation, parity->rotation, sizeof view.rotation);
    memcpy(view.rotation_q12, parity->rotation_q12,
           sizeof view.rotation_q12);
    memcpy(view.translation, parity->translation, sizeof view.translation);
    memcpy(view.translation_precise, parity->translation_precise,
           sizeof view.translation_precise);
    return view;
}

int reference_parity_box_visible(
    const int16_t bounds[6], const double matrix[9], const double tr[3],
    const ParityView* parity, double cx, double cy, int width, int height) {
    PSXModRenderView view = make_view(parity);
    return moh_vr_box_visible(
        bounds, matrix, tr, &view, cx, cy, width, height);
}

int reference_parity_ray_box(
    const double origin[3], const double direction[3],
    const int16_t bounds[6], double tmin, double tmax, double* t_enter) {
    if (!origin || !direction || !bounds || !t_enter ||
        !isfinite(tmin) || !isfinite(tmax) || tmin > tmax) {
        return 0;
    }
    for (int i = 0; i < 3; ++i) {
        if (!isfinite(origin[i]) || !isfinite(direction[i])) {
            return 0;
        }
    }
    return moh_vr_ray_box(
        origin, direction, bounds, tmin, tmax, t_enter);
}
