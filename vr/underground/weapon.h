#ifndef MOHU_VR_WEAPON_H
#define MOHU_VR_WEAPON_H

#include "mod_plugins.h"

#include <stddef.h>
#include <stdint.h>

/* The 22-node actor+4AC object is the third-person body. MP's native
 * actor+114 pointer names the separate first-person object at input+9F0. */
#define MOHU_VR_WEAPON_OBJECT_OFFSET 0x4ACu
#define MOHU_VR_WEAPON_FP_INPUT_OFFSET 0x9F0u
#define MOHU_VR_WEAPON_FP_RENDER_ADDR 0x800892E8u
#define MOHU_VR_WEAPON_FP_RENDER_WORD 0x27BDFFB8u
#define MOHU_VR_WEAPON_FP_RENDER_BYTES 0xA70u
#define MOHU_VR_WEAPON_FP_RENDER_FNV 0x39E56A35u
#define MOHU_VR_WEAPON_FP_CALLER_RA 0x8008A544u
#define MOHU_VR_WEAPON_FP_CALL_ADDR 0x8008A53Cu
#define MOHU_VR_WEAPON_FP_CALL_WORD 0x0C0224BAu
#define MOHU_VR_WEAPON_FP_PROJECT_ADDR 0x800894DCu
#define MOHU_VR_WEAPON_FP_PROJECT_WORD 0x8E650000u
#define MOHU_VR_WEAPON_FP_LEAVE_ADDR 0x80089D30u
#define MOHU_VR_WEAPON_FP_LEAVE_WORD 0x8FBF0040u
#define MOHU_VR_WEAPON_FP_MODEL_ADDR 0x8008DB98u
#define MOHU_VR_WEAPON_FP_MODEL_BYTES 0xB4u
#define MOHU_VR_WEAPON_FP_MODEL_FNV 0xFAE3646Eu
#define MOHU_VR_WEAPON_FP_MAX_NODES 32u
#define MOHU_VR_WEAPON_NODE_COUNT 22u

/*
 * W3 calibration is measured in the animated-model output space produced by
 * 8008DB98. All marker and axis positions use that space's integer model units;
 * model_units_per_metre describes the nominal physical size only. These P38
 * values are provisional until W3.3 headset acceptance.
 */
typedef struct {
    double grip_pivot[3];
    double muzzle[3];
    double right[3];
    double up[3];
    double forward[3];
    double model_units_per_metre;
    double reference_length_m;
    double forward_span_units;
    uint8_t provisional;
} MohuVrWeaponCalibration;

typedef struct {
    uint8_t id;
    uint8_t source_slot;
    uint8_t source_switch;
    const char* name;
    uint32_t mesh_magic;
    uint32_t geometry_fnv32;
    uint16_t face_count;
    uint16_t node_count;
    uint16_t vertices[MOHU_VR_WEAPON_FP_MAX_NODES];
    const MohuVrWeaponCalibration* calibration;
} MohuVrWeaponProfile;

size_t mohu_vr_weapon_profile_count(void);
const MohuVrWeaponProfile* mohu_vr_weapon_profile_at(size_t index);
const MohuVrWeaponProfile* mohu_vr_weapon_profile_find(uint8_t id);
const MohuVrWeaponCalibration* mohu_vr_weapon_calibration_find(uint8_t id);
int mohu_vr_weapon_mesh_layout_valid(const MohuVrWeaponProfile* profile,
                                     uint32_t magic, unsigned faces,
                                     const uint16_t* vertices, unsigned nodes);
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

/*
 * Compose the tracked delta into the GTE control block used by the measured
 * first-person geometry call. Words 0..4 hold RT plus control flags in the
 * upper half of word 4; words 5..7 hold TR. The caller must restore the
 * original eight-word snapshot after the geometry call.
 */
int mohu_vr_weapon_compose_gte_control(uint32_t control[8],
                                       const double delta_rotation[9],
                                       const int32_t pivot[3],
                                       const double delta_translation[3]);

/*
 * Replace a camera-relative weapon transform with an absolute hand transform.
 * hand_rotation/hand_translation are origin_from_native_camera; pivot is the
 * provisional native-camera rotation marker. The native RT may be scaled and
 * sheared and is preserved as the full affine hand_from_model basis. Overflow
 * or malformed input leaves control unchanged.
 */
int mohu_vr_weapon_compose_absolute_gte_control(
    uint32_t control[8], const double hand_rotation[9],
    const double hand_translation[3], const double pivot[3]);

#endif
