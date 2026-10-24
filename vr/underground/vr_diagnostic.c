#include "cpu_state.h"
#include "camera_map.h"
#include "engine_map.h"
#include "frustum.h"
#include "hud_packets.h"
#include "input.h"
#include "menu_surface.h"
#include "raycast.h"
#include "weapon.h"
#include "gpu_gl_renderer.h"
#include "mod_plugins.h"
#include "vr_pose_math.h"

#include <math.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MOHU_VR_DIAG_PLUGIN_ID "mohu.vr.diagnostic"
#define MOHU_VR_LEVEL_OFFSET_ENV "MOHU_VR_LEVEL_OFFSET_X"
#define MOHU_VR_LEVEL_OFFSET_LIMIT 2048
#define MOHU_VR_STEREO_PROOF_ENV "MOHU_VR_STEREO_PROOF"
#define MOHU_VR_EYE_OFFSET_ENV "MOHU_VR_EYE_OFFSET"
#define MOHU_VR_EYE_OFFSET_ALL_SPANS_ENV "MOHU_VR_EYE_OFFSET_ALL_SPANS"
#define MOHU_VR_EYE_RENDER_VIEW_ENV "MOHU_VR_EYE_RENDER_VIEW"
#define MOHU_VR_EYE_VIEW_OFFSET_ENV "MOHU_VR_EYE_VIEW_OFFSET"
#define MOHU_VR_EYE_YAW_MDEG_ENV "MOHU_VR_EYE_YAW_MDEG"
#define MOHU_VR_EYE_PITCH_MDEG_ENV "MOHU_VR_EYE_PITCH_MDEG"
#define MOHU_VR_EYE_HEAD_X_MILLI_ENV "MOHU_VR_EYE_HEAD_X_MILLI"
#define MOHU_VR_EYE_HEAD_Y_MILLI_ENV "MOHU_VR_EYE_HEAD_Y_MILLI"
#define MOHU_VR_EYE_HEAD_Z_MILLI_ENV "MOHU_VR_EYE_HEAD_Z_MILLI"
#define MOHU_VR_EYE_GUEST_SUBMIT_ENV "MOHU_VR_EYE_GUEST_SUBMIT"
#define MOHU_VR_REPLAY_DRIVER_ENV "MOHU_VR_REPLAY_FRAME_DRIVER"
#define MOHU_VR_OT_ONLY_ENV "MOHU_VR_STEREO_OT_ONLY"
#define MOHU_VR_HEAD_FRUSTUM_ENV "PSX_VR_HEAD_FRUSTUM"
#define MOHU_VR_SUPPRESS_FLAT_HUD_ENV "PSX_VR_SUPPRESS_FLAT_HUD"
#define MOHU_VR_HUD_TRACE_ENV "MOHU_VR_HUD_TRACE"
#define MOHU_VR_STEREO_DUMP_ENV "MOHU_VR_STEREO_DUMP_DIR"
#define MOHU_VR_STEREO_DUMP_PAIRS_ENV "MOHU_VR_STEREO_DUMP_PAIRS"
#define MOHU_VR_OPENXR_ENV "MOHU_VR_OPENXR"
#define MOHU_VR_WEAPON_POSE_ENV "PSX_VR_WEAPON_POSE"
#define MOHU_VR_WEAPON_TRACE_ENV "MOHU_VR_WEAPON_TRACE"
#define MOHU_VR_WEAPON_SYNTHETIC_X_ENV "MOHU_VR_WEAPON_SYNTHETIC_X"
#define MOHU_VR_WEAPON_SYNTHETIC_YAW_ENV "MOHU_VR_WEAPON_SYNTHETIC_YAW_MDEG"
#define MOHU_VR_WEAPON_TRACKING_LOSS_ENV "MOHU_VR_WEAPON_FORCE_TRACKING_LOSS"
#define MOHU_VR_WEAPON_FLAT_PROBE_ENV "MOHU_VR_WEAPON_FLAT_PROBE"
#define MOHU_VR_LASER_ENV "PSX_VR_LASER"
#define MOHU_VR_LASER_LEGACY_ENV "MOHU_VR_LASER"
#define MOHU_VR_LASER_RANGE_M_ENV "MOHU_VR_LASER_RANGE_M"
#define MOHU_VR_LASER_DOT_ENV "MOHU_VR_LASER_DOT"
#define MOHU_VR_LASER_SYNTHETIC_ENV "MOHU_VR_LASER_SYNTHETIC"
#define MOHU_VR_UNITS_PER_METER_ENV "MOHU_VR_UNITS_PER_METER"
#define MOHU_VR_MENU_DISTANCE_ENV "MOHU_VR_MENU_DISTANCE"
#define MOHU_VR_MENU_WIDTH_ENV "MOHU_VR_MENU_WIDTH"
#define MOHU_VR_EYE_OFFSET_LIMIT 256
#define MOHU_VR_EYE_ANGLE_LIMIT 180000
#define MOHU_VR_EYE_HEAD_MILLI_LIMIT 4096000
#define MOHU_VR_DIAGNOSTIC_UNITS_PER_METER 1000.0
#define MOHU_VR_DEFAULT_UNITS_PER_METER (48.0 / 0.067)
#define MOHU_VR_DEFAULT_MENU_DISTANCE 2.0
#define MOHU_VR_DEFAULT_MENU_WIDTH 2.0
#define MOHU_VR_PI 3.14159265358979323846
#define MOHU_VR_FALLBACK_PROJECTION_H 400.0

#define MOHU_VR_FRAME_CONTEXT_ADDR 0x800A7138u
#define MOHU_VR_WORLD_POINTER_ADDR 0x800A977Cu
#define MOHU_VR_WORLD_READY_ADDR 0x800A4914u

/* Underground equivalents of the reference 800AA178.. queue/mask block. */
#define MOHU_VR_LEVEL_MASK0_ADDR 0x800B7490u
#define MOHU_VR_LEVEL_MASK1_ADDR 0x800B7494u
#define MOHU_VR_LEVEL_MASK_BYPASS_ADDR 0x800B7498u
#define MOHU_VR_LEVEL_QUEUE_COUNT_ADDR 0x800B74B4u
#define MOHU_VR_LEVEL_QUEUE_ADDR 0x800B74B8u
#define MOHU_VR_LEVEL_QUEUE_SENTINEL_ADDR 0x800C8458u
#define MOHU_VR_LEVEL_H_ADDR 0x800A7140u
#define MOHU_VR_LEVEL_TREE_LEAF_CAPACITY 1000u
#define MOHU_VR_HUD_HEALTH_BUFFER_ADDR 0x800C8C88u
#define MOHU_VR_HUD_COMPASS_BUFFER_ADDR 0x800BA488u
#define MOHU_VR_HUD_COMPASS_BLOCK_LO 0x800B8C88u
#define MOHU_VR_HUD_COMPASS_BLOCK_HI 0x800BA4B0u
#define MOHU_VR_HUD_BUFFER_INDEX_ADDR 0x800A9354u
#define MOHU_VR_NATIVE_SUBMIT_TAIL_ADDR 0x80053CFCu
#define MOHU_VR_NATIVE_SUBMIT_TAIL_SIZE 80u
#define MOHU_VR_NATIVE_SUBMIT_TAIL_FNV 0xA7A38EA0u

typedef struct {
    const char* name;
    uint32_t address;
    uint32_t size;
    uint32_t fnv1a;
} MohuVrFlatHudBinding;

/* Live-confirmed flat HUD text renderer in the captured overlay generation. */
static const MohuVrFlatHudBinding k_flat_hud_bindings[] = {
    {"text", 0x8006B64Cu, 692u, 0x7E13324Du},
};

static bool g_active;
static bool g_checked[MOHU_VR_ROLE_COUNT];
static bool g_mismatch[MOHU_VR_ROLE_COUNT];
static bool g_reported[MOHU_VR_ROLE_COUNT];
static bool g_stereo_role_reported[MOHU_VR_ROLE_COUNT];
static bool g_camera_reported;
static bool g_level_offset_applied;
static uint32_t g_saved_trx;
static int32_t g_level_offset_x;
static bool g_stereo_proof;
static bool g_stereo_active;
static int32_t g_stereo_eye_offset;
static uint32_t g_stereo_current_eye;
static bool g_stereo_base_valid;
static uint32_t g_stereo_base_trx;
static uint32_t g_stereo_level_hits[2];
static uint32_t g_stereo_pose_apps[2];
static uint32_t g_stereo_guest_submits;
static bool g_stereo_apply_all_spans;
static bool g_stereo_render_view;
static bool g_stereo_guest_submit;
static bool g_head_frustum;
static bool g_head_frustum_keep_all;
static bool g_stereo_eye_view_valid;
static PSXModRenderView g_stereo_eye_view;
static uint32_t g_head_frustum_collects[2];
static uint32_t g_head_frustum_fallbacks[2];
static bool g_suppress_flat_hud;
static uint32_t g_flat_hud_skips[2];
static uint32_t g_flat_hud_unlinked[2];
static bool g_flat_hud_mismatch[1];
static bool g_hud_trace_done;
static bool g_stereo_pose_logged[2];
static bool g_stereo_pose_failure_reported;
static int32_t g_stereo_yaw_mdeg;
static int32_t g_stereo_pitch_mdeg;
static int32_t g_stereo_head_milli[3];
static uint32_t g_stereo_waits_skipped;
static uint32_t g_stereo_ot_words;
static uint32_t g_stereo_attempts;
static uint32_t g_stereo_pairs;
static uint32_t g_stereo_frame_x;
static uint32_t g_stereo_frame_y;
static uint32_t g_stereo_frame_w;
static uint32_t g_stereo_frame_h;
static bool g_stereo_ot_reported;
static int32_t g_stereo_dump_pairs = 60;
static bool g_replay_frame_driver;
static bool g_stereo_ot_only;
static bool g_frame_driver_args_valid;
static uint32_t g_frame_driver_args[4];
static bool g_frame_render_args_valid;
static uint32_t g_frame_render_args[4];
static bool g_openxr;
static bool g_clear_only;
static bool g_skip_final_submit;
static bool g_clear_before_submit;
static bool g_replaying_frame;
static bool g_keep_replay_submit;
static uint32_t g_replay_submits_skipped[2];
static bool g_native_tail_mismatch;
static int32_t g_clear_rgb;
static bool g_no_native_surface;
static int g_openxr_native_surface = -1;
static uint32_t g_native_surface_seen_attempts;
static uint32_t g_native_surface_idle_vblanks =
    MOHU_VR_NATIVE_SURFACE_IDLE_VBLANKS;
static double g_openxr_units_per_meter = MOHU_VR_DEFAULT_UNITS_PER_METER;
static double g_openxr_menu_distance = MOHU_VR_DEFAULT_MENU_DISTANCE;
static double g_openxr_menu_width = MOHU_VR_DEFAULT_MENU_WIDTH;
static PSXModRenderView g_openxr_eye_view[2];
static uint32_t g_openxr_begin_failures;
static uint32_t g_openxr_view_failures;
static uint32_t g_openxr_ends;
static bool g_openxr_failure_reported;
static bool g_movement;
static double g_move_deadzone = 0.2;
static double g_turn_gain = 0.65;
static bool g_input_guard_reported;
static bool g_weapon_pose;
static bool g_weapon_trace;
static uint32_t g_weapon_trace_count;
static int32_t g_weapon_synthetic_x;
static int32_t g_weapon_synthetic_yaw_mdeg;
static bool g_weapon_force_tracking_loss;
static bool g_weapon_flat_probe;
static uint32_t g_weapon_profile_hits[2];
static uint32_t g_weapon_profile_fallbacks[2];
static uint32_t g_weapon_profile_last_id;
static uint32_t g_weapon_profile_last_object;
static bool g_weapon_profile_guard_reported;
static bool g_weapon_pose_applied_reported;
static bool g_runtime_hook_counts_reported;
static bool g_weapon_model_active;
static bool g_weapon_matrix_saved;
static uint32_t g_weapon_model_object;
static uint32_t g_weapon_model_id;
static uint32_t g_weapon_matrix_addr;
static uint32_t g_weapon_matrix_words[8];
static uint32_t g_weapon_node_q_addr;
static uint32_t g_weapon_node_q_words[2];
static double g_weapon_delta_rotation[9];
static double g_weapon_delta_translation[3];
static bool g_weapon_neutral_valid;
static double g_weapon_neutral_rotation[9];
static double g_weapon_neutral_translation[3];
static uint32_t g_weapon_entry_ra;
static volatile int32_t g_weapon_control_x;
static volatile int32_t g_weapon_control_yaw_mdeg;
static volatile uint32_t g_weapon_control_generation;
static uint32_t g_weapon_control_seen;
static bool g_laser;
static bool g_laser_grip;
static bool g_laser_synthetic;
static double g_laser_range_m = 50.0;
static double g_laser_dot_px = 2.0;
static bool g_laser_level_valid;
static uint32_t g_laser_level_root;
static double g_laser_camera_rotation[9];
static double g_laser_camera_inverse[9];
static double g_laser_camera_translation[3];
static int32_t g_laser_offset_x;
static int32_t g_laser_offset_y;
static uint32_t g_laser_projection_h;
static uint32_t g_laser_projection_h_ref;
static uint32_t g_laser_hits[2];
static uint32_t g_laser_misses[2];

static void set_openxr_native_surface(bool enabled);

/* The game rebuilds the selected calibration after DualShock presentation.
 * Measured boot/load layouts swap entries 1/3; native LX/LY/RX retain their
 * turn/forward/strafe roles. Never force a guest configuration or table. */
static int vr_controller_source(PSXModControllerState* pad) {
    PSXModOpenXRInput input = {0};
    input.struct_size = sizeof input;
    if (g_stereo_active || !psx_mod_openxr_input(&input)) return 0;
    uint32_t player = psx_mod_read_word(MOHU_VR_SP_PLAYER_POINTER_ADDR);
    if (g_openxr_native_surface == 1 ||
        player < 0x80000000u || player >= 0x801FFC00u)
        return mohu_vr_menu_input_map(&input, g_move_deadzone, pad);
    bool analog_layout = psx_mod_read_word(0x800C47F0u) == 0;
    const unsigned entry[3] = {analog_layout ? 3u : 1u, 0,
                               analog_layout ? 1u : 3u};
    const unsigned native_axis[3] = {2, 3, 0};
    const uint32_t actions[9] = {0x40,0x10,0x20,1,0x80,0x80,0x800,3,2};
    bool valid = true;
    uint32_t hash = 2166136261u;
    for (uint32_t i = 0; i < 324u; ++i)
        hash = (hash ^ psx_mod_read_byte(0x80083C6Cu + i)) * 16777619u;
    valid = hash == 0x9CA131D0u;
    hash = 2166136261u;
    for (uint32_t i = 0; i < 84u; ++i)
        hash = (hash ^ psx_mod_read_byte(0x80083DB0u + i)) * 16777619u;
    valid = valid && hash == 0x2D93CB1Cu;
    for (unsigned i = 0; i < 9; ++i) {
        uint32_t action = psx_mod_read_word(0x800C4AA8u + i * 4);
        valid = valid && (i == 7 ? action == (analog_layout ? 0x200u : 3u) :
                         action == actions[i]) &&
                !psx_mod_read_word(0x800C4AD0u + i * 4);
    }
    MohuVRAnalogResponse response;
    for (unsigned i = 0; i < 3; ++i) {
        uint32_t base = 0x800C47C8u + entry[i] * 40;
        valid = valid && psx_mod_read_word(base) == native_axis[i] &&
                !psx_mod_read_word(base + 36);
        response.axis[i].center = psx_mod_read_byte(base + 14);
        response.axis[i].negative_factor = psx_mod_read_word(base + 20);
        response.axis[i].positive_factor = psx_mod_read_word(base + 24);
        response.axis[i].scale = psx_mod_read_word(base + 32) >> 8;
    }
    for (unsigned i = 0; i < sizeof response.curve; ++i)
        response.curve[i] = psx_mod_read_byte(0x800AB12Cu + i);
    if (!valid) {
        if (!g_input_guard_reported) {
            fprintf(stdout, "mohu-vr-input: unsupported code/control layout; "
                    "gameplay source neutral (select native Config. 2)\n");
            fflush(stdout);
            g_input_guard_reported = true;
        }
        return 0;
    }
    g_input_guard_reported = false;
    int merged = input.squeeze_active[0] && isfinite(input.squeeze[0]) &&
                 input.squeeze[0] >= .55f && input.squeeze[0] <= 1;
    return mohu_vr_input_map(&input, g_move_deadzone, g_turn_gain,
                             &response, merged, pad);
}

static uint32_t vr_controller_mode(const PSXModControllerInput* input) {
    (void)input;
    return PSX_MOD_CONTROLLER_ANALOG;
}

static void vr_diagnostic_entry(CPUState* cpu, uint32_t address);

static bool parse_bounded_int(const char* value, int32_t limit,
                              int32_t* result) {
    if (!value || !*value || !result) {
        return false;
    }
    char* end = NULL;
    long parsed = strtol(value, &end, 0);
    if (!end || *end || parsed < -limit || parsed > limit) {
        return false;
    }
    *result = (int32_t)parsed;
    return true;
}

static void parse_optional_int(const char* name, int32_t limit,
                               int32_t* value) {
    const char* text = getenv(name);
    if (!text || !*text) {
        return;
    }
    if (!parse_bounded_int(text, limit, value)) {
        fprintf(stdout,
                "mohu-vr-diag: ignored invalid %s=%s (range -%d..%d)\n",
                name, text, limit, limit);
        fflush(stdout);
    }
}

static void parse_optional_double(const char* name, double minimum,
                                  double maximum, double* value) {
    const char* text = getenv(name);
    if (!text || !*text) {
        return;
    }
    char* end = NULL;
    double parsed = strtod(text, &end);
    if (!end || *end || !isfinite(parsed) || parsed < minimum ||
        parsed > maximum) {
        fprintf(stdout,
                "mohu-vr-diag: ignored invalid %s=%s (range %.3f..%.3f)\n",
                name, text, minimum, maximum);
        fflush(stdout);
        return;
    }
    *value = parsed;
}

static uint32_t guest_range_fnv1a(uint32_t address, uint32_t size) {
    uint32_t hash = 2166136261u;
    uint32_t words = size / 4u;
    for (uint32_t i = 0; i < words; ++i) {
        uint32_t word = psx_mod_read_word(address + i * 4u);
        for (unsigned shift = 0; shift < 32; shift += 8) {
            hash ^= (word >> shift) & 0xFFu;
            hash *= 16777619u;
        }
    }
    return hash;
}

static uint32_t guest_function_fnv1a(const MohuVrEngineBinding* binding) {
    return guest_range_fnv1a(binding->target_address, binding->function_size);
}

static bool binding_for_address(uint32_t address, MohuVrEngineRole* role_out,
                                const MohuVrEngineBinding** binding_out) {
    for (size_t i = 0; i < mohu_vr_engine_map_count(); ++i) {
        const MohuVrEngineBinding* binding = mohu_vr_engine_map_at(i);
        if (binding && binding->target_address == address) {
            *role_out = binding->role;
            *binding_out = binding;
            return true;
        }
    }
    return false;
}

static bool ensure_binding_verified(const MohuVrEngineBinding* binding) {
    size_t index = (size_t)binding->role;
    if (index >= MOHU_VR_ROLE_COUNT ||
        binding->status < MOHU_VR_STATUS_STATIC_CONFIRMED) {
        return false;
    }
    if (!g_checked[index]) {
        g_checked[index] = true;
        uint32_t actual = guest_function_fnv1a(binding);
        if (actual != binding->target_function_fnv1a) {
            g_mismatch[index] = true;
            fprintf(stdout,
                    "mohu-vr-diag: signature mismatch role=%s address=0x%08X "
                    "expected=0x%08X actual=0x%08X\n",
                    binding->name, binding->target_address,
                    binding->target_function_fnv1a, actual);
            fflush(stdout);
        }
    }
    return !g_mismatch[index];
}

static bool verify_binding_now(const MohuVrEngineBinding* binding) {
    const uint32_t actual = guest_function_fnv1a(binding);
    if (actual == binding->target_function_fnv1a) {
        return true;
    }
    size_t index = (size_t)binding->role;
    if (index < MOHU_VR_ROLE_COUNT && !g_mismatch[index]) {
        g_mismatch[index] = true;
        fprintf(stdout,
                "mohu-vr-diag: live signature mismatch role=%s "
                "address=0x%08X expected=0x%08X actual=0x%08X\n",
                binding->name, binding->target_address,
                binding->target_function_fnv1a, actual);
        fflush(stdout);
    }
    return false;
}

static void report_runtime_hook_counts(void) {
    if (g_runtime_hook_counts_reported) {
        return;
    }
    g_runtime_hook_counts_reported = true;
    fprintf(stdout,
            "mohu-vr-diag: runtime hooks function=%u instruction=%u\n",
            g_psx_mod_function_entry_hooks, g_psx_mod_instruction_hooks);
    fflush(stdout);
}

static bool vr_laser_inverse(const double matrix[9], double inverse[9]) {
    if (!matrix || !inverse) {
        return false;
    }
    const double cofactor[9] = {
        matrix[4] * matrix[8] - matrix[5] * matrix[7],
        matrix[2] * matrix[7] - matrix[1] * matrix[8],
        matrix[1] * matrix[5] - matrix[2] * matrix[4],
        matrix[5] * matrix[6] - matrix[3] * matrix[8],
        matrix[0] * matrix[8] - matrix[2] * matrix[6],
        matrix[2] * matrix[3] - matrix[0] * matrix[5],
        matrix[3] * matrix[7] - matrix[4] * matrix[6],
        matrix[1] * matrix[6] - matrix[0] * matrix[7],
        matrix[0] * matrix[4] - matrix[1] * matrix[3],
    };
    const double determinant =
        matrix[0] * cofactor[0] + matrix[1] * cofactor[3] +
        matrix[2] * cofactor[6];
    if (!isfinite(determinant) || fabs(determinant) < 0.01) {
        return false;
    }
    for (unsigned i = 0; i < 9u; ++i) {
        inverse[i] = cofactor[i] / determinant;
        if (!isfinite(inverse[i]) || fabs(inverse[i]) > 64.0) {
            return false;
        }
    }
    return true;
}

static void vr_laser_mul3(const double matrix[9], const double vector[3],
                          double out[3]) {
    const double input[3] = {vector[0], vector[1], vector[2]};
    for (unsigned row = 0; row < 3u; ++row) {
        out[row] = matrix[row * 3u] * input[0] +
                   matrix[row * 3u + 1u] * input[1] +
                   matrix[row * 3u + 2u] * input[2];
    }
}

static bool vr_laser_capture_level(CPUState* cpu) {
    if (!g_laser || !g_stereo_active || g_laser_level_valid || !cpu) {
        return false;
    }
    const uint32_t root = cpu->gpr[4];
    if (root < 0x80000000u || root >= 0x801FFFC0u || (root & 3u)) {
        return false;
    }
    int16_t bounds[6];
    for (unsigned i = 0; i < 6u; ++i) {
        bounds[i] = (int16_t)psx_mod_read_half(root + i * 2u);
    }
    for (unsigned axis = 0; axis < 3u; ++axis) {
        if (bounds[axis] > bounds[axis + 3u]) {
            return false;
        }
    }
    for (unsigned i = 0; i < 9u; ++i) {
        g_laser_camera_rotation[i] =
            (int16_t)(cpu->gte_ctrl[i / 2u] >> ((i & 1u) * 16u)) /
            4096.0;
    }
    for (unsigned i = 0; i < 3u; ++i) {
        g_laser_camera_translation[i] =
            (int32_t)cpu->gte_ctrl[5u + i];
    }
    if (!vr_laser_inverse(g_laser_camera_rotation,
                          g_laser_camera_inverse)) {
        return false;
    }
    g_laser_offset_x = (int32_t)cpu->gte_ctrl[24];
    g_laser_offset_y = (int32_t)cpu->gte_ctrl[25];
    g_laser_projection_h = (uint32_t)cpu->gte_ctrl[26] & 0xFFFFu;
    g_laser_level_root = root;
    g_laser_level_valid = true;
    return true;
}

static bool vr_laser_project(const PSXModRenderView* view,
                             const double point[3],
                             double* screen_x, double* screen_y) {
    if (!view || !point || !screen_x || !screen_y ||
        !isfinite(point[0]) || !isfinite(point[1]) || !isfinite(point[2]) ||
        point[2] <= 1.0) {
        return false;
    }
    const double focal_x = view->projection ? view->fx_q16 : 400 * 65536.0;
    const double focal_y = view->projection ? view->fy_q16 : 400 * 65536.0;
    const double center_x = view->projection ? view->cx_delta_q16 : 0.0;
    const double center_y = view->projection ? view->cy_delta_q16 : 0.0;
    if (!isfinite(focal_x) || !isfinite(focal_y) || focal_x <= 0.0 ||
        focal_y <= 0.0) {
        return false;
    }
    double x = g_laser_offset_x + center_x +
               focal_x * point[0] / point[2];
    double y = g_laser_offset_y + center_y +
               focal_y * point[1] / point[2];
    g_laser_projection_h_ref = view->projection_h_ref;
    if (g_laser_projection_h_ref) {
        if (!g_laser_projection_h) {
            return false;
        }
        const double h_scale =
            (double)g_laser_projection_h /
            (double)g_laser_projection_h_ref;
        x *= h_scale;
        y *= h_scale;
    }
    *screen_x = x / 65536.0;
    *screen_y = y / 65536.0;
    return isfinite(*screen_x) && isfinite(*screen_y);
}

static bool vr_laser_clip(double* x0, double* y0, double* x1, double* y1) {
    const double low = -1023.0;
    const double high = 1023.0;
    const double dx = *x1 - *x0;
    const double dy = *y1 - *y0;
    double enter = 0.0;
    double leave = 1.0;
    const double edges[4] = {-dx, dx, -dy, dy};
    const double distances[4] = {*x0 - low, high - *x0,
                                 *y0 - low, high - *y0};
    for (unsigned i = 0; i < 4u; ++i) {
        if (fabs(edges[i]) < 1e-12) {
            if (distances[i] < 0.0) {
                return false;
            }
            continue;
        }
        const double t = distances[i] / edges[i];
        if (edges[i] < 0.0) {
            if (t > leave) {
                return false;
            }
            if (t > enter) {
                enter = t;
            }
        } else {
            if (t < enter) {
                return false;
            }
            if (t < leave) {
                leave = t;
            }
        }
    }
    if (leave <= enter) {
        return false;
    }
    const double ax = *x0 + dx * enter;
    const double ay = *y0 + dy * enter;
    const double bx = *x0 + dx * leave;
    const double by = *y0 + dy * leave;
    *x0 = ax;
    *y0 = ay;
    *x1 = bx;
    *y1 = by;
    return true;
}

static void vr_laser_draw(void) {
    if (!g_laser || (!g_laser_grip && !g_laser_synthetic) ||
        !g_stereo_active ||
        g_stereo_current_eye > 1u || !g_laser_level_valid) {
        return;
    }
    const PSXModRenderView* view = &g_stereo_eye_view;
    double eye_rotation[9];
    double eye_translation[3];
    for (unsigned i = 0; i < 9u; ++i) {
        eye_rotation[i] = view->precise ? view->rotation[i]
                                       : view->rotation_q12[i] / 4096.0;
    }
    for (unsigned i = 0; i < 3u; ++i) {
        eye_translation[i] =
            view->precise ? view->translation_precise[i]
                          : view->translation[i];
    }

    double origin[3];
    double direction[3];
    if (g_laser_synthetic) {
        static const double local_origin[3] = {
            120.0, 100.0, 240.0,
        };
        static const double local_direction[3] = {0.0, 0.0, 1.0};
        for (unsigned row = 0; row < 3u; ++row) {
            origin[row] = eye_translation[row];
            direction[row] = 0.0;
            for (unsigned col = 0; col < 3u; ++col) {
                origin[row] += eye_rotation[row * 3u + col] *
                               local_origin[col];
                direction[row] += eye_rotation[row * 3u + col] *
                                  local_direction[col];
            }
        }
    } else {
        PSXModOpenXRHands hands = {0};
        hands.struct_size = sizeof hands;
        if (!psx_mod_openxr_hands(&hands) || !hands.focused ||
            !hands.origin_valid || hands.age_ms > 150u) {
            return;
        }
        const PSXModTrackedPose* aim =
            &hands.pose[1][PSX_MOD_XR_AIM_POSE];
        if (!aim->active || (aim->flags & 3u) != 3u) {
            return;
        }
        double aim_quaternion[4];
        double aim_position[3];
        double origin_quaternion[4];
        double origin_position[3];
        for (unsigned i = 0; i < 4u; ++i) {
            aim_quaternion[i] = aim->orientation_xyzw[i];
            origin_quaternion[i] = hands.origin_orientation_xyzw[i];
        }
        for (unsigned i = 0; i < 3u; ++i) {
            aim_position[i] = aim->position_m[i];
            origin_position[i] = hands.origin_position_m[i];
        }
        double local_rotation[9];
        double local_translation[3];
        if (!vr_pose_to_transform(aim_quaternion, aim_position,
                                  origin_quaternion, origin_position,
                                  g_openxr_units_per_meter, local_rotation,
                                  local_translation)) {
            return;
        }
        for (unsigned row = 0; row < 3u; ++row) {
            origin[row] = eye_translation[row];
            direction[row] = 0.0;
            for (unsigned col = 0; col < 3u; ++col) {
                origin[row] += eye_rotation[row * 3u + col] *
                               local_translation[col];
                direction[row] += eye_rotation[row * 3u + col] *
                                  local_rotation[col * 3u + 2u];
            }
        }
    }
    double length = sqrt(direction[0] * direction[0] +
                         direction[1] * direction[1] +
                         direction[2] * direction[2]);
    if (!isfinite(length) || length < 1e-6) {
        return;
    }
    for (unsigned i = 0; i < 3u; ++i) {
        direction[i] /= length;
    }

    const unsigned eye =
        g_stereo_current_eye < 2u ? g_stereo_current_eye : 0u;
    double endpoint[3];
    for (unsigned i = 0; i < 3u; ++i) {
        endpoint[i] = origin[i] +
                      direction[i] * g_laser_range_m *
                          g_openxr_units_per_meter;
    }
    bool have_hit = false;
    if (g_laser_level_root) {
        double camera_offset[3];
        double world_origin[3];
        double world_direction[3];
        for (unsigned row = 0; row < 3u; ++row) {
            double camera_relative = 0.0;
            double camera_direction = 0.0;
            for (unsigned col = 0; col < 3u; ++col) {
                camera_relative +=
                    eye_rotation[col * 3u + row] *
                    (origin[col] - eye_translation[col]);
                camera_direction +=
                    eye_rotation[col * 3u + row] * direction[col];
            }
            camera_offset[row] =
                camera_relative - g_laser_camera_translation[row];
            world_direction[row] = camera_direction;
        }
        vr_laser_mul3(g_laser_camera_inverse, camera_offset, world_origin);
        vr_laser_mul3(g_laser_camera_inverse, world_direction,
                      world_direction);
        length = sqrt(world_direction[0] * world_direction[0] +
                      world_direction[1] * world_direction[1] +
                      world_direction[2] * world_direction[2]);
        if (isfinite(length) && length > 1e-6) {
            for (unsigned i = 0; i < 3u; ++i) {
                world_direction[i] /= length;
            }
            double distance = 0.0;
            if (mohu_vr_ray_tree(
                    g_laser_level_root, world_origin, world_direction,
                    NULL, 1,
                    g_laser_range_m * g_openxr_units_per_meter,
                    &distance, NULL)) {
                double world_hit[3];
                double camera_hit[3];
                for (unsigned i = 0; i < 3u; ++i) {
                    world_hit[i] =
                        world_origin[i] + world_direction[i] * distance;
                }
                vr_laser_mul3(g_laser_camera_rotation, world_hit, camera_hit);
                for (unsigned row = 0; row < 3u; ++row) {
                    double render_hit = eye_translation[row];
                    for (unsigned col = 0; col < 3u; ++col) {
                        render_hit +=
                            eye_rotation[row * 3u + col] *
                            (camera_hit[col] +
                             g_laser_camera_translation[col]);
                    }
                    endpoint[row] = render_hit;
                }
                have_hit = true;
            }
        }
    }

    double screen_start_x = 0.0;
    double screen_start_y = 0.0;
    double screen_end_x = 0.0;
    double screen_end_y = 0.0;
    if (!vr_laser_project(view, origin, &screen_start_x, &screen_start_y) ||
        !vr_laser_project(view, endpoint, &screen_end_x, &screen_end_y)) {
        return;
    }
    const double hit_x = screen_end_x;
    const double hit_y = screen_end_y;
    const bool draw_dot =
        have_hit && g_laser_dot_px >= 1.0 &&
        fabs(hit_x) <= 1023.0 && fabs(hit_y) <= 1023.0;
    if (!vr_laser_clip(&screen_start_x, &screen_start_y,
                       &screen_end_x, &screen_end_y)) {
        return;
    }

    const uint32_t color = 0xB0u;
    const long x0 = lround(screen_start_x);
    const long y0 = lround(screen_start_y);
    const long x1 = lround(screen_end_x);
    const long y1 = lround(screen_end_y);
    psx_mod_write_word(0x1F801810u, 0x50000000u | color);
    psx_mod_write_word(0x1F801810u,
                       ((uint32_t)(y0 & 0xFFFF) << 16u) |
                           (uint32_t)(x0 & 0xFFFF));
    psx_mod_write_word(0x1F801810u, color);
    psx_mod_write_word(0x1F801810u,
                       ((uint32_t)(y1 & 0xFFFF) << 16u) |
                           (uint32_t)(x1 & 0xFFFF));
    if (draw_dot) {
        const long radius = lround(g_laser_dot_px);
        const long center_x = lround(hit_x);
        const long center_y = lround(hit_y);
        const long left = center_x - radius < -1024
            ? -1024 : (center_x - radius > 1023 ? 1023 : center_x - radius);
        const long right = center_x + radius < -1024
            ? -1024 : (center_x + radius > 1023 ? 1023 : center_x + radius);
        const long top = center_y - radius < -1024
            ? -1024 : (center_y - radius > 1023 ? 1023 : center_y - radius);
        const long bottom = center_y + radius < -1024
            ? -1024 : (center_y + radius > 1023 ? 1023 : center_y + radius);
        psx_mod_write_word(0x1F801810u, 0x28000000u | color);
        psx_mod_write_word(0x1F801810u, color);
        psx_mod_write_word(0x1F801810u, color);
        psx_mod_write_word(0x1F801810u, color);
        psx_mod_write_word(0x1F801810u, color);
        psx_mod_write_word(0x1F801810u,
                           ((uint32_t)(top & 0x7FF) << 16u) |
                               (uint32_t)(left & 0x7FF));
        psx_mod_write_word(0x1F801810u,
                           ((uint32_t)(top & 0x7FF) << 16u) |
                               (uint32_t)(right & 0x7FF));
        psx_mod_write_word(0x1F801810u,
                           ((uint32_t)(bottom & 0x7FF) << 16u) |
                               (uint32_t)(left & 0x7FF));
        psx_mod_write_word(0x1F801810u,
                           ((uint32_t)(bottom & 0x7FF) << 16u) |
                               (uint32_t)(right & 0x7FF));
    }
    if (have_hit) {
        ++g_laser_hits[eye];
        psx_mod_counter_add("mohu.vr.laser.hit", 1);
    } else {
        ++g_laser_misses[eye];
        psx_mod_counter_add("mohu.vr.laser.miss", 1);
    }
}

static void vr_diagnostic_vblank(void) {
    report_runtime_hook_counts();
    if (g_openxr && !g_stereo_active &&
        mohu_vr_native_surface_due(
            g_stereo_attempts, &g_native_surface_seen_attempts,
            &g_native_surface_idle_vblanks, g_openxr_native_surface)) {
        set_openxr_native_surface(true);
        if (g_openxr_native_surface == 1) {
            psx_mod_counter_add("mohu.vr.native_surface.resume", 1);
        }
    }
    if (g_laser && (g_openxr || g_stereo_proof)) {
        PSXModOpenXRInput input = {0};
        input.struct_size = sizeof input;
        g_laser_grip =
            psx_mod_openxr_input(&input) &&
            input.squeeze_active[1] &&
            input.squeeze[1] >= 0.55f && input.squeeze[1] <= 1.0f;
    }
    const uint32_t generation = g_weapon_control_generation;
    if (generation != g_weapon_control_seen) {
        g_weapon_synthetic_x = g_weapon_control_x;
        g_weapon_synthetic_yaw_mdeg = g_weapon_control_yaw_mdeg;
        g_weapon_control_seen = generation;
    }
}

static int vr_weapon_control_command(const char* args, char* reply, int cap) {
    if (!args || !reply || cap < 1) {
        return 0;
    }
    if (strcmp(args, "reset") == 0) {
        g_weapon_control_x = 0;
        g_weapon_control_yaw_mdeg = 0;
    } else {
        char* end = NULL;
        unsigned seen = 0;
        const char* p = args;
        while (*p) {
            while (*p == ' ' || *p == '\t' || *p == ',') {
                ++p;
            }
            if (strncmp(p, "x=", 2u) == 0) {
                long value = strtol(p + 2, &end, 0);
                if (end == p + 2 || value < -2048 || value > 2048) {
                    return -1;
                }
                g_weapon_control_x = (int32_t)value;
                seen |= 1u;
                p = end;
            } else if (strncmp(p, "yaw=", 4u) == 0) {
                long value = strtol(p + 4, &end, 0);
                if (end == p + 4 || value < -180000 || value > 180000) {
                    return -1;
                }
                g_weapon_control_yaw_mdeg = (int32_t)value;
                seen |= 2u;
                p = end;
            } else {
                return -1;
            }
        }
        if (seen == 0u) {
            return -1;
        }
    }
    g_weapon_control_generation++;
    (void)snprintf(reply, (size_t)cap, "x=%d yaw_mdeg=%d",
                   g_weapon_control_x, g_weapon_control_yaw_mdeg);
    return 1;
}

static void report_scene_roots(CPUState* cpu) {
    if (g_camera_reported) {
        return;
    }
    g_camera_reported = true;

    uint32_t scene = psx_mod_read_word(MOHU_VR_SP_SCENE_POINTER_ADDR);
    uint32_t player = psx_mod_read_word(MOHU_VR_SP_PLAYER_POINTER_ADDR);
    uint32_t input = 0;
    if (player >= 0x80000000u && player < 0x80200000u) {
        input = psx_mod_read_word(player + MOHU_VR_PLAYER_INPUT_OFFSET);
    }
    fprintf(stdout,
            "mohu-vr-diag: scene_roots scene=0x%08X player=0x%08X "
            "input=0x%08X level_root=0x%08X\n",
            scene, player, input, cpu->gpr[4]);
    fflush(stdout);
}

static void stereo_guest_call(CPUState* cpu, uint32_t entry, uint32_t a0,
                              uint32_t a1, uint32_t a2, uint32_t ra) {
    cpu->gpr[4] = a0;
    cpu->gpr[5] = a1;
    cpu->gpr[6] = a2;
    cpu->gpr[31] = ra;
    psx_dispatch_call(cpu, entry, ra);
}

static void clear_stereo_rect(void) {
    static const uint32_t k_state_packet[] = {
        0xE3000000u, 0xE403BDFFu, 0xE5000000u,
        0xE100060Au, 0xE2000000u, 0xE6000000u,
    };
    for (size_t i = 0; i < sizeof(k_state_packet) / sizeof(k_state_packet[0]);
         ++i) {
        psx_mod_write_word(0x1F801810u, k_state_packet[i]);
    }
    psx_mod_write_word(0x1F801810u, 0x02000000u | (uint32_t)g_clear_rgb);
    psx_mod_write_word(0x1F801810u,
                       (g_stereo_frame_y << 16) | g_stereo_frame_x);
    psx_mod_write_word(0x1F801810u,
                       (g_stereo_frame_h << 16) | g_stereo_frame_w);
}

static uint32_t stereo_ot_base(void) {
    return psx_mod_read_word(MOHU_VR_FRAME_CONTEXT_ADDR + 0x2218u);
}

static void report_stereo_ot(uint32_t base) {
    if (g_stereo_ot_reported) {
        return;
    }
    g_stereo_ot_reported = true;
    uint32_t head = base + 511u * 4u;
    uint32_t tag = head >= 0x80000000u && head < 0x80200000u
                       ? psx_mod_read_word(head)
                       : 0u;
    fprintf(stdout,
            "mohu-vr-diag: stereo_ot base=0x%08X head=0x%08X tag=0x%08X\n",
            base, head, tag);
    fflush(stdout);
}

static void unlink_flat_hud_packets(uint32_t ot_base, uint32_t buffer) {
    if (buffer > 1u) {
        return;
    }
    const uint32_t health_ring =
        MOHU_VR_HUD_HEALTH_BUFFER_ADDR + buffer * 0xC00u;
    const uint32_t compass_node =
        MOHU_VR_HUD_COMPASS_BUFFER_ADDR + buffer * 40u;
    uint32_t previous = ot_base;
    uint32_t next = psx_mod_read_word(previous) & 0x00FFFFFFu;
    for (unsigned count = 0; next != 0x00FFFFFFu && count < 4096u; ++count) {
        if (next >= 0x200000u || (next & 3u)) {
            break;
        }
        const uint32_t node = 0x80000000u | next;
        const uint32_t tag = psx_mod_read_word(node);
        const uint32_t opcode = psx_mod_read_byte(node + 7u);
        const int health =
            node >= health_ring && node < health_ring + 32u * 24u &&
            (node - health_ring) % 48u == 0u &&
            (tag >> 24) == 11u && (opcode & 0xFCu) == 0x28u;
        const int compass =
            (node == compass_node ||
             (node >= MOHU_VR_HUD_COMPASS_BLOCK_LO &&
              node <= MOHU_VR_HUD_COMPASS_BLOCK_HI)) &&
            ((tag >> 24) == 9u || (tag >> 24) == 11u) &&
            ((opcode & 0xFCu) == 0x28u || (opcode & 0xFCu) == 0x2Cu);
        const int hud_bar = mohu_vr_ammo_icon_packet(node, tag, buffer);
        if (health || compass || hud_bar) {
            psx_mod_write_word(
                previous,
                (psx_mod_read_word(previous) & 0xFF000000u) |
                    (tag & 0x00FFFFFFu));
            g_flat_hud_unlinked[
                g_stereo_current_eye < 2u ? g_stereo_current_eye : 0u]++;
        } else {
            previous = node;
        }
        next = tag & 0x00FFFFFFu;
    }
}

static void trace_stereo_ot(uint32_t base) {
    const char* enabled = getenv(MOHU_VR_HUD_TRACE_ENV);
    if (g_hud_trace_done || !enabled || !*enabled || *enabled == '0') {
        return;
    }
    g_hud_trace_done = true;
    const uint32_t head = base + 511u * 4u;
    uint32_t node = head;
    fprintf(stdout, "mohu-vr-diag: ot_trace base=0x%08X head=0x%08X\n",
            base, head);
    for (unsigned count = 0; count < 8192u; ++count) {
        if (node < 0x80000000u || node >= 0x80200000u) {
            break;
        }
        const uint32_t tag = psx_mod_read_word(node);
        const uint32_t next = tag & 0x00FFFFFFu;
        const uint32_t opcode = psx_mod_read_byte(node + 7u);
        int top_left = 0;
        if (opcode >= 0x20u && opcode < 0x40u) {
            const unsigned vertices = opcode >= 0x38u ? 4u : 3u;
            for (unsigned vertex = 0; vertex < vertices; ++vertex) {
                const uint32_t packed = psx_mod_read_word(
                    node + 8u + vertex * 8u);
                const int16_t x = (int16_t)(packed & 0xFFFFu);
                const int16_t y = (int16_t)(packed >> 16);
                if (x >= 0 && y >= 0 && x < 128 && y < 64) {
                    top_left = 1;
                    break;
                }
            }
            const uint32_t xy = psx_mod_read_word(node + 8u);
            const int16_t x = (int16_t)xy;
            const int16_t y = (int16_t)(xy >> 16);
            if (x >= 360 && x <= 480 && y >= 0 && y <= 60 &&
                (tag >> 24) <= 12u) {
                fprintf(stdout, "mohu-vr-diag: hud_candidate node=0x%08X tag=0x%08X words=",
                        node, tag);
                for (unsigned i = 0; i < (tag >> 24); ++i) {
                    fprintf(stdout, "%s%08X", i ? "," : "",
                            psx_mod_read_word(node + 4u + i * 4u));
                }
                fprintf(stdout, "\n");
            }
        }
        if (count < 24u || count >= 1500u || top_left ||
            (node >= 0x800C8000u && node < 0x800CB000u)) {
            fprintf(stdout,
                    "mohu-vr-diag: ot_node index=%u node=0x%08X "
                    "tag=0x%08X op=0x%02X next=0x%06X top_left=%d\n",
                    count, node, tag, opcode, next, top_left);
        }
        if (next == 0x00FFFFFFu || next >= 0x200000u || (next & 3u)) {
            break;
        }
        node = 0x80000000u | next;
    }
    fflush(stdout);
}

static bool submit_stereo_ot(uint32_t base) {
    uint32_t node = base + 511u * 4u;
    for (uint32_t nodes = 0; nodes < 8192u; ++nodes) {
        if (node < 0x80000000u || node >= 0x80200000u) {
            return false;
        }
        uint32_t tag = psx_mod_read_word(node);
        uint32_t words = tag >> 24;
        uint32_t next = tag & 0x00FFFFFFu;
        if (words > 64u || node + 4u + words * 4u > 0x80200000u) {
            return false;
        }
        for (uint32_t i = 0; i < words; ++i) {
            psx_mod_write_word(0x1F801810u,
                               psx_mod_read_word(node + 4u + i * 4u));
            g_stereo_ot_words++;
        }
        if (next == 0x00FFFFFFu) {
            return true;
        }
        node = 0x80000000u | next;
    }
    return false;
}

static bool prepare_stereo_draw_env(CPUState* cpu, uint32_t ra) {
    const MohuVrEngineBinding* put_draw_env =
        mohu_vr_engine_map_find(MOHU_VR_ROLE_PUT_DRAW_ENV);
    uint32_t index = psx_mod_read_word(MOHU_VR_FRAME_CONTEXT_ADDR + 0x2204u);
    if (!put_draw_env || index > 1u || !ensure_binding_verified(put_draw_env)) {
        return false;
    }
    uint32_t env = MOHU_VR_FRAME_CONTEXT_ADDR + 16u + 184u * index;
    stereo_guest_call(cpu, put_draw_env->target_address, env, 0u, 0u, ra);
    return true;
}

static void set_openxr_native_surface(bool enabled) {
    if (g_no_native_surface) {
        enabled = false;
    }
    if (!g_openxr || g_openxr_native_surface == (enabled ? 1 : 0)) {
        return;
    }
    double distance = enabled ? g_openxr_menu_distance : 0.0;
    double width = enabled ? g_openxr_menu_width : 0.0;
    double units = enabled ? g_openxr_units_per_meter : 0.0;
    if (!psx_mod_openxr_native_surface(distance, width, units)) {
        if (!g_openxr_failure_reported) {
            g_openxr_failure_reported = true;
            fprintf(stdout,
                    "mohu-vr-diag: OpenXR native surface request failed "
                    "enabled=%d distance=%.3f width=%.3f units_per_meter=%.3f\n",
                    enabled ? 1 : 0, distance, width, units);
            fflush(stdout);
        }
        return;
    }
    g_openxr_native_surface = enabled ? 1 : 0;
    (void)psx_mod_set_stereo_presentation(enabled ? 0u : 1u);
}

static void stereo_quat_multiply(const double a[4], const double b[4],
                                 double out[4]) {
    out[0] = a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1];
    out[1] = a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0];
    out[2] = a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3];
    out[3] = a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2];
}

static bool build_stereo_render_view(CPUState* cpu, uint32_t eye,
                                     PSXModRenderView* view) {
    double focal = (uint16_t)cpu->gte_ctrl[26];
    const double width = (double)g_stereo_frame_w;
    const double height = (double)g_stereo_frame_h;
    if (!view || width <= 0.0 || height <= 0.0) {
        return false;
    }

    const bool guest_projection = focal > 0.0 && focal < 4096.0;
    if (!guest_projection) {
        focal = MOHU_VR_FALLBACK_PROJECTION_H;
    }
    double ofx = guest_projection
                     ? (double)(int32_t)cpu->gte_ctrl[24] / 65536.0
                     : width * 0.5;
    double ofy = guest_projection
                     ? (double)(int32_t)cpu->gte_ctrl[25] / 65536.0
                     : height * 0.5;
    if (ofx <= 0.0 || ofx >= width) {
        ofx = width * 0.5;
    }
    if (ofy <= 0.0 || ofy >= height) {
        ofy = height * 0.5;
    }
    const double fov[4] = {
        atan(-ofx / focal),
        atan((width - ofx) / focal),
        atan(ofy / focal),
        -atan((height - ofy) / focal),
    };

    const double yaw =
        (double)g_stereo_yaw_mdeg * 0.001 * MOHU_VR_PI / 180.0;
    const double pitch =
        (double)g_stereo_pitch_mdeg * 0.001 * MOHU_VR_PI / 180.0;
    const double qyaw[4] = {0.0, sin(yaw * 0.5), 0.0, cos(yaw * 0.5)};
    const double qpitch[4] = {sin(pitch * 0.5), 0.0, 0.0,
                              cos(pitch * 0.5)};
    double orientation[4];
    stereo_quat_multiply(qyaw, qpitch, orientation);

    const double eye_sign = eye == PSX_MOD_EYE_LEFT ? -1.0 : 1.0;
    const double position[3] = {
        eye_sign * (double)g_stereo_eye_offset /
                MOHU_VR_DIAGNOSTIC_UNITS_PER_METER +
            (double)g_stereo_head_milli[0] /
                (1000.0 * MOHU_VR_DIAGNOSTIC_UNITS_PER_METER),
        (double)g_stereo_head_milli[1] /
            (1000.0 * MOHU_VR_DIAGNOSTIC_UNITS_PER_METER),
        -(double)g_stereo_head_milli[2] /
            (1000.0 * MOHU_VR_DIAGNOSTIC_UNITS_PER_METER),
    };
    const double origin_orientation[4] = {0.0, 0.0, 0.0, 1.0};
    const double origin_position[3] = {0.0, 0.0, 0.0};
    if (!vr_pose_to_view(orientation, position, origin_orientation,
                         origin_position, fov,
                         MOHU_VR_DIAGNOSTIC_UNITS_PER_METER,
                         (int)width, (int)height, view)) {
        if (!g_stereo_pose_failure_reported) {
            g_stereo_pose_failure_reported = true;
            fprintf(stdout,
                    "mohu-vr-diag: stereo_pose conversion failed eye=%u "
                    "fov=%.6f,%.6f,%.6f,%.6f "
                    "position=%.6f,%.6f,%.6f orientation=%.6f,%.6f,%.6f,%.6f\n",
                    eye, fov[0], fov[1], fov[2], fov[3], position[0],
                    position[1], position[2], orientation[0],
                    orientation[1], orientation[2], orientation[3]);
            fflush(stdout);
        }
        return false;
    }
    if (!g_stereo_pose_logged[eye]) {
        g_stereo_pose_logged[eye] = true;
        fprintf(stdout,
                "mohu-vr-diag: stereo_pose eye=%u h=%.0f ofx=%.3f ofy=%.3f "
                "projection=%s "
                "translation=%d,%d,%d precise=%.6f,%.6f,%.6f "
                "yaw_mdeg=%d pitch_mdeg=%d head_milli=%d,%d,%d\n",
                eye, focal, ofx, ofy, guest_projection ? "guest" : "fallback",
                view->translation[0],
                view->translation[1], view->translation[2],
                view->translation_precise[0], view->translation_precise[1],
                view->translation_precise[2], g_stereo_yaw_mdeg,
                g_stereo_pitch_mdeg, g_stereo_head_milli[0],
                g_stereo_head_milli[1], g_stereo_head_milli[2]);
        fflush(stdout);
    }
    return true;
}

static int vr_stereo_eye_draw(CPUState* cpu, void* user, uint32_t eye) {
    (void)user;
    if (!g_stereo_proof || !g_stereo_active || eye > 1u) {
        return 0;
    }
    g_stereo_current_eye = eye;
    g_stereo_base_valid = false;
    g_stereo_eye_view_valid = false;
    g_laser_level_valid = false;
    g_laser_level_root = 0u;
    g_weapon_model_active = false;
    g_weapon_matrix_saved = false;
    g_weapon_model_object = 0u;
    g_weapon_matrix_addr = 0u;

    uint32_t ra = cpu->gpr[31];
    if (g_stereo_render_view) {
        PSXModRenderView view;
        if (g_openxr) {
            view = g_openxr_eye_view[eye];
        } else if (!build_stereo_render_view(cpu, eye, &view)) {
            if (!g_stereo_pose_failure_reported) {
                g_stereo_pose_failure_reported = true;
                fprintf(stdout,
                        "mohu-vr-diag: stereo_pose build failed eye=%u "
                        "frame=%ux%u h=%u ofx=0x%08X ofy=0x%08X\n",
                        eye, g_stereo_frame_w, g_stereo_frame_h,
                        (uint16_t)cpu->gte_ctrl[26], cpu->gte_ctrl[24],
                        cpu->gte_ctrl[25]);
                fflush(stdout);
            }
            return 0;
        }
        g_stereo_eye_view = view;
        g_stereo_eye_view_valid = true;
        if (!psx_mod_render_view(&view)) {
            if (!g_stereo_pose_failure_reported) {
                g_stereo_pose_failure_reported = true;
                fprintf(stdout,
                        "mohu-vr-diag: stereo_pose rejected eye=%u "
                        "translation=%d,%d,%d projection=%u precise=%u\n",
                        eye, view.translation[0], view.translation[1],
                        view.translation[2], view.projection, view.precise);
                fflush(stdout);
            }
            return 0;
        }
        g_stereo_pose_apps[eye]++;
    }
    if (!prepare_stereo_draw_env(cpu, ra)) {
        return 0;
    }
    clear_stereo_rect();
    if (g_clear_only) {
        return 1;
    }

    uint32_t ot = stereo_ot_base();
    if (ot < 0x80000000u || ot >= 0x80200000u) {
        return 0;
    }
    report_stereo_ot(ot);
    if (g_stereo_ot_only) {
        return submit_stereo_ot(ot);
    }

    if (g_replay_frame_driver) {
        const MohuVrEngineBinding* driver =
            mohu_vr_engine_map_find(MOHU_VR_ROLE_FRAME_DRIVER);
        if (!driver || !g_frame_driver_args_valid ||
            !ensure_binding_verified(driver)) {
            return 0;
        }
        for (size_t i = 0; i < 4u; ++i) {
            cpu->gpr[4u + i] = g_frame_driver_args[i];
        }
        cpu->gpr[31] = ra;
        psx_dispatch_call(cpu, driver->target_address, ra);
        uint32_t after = stereo_ot_base();
        fprintf(stdout,
                "mohu-vr-diag: stereo_driver_ot before=0x%08X after=0x%08X\n",
                ot, after);
        fflush(stdout);
        if (after >= 0x80000000u && after < 0x80200000u) {
            ot = after;
        }
        return submit_stereo_ot(ot);
    }

    if (!g_frame_render_args_valid) {
        return 0;
    }
    for (size_t i = 0; i < 4u; ++i) {
        cpu->gpr[4u + i] = g_frame_render_args[i];
    }
    cpu->gpr[31] = ra;
    g_replaying_frame = true;
    psx_dispatch_call(cpu, 0x80053BB4u, ra);
    g_replaying_frame = false;
    if (g_skip_final_submit) {
        return 1;
    }
    if (g_clear_before_submit) {
        clear_stereo_rect();
    }

    ot = stereo_ot_base();
    if (ot < 0x80000000u || ot >= 0x80200000u) {
        return 0;
    }
    trace_stereo_ot(ot);
    if (g_suppress_flat_hud) {
        unlink_flat_hud_packets(
            ot + 511u * 4u,
            psx_mod_read_word(MOHU_VR_HUD_BUFFER_INDEX_ADDR));
    }
    if (g_stereo_guest_submit) {
        const MohuVrEngineBinding* draw_otag =
            mohu_vr_engine_map_find(MOHU_VR_ROLE_DRAW_OTAG);
        if (!draw_otag || !ensure_binding_verified(draw_otag)) {
            return 0;
        }
        stereo_guest_call(cpu, draw_otag->target_address,
                          ot + 511u * 4u, 0u, 0u, ra);
        g_stereo_guest_submits++;
        vr_laser_draw();
        return 1;
    }
    return submit_stereo_ot(ot);
}

static void run_stereo_proof(CPUState* cpu) {
    if (!g_stereo_proof || g_stereo_active) {
        return;
    }
    uint32_t index = psx_mod_read_word(MOHU_VR_FRAME_CONTEXT_ADDR + 0x2204u);
    if (index > 1u) {
        return;
    }

    PSXModStereoFrame frame;
    memset(&frame, 0, sizeof(frame));
    frame.struct_size = (uint32_t)sizeof(frame);
    frame.period_vblanks = 1u;
    frame.x = 0u;
    /* Replay into one scratch buffer. The guest render's packet coordinates
     * are rooted at y=0; following the native display flip to y=240 clears a
     * buffer the frame does not draw, producing an alternating black pair. */
    frame.y = 0u;
    frame.w = 512u;
    frame.h = 240u;
    g_stereo_frame_x = frame.x;
    g_stereo_frame_y = frame.y;
    g_stereo_frame_w = frame.w;
    g_stereo_frame_h = frame.h;

    g_native_surface_idle_vblanks = 0u;
    if (g_openxr) {
        set_openxr_native_surface(false);
        if (!psx_mod_openxr_begin(frame.w, frame.h,
                                  g_openxr_units_per_meter)) {
            g_openxr_begin_failures++;
            set_openxr_native_surface(true);
            if (!g_openxr_failure_reported) {
                g_openxr_failure_reported = true;
                fprintf(stdout,
                        "mohu-vr-diag: OpenXR begin failed; flat native "
                        "surface remains active\n");
                fflush(stdout);
            }
            return;
        }
        if (!psx_mod_openxr_view(PSX_MOD_EYE_LEFT,
                                 &g_openxr_eye_view[PSX_MOD_EYE_LEFT]) ||
            !psx_mod_openxr_view(PSX_MOD_EYE_RIGHT,
                                 &g_openxr_eye_view[PSX_MOD_EYE_RIGHT])) {
            g_openxr_view_failures++;
            (void)psx_mod_openxr_end(0);
            set_openxr_native_surface(true);
            if (!g_openxr_failure_reported) {
                g_openxr_failure_reported = true;
                fprintf(stdout,
                        "mohu-vr-diag: OpenXR eye view location failed; "
                        "no stereo pair submitted\n");
                fflush(stdout);
            }
            return;
        }
    }

    g_stereo_attempts++;
    g_stereo_active = true;
    int rendered = psx_mod_render_stereo(cpu, &frame, vr_stereo_eye_draw, NULL);
    g_replaying_frame = false;
    g_stereo_active = false;
    if (g_openxr) {
        (void)psx_mod_openxr_end(rendered);
        g_openxr_ends++;
    }
    if (rendered) {
        g_stereo_pairs++;
    }
    if (g_stereo_attempts <= 3u || (g_stereo_attempts % 30u) == 0u) {
        fprintf(stdout,
                "mohu-vr-diag: stereo_proof attempt=%u pairs=%u rendered=%d "
                "status=%u y=%u offset=%d level_hits=%u/%u pose_apps=%u/%u "
                "guest_submits=%u ot_words=%u openxr=%d "
                "xr_begin_failures=%u xr_view_failures=%u xr_ends=%u "
                "frustum=%u/%u fallback=%u/%u hud_skips=%u/%u "
                "hud_unlinked=%u/%u replay_submits_skipped=%u/%u "
                "weapon_hits=%u/%u weapon_fallbacks=%u/%u "
                "laser_hits=%u/%u laser_misses=%u/%u\n",
                g_stereo_attempts, g_stereo_pairs, rendered,
                psx_mod_render_stereo_status(), frame.y, g_stereo_eye_offset,
                g_stereo_level_hits[0], g_stereo_level_hits[1],
                g_stereo_pose_apps[0], g_stereo_pose_apps[1],
                g_stereo_guest_submits, g_stereo_ot_words, g_openxr ? 1 : 0,
                g_openxr_begin_failures, g_openxr_view_failures,
                g_openxr_ends, g_head_frustum_collects[0],
                g_head_frustum_collects[1], g_head_frustum_fallbacks[0],
                g_head_frustum_fallbacks[1], g_flat_hud_skips[0],
                g_flat_hud_skips[1], g_flat_hud_unlinked[0],
                g_flat_hud_unlinked[1], g_replay_submits_skipped[0],
                g_replay_submits_skipped[1], g_weapon_profile_hits[0],
                g_weapon_profile_hits[1], g_weapon_profile_fallbacks[0],
                g_weapon_profile_fallbacks[1], g_laser_hits[0],
                g_laser_hits[1], g_laser_misses[0], g_laser_misses[1]);
        fflush(stdout);
        if (g_replay_frame_driver) {
            fprintf(stdout, "mohu-vr-diag: stereo waits_skipped=%u\n",
                    g_stereo_waits_skipped);
            fflush(stdout);
        }
    }
}

static int vr_head_frustum_filter(CPUState* cpu, uint32_t address) {
    vr_diagnostic_entry(cpu, address);
    if (!g_head_frustum || !g_stereo_active || !g_stereo_eye_view_valid ||
        g_stereo_current_eye > 1u) {
        return 0;
    }

    const MohuVrEngineBinding* binding =
        mohu_vr_engine_map_find(MOHU_VR_ROLE_LEVEL_VERTEX_TRANSFORMER);
    if (!binding ||
        binding->status < MOHU_VR_STATUS_STATIC_CONFIRMED ||
        !verify_binding_now(binding)) {
        g_head_frustum_fallbacks[g_stereo_current_eye]++;
        return 0;
    }

    const uint32_t root = cpu->gpr[4];
    double matrix[9];
    double tr[3];
    for (int i = 0; i < 9; ++i) {
        matrix[i] =
            (int16_t)(cpu->gte_ctrl[i / 2] >> ((i % 2) * 16)) / 4096.0;
    }
    for (int i = 0; i < 3; ++i) {
        tr[i] = (int32_t)cpu->gte_ctrl[5 + i];
    }
    const double cx = (int32_t)cpu->gte_ctrl[24] / 65536.0;
    const double cy = (int32_t)cpu->gte_ctrl[25] / 65536.0;
    const uint32_t masks[2] = {
        psx_mod_read_word(MOHU_VR_LEVEL_MASK0_ADDR),
        psx_mod_read_word(MOHU_VR_LEVEL_MASK1_ADDR),
    };

    uint32_t queue[MOHU_VR_LEVEL_TREE_LEAF_CAPACITY];
    unsigned count = 0;
    if (!mohu_vr_collect_tree(
            root, queue, &count, matrix, tr, &g_stereo_eye_view, cx, cy,
            masks, psx_mod_read_word(MOHU_VR_LEVEL_MASK_BYPASS_ADDR) != 0u,
            g_head_frustum_keep_all)) {
        g_head_frustum_fallbacks[g_stereo_current_eye]++;
        return 0;
    }

    for (unsigned i = 0; i < count; ++i) {
        psx_mod_write_word(
            MOHU_VR_LEVEL_QUEUE_ADDR + i * sizeof(uint32_t), queue[i]);
    }
    psx_mod_write_word(MOHU_VR_LEVEL_QUEUE_COUNT_ADDR, count);
    psx_mod_write_word(MOHU_VR_LEVEL_QUEUE_SENTINEL_ADDR, 0u);
    cpu->gte_ctrl[26] =
        (uint16_t)psx_mod_read_word(MOHU_VR_LEVEL_H_ADDR);
    g_head_frustum_collects[g_stereo_current_eye]++;
    return 1;
}

static int vr_flat_hud_filter(CPUState* cpu, uint32_t address) {
    (void)cpu;
    if (!g_active || !g_stereo_active || g_stereo_current_eye > 1u) {
        return 0;
    }
    for (size_t i = 0;
         i < sizeof(k_flat_hud_bindings) / sizeof(k_flat_hud_bindings[0]);
         ++i) {
        const MohuVrFlatHudBinding* binding = &k_flat_hud_bindings[i];
        if (binding->address != address) {
            continue;
        }
        if (guest_range_fnv1a(binding->address, binding->size) !=
            binding->fnv1a) {
            if (!g_flat_hud_mismatch[i]) {
                g_flat_hud_mismatch[i] = true;
                fprintf(stdout,
                        "mohu-vr-diag: HUD signature mismatch role=%s "
                        "address=0x%08X\n",
                        binding->name, binding->address);
                fflush(stdout);
            }
            return 0;
        }
        /* These producers only populate the flat 2D HUD. Skipping their call
         * leaves the eye's world frame intact while the proper hand/wrist HUD
         * implementation is still pending. */
        g_flat_hud_skips[g_stereo_current_eye]++;
        return 1;
    }
    return 0;
}

static int vr_native_submit_tail_filter(CPUState* cpu, uint32_t address) {
    (void)cpu;
    (void)address;
    if (!g_active || !g_stereo_active || !g_replaying_frame ||
        g_keep_replay_submit || g_stereo_current_eye > 1u) {
        return 0;
    }
    if (guest_range_fnv1a(MOHU_VR_NATIVE_SUBMIT_TAIL_ADDR,
                          MOHU_VR_NATIVE_SUBMIT_TAIL_SIZE) !=
        MOHU_VR_NATIVE_SUBMIT_TAIL_FNV) {
        if (!g_native_tail_mismatch) {
            g_native_tail_mismatch = true;
            fprintf(stdout, "mohu-vr-diag: native submit tail signature mismatch\n");
            fflush(stdout);
        }
        return 0;
    }
    /* The native tail submits before HUD unlink and before our explicit
     * projective DrawOTag. Its flat raster survives wherever that final draw
     * has no geometry (the sky). Let only the final cleaned eye OT submit. */
    g_replay_submits_skipped[g_stereo_current_eye]++;
    return 1;
}

static void vr_diagnostic_entry(CPUState* cpu, uint32_t address) {
    if (!g_active) {
        return;
    }
    report_runtime_hook_counts();

    MohuVrEngineRole role;
    const MohuVrEngineBinding* binding;
    if (!binding_for_address(address, &role, &binding) ||
        !ensure_binding_verified(binding)) {
        return;
    }

    size_t index = (size_t)role;
    if (index >= MOHU_VR_ROLE_COUNT) {
        return;
    }
    if (role == MOHU_VR_ROLE_LEVEL_VERTEX_TRANSFORMER) {
        report_scene_roots(cpu);
        (void)vr_laser_capture_level(cpu);
        if (g_stereo_active) {
            size_t eye = g_stereo_current_eye < 2u ? g_stereo_current_eye : 0u;
            g_stereo_level_hits[eye]++;
            if (!g_stereo_base_valid) {
                g_stereo_base_trx = cpu->gte_ctrl[5];
                g_stereo_base_valid = true;
            }
            if (!g_stereo_render_view && g_stereo_eye_offset != 0 &&
                (g_stereo_apply_all_spans ||
                 cpu->gte_ctrl[5] == g_stereo_base_trx)) {
                int32_t signed_offset =
                    g_stereo_current_eye == 0u ? -g_stereo_eye_offset
                                              : g_stereo_eye_offset;
                cpu->gte_ctrl[5] =
                    (uint32_t)((int32_t)cpu->gte_ctrl[5] + signed_offset);
                g_stereo_pose_apps[eye]++;
            }
        } else if (!g_stereo_active && g_level_offset_x != 0 &&
                   !g_level_offset_applied) {
            g_saved_trx = cpu->gte_ctrl[5];
            cpu->gte_ctrl[5] =
                (uint32_t)((int32_t)g_saved_trx + g_level_offset_x);
            g_level_offset_applied = true;
        }
    } else if (role == MOHU_VR_ROLE_GAMEPLAY_RENDER_WAIT &&
               g_level_offset_applied) {
        cpu->gte_ctrl[5] = g_saved_trx;
        g_level_offset_applied = false;
    }
    if (role == MOHU_VR_ROLE_GAMEPLAY_RENDER_WAIT && g_stereo_active) {
        g_stereo_waits_skipped++;
        (void)psx_mod_finish_function(cpu);
        return;
    }
    if (role == MOHU_VR_ROLE_POST_RENDER_UPDATE && g_stereo_active) {
        (void)psx_mod_finish_function(cpu);
        return;
    }
    if (role == MOHU_VR_ROLE_FRAME_DRIVER) {
        for (size_t i = 0; i < 4u; ++i) {
            g_frame_driver_args[i] = cpu->gpr[4u + i];
        }
        g_frame_driver_args_valid = true;
    }
    if (role == MOHU_VR_ROLE_FRAME_RENDER) {
        for (size_t i = 0; i < 4u; ++i) {
            g_frame_render_args[i] = cpu->gpr[4u + i];
        }
        g_frame_render_args_valid = true;
        run_stereo_proof(cpu);
    }
    if (g_stereo_active && g_stereo_current_eye < 2u &&
        !g_stereo_role_reported[index]) {
        g_stereo_role_reported[index] = true;
        fprintf(stdout,
                "mohu-vr-weapon: stereo role=%s eye=%u ra=0x%08X "
                "a0=0x%08X a1=0x%08X\n",
                binding->name, (unsigned)g_stereo_current_eye, cpu->gpr[31],
                cpu->gpr[4], cpu->gpr[5]);
        fflush(stdout);
    }
    if (g_reported[index]) {
        return;
    }

    g_reported[index] = true;
    fprintf(stdout,
            "mohu-vr-diag: verified role=%s address=0x%08X ra=0x%08X "
            "a0=0x%08X a1=0x%08X a2=0x%08X a3=0x%08X\n",
            binding->name, address, cpu->gpr[31], cpu->gpr[4], cpu->gpr[5],
            cpu->gpr[6], cpu->gpr[7]);
    fflush(stdout);
}

static void vr_weapon_trace_entry(CPUState* cpu, const char* mode) {
    if (g_weapon_trace && g_weapon_trace_count < 64u) {
        ++g_weapon_trace_count;
        fprintf(stdout,
                "mohu-vr-weapon: %s entry=%u a0=0x%08X a1=0x%08X a2=0x%08X "
                "ra=0x%08X H=%u stereo=%d eye=%u\n",
                mode, g_weapon_trace_count, cpu->gpr[4], cpu->gpr[5],
                cpu->gpr[6],
                cpu->gpr[31], (unsigned)cpu->gte_ctrl[26] & 0xffffu,
                g_stereo_active ? 1 : 0, (unsigned)g_stereo_current_eye);
        fflush(stdout);
    }
}

static bool vr_weapon_model_guard(uint32_t object, uint32_t* id_out) {
    if (!id_out || guest_range_fnv1a(MOHU_VR_WEAPON_MODEL_RENDER_ADDR,
                                    MOHU_VR_WEAPON_MODEL_BYTES) !=
                       MOHU_VR_WEAPON_MODEL_FNV1A ||
        guest_range_fnv1a(MOHU_VR_WEAPON_TRANSFORM_ADDR,
                          MOHU_VR_WEAPON_TRANSFORM_BYTES) !=
            MOHU_VR_WEAPON_TRANSFORM_FNV1A) {
        return false;
    }

    const uint32_t player1 = psx_mod_read_word(0x800A3604u);
    if (player1 < 0x800B0000u || player1 > 0x801FF800u ||
        psx_mod_read_word(player1 + 8u) != 1u ||
        object != player1 + MOHU_VR_WEAPON_OBJECT_OFFSET ||
        psx_mod_read_word(object + 0x70u) != 0x00160024u) {
        return false;
    }
    const uint32_t input =
        psx_mod_read_word(player1 + MOHU_VR_PLAYER_INPUT_OFFSET);
    if (input != player1 + 0x400u || input < 0x800B0000u ||
        input > 0x801FFC00u) {
        return false;
    }
    const uint8_t id = psx_mod_read_byte(input + 93u);
    if (!mohu_vr_weapon_profile_find(id)) {
        return false;
    }

    const uint32_t node_header = psx_mod_read_word(object + 0x80u);
    if (node_header < 0x80000000u || node_header > 0x801FFFF8u) {
        return false;
    }
    const uint32_t nodes = psx_mod_read_word(node_header);
    const uint32_t node_count = psx_mod_read_word(node_header + 4u);
    if (nodes < 0x80000000u || nodes > 0x801FFFC0u ||
        node_count != MOHU_VR_WEAPON_NODE_COUNT) {
        return false;
    }
    const uint32_t node_q =
        psx_mod_read_word(object + 0x88u);
    if (node_q < 0x80000000u ||
        node_q > 0x801FFFF0u - MOHU_VR_WEAPON_NODE_COUNT * 8u ||
        (node_q & 3u) != 0u) {
        return false;
    }

    uint8_t table[MOHU_VR_WEAPON_NODE_COUNT * 8u];
    uint16_t counts[MOHU_VR_WEAPON_NODE_COUNT];
    for (unsigned i = 0; i < MOHU_VR_WEAPON_NODE_COUNT; ++i) {
        const uint32_t a = nodes + i * 8u;
        const uint32_t first = psx_mod_read_word(a);
        const uint32_t second = psx_mod_read_word(a + 4u);
        for (unsigned shift = 0; shift < 32u; shift += 8u) {
            table[i * 8u + shift / 8u] =
                (uint8_t)(first >> shift);
            table[i * 8u + 4u + shift / 8u] =
                (uint8_t)(second >> shift);
        }
        counts[i] = (uint16_t)second;
    }
    if (mohu_vr_weapon_fnv1a(table, sizeof table) !=
            MOHU_VR_WEAPON_NODE_TABLE_FNV1A ||
        !mohu_vr_weapon_node_layout_valid(
            counts, MOHU_VR_WEAPON_NODE_COUNT)) {
        if (!g_weapon_profile_guard_reported) {
            g_weapon_profile_guard_reported = true;
            fprintf(stdout,
                    "mohu-vr-weapon: node geometry guard rejected "
                    "id=%u object=0x%08X\n",
                    (unsigned)id, object);
            fflush(stdout);
        }
        return false;
    }
    *id_out = id;
    g_weapon_node_q_addr = node_q;
    return true;
}

static void vr_weapon_identity_rotation(double rotation[9]) {
    memset(rotation, 0, 9u * sizeof rotation[0]);
    rotation[0] = 1.0;
    rotation[4] = 1.0;
    rotation[8] = 1.0;
}

static bool vr_weapon_prepare_delta(void) {
    vr_weapon_identity_rotation(g_weapon_delta_rotation);
    memset(g_weapon_delta_translation, 0,
           sizeof g_weapon_delta_translation);

    if (g_weapon_force_tracking_loss) {
        return false;
    }
    if (g_weapon_synthetic_x || g_weapon_synthetic_yaw_mdeg) {
        const double angle =
            g_weapon_synthetic_yaw_mdeg * MOHU_VR_PI / 180000.0;
        const double c = cos(angle);
        const double s = sin(angle);
        g_weapon_delta_rotation[0] = c;
        g_weapon_delta_rotation[2] = s;
        g_weapon_delta_rotation[6] = -s;
        g_weapon_delta_rotation[8] = c;
        g_weapon_delta_translation[0] = g_weapon_synthetic_x;
        return true;
    }

    PSXModOpenXRHands hands = {0};
    hands.struct_size = sizeof hands;
    double rotation[9];
    double translation[3];
    if (!psx_mod_openxr_hands(&hands) ||
        !mohu_vr_weapon_track_delta(
            &hands, g_openxr_units_per_meter, rotation, translation)) {
        return false;
    }
    if (!g_weapon_neutral_valid) {
        memcpy(g_weapon_neutral_rotation, rotation, sizeof rotation);
        memcpy(g_weapon_neutral_translation, translation,
               sizeof translation);
        g_weapon_neutral_valid = true;
        return true;
    }
    return mohu_vr_weapon_relative_delta(
        rotation, translation, g_weapon_neutral_rotation,
        g_weapon_neutral_translation, g_weapon_delta_rotation,
        g_weapon_delta_translation);
}

static bool vr_weapon_scope(uint32_t* eye_out) {
    if (!g_weapon_pose || !eye_out) {
        return false;
    }
    if (g_stereo_active && g_stereo_current_eye < 2u) {
        *eye_out = g_stereo_current_eye;
        return true;
    }
    if (g_weapon_flat_probe && !g_stereo_active) {
        *eye_out = 0u;
        return true;
    }
    return false;
}

static void vr_weapon_model_enter(CPUState* cpu, uint32_t address) {
    (void)address;
    report_runtime_hook_counts();
    const uint32_t control_generation = g_weapon_control_generation;
    if (control_generation != g_weapon_control_seen) {
        g_weapon_synthetic_x = g_weapon_control_x;
        g_weapon_synthetic_yaw_mdeg = g_weapon_control_yaw_mdeg;
        g_weapon_control_seen = control_generation;
    }
    uint32_t eye = 0;
    if (!vr_weapon_scope(&eye)) {
        return;
    }
    if (g_weapon_model_active) {
        ++g_weapon_profile_fallbacks[eye];
        psx_mod_counter_add("mohu.vr.weapon.model_active_collision", 1);
        return;
    }

    const uint32_t object = cpu->gpr[4];
    uint32_t id = 0;
    if (cpu->gpr[31] != MOHU_VR_WEAPON_MODEL_CALLER_RA ||
        cpu->gpr[5] != psx_mod_read_word(object + 0x84u) ||
        !vr_weapon_model_guard(object, &id)) {
        ++g_weapon_profile_fallbacks[eye];
        psx_mod_counter_add("mohu.vr.weapon.model_guard_fail", 1);
        return;
    }
    if (!vr_weapon_prepare_delta()) {
        ++g_weapon_profile_fallbacks[eye];
        psx_mod_counter_add("mohu.vr.weapon.model_tracking_fail", 1);
        return;
    }

    g_weapon_model_active = true;
    g_weapon_matrix_saved = false;
    g_weapon_model_object = object;
    g_weapon_model_id = id;
    g_weapon_entry_ra = cpu->gpr[31];
    const uint32_t q_addr =
        g_weapon_node_q_addr + 13u * 8u;
    g_weapon_node_q_words[0] = psx_mod_read_word(q_addr);
    g_weapon_node_q_words[1] = psx_mod_read_word(q_addr + 4u);
    int16_t node_q[4];
    for (unsigned i = 0; i < 4u; ++i) {
        node_q[i] =
            (int16_t)(g_weapon_node_q_words[i / 2u] >>
                      ((i & 1u) * 16u));
    }
    if (mohu_vr_weapon_rotate_node_q12(
            node_q, g_weapon_delta_rotation)) {
        psx_mod_write_word(
            q_addr, ((uint32_t)(uint16_t)node_q[0]) |
                    ((uint32_t)(uint16_t)node_q[1] << 16u));
        psx_mod_write_word(
            q_addr + 4u, ((uint32_t)(uint16_t)node_q[2]) |
                         ((uint32_t)(uint16_t)node_q[3] << 16u));
    }
    psx_mod_counter_add("mohu.vr.weapon.model_enter", 1);
    vr_weapon_trace_entry(cpu, "model");
}

static void vr_weapon_model_matrix(CPUState* cpu, uint32_t address) {
    (void)address;
    psx_mod_counter_add("mohu.vr.weapon.matrix_seen", 1);
    uint32_t eye = 0;
    if (!g_weapon_model_active || g_weapon_matrix_saved ||
        !vr_weapon_scope(&eye) ||
        cpu->gpr[10] != g_weapon_model_object) {
        psx_mod_counter_add("mohu.vr.weapon.matrix_guard_fail", 1);
        return;
    }
    const uint32_t matrix = cpu->gpr[5];
    if (matrix < 0x801FF800u || matrix > 0x801FFFE0u ||
        (matrix & 3u) != 0u) {
        ++g_weapon_profile_fallbacks[eye];
        g_weapon_model_active = false;
        psx_mod_counter_add("mohu.vr.weapon.matrix_address_fail", 1);
        return;
    }

    int16_t native_rotation[9];
    int32_t native_translation[3];
    for (unsigned i = 0; i < 8u; ++i) {
        g_weapon_matrix_words[i] =
            psx_mod_read_word(matrix + i * 4u);
    }
    for (unsigned i = 0; i < 9u; ++i) {
        native_rotation[i] =
            (int16_t)psx_mod_read_half(matrix + i * 2u);
    }
    native_translation[0] = (int32_t)g_weapon_matrix_words[5];
    native_translation[1] = (int32_t)g_weapon_matrix_words[6];
    native_translation[2] = (int32_t)g_weapon_matrix_words[7];

    int16_t tracked_rotation[9];
    int32_t tracked_translation[3];
    static const double no_rotation[9] = {
        1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0,
    };
    if (!mohu_vr_weapon_compose_gte(
            native_rotation, native_translation, no_rotation,
            native_translation, g_weapon_delta_translation,
            tracked_rotation, tracked_translation)) {
        ++g_weapon_profile_fallbacks[eye];
        g_weapon_model_active = false;
        psx_mod_counter_add("mohu.vr.weapon.matrix_compose_fail", 1);
        return;
    }

    for (unsigned i = 0; i < 9u; ++i) {
        psx_mod_write_half(matrix + i * 2u,
                           (uint16_t)tracked_rotation[i]);
    }
    for (unsigned i = 0; i < 3u; ++i) {
        psx_mod_write_word(matrix + 20u + i * 4u,
                           (uint32_t)tracked_translation[i]);
    }

    g_weapon_matrix_addr = matrix;
    g_weapon_matrix_saved = true;
    ++g_weapon_profile_hits[eye];
    psx_mod_counter_add("mohu.vr.weapon.model_apply", 1);
    if (!g_weapon_pose_applied_reported) {
        g_weapon_pose_applied_reported = true;
        fprintf(stdout,
                "mohu-vr-weapon: model affine eye=%u id=%u "
                "object=0x%08X matrix=0x%08X pivot=%d,%d,%d "
                "entry_ra=0x%08X synthetic_x=%d yaw_mdeg=%d\n",
                eye, g_weapon_model_id, g_weapon_model_object, matrix,
                native_translation[0], native_translation[1],
                native_translation[2], g_weapon_entry_ra,
                g_weapon_synthetic_x, g_weapon_synthetic_yaw_mdeg);
        fflush(stdout);
    }
}

static void vr_weapon_model_leave(CPUState* cpu, uint32_t address) {
    (void)cpu;
    (void)address;
    if (g_weapon_matrix_saved) {
        for (unsigned i = 0; i < 8u; ++i) {
            psx_mod_write_word(g_weapon_matrix_addr + i * 4u,
                               g_weapon_matrix_words[i]);
        }
    } else if (g_weapon_model_active) {
        uint32_t eye = 0;
        if (vr_weapon_scope(&eye)) {
            ++g_weapon_profile_fallbacks[eye];
            psx_mod_counter_add("mohu.vr.weapon.leave_without_apply", 1);
        }
    }
    if (g_weapon_node_q_addr) {
        const uint32_t q_addr =
            g_weapon_node_q_addr + 13u * 8u;
        psx_mod_write_word(q_addr, g_weapon_node_q_words[0]);
        psx_mod_write_word(q_addr + 4u, g_weapon_node_q_words[1]);
    }
    g_weapon_matrix_saved = false;
    g_weapon_model_active = false;
    g_weapon_model_object = 0u;
    g_weapon_matrix_addr = 0u;
    g_weapon_node_q_addr = 0u;
}

static void vr_diagnostic_activate(void) {
    g_active = true;
    const char* clear_only = getenv("MOHU_VR_CLEAR_ONLY");
    g_clear_only = clear_only && *clear_only && *clear_only != '0';
    const char* skip_submit = getenv("MOHU_VR_SKIP_FINAL_SUBMIT");
    g_skip_final_submit = skip_submit && *skip_submit && *skip_submit != '0';
    const char* clear_before = getenv("MOHU_VR_CLEAR_BEFORE_SUBMIT");
    g_clear_before_submit = clear_before && *clear_before && *clear_before != '0';
    const char* keep_submit = getenv("MOHU_VR_KEEP_REPLAY_SUBMIT");
    g_keep_replay_submit = keep_submit && *keep_submit && *keep_submit != '0';
    parse_optional_int("MOHU_VR_CLEAR_RGB", 0xFFFFFF, &g_clear_rgb);
    if (g_clear_rgb < 0) {
        g_clear_rgb = 0;
    }
    const char* no_native = getenv("MOHU_VR_NO_NATIVE_SURFACE");
    g_no_native_surface = no_native && *no_native && *no_native != '0';
    fprintf(stdout,
            "mohu-vr-diag: controls clear_only=%d clear_rgb=0x%06X "
            "no_native=%d skip_final_submit=%d clear_before_submit=%d "
            "keep_replay_submit=%d\n",
            g_clear_only, (unsigned)g_clear_rgb, g_no_native_surface,
            g_skip_final_submit, g_clear_before_submit, g_keep_replay_submit);
    const char* offset = getenv(MOHU_VR_LEVEL_OFFSET_ENV);
    if (offset && *offset) {
        if (!parse_bounded_int(offset, MOHU_VR_LEVEL_OFFSET_LIMIT,
                               &g_level_offset_x)) {
            fprintf(stdout,
                    "mohu-vr-diag: ignored invalid %s=%s "
                    "(range -%d..%d)\n",
                    MOHU_VR_LEVEL_OFFSET_ENV, offset,
                    MOHU_VR_LEVEL_OFFSET_LIMIT,
                    MOHU_VR_LEVEL_OFFSET_LIMIT);
        }
    }
    const char* stereo = getenv(MOHU_VR_STEREO_PROOF_ENV);
    g_stereo_proof = stereo && *stereo && *stereo != '0';
    const char* replay_driver = getenv(MOHU_VR_REPLAY_DRIVER_ENV);
    g_replay_frame_driver = replay_driver && *replay_driver &&
                            *replay_driver != '0';
    const char* all_spans = getenv(MOHU_VR_EYE_OFFSET_ALL_SPANS_ENV);
    g_stereo_apply_all_spans = all_spans && *all_spans && *all_spans != '0';
    const char* render_view = getenv(MOHU_VR_EYE_RENDER_VIEW_ENV);
    if (!render_view || !*render_view) {
        render_view = getenv(MOHU_VR_EYE_VIEW_OFFSET_ENV);
    }
    g_stereo_render_view = render_view && *render_view &&
                           *render_view != '0';
    parse_optional_int(MOHU_VR_EYE_YAW_MDEG_ENV, MOHU_VR_EYE_ANGLE_LIMIT,
                       &g_stereo_yaw_mdeg);
    parse_optional_int(MOHU_VR_EYE_PITCH_MDEG_ENV, MOHU_VR_EYE_ANGLE_LIMIT,
                       &g_stereo_pitch_mdeg);
    parse_optional_int(MOHU_VR_EYE_HEAD_X_MILLI_ENV,
                       MOHU_VR_EYE_HEAD_MILLI_LIMIT,
                       &g_stereo_head_milli[0]);
    parse_optional_int(MOHU_VR_EYE_HEAD_Y_MILLI_ENV,
                       MOHU_VR_EYE_HEAD_MILLI_LIMIT,
                       &g_stereo_head_milli[1]);
    parse_optional_int(MOHU_VR_EYE_HEAD_Z_MILLI_ENV,
                       MOHU_VR_EYE_HEAD_MILLI_LIMIT,
                       &g_stereo_head_milli[2]);
    parse_optional_int(MOHU_VR_STEREO_DUMP_PAIRS_ENV, 600,
                       &g_stereo_dump_pairs);
    const char* ot_only = getenv(MOHU_VR_OT_ONLY_ENV);
    g_stereo_ot_only = ot_only && *ot_only && *ot_only != '0';
    const char* guest_submit = getenv(MOHU_VR_EYE_GUEST_SUBMIT_ENV);
    g_stereo_guest_submit = guest_submit && *guest_submit &&
                            *guest_submit != '0';
    const char* head_frustum = getenv(MOHU_VR_HEAD_FRUSTUM_ENV);
    if (head_frustum && *head_frustum) {
        int32_t mode = 0;
        if (parse_bounded_int(head_frustum, 2, &mode)) {
            g_head_frustum = mode > 0;
            g_head_frustum_keep_all = mode >= 2;
        } else {
            fprintf(stdout,
                    "mohu-vr-diag: ignored invalid %s=%s (range 0..2)\n",
                    MOHU_VR_HEAD_FRUSTUM_ENV, head_frustum);
            fflush(stdout);
        }
    }
    const char* suppress_flat_hud =
        getenv(MOHU_VR_SUPPRESS_FLAT_HUD_ENV);
    g_suppress_flat_hud = suppress_flat_hud && *suppress_flat_hud &&
                          *suppress_flat_hud != '0';
    const char* openxr = getenv(MOHU_VR_OPENXR_ENV);
    g_openxr = openxr && *openxr && *openxr != '0';
    if (g_openxr) {
        g_stereo_proof = true;
        g_stereo_render_view = true;
        g_stereo_guest_submit = true;
        parse_optional_double(MOHU_VR_UNITS_PER_METER_ENV, 1.0, 65536.0,
                              &g_openxr_units_per_meter);
        parse_optional_double(MOHU_VR_MENU_DISTANCE_ENV, 0.25, 20.0,
                              &g_openxr_menu_distance);
        parse_optional_double(MOHU_VR_MENU_WIDTH_ENV, 0.25, 10.0,
                              &g_openxr_menu_width);
        if (!psx_mod_openxr_enable(1)) {
            g_openxr = false;
            fprintf(stdout,
                    "mohu-vr-diag: OpenXR unavailable; built without "
                    "PSX_OPENXR or no OpenGL renderer\n");
            fflush(stdout);
        }
    }
    const char* weapon_pose = getenv(MOHU_VR_WEAPON_POSE_ENV);
    g_weapon_pose = weapon_pose && *weapon_pose && *weapon_pose != '0';
    const char* weapon_trace = getenv(MOHU_VR_WEAPON_TRACE_ENV);
    g_weapon_trace = weapon_trace && *weapon_trace && *weapon_trace != '0';
    g_weapon_synthetic_x = 0;
    parse_optional_int(MOHU_VR_WEAPON_SYNTHETIC_X_ENV, 2048,
                       &g_weapon_synthetic_x);
    g_weapon_synthetic_yaw_mdeg = 0;
    parse_optional_int(MOHU_VR_WEAPON_SYNTHETIC_YAW_ENV, 180000,
                       &g_weapon_synthetic_yaw_mdeg);
    const char* tracking_loss = getenv(MOHU_VR_WEAPON_TRACKING_LOSS_ENV);
    g_weapon_force_tracking_loss =
        tracking_loss && *tracking_loss && *tracking_loss != '0';
    const char* flat_probe = getenv(MOHU_VR_WEAPON_FLAT_PROBE_ENV);
    g_weapon_flat_probe =
        flat_probe && *flat_probe && *flat_probe != '0';
    g_weapon_neutral_valid = false;
    g_weapon_model_active = false;
    g_weapon_matrix_saved = false;
    g_weapon_control_x = g_weapon_synthetic_x;
    g_weapon_control_yaw_mdeg = g_weapon_synthetic_yaw_mdeg;
    g_weapon_control_generation = 0u;
    g_weapon_control_seen = 0u;
    const char* laser = getenv(MOHU_VR_LASER_ENV);
    if (!laser) {
        laser = getenv(MOHU_VR_LASER_LEGACY_ENV);
    }
    g_laser = !laser || !*laser || *laser != '0';
    const char* laser_synthetic = getenv(MOHU_VR_LASER_SYNTHETIC_ENV);
    g_laser_synthetic = laser_synthetic && *laser_synthetic &&
                        *laser_synthetic != '0';
    parse_optional_double(MOHU_VR_LASER_RANGE_M_ENV, 1.0, 500.0,
                          &g_laser_range_m);
    parse_optional_double(MOHU_VR_LASER_DOT_ENV, 0.0, 32.0,
                          &g_laser_dot_px);
    g_laser_grip = false;
    g_laser_level_valid = false;
    g_laser_level_root = 0u;
    if (g_replay_frame_driver) {
        g_frame_driver_args[0] = MOHU_VR_FRAME_CONTEXT_ADDR;
        g_frame_driver_args_valid = true;
    }
    const char* movement = getenv("PSX_VR_MOVEMENT");
    /* Explicit opt-in also supports synthetic actions without an XR session.
     * Flat launch remains inert even if movement was inherited. */
    g_movement = g_stereo_proof && (movement && *movement ?
                                   *movement != '0' : g_openxr);
    parse_optional_double("PSX_VR_MOVE_DEADZONE", 0.0, 0.9, &g_move_deadzone);
    parse_optional_double("PSX_VR_TURN_GAIN", 0.0, 2.0, &g_turn_gain);
    if (g_movement) {
        int mode = psx_mod_set_controller_mode_override(0, PSX_MOD_CONTROLLER_ANALOG);
        int policy = psx_mod_set_controller_presentation_policy(
            0, vr_controller_mode, PSX_MOD_CONTROLLER_ANALOG, 1);
        int source = psx_mod_set_controller_source(0, vr_controller_source);
        if (!mode || !policy || !source) {
            (void)psx_mod_set_controller_source(0, NULL);
            g_movement = false;
        }
    }
    fprintf(stdout, "mohu-vr-input: enabled=%d deadzone=%.3f turn_gain=%.3f "
            "config=2 sample=offline\n", g_movement, g_move_deadzone, g_turn_gain);
    if (g_stereo_proof) {
        const char* eye_offset = getenv(MOHU_VR_EYE_OFFSET_ENV);
        if (eye_offset && *eye_offset &&
            !parse_bounded_int(eye_offset, MOHU_VR_EYE_OFFSET_LIMIT,
                               &g_stereo_eye_offset)) {
            fprintf(stdout,
                    "mohu-vr-diag: ignored invalid %s=%s "
                    "(range -%d..%d)\n",
                    MOHU_VR_EYE_OFFSET_ENV, eye_offset,
                    MOHU_VR_EYE_OFFSET_LIMIT, MOHU_VR_EYE_OFFSET_LIMIT);
        }
        (void)psx_mod_set_stereo_presentation(1u);
        if (g_stereo_render_view) {
            psx_mod_set_render_projective(1);
        }
        if (g_openxr) {
            set_openxr_native_surface(true);
        }
        const char* dump_dir = getenv(MOHU_VR_STEREO_DUMP_ENV);
        if (dump_dir && *dump_dir) {
            gl_renderer_stereo_dump_arm(
                dump_dir, g_stereo_dump_pairs > 0 ? g_stereo_dump_pairs : 60);
            fprintf(stdout, "mohu-vr-diag: stereo pair dump armed dir=%s\n",
                    dump_dir);
            fflush(stdout);
        }
    }
    size_t hooks = 0;
    for (size_t i = 0; i < mohu_vr_engine_map_count(); ++i) {
        const MohuVrEngineBinding* binding = mohu_vr_engine_map_at(i);
        if (binding && binding->container_kind == MOHU_VR_CONTAINER_OVERLAY &&
            binding->status >= MOHU_VR_STATUS_STATIC_CONFIRMED) {
            hooks++;
        }
    }
    fprintf(stdout,
            "mohu-vr-diag: active bindings=%zu overlay_hooks=%zu read_only=%d "
            "level_offset_x=%d stereo_proof=%d eye_offset=%d render_view=%d "
            "all_spans=%d replay_driver=%d yaw_mdeg=%d pitch_mdeg=%d "
            "head_milli=%d,%d,%d guest_submit=%d head_frustum=%d openxr=%d "
            "flat_hud=%d weapon_pose=%d units_per_meter=%.3f\n",
            mohu_vr_engine_map_count(), hooks + 1u, g_stereo_proof ? 0 : 1,
            g_level_offset_x, g_stereo_proof ? 1 : 0, g_stereo_eye_offset,
            g_stereo_render_view ? 1 : 0, g_stereo_apply_all_spans ? 1 : 0,
            g_replay_frame_driver ? 1 : 0, g_stereo_yaw_mdeg,
            g_stereo_pitch_mdeg, g_stereo_head_milli[0],
            g_stereo_head_milli[1], g_stereo_head_milli[2],
            g_stereo_guest_submit ? 1 : 0, g_head_frustum ? 1 : 0,
            g_openxr ? 1 : 0, g_suppress_flat_hud ? 1 : 0,
            g_weapon_pose ? 1 : 0,
            g_openxr_units_per_meter);
    fprintf(stdout,
            "mohu-vr-weapon: flat_probe=%d synthetic_x=%d yaw_mdeg=%d "
            "tracking_loss=%d\n",
            g_weapon_flat_probe ? 1 : 0, g_weapon_synthetic_x,
            g_weapon_synthetic_yaw_mdeg,
            g_weapon_force_tracking_loss ? 1 : 0);
    fprintf(stdout,
            "mohu-vr-laser: enabled=%d range_m=%.3f dot_px=%.3f "
            "trigger=right_squeeze synthetic=%d\n",
            g_laser ? 1 : 0, g_laser_range_m, g_laser_dot_px,
            g_laser_synthetic ? 1 : 0);
    fprintf(stdout,
            "mohu-vr-diag: single_player_scene=0x%08X player=0x%08X "
            "player_input_offset=0x%X\n",
            MOHU_VR_SP_SCENE_POINTER_ADDR, MOHU_VR_SP_PLAYER_POINTER_ADDR,
            MOHU_VR_PLAYER_INPUT_OFFSET);
    fflush(stdout);
}

PSX_MOD_CONSTRUCTOR(psx_register_mohu_vr_diagnostic_plugin) {
    (void)psx_mod_register_activation_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, vr_diagnostic_activate);
    (void)psx_mod_register_vblank_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, vr_diagnostic_vblank);
    (void)psx_mod_register_command(
        "mohu.vr.weapon.pose", vr_weapon_control_command);
    for (size_t i = 0; i < mohu_vr_engine_map_count(); ++i) {
        const MohuVrEngineBinding* binding = mohu_vr_engine_map_at(i);
        if (binding && binding->status >= MOHU_VR_STATUS_STATIC_CONFIRMED) {
            if (binding->role == MOHU_VR_ROLE_LEVEL_VERTEX_TRANSFORMER) {
                (void)psx_mod_register_function_filter_plugin(
                    MOHU_VR_DIAG_PLUGIN_ID, binding->target_address,
                    vr_head_frustum_filter);
            } else if (binding->role == MOHU_VR_ROLE_PLAYER_OBJECT_UPDATE ||
                       binding->role == MOHU_VR_ROLE_SINGLE_PLAYER_UPDATE ||
                       binding->role == MOHU_VR_ROLE_FIRST_PERSON_MODEL_RENDER) {
                /* This vtable method is reached through the dirty-RAM
                 * interpreter, so audited instruction sites are its hook
                 * contract rather than a function-entry table entry. */
            } else {
                (void)psx_mod_register_function_entry_plugin(
                    MOHU_VR_DIAG_PLUGIN_ID, binding->target_address,
                    vr_diagnostic_entry);
            }
        }
    }
    const int weapon_enter = psx_mod_register_instruction_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, MOHU_VR_WEAPON_MODEL_RENDER_ADDR,
        MOHU_VR_WEAPON_MODEL_RENDER_WORD, vr_weapon_model_enter);
    const int weapon_matrix = psx_mod_register_instruction_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, MOHU_VR_WEAPON_MODEL_MATRIX_ADDR,
        MOHU_VR_WEAPON_MODEL_MATRIX_WORD, vr_weapon_model_matrix);
    const int weapon_leave = psx_mod_register_instruction_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, MOHU_VR_WEAPON_MODEL_LEAVE_ADDR,
        MOHU_VR_WEAPON_MODEL_LEAVE_WORD, vr_weapon_model_leave);
    fprintf(stdout,
            "mohu-vr-weapon: model hooks enter=%d matrix=%d leave=%d\n",
            weapon_enter, weapon_matrix, weapon_leave);
    fflush(stdout);
    (void)psx_mod_register_function_filter_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, MOHU_VR_NATIVE_SUBMIT_TAIL_ADDR,
        vr_native_submit_tail_filter);
    for (size_t i = 0;
         i < sizeof(k_flat_hud_bindings) / sizeof(k_flat_hud_bindings[0]);
         ++i) {
        (void)psx_mod_register_function_filter_plugin(
            MOHU_VR_DIAG_PLUGIN_ID, k_flat_hud_bindings[i].address,
            vr_flat_hud_filter);
    }
}
