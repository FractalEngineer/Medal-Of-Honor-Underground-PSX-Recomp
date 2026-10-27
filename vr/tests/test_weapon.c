#include "weapon.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#define CHECK(value)                                                          \
    do {                                                                      \
        if (!(value)) {                                                       \
            fprintf(stderr, "FAIL line %d\n", __LINE__);                      \
            return 1;                                                         \
        }                                                                     \
    } while (0)

static const uint16_t k_expected_nodes[MOHU_VR_WEAPON_NODE_COUNT] = {
    0, 2, 13, 11, 6, 12, 12, 6, 5, 0, 4,
    0, 0, 39, 1, 11, 6, 8, 1, 11, 6, 8,
};

static void identity_matrix(double matrix[9]) {
    memset(matrix, 0, 9u * sizeof matrix[0]);
    for (unsigned i = 0; i < 3u; ++i) {
        matrix[i * 3u + i] = 1.0;
    }
}

static void valid_hands(PSXModOpenXRHands* hands) {
    memset(hands, 0, sizeof *hands);
    hands->struct_size = sizeof *hands;
    hands->focused = 1u;
    hands->origin_valid = 1u;
    hands->age_ms = 10u;
    hands->origin_orientation_xyzw[3] = 1.0;
    for (unsigned pose = PSX_MOD_XR_GRIP_POSE; pose <= PSX_MOD_XR_AIM_POSE;
         ++pose) {
        hands->pose[1][pose].active = 1u;
        hands->pose[1][pose].flags = 3u;
        hands->pose[1][pose].orientation_xyzw[3] = 1.0;
    }
}

int main(void) {
    CHECK(mohu_vr_weapon_profile_count() == 13u);
    for (size_t i = 0; i < mohu_vr_weapon_profile_count(); ++i) {
        const MohuVrWeaponProfile* profile = mohu_vr_weapon_profile_at(i);
        CHECK(profile && profile->name && mohu_vr_weapon_profile_find(profile->id));
        CHECK(profile->geometry_fnv32 && profile->node_count <= 32u);
        CHECK(profile->calibration && profile->calibration->provisional == 1u);
        CHECK(profile->calibration->model_units_per_metre > 1.0);
        CHECK(profile->calibration->reference_length_m > 0.0);
        CHECK(profile->gun_face_count &&
              profile->gun_face_count < profile->face_count);
        CHECK(profile->gun_vertex_count);
        CHECK(mohu_vr_weapon_mesh_layout_valid(profile, profile->mesh_magic,
            profile->face_count, profile->vertices, profile->node_count));
        CHECK(!mohu_vr_weapon_mesh_layout_valid(profile, 0x00160024u,
            profile->face_count, k_expected_nodes, MOHU_VR_WEAPON_NODE_COUNT));
        uint16_t vertices[MOHU_VR_WEAPON_FP_MAX_NODES];
        memcpy(vertices, profile->vertices, sizeof vertices);
        ++vertices[profile->node_count - 1u];
        CHECK(!mohu_vr_weapon_mesh_layout_valid(profile, profile->mesh_magic,
            profile->face_count, vertices, profile->node_count));
        CHECK(!mohu_vr_weapon_mesh_layout_valid(profile, profile->mesh_magic,
            profile->face_count + 1u, profile->vertices, profile->node_count));
        for (size_t j = 0; j < i; ++j) {
            CHECK(mohu_vr_weapon_profile_at(j)->id != profile->id);
        }
        unsigned gun_vertices = 0;
        for (unsigned node = 0; node < profile->node_count; ++node) {
            const int whole_node =
                (profile->gun_nodes & (UINT32_C(1) << node)) != 0u;
            if (whole_node) {
                gun_vertices += profile->vertices[node];
            } else if (node == profile->partial_node) {
                for (unsigned vertex = 0;
                     vertex < profile->vertices[node]; ++vertex) {
                    if ((profile->partial_vertices[vertex / 64u] >>
                         (vertex % 64u)) & UINT64_C(1)) {
                        ++gun_vertices;
                    }
                }
            }
            for (unsigned vertex = 0; vertex < profile->vertices[node];
                 ++vertex) {
                const int partial = node == profile->partial_node &&
                    ((profile->partial_vertices[vertex / 64u] >>
                      (vertex % 64u)) & UINT64_C(1));
                CHECK(mohu_vr_weapon_gun_vertex(profile, node, vertex) ==
                      (whole_node || partial));
            }
            CHECK(!mohu_vr_weapon_gun_vertex(
                profile, node, profile->vertices[node]));
        }
        CHECK(gun_vertices == profile->gun_vertex_count);
        CHECK(!mohu_vr_weapon_gun_vertex(profile, profile->node_count, 0u));
    }
    CHECK(!mohu_vr_weapon_profile_at(mohu_vr_weapon_profile_count()));
    CHECK(!mohu_vr_weapon_profile_find(2u));
    CHECK(mohu_vr_weapon_gun_vertex(
        mohu_vr_weapon_profile_find(0u), 11u, 6u));
    CHECK(mohu_vr_weapon_gun_vertex(
        mohu_vr_weapon_profile_find(0u), 11u, 32u));
    CHECK(!mohu_vr_weapon_gun_vertex(
        mohu_vr_weapon_profile_find(0u), 11u, 33u));
    CHECK(mohu_vr_weapon_gun_vertex(
        mohu_vr_weapon_profile_find(9u), 11u, 17u));
    CHECK(!mohu_vr_weapon_gun_vertex(
        mohu_vr_weapon_profile_find(9u), 11u, 18u));
    CHECK(mohu_vr_weapon_gun_vertex(
        mohu_vr_weapon_profile_find(9u), 11u, 26u));
    CHECK(mohu_vr_weapon_gun_vertex(
        mohu_vr_weapon_profile_find(1u), 26u, 0u));
    CHECK(!mohu_vr_weapon_gun_vertex(
        mohu_vr_weapon_profile_find(1u), 22u, 0u));
    {
        const MohuVrWeaponCalibration* calibration =
            mohu_vr_weapon_calibration_find(0u);
        const double grip[3] = {
            76.555555555556, 100.777777777778, 287.888888888889,
        };
        const double muzzle[3] = {81.8, 110.6, 447.6};
        const double right[3] = {
            0.999745337201, 0.0, -0.022566806250,
        };
        const double up[3] = {
            0.000331387923, -0.999892173236, 0.014681010987,
        };
        const double forward[3] = {
            0.022564372944, 0.014684750646, 0.999637537897,
        };
        CHECK(calibration && calibration->provisional == 1u);
        for (unsigned axis = 0; axis < 3u; ++axis) {
            CHECK(fabs(calibration->grip_pivot[axis] - grip[axis]) < 1e-11);
            CHECK(fabs(calibration->muzzle[axis] - muzzle[axis]) < 1e-11);
            CHECK(fabs(calibration->right[axis] - right[axis]) < 1e-12);
            CHECK(fabs(calibration->up[axis] - up[axis]) < 1e-12);
            CHECK(fabs(calibration->forward[axis] - forward[axis]) < 1e-12);
        }
        CHECK(fabs(calibration->model_units_per_metre -
                   760.489674616524) < 1e-11);
        CHECK(fabs(calibration->reference_length_m - 0.216) < 1e-12);
        CHECK(fabs(calibration->forward_span_units -
                   164.265769717169) < 1e-11);
        const double axes[3][3] = {
            {calibration->right[0], calibration->right[1],
             calibration->right[2]},
            {calibration->up[0], calibration->up[1], calibration->up[2]},
            {calibration->forward[0], calibration->forward[1],
             calibration->forward[2]},
        };
        for (unsigned i = 0; i < 3u; ++i) {
            const double length =
                sqrt(axes[i][0] * axes[i][0] +
                     axes[i][1] * axes[i][1] +
                     axes[i][2] * axes[i][2]);
            CHECK(fabs(length - 1.0) < 1e-11);
            for (unsigned j = i + 1u; j < 3u; ++j) {
                const double dot =
                    axes[i][0] * axes[j][0] +
                    axes[i][1] * axes[j][1] +
                    axes[i][2] * axes[j][2];
                CHECK(fabs(dot) < 1e-11);
            }
        }
        const double grip_to_muzzle[3] = {
            muzzle[0] - grip[0], muzzle[1] - grip[1], muzzle[2] - grip[2],
        };
        const double projected =
            grip_to_muzzle[0] * forward[0] +
            grip_to_muzzle[1] * forward[1] +
            grip_to_muzzle[2] * forward[2];
        CHECK(projected > 0.0);
        CHECK(fabs(calibration->forward_span_units /
                       calibration->model_units_per_metre -
                   calibration->reference_length_m) < 1e-11);
        for (unsigned id = 0u; id < 255u; ++id) {
            const MohuVrWeaponProfile* profile =
                mohu_vr_weapon_profile_find((uint8_t)id);
            CHECK(profile
                ? mohu_vr_weapon_calibration_find((uint8_t)id) ==
                      profile->calibration
                : !mohu_vr_weapon_calibration_find((uint8_t)id));
        }
    }
    CHECK(!mohu_vr_weapon_mesh_layout_valid(NULL, 0, 0, NULL, 0));
    CHECK(mohu_vr_weapon_node_layout_valid(
        k_expected_nodes, MOHU_VR_WEAPON_NODE_COUNT));

    uint16_t wrong[MOHU_VR_WEAPON_NODE_COUNT];
    memcpy(wrong, k_expected_nodes, sizeof wrong);
    wrong[13]++;
    CHECK(!mohu_vr_weapon_node_layout_valid(
        wrong, MOHU_VR_WEAPON_NODE_COUNT));
    CHECK(!mohu_vr_weapon_node_layout_valid(
        k_expected_nodes, MOHU_VR_WEAPON_NODE_COUNT - 1u));
    CHECK(!mohu_vr_weapon_node_layout_valid(NULL,
                                            MOHU_VR_WEAPON_NODE_COUNT));

    PSXModOpenXRHands hands;
    valid_hands(&hands);
    hands.pose[1][PSX_MOD_XR_GRIP_POSE].position_m[0] = 1.0;
    hands.pose[1][PSX_MOD_XR_GRIP_POSE].position_m[1] = 2.0;
    hands.pose[1][PSX_MOD_XR_GRIP_POSE].position_m[2] = 3.0;
    double current_rotation[9];
    double current_translation[3];
    CHECK(mohu_vr_weapon_track_delta(
        &hands, 1000.0, current_rotation, current_translation));
    for (unsigned i = 0; i < 3u; ++i) {
        CHECK(fabs(current_rotation[i * 3u + i] - 1.0) < 1e-12);
    }
    CHECK(fabs(current_translation[0] - 1000.0) < 1e-9);
    CHECK(fabs(current_translation[1] + 2000.0) < 1e-9);
    CHECK(fabs(current_translation[2] + 3000.0) < 1e-9);

    double base_rotation[9];
    const double base_translation[3] = {25.0, -50.0, 100.0};
    identity_matrix(base_rotation);
    double relative_rotation[9];
    double relative_translation[3];
    CHECK(mohu_vr_weapon_relative_delta(
        current_rotation, current_translation, base_rotation,
        base_translation, relative_rotation, relative_translation));
    CHECK(fabs(relative_rotation[0] - 1.0) < 1e-12);
    CHECK(fabs(relative_translation[0] - 975.0) < 1e-9);
    CHECK(fabs(relative_translation[1] + 1950.0) < 1e-9);
    CHECK(fabs(relative_translation[2] + 3100.0) < 1e-9);

    const int16_t native_rotation[9] = {
        4096, 0, 0, 0, 4096, 0, 0, 0, 4096,
    };
    const int32_t native_translation[3] = {100, -200, 300};
    const int32_t pivot[3] = {100, -200, 300};
    const double zero_translation[3] = {0.0, 0.0, 0.0};
    int16_t composed_rotation[9];
    int32_t composed_translation[3];
    identity_matrix(current_rotation);
    CHECK(mohu_vr_weapon_compose_gte(
        native_rotation, native_translation, current_rotation, pivot,
        zero_translation, composed_rotation, composed_translation));
    CHECK(memcmp(composed_rotation, native_rotation,
                 sizeof native_rotation) == 0);
    CHECK(memcmp(composed_translation, native_translation,
                 sizeof native_translation) == 0);
    current_translation[0] = 12.0;
    current_translation[1] = -34.0;
    current_translation[2] = 56.0;
    CHECK(mohu_vr_weapon_compose_gte(
        native_rotation, native_translation, current_rotation, pivot,
        current_translation, composed_rotation, composed_translation));
    CHECK(composed_translation[0] == 100 + 12 * 4096);
    CHECK(composed_translation[1] == -200 - 34 * 4096);
    CHECK(composed_translation[2] == 300 + 56 * 4096);

    uint32_t control[8] = {4096u, 0u, 4096u, 0u, 0xABCD1000u, 100u,
                           (uint32_t)-200, 300u};
    uint32_t original_control[8];
    memcpy(original_control, control, sizeof control);
    CHECK(mohu_vr_weapon_compose_gte_control(control, current_rotation,
                                             pivot, zero_translation));
    CHECK(memcmp(control, original_control, sizeof control) == 0);
    CHECK(mohu_vr_weapon_compose_gte_control(control, current_rotation,
                                             pivot, current_translation));
    CHECK(control[4] == 0xABCD1000u);
    CHECK((int32_t)control[5] == 112);
    CHECK((int32_t)control[6] == -234);
    CHECK((int32_t)control[7] == 356);
    memcpy(original_control, control, sizeof control);
    current_translation[0] = 1e12;
    CHECK(!mohu_vr_weapon_compose_gte_control(control, current_rotation,
                                              pivot, current_translation));
    CHECK(memcmp(control, original_control, sizeof control) == 0);

    int16_t node_quaternion[4] = {0, 0, 0, 4096};
    const double quarter_y[9] = {
        0.0, 0.0, 1.0, 0.0, 1.0, 0.0, -1.0, 0.0, 0.0,
    };
    CHECK(mohu_vr_weapon_rotate_node_q12(
        node_quaternion, quarter_y));
    CHECK(fabs(fabs((double)node_quaternion[1]) - 2896.0) < 2.0);
    CHECK(fabs(fabs((double)node_quaternion[3]) - 2896.0) < 2.0);

    uint32_t absolute_control[8] = {
        0xFFAE600Au, 0xFFF8F847u, 0xFD323C0Du, 0x017D0294u,
        0x00001FE8u, 0u, 0u, 0u,
    };
    uint32_t absolute_original[8];
    memcpy(absolute_original, absolute_control, sizeof absolute_control);
    const double absolute_pivot[3] = {98.0, 296.0, 193.0};
    const double absolute_zero[3] = {0.0, 0.0, 0.0};
    identity_matrix(current_rotation);
    CHECK(mohu_vr_weapon_compose_absolute_gte_control(
        absolute_control, current_rotation, absolute_zero, absolute_pivot));
    CHECK(memcmp(absolute_control, absolute_original,
                 sizeof absolute_control) == 0);

    const double absolute_translation[3] = {12.0, -34.0, 56.0};
    CHECK(mohu_vr_weapon_compose_absolute_gte_control(
        absolute_control, quarter_y, absolute_translation, absolute_pivot));
    int16_t absolute_rt[9];
    int32_t absolute_tr[3];
    for (unsigned i = 0; i < 9u; ++i) {
        absolute_rt[i] =
            (int16_t)(absolute_control[i / 2u] >> ((i & 1u) * 16u));
    }
    for (unsigned i = 0; i < 3u; ++i) {
        absolute_tr[i] = (int32_t)absolute_control[5u + i];
    }
    const double inverse_native[9] = {
        1.655236093e-01, -1.097802097e-04, 4.005403446e-02,
        -5.373667671e-04, 2.658623159e-01, 2.324029979e-02,
        -1.334976070e-02, -1.239239562e-02, 4.971486022e-01,
    };
    double model_pivot[3];
    for (unsigned row = 0; row < 3u; ++row) {
        model_pivot[row] = 0.0;
        for (unsigned col = 0; col < 3u; ++col) {
            model_pivot[row] +=
                inverse_native[row * 3u + col] * absolute_pivot[col];
        }
    }
    double pivot_camera[3];
    for (unsigned row = 0; row < 3u; ++row) {
        pivot_camera[row] = (double)absolute_tr[row];
        for (unsigned col = 0; col < 3u; ++col) {
            pivot_camera[row] +=
                absolute_rt[row * 3u + col] / 4096.0 * model_pivot[col];
        }
        CHECK(fabs(pivot_camera[row] -
                   (absolute_pivot[row] + absolute_translation[row])) < 0.5);
    }
    memcpy(absolute_original, absolute_control, sizeof absolute_control);
    current_rotation[0] = NAN;
    CHECK(!mohu_vr_weapon_compose_absolute_gte_control(
        absolute_control, current_rotation, absolute_translation,
        absolute_pivot));
    CHECK(memcmp(absolute_control, absolute_original,
                 sizeof absolute_control) == 0);

    hands.age_ms = 151u;
    CHECK(!mohu_vr_weapon_track_delta(
        &hands, 1000.0, current_rotation, current_translation));
    hands.age_ms = 10u;
    hands.focused = 0u;
    CHECK(!mohu_vr_weapon_track_delta(
        &hands, 1000.0, current_rotation, current_translation));
    hands.focused = 1u;
    hands.pose[1][PSX_MOD_XR_AIM_POSE].flags = 1u;
    CHECK(!mohu_vr_weapon_track_delta(
        &hands, 1000.0, current_rotation, current_translation));
    hands.pose[1][PSX_MOD_XR_AIM_POSE].flags = 3u;
    CHECK(!mohu_vr_weapon_track_delta(
        &hands, NAN, current_rotation, current_translation));
    hands.pose[1][PSX_MOD_XR_AIM_POSE].orientation_xyzw[3] = 0.0;
    CHECK(!mohu_vr_weapon_track_delta(
        &hands, 1000.0, current_rotation, current_translation));

    const uint32_t flash_xy[4] = {
        0x00580113u, 0x005D0140u, 0x0077010Cu, 0x007C0139u,
    };
    uint32_t flash_out[4];
    CHECK(mohu_vr_weapon_translate_flash_quad(
        flash_xy, 289.0, 95.0, flash_out));
    const uint32_t flash_expected[4] = {
        0x004D010Eu, 0x0052013Bu, 0x006C0107u, 0x00710134u,
    };
    CHECK(memcmp(flash_out, flash_expected, sizeof flash_out) == 0);
    CHECK(!mohu_vr_weapon_translate_flash_quad(
        flash_xy, NAN, 95.0, flash_out));
    CHECK(!mohu_vr_weapon_translate_flash_quad(
        flash_xy, 1023.0, 1023.0, flash_out));

    puts("PASS: weapon profiles, node guard, tracked affine and stale fallback");
    return 0;
}
