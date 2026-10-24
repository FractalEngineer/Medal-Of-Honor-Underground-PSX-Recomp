#include "weapon.h"

#include "vr_pose_math.h"

#include <limits.h>
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

uint64_t mohu_vr_weapon_fnv1a(const void* bytes, size_t size) {
    if (!bytes && size) {
        return 0u;
    }
    uint64_t hash = UINT64_C(1469598103934665603);
    const uint8_t* p = (const uint8_t*)bytes;
    for (size_t i = 0; i < size; ++i) {
        hash ^= p[i];
        hash *= UINT64_C(1099511628211);
    }
    return hash;
}

int mohu_vr_weapon_track_delta(const PSXModOpenXRHands* hands,
                               double units_per_meter, double rotation[9],
                               double translation[3]) {
    if (!hands || !rotation || !translation ||
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
    return 1;
}

int mohu_vr_weapon_relative_delta(const double current_rotation[9],
                                  const double current_translation[3],
                                  const double base_rotation[9],
                                  const double base_translation[3],
                                  double rotation[9], double translation[3]) {
    if (!current_rotation || !current_translation || !base_rotation ||
        !base_translation || !rotation || !translation) {
        return 0;
    }
    for (unsigned i = 0; i < 9u; ++i) {
        if (!isfinite(current_rotation[i]) ||
            !isfinite(base_rotation[i])) {
            return 0;
        }
    }
    for (unsigned i = 0; i < 3u; ++i) {
        if (!isfinite(current_translation[i]) ||
            !isfinite(base_translation[i])) {
            return 0;
        }
    }

    double base_t[9];
    for (unsigned row = 0; row < 3u; ++row) {
        for (unsigned col = 0; col < 3u; ++col) {
            base_t[row * 3u + col] = base_rotation[col * 3u + row];
        }
    }
    for (unsigned row = 0; row < 3u; ++row) {
        double base_shifted = 0.0;
        for (unsigned col = 0; col < 3u; ++col) {
            double value = 0.0;
            for (unsigned k = 0; k < 3u; ++k) {
                value += current_rotation[row * 3u + k] *
                         base_t[k * 3u + col];
            }
            if (!isfinite(value)) {
                return 0;
            }
            rotation[row * 3u + col] = value;
            base_shifted += value * base_translation[col];
        }
        translation[row] = current_translation[row] - base_shifted;
        if (!isfinite(translation[row])) {
            return 0;
        }
    }
    return 1;
}

int mohu_vr_weapon_compose_gte(const int16_t native_rotation[9],
                               const int32_t native_translation[3],
                               const double delta_rotation[9],
                               const int32_t pivot[3],
                               const double delta_translation[3],
                               int16_t rotation[9],
                               int32_t translation[3]) {
    if (!native_rotation || !native_translation || !delta_rotation ||
        !pivot || !delta_translation || !rotation || !translation) {
        return 0;
    }
    for (unsigned i = 0; i < 9u; ++i) {
        if (!isfinite(delta_rotation[i])) {
            return 0;
        }
    }
    for (unsigned i = 0; i < 3u; ++i) {
        if (!isfinite(delta_translation[i])) {
            return 0;
        }
    }

    for (unsigned row = 0; row < 3u; ++row) {
        for (unsigned col = 0; col < 3u; ++col) {
            double value = 0.0;
            for (unsigned k = 0; k < 3u; ++k) {
                value += delta_rotation[row * 3u + k] *
                         (double)native_rotation[k * 3u + col];
            }
            long rounded = lround(value);
            if (!isfinite(value) || rounded < INT16_MIN ||
                rounded > INT16_MAX) {
                return 0;
            }
            rotation[row * 3u + col] = (int16_t)rounded;
        }

        double shifted = (double)pivot[row];
        for (unsigned col = 0; col < 3u; ++col) {
            shifted += delta_rotation[row * 3u + col] *
                       ((double)native_translation[col] -
                        (double)pivot[col]);
        }
        shifted += delta_translation[row] * 4096.0;
        if (!isfinite(shifted) || shifted < INT32_MIN ||
            shifted > INT32_MAX) {
            return 0;
        }
        translation[row] = (int32_t)llround(shifted);
    }
    return 1;
}

int mohu_vr_weapon_rotate_node_q12(int16_t quaternion[4],
                                   const double rotation[9]) {
    if (!quaternion || !rotation) {
        return 0;
    }
    double trace =
        rotation[0] + rotation[4] + rotation[8];
    double qd[4];
    if (trace > 0.0) {
        double s = sqrt(trace + 1.0) * 2.0;
        qd[3] = 0.25 * s;
        qd[0] = (rotation[7] - rotation[5]) / s;
        qd[1] = (rotation[2] - rotation[6]) / s;
        qd[2] = (rotation[3] - rotation[1]) / s;
    } else if (rotation[0] > rotation[4] &&
               rotation[0] > rotation[8]) {
        double s =
            sqrt(1.0 + rotation[0] - rotation[4] - rotation[8]) * 2.0;
        qd[3] = (rotation[7] - rotation[5]) / s;
        qd[0] = 0.25 * s;
        qd[1] = (rotation[1] + rotation[3]) / s;
        qd[2] = (rotation[2] + rotation[6]) / s;
    } else if (rotation[4] > rotation[8]) {
        double s =
            sqrt(1.0 + rotation[4] - rotation[0] - rotation[8]) * 2.0;
        qd[3] = (rotation[2] - rotation[6]) / s;
        qd[0] = (rotation[1] + rotation[3]) / s;
        qd[1] = 0.25 * s;
        qd[2] = (rotation[5] + rotation[7]) / s;
    } else {
        double s =
            sqrt(1.0 + rotation[8] - rotation[0] - rotation[4]) * 2.0;
        qd[3] = (rotation[3] - rotation[1]) / s;
        qd[0] = (rotation[2] + rotation[6]) / s;
        qd[1] = (rotation[5] + rotation[7]) / s;
        qd[2] = 0.25 * s;
    }

    double qn[4];
    double norm = 0.0;
    for (unsigned i = 0; i < 4u; ++i) {
        qn[i] = (double)quaternion[i] / 4096.0;
        norm += qn[i] * qn[i];
    }
    if (!isfinite(norm) || norm < 0.75 || norm > 1.25) {
        return 0;
    }
    norm = sqrt(norm);
    for (unsigned i = 0; i < 4u; ++i) {
        qn[i] /= norm;
    }

    const double x = qd[3] * qn[0] + qd[0] * qn[3] +
                     qd[1] * qn[2] - qd[2] * qn[1];
    const double y = qd[3] * qn[1] - qd[0] * qn[2] +
                     qd[1] * qn[3] + qd[2] * qn[0];
    const double z = qd[3] * qn[2] + qd[0] * qn[1] -
                     qd[1] * qn[0] + qd[2] * qn[3];
    const double w = qd[3] * qn[3] - qd[0] * qn[0] -
                     qd[1] * qn[1] - qd[2] * qn[2];
    const double values[4] = {x, y, z, w};
    for (unsigned i = 0; i < 4u; ++i) {
        long rounded = lround(values[i] * 4096.0);
        if (!isfinite(values[i]) || rounded < INT16_MIN ||
            rounded > INT16_MAX) {
            return 0;
        }
        quaternion[i] = (int16_t)rounded;
    }
    return 1;
}
