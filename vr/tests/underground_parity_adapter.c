#include "parity_adapter.h"

#include "../underground/frustum.h"
#include "../underground/inverse.h"
#include "../underground/raycast.h"

#include <string.h>

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

int underground_parity_inverse(const double matrix[9], double inverse[9]) {
    return mohu_vr_laser_inverse(matrix, inverse);
}

int underground_parity_box_visible(
    const int16_t bounds[6], const double matrix[9], const double tr[3],
    const ParityView* parity, double cx, double cy, int width, int height) {
    PSXModRenderView view = make_view(parity);
    return mohu_vr_box_visible(
        bounds, matrix, tr, &view, cx, cy, width, height);
}

int underground_parity_mp_box_visible(
    const int16_t center[3], int16_t radius, const double matrix[9],
    const double tr[3], const ParityView* parity, double cx, double cy,
    int width, int height) {
    PSXModRenderView view = make_view(parity);
    return mohu_vr_mp_box_visible(
        center, radius, matrix, tr, &view, cx, cy, width, height);
}

int underground_parity_ray_box(
    const double origin[3], const double direction[3],
    const int16_t bounds[6], double tmin, double tmax, double* t_enter) {
    return mohu_vr_ray_box(origin, direction, bounds, tmin, tmax, t_enter);
}
