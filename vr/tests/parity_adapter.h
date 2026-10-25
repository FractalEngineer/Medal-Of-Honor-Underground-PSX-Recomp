#pragma once

#include <stdint.h>

typedef struct ParityView {
    int projection;
    int precise;
    int32_t fx_q16;
    int32_t fy_q16;
    int32_t cx_delta_q16;
    int32_t cy_delta_q16;
    double rotation[9];
    int32_t rotation_q12[9];
    double translation[3];
    double translation_precise[3];
} ParityView;

int reference_parity_inverse(const double matrix[9], double inverse[9]);
int underground_parity_inverse(const double matrix[9], double inverse[9]);

int reference_parity_box_visible(
    const int16_t bounds[6], const double matrix[9], const double tr[3],
    const ParityView* view, double cx, double cy, int width, int height);
int underground_parity_box_visible(
    const int16_t bounds[6], const double matrix[9], const double tr[3],
    const ParityView* view, double cx, double cy, int width, int height);
int underground_parity_mp_box_visible(
    const int16_t center[3], int16_t radius, const double matrix[9],
    const double tr[3], const ParityView* view, double cx, double cy,
    int width, int height);

int reference_parity_ray_box(
    const double origin[3], const double direction[3],
    const int16_t bounds[6], double tmin, double tmax, double* t_enter);
int underground_parity_ray_box(
    const double origin[3], const double direction[3],
    const int16_t bounds[6], double tmin, double tmax, double* t_enter);
