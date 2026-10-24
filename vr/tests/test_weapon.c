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

static void identity_view(PSXModRenderView* view) {
    memset(view, 0, sizeof *view);
    view->struct_size = sizeof *view;
    for (unsigned i = 0; i < 3u; ++i) {
        view->rotation_q12[i * 3u + i] = 4096;
        view->rotation[i * 3u + i] = 1.0;
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
        for (size_t j = 0; j < i; ++j) {
            CHECK(mohu_vr_weapon_profile_at(j)->id != profile->id);
        }
    }
    CHECK(!mohu_vr_weapon_profile_at(mohu_vr_weapon_profile_count()));
    CHECK(!mohu_vr_weapon_profile_find(2u));
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

    PSXModRenderView base;
    PSXModRenderView tracked;
    PSXModOpenXRHands hands;
    const double pivot[3] = {250.0, -200.0, 100.0};
    identity_view(&base);
    valid_hands(&hands);
    hands.pose[1][PSX_MOD_XR_GRIP_POSE].position_m[0] = 1.0;
    hands.pose[1][PSX_MOD_XR_GRIP_POSE].position_m[1] = 2.0;
    hands.pose[1][PSX_MOD_XR_GRIP_POSE].position_m[2] = 3.0;
    CHECK(mohu_vr_weapon_track_view(
        &hands, &base, 1000.0, pivot, &tracked));
    for (unsigned i = 0; i < 3u; ++i) {
        CHECK(tracked.rotation_q12[i * 3u + i] == 4096);
        CHECK(fabs(tracked.rotation[i * 3u + i] - 1.0) < 1e-12);
    }
    CHECK(tracked.precise == 1u);
    CHECK(tracked.projection == base.projection);

    hands.age_ms = 151u;
    CHECK(!mohu_vr_weapon_track_view(
        &hands, &base, 1000.0, pivot, &tracked));
    hands.age_ms = 10u;
    hands.focused = 0u;
    CHECK(!mohu_vr_weapon_track_view(
        &hands, &base, 1000.0, pivot, &tracked));
    hands.focused = 1u;
    hands.pose[1][PSX_MOD_XR_AIM_POSE].flags = 1u;
    CHECK(!mohu_vr_weapon_track_view(
        &hands, &base, 1000.0, pivot, &tracked));
    hands.pose[1][PSX_MOD_XR_AIM_POSE].flags = 3u;
    CHECK(!mohu_vr_weapon_track_view(
        &hands, &base, NAN, pivot, &tracked));
    hands.pose[1][PSX_MOD_XR_AIM_POSE].orientation_xyzw[3] = 0.0;
    CHECK(!mohu_vr_weapon_track_view(
        &hands, &base, 1000.0, pivot, &tracked));

    puts("PASS: weapon profiles, node guard, pose validity and stale fallback");
    return 0;
}
