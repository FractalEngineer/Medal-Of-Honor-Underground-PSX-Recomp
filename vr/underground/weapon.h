#ifndef MOHU_VR_WEAPON_H
#define MOHU_VR_WEAPON_H

#include "mod_plugins.h"

#include <stddef.h>
#include <stdint.h>

/*
 * The multiplayer fixture roots point at the player actor. The first-person
 * model object is at actor + 0x4AC. Its 22-node table is shared by the measured
 * multiplayer weapon IDs, while the selected weapon data is referenced through
 * the object's per-frame geometry state.
 */
#define MOHU_VR_WEAPON_OBJECT_OFFSET 0x4ACu
#define MOHU_VR_WEAPON_UPDATE_ADDR 0x800892E8u
#define MOHU_VR_WEAPON_UPDATE_WORD 0x27BDFFB8u
#define MOHU_VR_WEAPON_UPDATE_LEAVE_ADDR 0x80089D30u
#define MOHU_VR_WEAPON_UPDATE_LEAVE_WORD 0x8FBF0040u
#define MOHU_VR_WEAPON_OBJECT_UPDATE_RA 0x8008A7C8u
#define MOHU_VR_WEAPON_MODEL_RENDER_ADDR 0x8008DB98u
#define MOHU_VR_WEAPON_MODEL_RENDER_WORD 0x27BDFFC8u
#define MOHU_VR_WEAPON_MODEL_MATRIX_ADDR 0x8008DC30u
#define MOHU_VR_WEAPON_MODEL_MATRIX_WORD 0x01403821u
#define MOHU_VR_WEAPON_MODEL_CALLER_RA 0x8008946Cu
#define MOHU_VR_WEAPON_MODEL_LEAVE_ADDR 0x8008DC3Cu
#define MOHU_VR_WEAPON_MODEL_LEAVE_WORD 0x8FBF0030u
#define MOHU_VR_WEAPON_MODEL_BYTES 0xB4u
#define MOHU_VR_WEAPON_MODEL_FNV1A 0xFAE3646Eu
#define MOHU_VR_WEAPON_TRANSFORM_ADDR 0x80014184u
#define MOHU_VR_WEAPON_TRANSFORM_BYTES 0x374u
#define MOHU_VR_WEAPON_TRANSFORM_FNV1A 0xF7657400u
#define MOHU_VR_WEAPON_NODE_TABLE_FNV1A 0x53CDF1BC0D374630ull
#define MOHU_VR_WEAPON_SP_OBJECT_OFFSET 0x1E0u
#define MOHU_VR_WEAPON_SP_RENDER_ADDR 0x8007A554u
#define MOHU_VR_WEAPON_SP_RENDER_WORD 0x27BDFF68u
#define MOHU_VR_WEAPON_SP_RENDER_LEAVE_ADDR 0x8007A7F0u
#define MOHU_VR_WEAPON_SP_RENDER_LEAVE_WORD 0x8FBF0090u
#define MOHU_VR_WEAPON_NODE_COUNT 22u

typedef struct {
    uint8_t id;
    uint8_t source_slot;
    uint8_t source_switch;
    const char* name;
} MohuVrWeaponProfile;

size_t mohu_vr_weapon_profile_count(void);
const MohuVrWeaponProfile* mohu_vr_weapon_profile_at(size_t index);
const MohuVrWeaponProfile* mohu_vr_weapon_profile_find(uint8_t id);
int mohu_vr_weapon_node_layout_valid(const uint16_t counts[22],
                                     unsigned count);
uint64_t mohu_vr_weapon_fnv1a(const void* bytes, size_t size);

/*
 * Build the camera-axis rigid delta for the right hand. The result is a unit
 * rotation and a camera-unit translation. It is applied to the measured
 * first-person model matrix only, never to the world render view.
 */
int mohu_vr_weapon_track_delta(const PSXModOpenXRHands* hands,
                               double units_per_meter, double rotation[9],
                               double translation[3]);

/*
 * Express current tracking relative to the first accepted hand pose:
 * D = current * inverse(base). Invalid inputs return zero.
 */
int mohu_vr_weapon_relative_delta(const double current_rotation[9],
                                  const double current_translation[3],
                                  const double base_rotation[9],
                                  const double base_translation[3],
                                  double rotation[9], double translation[3]);

/*
 * Compose a camera-space rigid delta with a packed PSX 4x4 affine. Rotation
 * coefficients are Q12; translation and pivot are GTE fixed-point values.
 * The native affine remains the animation/recoil input. Overflow is rejected.
 */
int mohu_vr_weapon_compose_gte(const int16_t native_rotation[9],
                               const int32_t native_translation[3],
                               const double delta_rotation[9],
                               const int32_t pivot[3],
                               const double delta_translation[3],
                               int16_t rotation[9],
                               int32_t translation[3]);

/* Compose a camera-axis rotation with one node's packed Q12 quaternion. */
int mohu_vr_weapon_rotate_node_q12(int16_t quaternion[4],
                                   const double rotation[9]);

#endif
