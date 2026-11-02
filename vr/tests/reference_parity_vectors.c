#include "parity_adapter.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>

#define SENTINEL 1234567.25

static int failures;

static void fail(const char* name, const char* why) {
    printf("FAIL|%s|%s\n", name, why);
    ++failures;
}

static int same(double a, double b, double tolerance) {
    return isfinite(a) && isfinite(b) && fabs(a - b) <= tolerance;
}

static int multiply_is_identity(const double matrix[9],
                                const double inverse[9]) {
    for (int row = 0; row < 3; ++row) {
        for (int col = 0; col < 3; ++col) {
            double value = 0.0;
            for (int k = 0; k < 3; ++k) {
                value += matrix[row * 3 + k] * inverse[k * 3 + col];
            }
            if (!same(value, row == col ? 1.0 : 0.0, 1e-9)) {
                return 0;
            }
        }
    }
    return 1;
}

static void inverse_case(const char* name, const double matrix[9],
                         int expect_reference, int expect_underground) {
    double reference[9];
    double underground[9];
    for (int i = 0; i < 9; ++i) {
        reference[i] = SENTINEL;
        underground[i] = SENTINEL;
    }
    const int ref_ok = reference_parity_inverse(matrix, reference);
    const int und_ok = underground_parity_inverse(matrix, underground);
    int ref_unchanged = 1;
    int und_unchanged = 1;
    for (int i = 0; i < 9; ++i) {
        ref_unchanged &= reference[i] == SENTINEL;
        und_unchanged &= underground[i] == SENTINEL;
    }
    printf("CASE|inverse.%s|REF=%d|UNDERGROUND=%d|"
           "REF_UNCHANGED=%d|UNDERGROUND_UNCHANGED=%d\n",
           name, ref_ok, und_ok, ref_unchanged, und_unchanged);
    if (ref_ok != expect_reference || und_ok != expect_underground) {
        fail(name, "unexpected acceptance policy");
        return;
    }
    if (ref_ok && !multiply_is_identity(matrix, reference)) {
        fail(name, "reference inverse is not the identity inverse");
    }
    if (und_ok && !multiply_is_identity(matrix, underground)) {
        fail(name, "Underground inverse is not the identity inverse");
    }
    if (ref_ok && und_ok) {
        for (int i = 0; i < 9; ++i) {
            if (!same(reference[i], underground[i], 1e-10)) {
                fail(name, "accepted inverse outputs disagree");
                return;
            }
        }
    }
}

static void inverse_translation_case(const double matrix[9],
                                     const double translation[3]) {
    double transformed[3];
    for (int row = 0; row < 3; ++row) {
        transformed[row] = 0.0;
        for (int col = 0; col < 3; ++col) {
            transformed[row] += matrix[row * 3 + col] * translation[col];
        }
    }
    double reference[9];
    double underground[9];
    const int ref_ok = reference_parity_inverse(matrix, reference);
    const int und_ok = underground_parity_inverse(matrix, underground);
    printf("CASE|inverse.translation_reconstruction|REF=%d|UNDERGROUND=%d\n",
           ref_ok, und_ok);
    if (!ref_ok || !und_ok) {
        fail("translation_reconstruction",
             "a valid inverse was rejected during reconstruction");
        return;
    }
    for (int row = 0; row < 3; ++row) {
        double ref_value = 0.0;
        double und_value = 0.0;
        for (int col = 0; col < 3; ++col) {
            ref_value += reference[row * 3 + col] * transformed[col];
            und_value += underground[row * 3 + col] * transformed[col];
        }
        if (!same(ref_value, translation[row], 1e-9) ||
            !same(und_value, translation[row], 1e-9)) {
            fail("translation_reconstruction",
                 "inverse did not reconstruct the analytic input");
            return;
        }
    }
}

static void box_case(const char* name, const int16_t bounds[6],
                     const double matrix[9], const double tr[3],
                     const ParityView* view, double cx, double cy,
                     int width, int height, int expected) {
    const int ref = reference_parity_box_visible(
        bounds, matrix, tr, view, cx, cy, width, height);
    const int und = underground_parity_box_visible(
        bounds, matrix, tr, view, cx, cy, width, height);
    printf("CASE|box.%s|REF=%d|UNDERGROUND=%d\n", name, ref, und);
    if (ref != expected || und != expected || ref != und) {
        fail(name, "visibility result differs from expected policy");
    }
}

static void ray_case(const char* name, const double origin[3],
                     const double direction[3], const int16_t bounds[6],
                     double tmin, double tmax, int expected,
                     double expected_t) {
    double ref_t = SENTINEL;
    double und_t = SENTINEL;
    const int ref = reference_parity_ray_box(
        origin, direction, bounds, tmin, tmax, &ref_t);
    const int und = underground_parity_ray_box(
        origin, direction, bounds, tmin, tmax, &und_t);
    printf("CASE|ray.%s|REF=%d|UNDERGROUND=%d|REF_T=%.17g|UNDERGROUND_T=%.17g\n",
           name, ref, und, ref_t, und_t);
    if (ref != expected || und != expected || ref != und) {
        fail(name, "ray acceptance differs from expected policy");
        return;
    }
    if (ref && (!same(ref_t, expected_t, 1e-12) ||
                !same(und_t, expected_t, 1e-12))) {
        fail(name, "ray entry distance differs from analytic result");
    }
}

static ParityView q12_view(void) {
    ParityView view = {0};
    view.projection = 1;
    view.fx_q16 = 256 * 65536;
    view.fy_q16 = 256 * 65536;
    view.rotation_q12[0] = 4096;
    view.rotation_q12[4] = 4096;
    view.rotation_q12[8] = 4096;
    return view;
}

int main(void) {
    const double identity[9] = {1, 0, 0, 0, 1, 0, 0, 0, 1};
    const double scaled_sheared[9] = {
        1.0, 0.25, -0.5,
        0.0, 1.5, 0.75,
        0.5, -0.25, 2.0,
    };
    const double singular[9] = {0};
    const double near_singular[9] = {1, 0, 0, 0, 1, 0, 0, 0, 0.009};
    const double threshold_reject[9] = {
        1, 0, 0, 0, 1, 0, 0, 0, 0.009999,
    };
    const double threshold_near_pass[9] = {
        1, 0, 0, 0, 1, 0, 0, 0, 0.0100001,
    };
    const double high_determinant[9] = {5, 0, 0, 0, 5, 0, 0, 0, 5};
    const double coefficient_reject[9] = {0.01, 0, 0, 0, 10, 0, 0, 0, 1};
    const double nonfinite[9] = {1, 0, 0, 0, NAN, 0, 0, 0, 1};
    const double translation[3] = {7, -3, 5};
    inverse_case("identity", identity, 1, 1);
    inverse_case("scaled_sheared_w1", scaled_sheared, 1, 1);
    inverse_translation_case(scaled_sheared, translation);
    inverse_case("singular_zero", singular, 0, 0);
    inverse_case("near_singular", near_singular, 0, 0);
    inverse_case("threshold_reject", threshold_reject, 0, 0);
    inverse_case("threshold_near_pass", threshold_near_pass, 0, 0);
    inverse_case("high_determinant_policy", high_determinant, 0, 1);
    inverse_case("coefficient_policy", coefficient_reject, 0, 0);
    inverse_case("nonfinite_reject", nonfinite, 0, 0);

    const double model[9] = {1, 0, 0, 0, 1, 0, 0, 0, 1};
    const double tr[3] = {0, 0, 0};
    const int16_t forward[6] = {-10, -10, 90, 10, 10, 110};
    const int16_t behind[6] = {-10, -10, -110, 10, 10, -90};
    const int16_t side[6] = {390, -10, 90, 410, 10, 110};
    const int16_t crossing[6] = {-1000, -1000, -10, 1000, 1000, 1000};
    ParityView basic = q12_view();
    box_case("forward_512x240", forward, model, tr, &basic,
             256, 120, 512, 240, 1);
    box_case("behind_512x240", behind, model, tr, &basic,
             256, 120, 512, 240, 0);
    box_case("side_512x240", side, model, tr, &basic,
             256, 120, 512, 240, 0);
    box_case("crossing_plane", crossing, model, tr, &basic,
             256, 120, 512, 240, 1);

    ParityView rotated = basic;
    rotated.rotation_q12[0] = -4096;
    rotated.rotation_q12[8] = -4096;
    box_case("eye_rotation_behind", behind, model, tr, &rotated,
             256, 120, 512, 240, 1);
    box_case("eye_rotation_forward", forward, model, tr, &rotated,
             256, 120, 512, 240, 0);

    ParityView translated = basic;
    translated.translation[0] = -400;
    box_case("eye_translation_side", side, model, tr, &translated,
             256, 120, 512, 240, 1);

    const double saturated_tr[3] = {40000, 0, 0};
    box_case("saturated_keep", forward, model, saturated_tr, &basic,
             256, 120, 512, 240, 1);

    ParityView precise = {0};
    precise.projection = 1;
    precise.precise = 1;
    precise.fx_q16 = 270 * 65536;
    precise.fy_q16 = 180 * 65536;
    precise.cx_delta_q16 = 12 * 65536;
    precise.cy_delta_q16 = -8 * 65536;
    precise.rotation[0] = precise.rotation[4] = precise.rotation[8] = 1.0;
    box_case("precise_asymmetric_forward", forward, model, tr, &precise,
             270, 60, 540, 120, 1);
    box_case("precise_mp_bounds_side", side, model, tr, &precise,
             270, 60, 540, 120, 0);
    box_case("invalid_dimensions_conservative", forward, model, tr, &precise,
             270, 60, 0, 120, 1);

    const int16_t center[3] = {100, 0, 100};
    const int mp = underground_parity_mp_box_visible(
        center, 10, model, tr, &precise, 270, 60, 540, 120);
    const int16_t expanded[6] = {90, -10, 90, 110, 10, 110};
    const int expanded_ref = reference_parity_box_visible(
        expanded, model, tr, &precise, 270, 60, 540, 120);
    printf("CASE|box.mp_sphere|UNDERGROUND=%d|REF_EXPANDED=%d\n",
           mp, expanded_ref);
    if (mp != 1 || expanded_ref != 1) {
        fail("mp_sphere",
             "MP sphere wrapper did not match expanded reference box");
    }
    const int16_t extreme[3] = {32760, 0, 100};
    if (underground_parity_mp_box_visible(
            extreme, 10, model, tr, &precise, 270, 60, 540, 120) != -1) {
        fail("mp_sphere_extreme", "overflowing sphere did not use fallback");
    }
    if (underground_parity_mp_box_visible(
            center, -1, model, tr, &precise, 270, 60, 540, 120) != -1) {
        fail("mp_sphere_negative", "negative radius did not use fallback");
    }

    const int16_t box[6] = {-10, -10, 100, 10, 10, 120};
    const double z[3] = {0, 0, 1};
    const double negative_z[3] = {0, 0, -1};
    const double x[3] = {1, 0, 0};
    const double origin[3] = {0, 0, 0};
    const double behind_origin[3] = {0, 0, 300};
    const double inside[3] = {0, 0, 110};
    const double outside_parallel[3] = {0, 20, 110};
    const double side_origin[3] = {100, 0, 0};
    ray_case("positive", origin, z, box, 0, 1000, 1, 100);
    ray_case("negative", behind_origin, negative_z, box, 0, 1000, 1, 180);
    ray_case("parallel_inside", inside, x, box, 0, 1000, 1, 0);
    ray_case("parallel_outside", outside_parallel, x, box,
             0, 1000, 0, SENTINEL);
    ray_case("origin_inside", inside, z, box, 0, 1000, 1, 0);
    ray_case("range_too_short", origin, z, box, 0, 50, 0, SENTINEL);
    ray_case("side_miss", side_origin, z, box, 0, 1000, 0, SENTINEL);
    ray_case("tmin_clamp", inside, z, box, 5, 20, 1, 5);
    ray_case("reversed_range", origin, z, box, 50, 10, 0, SENTINEL);
    const int16_t reversed_bounds[6] = {10, -10, 100, -10, 10, 120};
    ray_case("reversed_bounds", origin, z, reversed_bounds,
             0, 1000, 0, SENTINEL);
    const double nan_origin[3] = {NAN, 0, 0};
    const int16_t valid_bounds[6] = {-10, -10, 100, 10, 10, 120};
    double ignored_t = SENTINEL;
    if (reference_parity_ray_box(
            NULL, z, valid_bounds, 0, 1000, &ignored_t) ||
        underground_parity_ray_box(
            NULL, z, valid_bounds, 0, 1000, &ignored_t)) {
        fail("null_origin", "a null ray adapter input was accepted");
    }
    const int ref_nonfinite = reference_parity_ray_box(
        nan_origin, z, valid_bounds, 0, 1000, &ignored_t);
    const int und_nonfinite = underground_parity_ray_box(
        nan_origin, z, valid_bounds, 0, 1000, &ignored_t);
    printf("CASE|ray.nonfinite_origin_adapter|REF=%d|UNDERGROUND=%d\n",
           ref_nonfinite, und_nonfinite);
    if (ref_nonfinite) {
        fail("nonfinite_origin",
             "the reference adapter accepted a nonfinite origin");
    }
    if (reference_parity_ray_box(
            origin, z, valid_bounds, 0, INFINITY, &ignored_t) ||
        underground_parity_ray_box(
            origin, z, valid_bounds, 0, INFINITY, &ignored_t)) {
        fail("nonfinite_range", "a nonfinite range was accepted");
    }

    if (failures) {
        printf("SUMMARY|FAIL|%d\n", failures);
        return 1;
    }
    printf("SUMMARY|PASS|0\n");
    return 0;
}
