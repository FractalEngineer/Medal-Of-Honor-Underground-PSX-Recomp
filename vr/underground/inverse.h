#pragma once

#include "vr_geometry_math.h"

/*
 * Underground keeps its historical inverse bounds and no upper determinant
 * cap. The framework computes into temporaries and only publishes a complete
 * inverse, so a coefficient-policy rejection no longer leaves partial output.
 */
static inline int mohu_vr_laser_inverse(const double matrix[9],
                                        double inverse[9]) {
    const PSXVRMatrixInversePolicy policy = {
        .min_abs_determinant = 0.01,
        .max_abs_determinant = INFINITY,
        .max_abs_coefficient = 64.0,
    };
    return psx_vr_inverse3x3(matrix, &policy, inverse);
}
