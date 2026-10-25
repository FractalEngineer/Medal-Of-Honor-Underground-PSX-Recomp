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
    }
    CHECK(!mohu_vr_weapon_profile_at(mohu_vr_weapon_profile_count()));
    CHECK(!mohu_vr_weapon_profile_find(2u));
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

    puts("PASS: weapon profiles, node guard, tracked affine and stale fallback");
    return 0;
}
