#include "weapon.h"

#include "vr_pose_math.h"

#include <limits.h>
#include <math.h>
#include <string.h>

static const MohuVrWeaponCalibration k_p38_calibration = {
    {76.555555555556, 100.777777777778, 287.888888888889},
    {81.800000000000, 110.600000000000, 447.600000000000},
    {0.999745337201, 0.000000000000, -0.022566806250},
    {0.000331387923, -0.999892173236, 0.014681010987},
    {0.022564372944, 0.014684750646, 0.999637537897},
    760.489674616524,
    0.216000000000,
    164.265769717169,
    1u,
};

static const MohuVrWeaponProfile k_weapon_profiles[] = {
    {0u, 1u, 0u, "P38 pistol", 0xe0007u, 0x8544f8b9u, 354u, 14u,
     {0, 0, 0, 0, 0, 0, 0, 0, 0, 20, 0, 149, 0, 69},
     &k_p38_calibration},
    {1u, 1u, 1u, "MP40", 0x200007u, 0x8095cafbu, 316u, 32u,
     {0, 0, 0, 0, 0, 0, 0, 0, 0, 14, 21, 5, 4, 4, 4, 0, 4, 4, 0, 3, 2, 0, 1, 0, 0, 0, 102, 0, 0, 6, 0, 16},
     NULL},
    {4u, 2u, 2u, "Shotgun", 0x150007u, 0x805bd649u, 306u, 21u,
     {0, 0, 0, 0, 0, 0, 0, 0, 14, 21, 14, 0, 5, 8, 0, 0, 0, 0, 99, 0, 38},
     NULL},
    {5u, 3u, 2u, "Scoped rifle", 0x1a0007u, 0x9f7ada24u, 383u, 26u,
     {0, 0, 0, 0, 0, 0, 0, 0, 14, 21, 22, 4, 4, 4, 4, 4, 0, 1, 0, 0, 0, 0, 145, 0, 0, 14},
     NULL},
    {8u, 2u, 0u, "Colt .45", 0xe0007u, 0x267e86aau, 303u, 14u,
     {0, 0, 0, 0, 0, 0, 0, 0, 0, 20, 0, 92, 0, 68},
     NULL},
    {9u, 3u, 0u, "Silenced pistol", 0xe0007u, 0x65f76c5du, 310u, 14u,
     {0, 0, 0, 0, 0, 0, 0, 0, 0, 20, 0, 122, 0, 57},
     NULL},
    {10u, 1u, 3u, "Stick grenade", 0x180007u, 0xddce0989u, 341u, 24u,
     {0, 0, 0, 0, 0, 0, 0, 0, 19, 16, 21, 7, 4, 4, 5, 8, 3, 5, 4, 8, 1, 0, 0, 58},
     NULL},
    {12u, 4u, 0u, "M1 Garand", 0x170007u, 0x450f78dcu, 280u, 23u,
     {0, 0, 0, 0, 0, 0, 0, 0, 12, 16, 17, 5, 4, 4, 4, 2, 0, 3, 0, 0, 0, 0, 136},
     NULL},
    {13u, 4u, 2u, "Panzerfaust", 0x1f0007u, 0x68cbd37u, 333u, 31u,
     {0, 0, 0, 0, 0, 0, 0, 0, 14, 21, 21, 5, 4, 4, 4, 0, 4, 4, 0, 3, 0, 1, 2, 0, 0, 0, 0, 70, 10, 0, 36},
     NULL},
    {14u, 3u, 1u, "Crossbow", 0x1d0007u, 0xdff185cau, 290u, 29u,
     {0, 0, 0, 0, 0, 0, 0, 0, 0, 21, 40, 0, 0, 0, 20, 0, 0, 18, 14, 21, 0, 14, 0, 45, 0, 19, 6, 0, 21},
     NULL},
    {15u, 2u, 3u, "Petrol bomb", 0x1c0007u, 0x7ca0dbecu, 397u, 28u,
     {0, 0, 0, 0, 0, 0, 0, 0, 21, 14, 23, 8, 5, 8, 0, 8, 4, 0, 3, 1, 0, 2, 0, 0, 0, 92, 5, 2},
     NULL},
    {16u, 2u, 1u, "Sten", 0x1f0007u, 0x29d5bc18u, 354u, 31u,
     {0, 0, 0, 0, 0, 0, 0, 0, 0, 21, 21, 5, 4, 4, 4, 0, 4, 4, 0, 3, 2, 0, 1, 0, 0, 0, 135, 0, 0, 17, 14},
     NULL},
    {17u, 1u, 2u, "StG44", 0x200007u, 0xf467028bu, 352u, 32u,
     {0, 0, 0, 0, 0, 0, 0, 0, 0, 21, 21, 5, 4, 4, 4, 0, 4, 4, 0, 3, 0, 1, 2, 0, 0, 0, 0, 132, 0, 16, 0, 13},
     NULL},
};

static const uint16_t k_node_counts[MOHU_VR_WEAPON_NODE_COUNT] = {
    0u, 2u, 13u, 11u, 6u, 12u, 12u, 6u, 5u, 0u, 4u,
    0u, 0u, 39u, 1u, 11u, 6u, 8u, 1u, 11u, 6u, 8u,
};

int mohu_vr_weapon_calibrated_control(
    uint32_t control[8], const double hand_rotation[9],
    const double hand_translation[3], double units_per_metre,
    const MohuVrWeaponCalibration* c) {
    if (!control || !hand_rotation || !hand_translation || !c ||
        !isfinite(units_per_metre) || units_per_metre < 1 ||
        units_per_metre > 65536 || !isfinite(c->model_units_per_metre) ||
        c->model_units_per_metre < 1) return 0;
    const double scale = units_per_metre / c->model_units_per_metre;
    uint32_t result[8];
    memcpy(result, control, sizeof result);
    int16_t rt[9];
    /* Measured +up is -Y in PSX camera coordinates. Use right/down/forward
     * rows to keep the model-to-hand basis right handed. */
    for (unsigned row=0; row<3; ++row) {
        for (unsigned col=0; col<3; ++col) {
            const double value = scale * 4096.0 *
                (hand_rotation[row*3] * c->right[col] -
                 hand_rotation[row*3+1] * c->up[col] +
                 hand_rotation[row*3+2] * c->forward[col]);
            if (!isfinite(value) || value < INT16_MIN || value > INT16_MAX) return 0;
            rt[row*3+col] = (int16_t)lround(value);
        }
        double value = hand_translation[row];
        for (unsigned k=0; k<3; ++k)
            value -= (double)rt[row*3+k] / 4096.0 * c->grip_pivot[k];
        if (!isfinite(value) || value < INT32_MIN || value > INT32_MAX) return 0;
        result[row+5] = (uint32_t)(int32_t)llround(value);
    }
    for (unsigned i=0; i<4; ++i)
        result[i] = (uint16_t)rt[2*i] | ((uint32_t)(uint16_t)rt[2*i+1] << 16);
    result[4] = (control[4] & 0xFFFF0000u) | (uint16_t)rt[8];
    memcpy(control, result, sizeof result);
    return 1;
}

int mohu_vr_weapon_muzzle_shot(
    const uint32_t control[8], const MohuVrWeaponCalibration* c,
    const double inverse[9], const double camera_translation[3],
    int32_t position[3], int32_t angles[3]) {
    if (!control || !c || !inverse || !camera_translation || !position || !angles)
        return 0;
    double muzzle[3], axis[3];
    for (unsigned row=0; row<3; ++row) {
        muzzle[row] = (int32_t)control[5+row];
        axis[row] = 0;
        for (unsigned col=0; col<3; ++col) {
            const unsigned i=row*3+col;
            const double r = (int16_t)(control[i/2] >> ((i&1u)*16u)) / 4096.0;
            muzzle[row] += r * c->muzzle[col];
            axis[row] += r * c->forward[col];
        }
    }
    int32_t p[3];
    double d[3] = {0};
    for (unsigned row=0; row<3; ++row) {
        double value=0;
        for (unsigned col=0; col<3; ++col) {
            if (!isfinite(inverse[row*3+col]) || !isfinite(camera_translation[col]))
                return 0;
            value += inverse[row*3+col] * (muzzle[col] - camera_translation[col]);
            d[row] += inverse[row*3+col] * axis[col];
        }
        if (!isfinite(value) || fabs(value) > 32767) return 0;
        p[row] = (int32_t)llround(value*65536.0);
    }
    const double length = sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]);
    if (!isfinite(length) || length < .01) return 0;
    /* Same native angle conversion as the reference aim helper; Underground
     * stores these 16.16 turns at +23C/+240/+244. Native basis/history follows. */
    const double turns = 4096.0 / (2.0 * 3.14159265358979323846);
    double yaw=atan2(d[0], d[2])*turns;
    if (yaw < 0) yaw += 4096.0;
    const int32_t a[3] = {
        (int32_t)llround(atan2(-d[1], hypot(d[0],d[2]))*turns*65536.0),
        (int32_t)llround(yaw*65536.0), 0,
    };
    memcpy(position, p, sizeof p);
    memcpy(angles, a, sizeof a);
    return 1;
}

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

const MohuVrWeaponCalibration* mohu_vr_weapon_calibration_find(uint8_t id) {
    const MohuVrWeaponProfile* profile = mohu_vr_weapon_profile_find(id);
    return profile ? profile->calibration : NULL;
}

int mohu_vr_weapon_mesh_layout_valid(const MohuVrWeaponProfile* profile,
                                     uint32_t magic, unsigned faces,
                                     const uint16_t* vertices, unsigned nodes) {
    return profile && vertices && nodes <= MOHU_VR_WEAPON_FP_MAX_NODES &&
           nodes == profile->node_count && magic == profile->mesh_magic &&
           faces == profile->face_count &&
           memcmp(vertices, profile->vertices, nodes * sizeof *vertices) == 0;
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

int mohu_vr_weapon_compose_gte_control(uint32_t control[8],
                                       const double delta_rotation[9],
                                       const int32_t pivot[3],
                                       const double delta_translation[3]) {
    if (!control || !delta_rotation || !pivot || !delta_translation) {
        return 0;
    }
    int16_t native_rotation[9];
    int32_t native_translation[3];
    for (unsigned i = 0; i < 9u; ++i) {
        native_rotation[i] =
            (int16_t)(control[i / 2u] >> ((i & 1u) * 16u));
    }
    for (unsigned i = 0; i < 3u; ++i) {
        native_translation[i] = (int32_t)control[5u + i];
    }

    int16_t tracked_rotation[9];
    int32_t tracked_translation[3];
    /* The affine builder stores translation in Q12. GTE TR registers instead
     * consume integer camera units, so cancel that packing scale here. */
    const double control_delta[3] = {
        delta_translation[0] / 4096.0,
        delta_translation[1] / 4096.0,
        delta_translation[2] / 4096.0,
    };
    if (!mohu_vr_weapon_compose_gte(
            native_rotation, native_translation, delta_rotation, pivot,
            control_delta, tracked_rotation, tracked_translation)) {
        return 0;
    }

    for (unsigned i = 0; i < 4u; ++i) {
        control[i] =
            (uint32_t)(uint16_t)tracked_rotation[i * 2u] |
            ((uint32_t)(uint16_t)tracked_rotation[i * 2u + 1u] << 16u);
    }
    control[4] = (control[4] & 0xFFFF0000u) |
                 (uint32_t)(uint16_t)tracked_rotation[8];
    for (unsigned i = 0; i < 3u; ++i) {
        control[5u + i] = (uint32_t)tracked_translation[i];
    }
    return 1;
}

int mohu_vr_weapon_compose_absolute_gte_control(
    uint32_t control[8], const double hand_rotation[9],
    const double hand_translation[3], const double pivot[3]) {
    if (!control || !hand_rotation || !hand_translation || !pivot) {
        return 0;
    }
    for (unsigned i = 0; i < 9u; ++i) {
        if (!isfinite(hand_rotation[i])) {
            return 0;
        }
    }
    for (unsigned i = 0; i < 3u; ++i) {
        if (!isfinite(hand_translation[i]) || !isfinite(pivot[i])) {
            return 0;
        }
    }

    int16_t native_rotation[9];
    int32_t native_translation[3];
    for (unsigned i = 0; i < 9u; ++i) {
        native_rotation[i] =
            (int16_t)(control[i / 2u] >> ((i & 1u) * 16u));
    }
    for (unsigned i = 0; i < 3u; ++i) {
        native_translation[i] = (int32_t)control[5u + i];
    }

    int16_t result_rotation[9];
    int32_t result_translation[3];
    for (unsigned row = 0; row < 3u; ++row) {
        for (unsigned col = 0; col < 3u; ++col) {
            double value = 0.0;
            for (unsigned k = 0; k < 3u; ++k) {
                value += hand_rotation[row * 3u + k] *
                         (double)native_rotation[k * 3u + col];
            }
            const long rounded = lround(value);
            if (!isfinite(value) || rounded < INT16_MIN ||
                rounded > INT16_MAX) {
                return 0;
            }
            result_rotation[row * 3u + col] = (int16_t)rounded;
        }

        double value = pivot[row] + hand_translation[row];
        for (unsigned k = 0; k < 3u; ++k) {
            value += hand_rotation[row * 3u + k] *
                     ((double)native_translation[k] - pivot[k]);
        }
        if (!isfinite(value) || value < INT32_MIN || value > INT32_MAX) {
            return 0;
        }
        result_translation[row] = (int32_t)llround(value);
    }

    for (unsigned i = 0; i < 4u; ++i) {
        control[i] =
            (uint32_t)(uint16_t)result_rotation[i * 2u] |
            ((uint32_t)(uint16_t)result_rotation[i * 2u + 1u] << 16u);
    }
    control[4] = (control[4] & 0xFFFF0000u) |
                 (uint32_t)(uint16_t)result_rotation[8];
    for (unsigned i = 0; i < 3u; ++i) {
        control[5u + i] = (uint32_t)result_translation[i];
    }
    return 1;
}
