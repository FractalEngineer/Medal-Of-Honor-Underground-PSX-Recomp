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
#define MOHU_VR_WEAPON_VERTEX_LIMIT 256u
#define MOHU_VR_WEAPON_VERTEX_WORDS \
    (MOHU_VR_WEAPON_VERTEX_LIMIT / 64u)
#define MOHU_VR_WEAPON_NODE_COUNT 22u
#define MOHU_VR_P38_TRIANGLE_STREAM_BYTES 4320u
#define MOHU_VR_P38_TRIANGLE_STREAM_FNV 0x1F000741u

/*
 * W3 calibration is measured in the animated-model output space produced by
 * 8008DB98. All marker and axis positions use that space's integer model units;
 * model_units_per_metre describes physical display size. The shipping candidate
 * preserves authored axes and uses the reference firearm scale; old PCA/nominal
 * calibration receipts describe the preceding candidate, not these defaults.
 * All physical values remain provisional until the next headset batch.
 */
typedef struct {
    double grip_pivot[3];
    double muzzle[3];
    double right[3];
    double up[3];
    double forward[3];
    /* Camera-space translation moved together with the rendered model and
     * its muzzle ray. Use this for mount geometry, not per-save calibration. */
    double mount_offset_m[3];
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
    uint16_t gun_face_count;
    uint16_t gun_vertex_count;
    uint32_t gun_nodes;
    uint8_t partial_node;
    uint64_t partial_vertices[MOHU_VR_WEAPON_VERTEX_WORDS];
    const MohuVrWeaponCalibration* calibration;
} MohuVrWeaponProfile;

/*
 * Selected gun components are represented by whole nodes except for the P38
 * barrel and silenced-pistol suppressor, which share animated nodes with the
 * arms. StG's fused hand needs a semantic partial-node mask as well: shared
 * stock boundary vertices stay selected while private hand vertices reject
 * mixed hand faces through native SZ. Every index is checked against node count.
 */
static inline int mohu_vr_weapon_gun_vertex(
    const MohuVrWeaponProfile* profile, unsigned node, unsigned vertex) {
    if (!profile || node >= profile->node_count ||
        vertex >= profile->vertices[node]) return 0;
    if (profile->gun_nodes & (UINT32_C(1) << node)) return 1;
    return node == profile->partial_node &&
           ((profile->partial_vertices[vertex / 64u] >>
             (vertex % 64u)) & UINT64_C(1));
}

size_t mohu_vr_weapon_profile_count(void);
const MohuVrWeaponProfile* mohu_vr_weapon_profile_at(size_t index);
const MohuVrWeaponProfile* mohu_vr_weapon_profile_find(uint8_t id);
const MohuVrWeaponCalibration* mohu_vr_weapon_calibration_find(uint8_t id);
/* Exact SP asset variants retain full geometry/metadata identity checks. */
int mohu_vr_weapon_sp_geometry_valid(const MohuVrWeaponProfile* profile,
                                     uint32_t geometry_fnv32);
/* Uniform power-of-two precision lift, preserving ratios and Q12 bounds.
 * Apply the returned factor to the render-view eye translation as well. */
int mohu_vr_weapon_precision_control(uint32_t control[8], double* factor);
/* Candidate only: the caller must also prove that the eye OT and model
 * sources do not reference this native double-buffer region before writing. */
uint32_t mohu_vr_weapon_spare_bank(uint32_t base, uint32_t bytes,
                                 uint32_t cursor, uint32_t end);
/* Preserve the focused P38 contract as a named wrapper for existing tests. */
int mohu_vr_p38_gun_vertex(unsigned node, unsigned vertex);
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

/* Opt-in W3 calibration candidate. Animated vertices remain native. Map the
 * measured model grip/basis into the hand instead of rotating authored camera
 * placement. P38's W5 shot override shares the same quantized affine. */
int mohu_vr_weapon_calibrated_control(
    uint32_t control[8], const double hand_rotation[9],
    const double hand_translation[3], double units_per_metre,
    const MohuVrWeaponCalibration* calibration);
int mohu_vr_weapon_muzzle_shot(
    const uint32_t control[8], const MohuVrWeaponCalibration* calibration,
    const double camera_inverse[9], const double camera_translation[3],
    int32_t position[3], int32_t angles[3]);
/* Shared unscaled fixed muzzle ray for native shots and per-eye laser.
 * The caller supplies the same quantized calibration affine, never recoil. */
int mohu_vr_weapon_model_ray(const uint32_t control[8], const double tip[3],
    const double axis[3], double origin[3], double direction[3]);
/* Convert one immutable animated marker tip and model-space axis through the
 * same quantized render affine. The static P38 muzzle helper above is the
 * compatibility wrapper for this path. */
int mohu_vr_weapon_animated_shot(
    const uint32_t control[8], const double tip[3],
    const double axis[3], const double camera_inverse[9],
    const double camera_translation[3], int32_t position[3],
    int32_t angles[3]);
/* Translate the four packed XY words of the native screen-space muzzle flash
 * so their centre follows a projected rendered muzzle. Topology and size are
 * preserved; an off-screen or malformed result is rejected. */
int mohu_vr_weapon_translate_flash_quad(
    const uint32_t xy[4], double target_x, double target_y, uint32_t out[4]);

#endif
