#include "weapon.h"

#include "vr_pose_math.h"

#include <math.h>
#include <string.h>

static const MohuVrWeaponProfile k_weapon_profiles[] = {
    {0u, 1u, 0u, "P38 pistol"},
    {1u, 1u, 1u, "MP40"},
    {4u, 2u, 2u, "shotgun"},
    {5u, 3u, 2u, "scoped rifle"},
    {8u, 2u, 0u, "Colt .45"},
    {9u, 3u, 0u, "silenced pistol"},
    {10u, 1u, 3u, "stick grenade"},
    {12u, 4u, 0u, "M1 Garand"},
    {13u, 4u, 2u, "Panzerfaust"},
    {14u, 3u, 1u, "crossbow"},
    {15u, 2u, 3u, "petrol bomb"},
    {16u, 2u, 1u, "Sten"},
    {17u, 1u, 2u, "StG44"},
};

static const uint16_t k_node_counts[MOHU_VR_WEAPON_NODE_COUNT] = {
    0u, 2u, 13u, 11u, 6u, 12u, 12u, 6u, 5u, 0u, 4u,
    0u, 0u, 39u, 1u, 11u, 6u, 8u, 1u, 11u, 6u, 8u,
};

size_t mohu_vr_weapon_profile_count(void) {
    return sizeof k_weapon_profiles / sizeof k_weapon_profiles[0];
}

const MohuVrWeaponProfile* mohu_vr_weapon_profile_at(size_t index) {
    return index < mohu_vr_weapon_profile_count() ? &k_weapon_profiles[index]
                                                  : NULL;
}

const MohuVrWeaponProfile* mohu_vr_weapon_profile_find(uint8_t id) {
    for (size_t i = 0; i < mohu_vr_weapon_profile_count(); ++i) {
        if (k_weapon_profiles[i].id == id) {
            return &k_weapon_profiles[i];
        }
    }
    return NULL;
}

int mohu_vr_weapon_node_layout_valid(const uint16_t counts[22],
                                     unsigned count) {
    if (!counts || count != MOHU_VR_WEAPON_NODE_COUNT) {
        return 0;
    }
    return memcmp(counts, k_node_counts, sizeof k_node_counts) == 0;
}

int mohu_vr_weapon_track_view(const PSXModOpenXRHands* hands,
                              const PSXModRenderView* base,
                              double units_per_meter,
                              const double pivot[3],
                              PSXModRenderView* out) {
    if (!hands || !base || !pivot || !out ||
        hands->struct_size != sizeof *hands || !hands->focused ||
        !hands->origin_valid || hands->age_ms > 150u ||
        !isfinite(units_per_meter) || units_per_meter < 1.0 ||
        units_per_meter > 65536.0) {
        return 0;
    }

    const PSXModTrackedPose* grip =
        &hands->pose[1][PSX_MOD_XR_GRIP_POSE];
    const PSXModTrackedPose* aim =
        &hands->pose[1][PSX_MOD_XR_AIM_POSE];
    if (!grip->active || !aim->active ||
        (grip->flags & 3u) != 3u || (aim->flags & 3u) != 3u) {
        return 0;
    }

    double rotation[9];
    double translation[3];
    double aim_q[4];
    double grip_p[3];
    for (unsigned i = 0; i < 4u; ++i) {
        aim_q[i] = aim->orientation_xyzw[i];
    }
    for (unsigned i = 0; i < 3u; ++i) {
        grip_p[i] = grip->position_m[i];
    }
    if (!vr_pose_to_transform(aim_q, grip_p,
                              hands->origin_orientation_xyzw,
                              hands->origin_position_m, units_per_meter,
                              rotation, translation)) {
        return 0;
    }

    *out = *base;
    for (unsigned row = 0; row < 3u; ++row) {
        double shifted = translation[row];
        for (unsigned col = 0; col < 3u; ++col) {
            shifted -= rotation[row * 3u + col] * pivot[col];
            out->rotation_q12[row * 3u + col] =
                (int32_t)lround(rotation[row * 3u + col] * 4096.0);
        }
        if (!isfinite(shifted) || fabs(shifted) > 32767.0) {
            return 0;
        }
        out->translation[row] = (int32_t)lround(shifted);
        out->translation_precise[row] = shifted;
    }
    memcpy(out->rotation, rotation, sizeof rotation);
    out->precise = 1u;
    return 1;
}
