#include "cpu_state.h"
#include "camera_map.h"
#include "engine_map.h"
#include "frustum.h"
#include "hud_packets.h"
#include "input.h"
#include "inverse.h"
#include "menu_surface.h"
#include "mp_view.h"
#include "raycast.h"
#include "shot.h"
#include "psx_cycles.h"
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
#define MOHU_VR_INPUT_CONVERTER_ADDR 0x80083C6Cu
#define MOHU_VR_INPUT_CONVERTER_SIZE 324u
#define MOHU_VR_INPUT_CONVERTER_FNV 0x9CA131D0u
#define MOHU_VR_INPUT_DISPATCHER_ADDR 0x80083DB0u
#define MOHU_VR_INPUT_DISPATCHER_SIZE 84u
#define MOHU_VR_INPUT_DISPATCHER_FNV 0x2D93CB1Cu
#define MOHU_VR_INPUT_AXES_ADDR 0x800C47C8u
#define MOHU_VR_INPUT_ACTIONS_ADDR 0x800C4AA8u
#define MOHU_VR_INPUT_INVERSIONS_ADDR 0x800C4AD0u
#define MOHU_VR_INPUT_CURVE_ADDR 0x800AB12Cu

/* The multiplayer overlay shares the mapper contract but relocates every table. */
#define MOHU_VR_MP_INPUT_CONVERTER_ADDR 0x800799E4u
#define MOHU_VR_MP_INPUT_CONVERTER_SIZE 324u
#define MOHU_VR_MP_INPUT_CONVERTER_FNV 0x890B7F9Fu
#define MOHU_VR_MP_INPUT_DISPATCHER_ADDR 0x80079B28u
#define MOHU_VR_MP_INPUT_DISPATCHER_SIZE 84u
#define MOHU_VR_MP_INPUT_DISPATCHER_FNV 0x9E630C72u
#define MOHU_VR_MP_INPUT_AXES_ADDR 0x800C0BF0u
#define MOHU_VR_MP_INPUT_ACTIONS_ADDR 0x800C0ED0u
#define MOHU_VR_MP_INPUT_INVERSIONS_ADDR 0x800C0F20u
#define MOHU_VR_MP_INPUT_CURVE_ADDR 0x800A458Cu
#define MOHU_VR_MP_INPUT_ENABLED_ADDR 0x800A4578u

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
static bool g_mp_control;
static bool g_stereo_mp;
static bool g_mp_reported;
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
typedef struct {
    uint32_t node;
    uint32_t return_address;
    uint32_t eye;
    int16_t center[3];
    int16_t radius;
    uint32_t control[8];
    uint32_t screen_width;
    uint32_t screen_height;
    uint32_t projection_h;
    uint32_t ofx_q16;
    uint32_t ofy_q16;
    uint32_t camera;
    uint32_t input;
    uint32_t view;
    uint32_t native_result;
    uint32_t override_result;
    bool result_valid;
    bool override_valid;
} MohuVrMpFrustumSample;
static bool g_mp_frustum_capture;
static uint32_t g_mp_frustum_capture_count;
static uint32_t g_mp_frustum_capture_last;
static MohuVrMpFrustumSample g_mp_frustum_samples[64];
static bool g_mp_frustum;
static bool g_mp_replay_guard_valid;
static uint32_t g_mp_frustum_overrides[2];
static uint32_t g_mp_frustum_fallbacks[2];
static bool g_mp_frustum_failure_reported;
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
static bool g_weapon_viewmodel_pending;
static bool g_weapon_viewmodel_applied;
static bool g_weapon_viewmodel_view;
static bool g_weapon_gun_only;
static bool g_weapon_gun_only_all;
static bool g_weapon_gun_only_ready;
static bool g_weapon_delta_valid;
static uint32_t g_mp_weapon_draws[2];
static uint32_t g_weapon_viewmodel_saved_control[8];
static uint32_t g_weapon_viewmodel_sp;
static uint32_t g_weapon_trace_count;
static int32_t g_weapon_synthetic_x;
static int32_t g_weapon_synthetic_yaw_mdeg;
static bool g_weapon_force_tracking_loss;
static bool g_weapon_flat_probe;
static uint32_t g_weapon_profile_hits[2];
static uint32_t g_weapon_profile_fallbacks[2];
static uint32_t g_weapon_profile_last_id;
static uint32_t g_weapon_profile_last_object;
static uint32_t g_weapon_capture_sequence;
static uint32_t g_weapon_capture_node = 11u;
static bool g_weapon_capture_valid;
static uint32_t g_weapon_capture_frame;
static uint32_t g_weapon_capture_node_table;
static uint32_t g_weapon_capture_output_table;
static uint32_t g_weapon_capture_node_count;
static uint32_t g_weapon_capture_local_addr;
static uint32_t g_weapon_capture_output_addr;
static int16_t g_weapon_capture_local[MOHU_VR_WEAPON_FP_MAX_NODES][4];
static int16_t g_weapon_capture_animated[MOHU_VR_WEAPON_FP_MAX_NODES][4];
enum { MOHU_VR_WEAPON_CAPTURE_VERTEX_LIMIT = 256 };
static int16_t
    g_weapon_capture_local_vertices[MOHU_VR_WEAPON_CAPTURE_VERTEX_LIMIT][4];
static int16_t
    g_weapon_capture_animated_vertices[MOHU_VR_WEAPON_CAPTURE_VERTEX_LIMIT][4];
static uint32_t g_weapon_capture_vertex_count;
static int16_t
    g_weapon_capture_snapshot_local[MOHU_VR_WEAPON_CAPTURE_VERTEX_LIMIT][4];
static int16_t
    g_weapon_capture_snapshot_animated[MOHU_VR_WEAPON_CAPTURE_VERTEX_LIMIT][4];
static uint32_t g_weapon_capture_snapshot_count;
static bool g_weapon_capture_snapshot_valid;
enum { MOHU_VR_WEAPON_FRAME_VERTEX_LIMIT = 256 };
static int16_t
    g_weapon_capture_frame_local[MOHU_VR_WEAPON_FRAME_VERTEX_LIMIT][4];
static int16_t
    g_weapon_capture_frame_animated[MOHU_VR_WEAPON_FRAME_VERTEX_LIMIT][4];
static uint8_t
    g_weapon_capture_frame_nodes[MOHU_VR_WEAPON_FRAME_VERTEX_LIMIT];
static uint16_t
    g_weapon_capture_frame_indices[MOHU_VR_WEAPON_FRAME_VERTEX_LIMIT];
static uint16_t
    g_weapon_capture_frame_node_counts[MOHU_VR_WEAPON_FP_MAX_NODES];
static uint32_t g_weapon_capture_frame_vertex_count;
static uint32_t g_weapon_capture_frame_native_control[8];
static bool g_weapon_capture_frame_valid;
/* A request copies the next complete model frame so chunk readers cannot
 * observe a different animation frame between the metadata and vertices. */
static int16_t
    g_weapon_capture_frame_snapshot_local[MOHU_VR_WEAPON_FRAME_VERTEX_LIMIT][4];
static int16_t g_weapon_capture_frame_snapshot_animated
    [MOHU_VR_WEAPON_FRAME_VERTEX_LIMIT][4];
static uint8_t
    g_weapon_capture_frame_snapshot_nodes[MOHU_VR_WEAPON_FRAME_VERTEX_LIMIT];
static uint16_t
    g_weapon_capture_frame_snapshot_indices[MOHU_VR_WEAPON_FRAME_VERTEX_LIMIT];
static uint16_t g_weapon_capture_frame_snapshot_node_counts
    [MOHU_VR_WEAPON_FP_MAX_NODES];
static uint32_t g_weapon_capture_frame_snapshot_vertex_count;
static uint32_t g_weapon_capture_frame_snapshot_native_control[8];
static uint32_t g_weapon_capture_frame_snapshot_sequence;
static uint32_t g_weapon_capture_frame_snapshot_frame;
static uint32_t g_weapon_capture_frame_snapshot_id;
static uint32_t g_weapon_capture_frame_snapshot_node_count;
static bool g_weapon_capture_frame_snapshot_valid;
static bool g_weapon_capture_frame_requested;
static uint32_t g_weapon_capture_local_addrs[MOHU_VR_WEAPON_FP_MAX_NODES];
static uint32_t g_weapon_capture_output_addrs[MOHU_VR_WEAPON_FP_MAX_NODES];
static uint32_t g_weapon_capture_native_control[8];
static uint32_t g_weapon_capture_tracked_control[8];
static uint32_t g_weapon_capture_restored_control[8];
static bool g_weapon_capture_tracked_valid;
static bool g_weapon_capture_restored_valid;
static bool g_weapon_capture_eye_view_valid;
static PSXModRenderView g_weapon_capture_eye_view;
static int32_t g_weapon_capture_ofx_q16;
static int32_t g_weapon_capture_ofy_q16;
static bool g_weapon_capture_bounds_valid;
static double g_weapon_capture_camera_min[3];
static double g_weapon_capture_camera_max[3];
static double g_weapon_capture_screen_min[2];
static double g_weapon_capture_screen_max[2];
static bool g_weapon_pose_applied_reported;
static bool g_runtime_hook_counts_reported;
static double g_weapon_delta_rotation[9];
static double g_weapon_delta_translation[3];
static bool g_weapon_absolute;
static bool g_p38_calibrated, g_p38_aim;
static bool g_weapon_calibrated_all;
static uint32_t g_p38_masked_vertices[2], g_p38_gun_vertices[2];
static volatile int32_t g_weapon_control_x;
static volatile int32_t g_weapon_control_yaw_mdeg;
static volatile int32_t g_weapon_control_loss;
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
static int g_input_mode_reported = -1;
static bool g_input_callback_reported;

static void set_openxr_native_surface(bool enabled);
static uint32_t guest_range_fnv1a(uint32_t address, uint32_t size);
static bool vr_mp_snapshot(MohuVrMpState* state);

static bool vr_mp_input_snapshot(MohuVrMpInputState* state) {
    if (!state) return false;
    memset(state, 0, sizeof *state);
    state->width = psx_mod_read_word(MOHU_VR_MP_CONTEXT);
    state->height = psx_mod_read_word(MOHU_VR_MP_CONTEXT + 4u);
    state->focal = psx_mod_read_word(MOHU_VR_MP_CONTEXT + 8u);
    state->player = psx_mod_read_word(MOHU_VR_MP_P1_ROOT);
    state->other_player = psx_mod_read_word(MOHU_VR_MP_P1_ROOT + 4u);
    state->current_player = psx_mod_read_word(MOHU_VR_MP_CURRENT_PLAYER);
    if (!mohu_vr_mp_actor_address(state->player) ||
        !mohu_vr_mp_actor_address(state->other_player)) return false;
    state->player_class = psx_mod_read_word(state->player + 8u);
    state->other_class = psx_mod_read_word(state->other_player + 8u);
    state->player_input = psx_mod_read_word(state->player + 0x39Cu);
    state->other_input = psx_mod_read_word(state->other_player + 0x39Cu);
    return mohu_vr_mp_input_state_valid(state) != 0;
}

static bool vr_input_actions_match(uint32_t actions_address,
                                   uint32_t inversions_address,
                                   const uint32_t expected[9]) {
    for (unsigned index = 0; index < 9u; ++index) {
        if (psx_mod_read_word(actions_address + index * 4u) != expected[index] ||
            psx_mod_read_word(inversions_address + index * 4u) != 0u) {
            return false;
        }
    }
    return true;
}

static bool vr_input_response_load(uint32_t axes_address, unsigned config,
                                   const unsigned entry[3],
                                   const unsigned native_axis[3],
                                   uint32_t curve_address,
                                   MohuVRAnalogResponse* response) {
    if (!response || config > 1u) return false;
    memset(response, 0, sizeof *response);
    for (unsigned index = 0; index < 3u; ++index) {
        if (entry[index] > 3u) return false;
        const uint32_t base =
            axes_address + config * 160u + entry[index] * 40u;
        MohuVRAnalogAxis* axis = &response->axis[index];
        if (psx_mod_read_word(base) != native_axis[index] ||
            psx_mod_read_word(base + 36u) != 0u) {
            return false;
        }
        axis->center = psx_mod_read_byte(base + 14u);
        axis->negative_factor = psx_mod_read_word(base + 20u);
        axis->positive_factor = psx_mod_read_word(base + 24u);
        axis->scale = psx_mod_read_word(base + 32u) >> 8;
    }
    for (unsigned index = 0; index < sizeof response->curve; ++index)
        response->curve[index] = psx_mod_read_byte(curve_address + index);
    return true;
}

/* The game rebuilds the selected calibration after DualShock presentation.
 * Measured boot/load layouts swap entries 1/3; native LX/LY/RX retain their
 * turn/forward/strafe roles. Never force a guest configuration or table. */
static int vr_controller_source(PSXModControllerState* pad) {
    psx_mod_counter_add("mohu.vr.input.callback", 1);
    if (g_stereo_active) {
        /* Eye replay runs guest code synchronously. Do not even query the XR
         * action snapshot from that render transaction. */
        psx_mod_counter_add("mohu.vr.input.render_blocked", 1);
        return 0;
    }
    PSXModOpenXRInput input = {0};
    input.struct_size = sizeof input;
    const bool input_ok = psx_mod_openxr_input(&input);
    if (!g_input_callback_reported) {
        g_input_callback_reported = true;
        fprintf(stdout, "mohu-vr-input: callback stereo=0 input=%d\n",
                input_ok ? 1 : 0);
        fflush(stdout);
    }
    if (!input_ok) return 0;
    if (!input.focused) {
        psx_mod_counter_add("mohu.vr.input.focus_lost", 1);
    }
    MohuVrMpInputState mp;
    const bool multiplayer = vr_mp_input_snapshot(&mp);
    uint32_t player = psx_mod_read_word(MOHU_VR_SP_PLAYER_POINTER_ADDR);
    const int input_mode = g_openxr_native_surface == 1 ? 2 : multiplayer ? 1 : 0;
    psx_mod_counter_add(
        input_mode == 2 ? "mohu.vr.input.mode.menu"
                        : input_mode == 1 ? "mohu.vr.input.mode.mp"
                                          : "mohu.vr.input.mode.sp",
        1);
    if (input_mode != g_input_mode_reported) {
        g_input_mode_reported = input_mode;
        fprintf(stdout, "mohu-vr-input: mode=%s mp_player=0x%08X "
                        "sp_player=0x%08X current=0x%08X\n",
                input_mode == 2 ? "menu" : input_mode == 1 ? "mp" : "sp",
                multiplayer ? mp.player : 0u, player,
                multiplayer ? mp.current_player : 0u);
        fflush(stdout);
    }
    if (g_openxr_native_surface == 1 ||
        (!multiplayer &&
         (player < 0x80000000u || player >= 0x801FFC00u)))
        return mohu_vr_menu_input_map(&input, g_move_deadzone, pad);

    const uint32_t converter_address =
        multiplayer ? MOHU_VR_MP_INPUT_CONVERTER_ADDR
                    : MOHU_VR_INPUT_CONVERTER_ADDR;
    const uint32_t converter_size =
        multiplayer ? MOHU_VR_MP_INPUT_CONVERTER_SIZE
                    : MOHU_VR_INPUT_CONVERTER_SIZE;
    const uint32_t converter_hash =
        multiplayer ? MOHU_VR_MP_INPUT_CONVERTER_FNV
                    : MOHU_VR_INPUT_CONVERTER_FNV;
    const uint32_t dispatcher_address =
        multiplayer ? MOHU_VR_MP_INPUT_DISPATCHER_ADDR
                    : MOHU_VR_INPUT_DISPATCHER_ADDR;
    const uint32_t dispatcher_size =
        multiplayer ? MOHU_VR_MP_INPUT_DISPATCHER_SIZE
                    : MOHU_VR_INPUT_DISPATCHER_SIZE;
    const uint32_t dispatcher_hash =
        multiplayer ? MOHU_VR_MP_INPUT_DISPATCHER_FNV
                    : MOHU_VR_INPUT_DISPATCHER_FNV;
    const uint32_t axes_address =
        multiplayer ? MOHU_VR_MP_INPUT_AXES_ADDR : MOHU_VR_INPUT_AXES_ADDR;
    const uint32_t actions_address =
        multiplayer ? MOHU_VR_MP_INPUT_ACTIONS_ADDR
                    : MOHU_VR_INPUT_ACTIONS_ADDR;
    const uint32_t inversions_address =
        multiplayer ? MOHU_VR_MP_INPUT_INVERSIONS_ADDR
                    : MOHU_VR_INPUT_INVERSIONS_ADDR;
    const uint32_t curve_address =
        multiplayer ? MOHU_VR_MP_INPUT_CURVE_ADDR : MOHU_VR_INPUT_CURVE_ADDR;
    bool analog_layout = multiplayer ||
                         psx_mod_read_word(0x800C47F0u) == 0;
    const unsigned entry[3] = {
        multiplayer ? 3u : (analog_layout ? 3u : 1u),
        0,
        multiplayer ? 1u : (analog_layout ? 1u : 3u),
    };
    const unsigned native_axis[3] = {2, 3, 0};
    const uint32_t analog_actions[9] =
        {0x40, 0x10, 0x20, 1, 0x80, 0x80, 0x800, 0x200, 2};
    const uint32_t initial_actions[9] =
        {0x40, 0x10, 0x20, 1, 0x80, 0x80, 0x800, 3, 2};
    bool valid =
        guest_range_fnv1a(converter_address, converter_size) == converter_hash &&
        guest_range_fnv1a(dispatcher_address, dispatcher_size) ==
            dispatcher_hash &&
        vr_input_actions_match(
            actions_address, inversions_address,
            multiplayer || analog_layout ? analog_actions : initial_actions);
    if (multiplayer) {
        valid = valid && psx_mod_read_word(MOHU_VR_MP_INPUT_ENABLED_ADDR) != 0u;
    }
    MohuVRAnalogResponse response;
    valid = valid &&
            vr_input_response_load(axes_address,
                                   multiplayer ? 0u : analog_layout ? 0u : 1u,
                                   entry, native_axis, curve_address, &response);
    if (!valid) {
        psx_mod_counter_add("mohu.vr.input.guard_fallback", 1);
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
static void run_stereo_proof(CPUState* cpu);

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
    if (!mohu_vr_laser_inverse(g_laser_camera_rotation,
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
        g_weapon_force_tracking_loss = g_weapon_control_loss != 0;
        g_weapon_control_seen = generation;
    }
}

static int vr_weapon_control_command(const char* args, char* reply, int cap) {
    if (!args || !reply || cap < 1) {
        return 0;
    }
    int32_t next_x = g_weapon_control_x;
    int32_t next_yaw = g_weapon_control_yaw_mdeg;
    int32_t next_loss = g_weapon_control_loss;
    if (strcmp(args, "reset") == 0) {
        next_x = 0;
        next_yaw = 0;
        next_loss = 0;
    } else {
        char* end = NULL;
        unsigned seen = 0;
        const char* p = args;
        while (*p) {
            while (*p == ' ' || *p == '\t' || *p == ',') {
                ++p;
            }
            if (!*p) break;
            if (strncmp(p, "x=", 2u) == 0) {
                long value = strtol(p + 2, &end, 0);
                if (end == p + 2 || value < -2048 || value > 2048) {
                    return -1;
                }
                next_x = (int32_t)value;
                seen |= 1u;
                p = end;
            } else if (strncmp(p, "yaw=", 4u) == 0) {
                long value = strtol(p + 4, &end, 0);
                if (end == p + 4 || value < -180000 || value > 180000) {
                    return -1;
                }
                next_yaw = (int32_t)value;
                seen |= 2u;
                p = end;
            } else if (strncmp(p, "lost=", 5u) == 0) {
                long value = strtol(p + 5, &end, 0);
                if (end == p + 5 || value < 0 || value > 1) return -1;
                next_loss = (int32_t)value;
                seen |= 4u;
                p = end;
            } else {
                return -1;
            }
        }
        if (seen == 0u) {
            return -1;
        }
    }
    g_weapon_control_x = next_x;
    g_weapon_control_yaw_mdeg = next_yaw;
    g_weapon_control_loss = next_loss;
    g_weapon_control_generation++;
    (void)snprintf(reply, (size_t)cap, "x=%d yaw_mdeg=%d lost=%d",
                   g_weapon_control_x, g_weapon_control_yaw_mdeg,
                   g_weapon_control_loss);
    return 1;
}

static int vr_weapon_space_command(const char* args, char* reply, int cap) {
    if (!args || !reply || cap < 1) {
        return 0;
    }
    if (strncmp(args, "node=", 5u) == 0) {
        char* end = NULL;
        const long value = strtol(args + 5, &end, 0);
        if (end == args + 5 || *end != '\0' || value < 0 ||
            value >= (long)MOHU_VR_WEAPON_FP_MAX_NODES) {
            return -1;
        }
        g_weapon_capture_node = (uint32_t)value;
        g_weapon_capture_snapshot_valid = false;
        (void)snprintf(reply, (size_t)cap,
                       "{\"valid\":false,\"sequence\":%u}",
                       g_weapon_capture_sequence);
        return 1;
    } else if (strcmp(args, "frame-capture") == 0) {
        g_weapon_capture_frame_snapshot_valid = false;
        g_weapon_capture_frame_requested = true;
        (void)snprintf(reply, (size_t)cap,
                       "{\"requested\":true,\"sequence\":%u}",
                       g_weapon_capture_sequence);
        return 1;
    } else if (strcmp(args, "frame") == 0) {
        if (!g_weapon_capture_frame_snapshot_valid) {
            (void)snprintf(reply, (size_t)cap,
                           "{\"valid\":false,\"sequence\":%u}",
                           g_weapon_capture_frame_snapshot_sequence);
            return 1;
        }
        int written = snprintf(
            reply, (size_t)cap,
            "{\"valid\":true,\"sequence\":%u,\"frame\":%u,\"id\":%u,"
            "\"node_count\":%u,\"vertex_count\":%u,\"nodes\":[",
            g_weapon_capture_frame_snapshot_sequence,
            g_weapon_capture_frame_snapshot_frame,
            g_weapon_capture_frame_snapshot_id,
            g_weapon_capture_frame_snapshot_node_count,
            g_weapon_capture_frame_snapshot_vertex_count);
        for (uint32_t node = 0;
             written > 0 && written < cap &&
             node < g_weapon_capture_frame_snapshot_node_count; ++node) {
            written += snprintf(
                reply + written, (size_t)(cap - written),
                "%s{\"node\":%u,\"count\":%u}", node ? "," : "", node,
                g_weapon_capture_frame_snapshot_node_counts[node]);
        }
        if (written > 0 && written < cap) {
            written += snprintf(
                reply + written, (size_t)(cap - written),
                "],\"native_gte\":[\"%08X\",\"%08X\",\"%08X\",\"%08X\","
                "\"%08X\",\"%08X\",\"%08X\",\"%08X\"]}",
                g_weapon_capture_frame_snapshot_native_control[0],
                g_weapon_capture_frame_snapshot_native_control[1],
                g_weapon_capture_frame_snapshot_native_control[2],
                g_weapon_capture_frame_snapshot_native_control[3],
                g_weapon_capture_frame_snapshot_native_control[4],
                g_weapon_capture_frame_snapshot_native_control[5],
                g_weapon_capture_frame_snapshot_native_control[6],
                g_weapon_capture_frame_snapshot_native_control[7]);
        }
        return written >= 0 && written < cap ? 1 : -1;
    } else if (strncmp(args, "frame=", 6u) == 0) {
        char* end = NULL;
        const long start = strtol(args + 6, &end, 0);
        if (end == args + 6 || *end != '\0' || start < 0 ||
            start > (long)g_weapon_capture_frame_snapshot_vertex_count ||
            !g_weapon_capture_frame_snapshot_valid) {
            return -1;
        }
        const uint32_t available =
            start < (long)g_weapon_capture_frame_snapshot_vertex_count
                ? g_weapon_capture_frame_snapshot_vertex_count -
                      (uint32_t)start
                : 0u;
        const uint32_t count = available < 4u ? available : 4u;
        int written = snprintf(
            reply, (size_t)cap,
            "{\"valid\":true,\"sequence\":%u,\"start\":%ld,\"count\":%u,"
            "\"total\":%u,\"nodes\":[",
            g_weapon_capture_frame_snapshot_sequence, start, count,
            g_weapon_capture_frame_snapshot_vertex_count);
        for (uint32_t i = 0; i < count && written > 0 && written < cap; ++i) {
            const uint32_t index = (uint32_t)start + i;
            written += snprintf(
                reply + written, (size_t)(cap - written), "%s%d",
                i ? "," : "",
                g_weapon_capture_frame_snapshot_nodes[index]);
        }
        if (written > 0 && written < cap) {
            written += snprintf(reply + written, (size_t)(cap - written),
                                "],\"indices\":[");
        }
        for (uint32_t i = 0; i < count && written > 0 && written < cap; ++i) {
            const uint32_t index = (uint32_t)start + i;
            written += snprintf(
                reply + written, (size_t)(cap - written), "%s%u",
                i ? "," : "",
                g_weapon_capture_frame_snapshot_indices[index]);
        }
        if (written > 0 && written < cap) {
            written += snprintf(reply + written, (size_t)(cap - written),
                                "],\"local\":[");
        }
        for (uint32_t i = 0; i < count && written > 0 && written < cap; ++i) {
            const int16_t* vertex =
                g_weapon_capture_frame_snapshot_local[(uint32_t)start + i];
            written += snprintf(
                reply + written, (size_t)(cap - written),
                "%s[%d,%d,%d,%d]", i ? "," : "", vertex[0], vertex[1],
                vertex[2], vertex[3]);
        }
        if (written > 0 && written < cap) {
            written += snprintf(reply + written, (size_t)(cap - written),
                                "],\"animated\":[");
        }
        for (uint32_t i = 0; i < count && written > 0 && written < cap; ++i) {
            const int16_t* vertex =
                g_weapon_capture_frame_snapshot_animated
                    [(uint32_t)start + i];
            written += snprintf(
                reply + written, (size_t)(cap - written),
                "%s[%d,%d,%d,%d]", i ? "," : "", vertex[0], vertex[1],
                vertex[2], vertex[3]);
        }
        if (written > 0 && written < cap) {
            (void)snprintf(reply + written, (size_t)(cap - written), "]}");
        }
        return written >= 0 && written < cap ? 1 : -1;
    } else if (strcmp(args, "bounds") == 0) {
        if (!g_weapon_capture_bounds_valid) {
            (void)snprintf(reply, (size_t)cap,
                           "{\"valid\":false,\"sequence\":%u}",
                           g_weapon_capture_sequence);
            return 1;
        }
        (void)snprintf(
            reply, (size_t)cap,
            "{\"valid\":true,\"sequence\":%u,\"camera_min\":[%.9f,%.9f,%.9f],"
            "\"camera_max\":[%.9f,%.9f,%.9f],"
            "\"screen_min\":[%.9f,%.9f],\"screen_max\":[%.9f,%.9f]}",
            g_weapon_capture_sequence, g_weapon_capture_camera_min[0],
            g_weapon_capture_camera_min[1], g_weapon_capture_camera_min[2],
            g_weapon_capture_camera_max[0], g_weapon_capture_camera_max[1],
            g_weapon_capture_camera_max[2], g_weapon_capture_screen_min[0],
            g_weapon_capture_screen_min[1], g_weapon_capture_screen_max[0],
            g_weapon_capture_screen_max[1]);
        return 1;
    } else if (strncmp(args, "vertices=", 9u) == 0) {
        char* end = NULL;
        const long start = strtol(args + 9, &end, 0);
        if (end == args + 9 || *end != '\0' || start < 0 ||
            start > (long)g_weapon_capture_snapshot_count ||
            !g_weapon_capture_snapshot_valid) {
            return -1;
        }
        const uint32_t available =
            start < (long)g_weapon_capture_snapshot_count
                ? g_weapon_capture_snapshot_count - (uint32_t)start
                : 0u;
        const uint32_t count = available < 4u ? available : 4u;
        int written = snprintf(
            reply, (size_t)cap,
            "{\"valid\":true,\"sequence\":%u,\"node\":%u,\"start\":%ld,"
            "\"count\":%u,\"total\":%u,\"local\":[",
            g_weapon_capture_sequence, g_weapon_capture_node, start, count,
            g_weapon_capture_snapshot_count);
        for (uint32_t i = 0; i < count && written > 0 && written < cap; ++i) {
            const int16_t* vertex =
                g_weapon_capture_snapshot_local[(uint32_t)start + i];
            written += snprintf(
                reply + written, (size_t)(cap - written),
                "%s[%d,%d,%d,%d]", i ? "," : "", vertex[0], vertex[1],
                vertex[2], vertex[3]);
        }
        if (written > 0 && written < cap) {
            written += snprintf(reply + written, (size_t)(cap - written),
                                "],\"animated\":[");
        }
        for (uint32_t i = 0; i < count && written > 0 && written < cap; ++i) {
            const int16_t* vertex =
                g_weapon_capture_snapshot_animated[(uint32_t)start + i];
            written += snprintf(
                reply + written, (size_t)(cap - written),
                "%s[%d,%d,%d,%d]", i ? "," : "", vertex[0], vertex[1],
                vertex[2], vertex[3]);
        }
        if (written > 0 && written < cap) {
            (void)snprintf(reply + written, (size_t)(cap - written), "]}");
        }
        return 1;
    } else if (*args) {
        return -1;
    }
    if (!g_weapon_capture_valid || !g_weapon_capture_tracked_valid) {
        (void)snprintf(reply, (size_t)cap,
                       "{\"valid\":false,\"sequence\":%u}",
                       g_weapon_capture_sequence);
        return 1;
    }
    const uint32_t node = g_weapon_capture_node < g_weapon_capture_node_count
                              ? g_weapon_capture_node
                              : 0u;
    if (node != g_weapon_capture_node ||
        !g_weapon_capture_vertex_count) {
        (void)snprintf(reply, (size_t)cap,
                       "{\"valid\":false,\"sequence\":%u}",
                       g_weapon_capture_sequence);
        return 1;
    }
    const uint32_t snapshot_count =
        g_weapon_capture_vertex_count < MOHU_VR_WEAPON_CAPTURE_VERTEX_LIMIT
            ? g_weapon_capture_vertex_count
            : MOHU_VR_WEAPON_CAPTURE_VERTEX_LIMIT;
    memcpy(g_weapon_capture_snapshot_local, g_weapon_capture_local_vertices,
           snapshot_count * sizeof g_weapon_capture_snapshot_local[0]);
    memcpy(g_weapon_capture_snapshot_animated,
           g_weapon_capture_animated_vertices,
           snapshot_count * sizeof g_weapon_capture_snapshot_animated[0]);
    g_weapon_capture_snapshot_count = snapshot_count;
    g_weapon_capture_snapshot_valid = true;
    g_weapon_capture_local_addr = g_weapon_capture_local_addrs[node];
    g_weapon_capture_output_addr = g_weapon_capture_output_addrs[node];
    const PSXModRenderView* view = &g_weapon_capture_eye_view;
    (void)snprintf(
        reply, (size_t)cap,
        "{\"valid\":true,\"sequence\":%u,\"frame\":%u,\"id\":%u,"
        "\"object\":\"%08X\",\"node_table\":\"%08X\","
        "\"output_table\":\"%08X\",\"count\":%u,\"node\":%u,"
        "\"local_addr\":\"%08X\",\"output_addr\":\"%08X\","
        "\"local\":[%d,%d,%d,%d],\"animated\":[%d,%d,%d,%d],"
        "\"native_gte\":[\"%08X\",\"%08X\",\"%08X\",\"%08X\","
        "\"%08X\",\"%08X\",\"%08X\",\"%08X\"],"
        "\"tracked_gte\":[\"%08X\",\"%08X\",\"%08X\",\"%08X\","
        "\"%08X\",\"%08X\",\"%08X\",\"%08X\"],"
        "\"restored\":%d,"
        "\"restored_gte\":[\"%08X\",\"%08X\",\"%08X\",\"%08X\","
        "\"%08X\",\"%08X\",\"%08X\",\"%08X\"],"
        "\"eye_view\":%d,\"eye\":%u,\"h\":133,\"precise\":%u,"
        "\"view_rt12\":[%d,%d,%d,%d,%d,%d,%d,%d,%d],"
        "\"view_t\":[%d,%d,%d],\"view_t_precise\":[%.9f,%.9f,%.9f],"
        "\"view_h_ref\":%u,"
        "\"gte_ofx_q16\":%d,\"gte_ofy_q16\":%d,"
        "\"delta_r\":[%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f],"
        "\"delta_t\":[%.9f,%.9f,%.9f]}",
        g_weapon_capture_sequence, g_weapon_capture_frame,
        g_weapon_profile_last_id, g_weapon_profile_last_object,
        g_weapon_capture_node_table, g_weapon_capture_output_table,
        g_weapon_capture_node_count, node,
        g_weapon_capture_local_addr, g_weapon_capture_output_addr,
        g_weapon_capture_local[node][0], g_weapon_capture_local[node][1],
        g_weapon_capture_local[node][2], g_weapon_capture_local[node][3],
        g_weapon_capture_animated[node][0],
        g_weapon_capture_animated[node][1],
        g_weapon_capture_animated[node][2],
        g_weapon_capture_animated[node][3],
        g_weapon_capture_native_control[0],
        g_weapon_capture_native_control[1],
        g_weapon_capture_native_control[2],
        g_weapon_capture_native_control[3],
        g_weapon_capture_native_control[4],
        g_weapon_capture_native_control[5],
        g_weapon_capture_native_control[6],
        g_weapon_capture_native_control[7],
        g_weapon_capture_tracked_control[0],
        g_weapon_capture_tracked_control[1],
        g_weapon_capture_tracked_control[2],
        g_weapon_capture_tracked_control[3],
        g_weapon_capture_tracked_control[4],
        g_weapon_capture_tracked_control[5],
        g_weapon_capture_tracked_control[6],
        g_weapon_capture_tracked_control[7],
        g_weapon_capture_restored_valid ? 1 : 0,
        g_weapon_capture_restored_control[0],
        g_weapon_capture_restored_control[1],
        g_weapon_capture_restored_control[2],
        g_weapon_capture_restored_control[3],
        g_weapon_capture_restored_control[4],
        g_weapon_capture_restored_control[5],
        g_weapon_capture_restored_control[6],
        g_weapon_capture_restored_control[7],
        g_weapon_capture_eye_view_valid ? 1 : 0,
        g_stereo_current_eye, view->precise,
        view->rotation_q12[0], view->rotation_q12[1],
        view->rotation_q12[2], view->rotation_q12[3],
        view->rotation_q12[4], view->rotation_q12[5],
        view->rotation_q12[6], view->rotation_q12[7],
        view->rotation_q12[8], view->translation[0],
        view->translation[1], view->translation[2],
        view->translation_precise[0], view->translation_precise[1],
        view->translation_precise[2], view->projection_h_ref,
        g_weapon_capture_ofx_q16,
        g_weapon_capture_ofy_q16, g_weapon_delta_rotation[0],
        g_weapon_delta_rotation[1], g_weapon_delta_rotation[2],
        g_weapon_delta_rotation[3], g_weapon_delta_rotation[4],
        g_weapon_delta_rotation[5], g_weapon_delta_rotation[6],
        g_weapon_delta_rotation[7], g_weapon_delta_rotation[8],
        g_weapon_delta_translation[0], g_weapon_delta_translation[1],
        g_weapon_delta_translation[2]);
    return 1;
}

static int vr_stereo_pose_command(const char* args, char* reply, int cap) {
    if (!args || !reply || cap < 1) {
        return 0;
    }
    long yaw = g_stereo_yaw_mdeg;
    long pitch = g_stereo_pitch_mdeg;
    long head[3] = {
        g_stereo_head_milli[0], g_stereo_head_milli[1],
        g_stereo_head_milli[2],
    };
    if (strcmp(args, "reset") == 0) {
        yaw = 0;
        pitch = 0;
        head[0] = head[1] = head[2] = 0;
    } else {
        char* end = NULL;
        unsigned seen = 0u;
        const char* p = args;
        while (*p) {
            while (*p == ' ' || *p == '\t' || *p == ',') {
                ++p;
            }
            if (!*p) break;
            long* target = NULL;
            long limit = MOHU_VR_EYE_HEAD_MILLI_LIMIT;
            if (strncmp(p, "yaw=", 4u) == 0) {
                target = &yaw;
                p += 4;
                limit = MOHU_VR_EYE_ANGLE_LIMIT;
                seen |= 1u;
            } else if (strncmp(p, "pitch=", 6u) == 0) {
                target = &pitch;
                p += 6;
                limit = MOHU_VR_EYE_ANGLE_LIMIT;
                seen |= 2u;
            } else if (strncmp(p, "x=", 2u) == 0) {
                target = &head[0];
                p += 2;
                seen |= 4u;
            } else if (strncmp(p, "y=", 2u) == 0) {
                target = &head[1];
                p += 2;
                seen |= 8u;
            } else if (strncmp(p, "z=", 2u) == 0) {
                target = &head[2];
                p += 2;
                seen |= 16u;
            } else {
                return -1;
            }
            const long value = strtol(p, &end, 0);
            if (end == p || value < -limit || value > limit) {
                return -1;
            }
            *target = value;
            p = end;
        }
        if (!seen) {
            return -1;
        }
    }
    g_stereo_yaw_mdeg = (int32_t)yaw;
    g_stereo_pitch_mdeg = (int32_t)pitch;
    for (unsigned i = 0; i < 3u; ++i) {
        g_stereo_head_milli[i] = (int32_t)head[i];
    }
    (void)snprintf(reply, (size_t)cap,
                   "yaw_mdeg=%d pitch_mdeg=%d head_milli=%d,%d,%d",
                   g_stereo_yaw_mdeg, g_stereo_pitch_mdeg,
                   g_stereo_head_milli[0], g_stereo_head_milli[1],
                   g_stereo_head_milli[2]);
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

static bool vr_mp_snapshot(MohuVrMpState* state) {
    if (!state) return false;
    memset(state, 0, sizeof *state);
    state->index = psx_mod_read_word(MOHU_VR_MP_CONTEXT + 0x2204u);
    state->width = psx_mod_read_word(MOHU_VR_MP_CONTEXT);
    state->height = psx_mod_read_word(MOHU_VR_MP_CONTEXT + 4u);
    state->focal = psx_mod_read_word(MOHU_VR_MP_CONTEXT + 8u);
    state->camera = psx_mod_read_word(MOHU_VR_MP_CAMERA_ROOT);
    state->player = psx_mod_read_word(MOHU_VR_MP_P1_ROOT);
    state->scene = psx_mod_read_word(MOHU_VR_MP_SCENE_ROOT);
    if (!mohu_vr_mp_actor_address(state->camera) ||
        !mohu_vr_mp_actor_address(state->player)) return false;
    state->camera_class = psx_mod_read_word(state->camera + 8u);
    state->player_class = psx_mod_read_word(state->player + 8u);
    state->camera_input = psx_mod_read_word(state->camera + 0x39Cu);
    state->player_input = psx_mod_read_word(state->player + 0x39Cu);
    if (state->camera_input != state->camera + 0x400u) return false;
    const uint32_t handle = psx_mod_read_word(state->camera_input + 12u);
    if (!handle || (handle & 0xffffu) >= 512u) return false;
    state->camera_owner = psx_mod_read_word(0x800A35F8u + (handle & 0xffffu) * 4u);
    return mohu_vr_mp_state_valid(state) != 0;
}

static bool vr_mp_code_valid(void) {
    static const struct { uint32_t address, bytes, hash; } code[] = {
        {MOHU_VR_MP_FRAME, 0x200u, 0x6CDFBB75u},
        {MOHU_VR_MP_SELECT, 0x14Cu, 0x2BE15194u},
        {MOHU_VR_MP_SCENE, 0x180u, 0x04C21F46u},
        {MOHU_VR_MP_SCENE_CALLBACK, 0x290u, 0xA2AAC71Bu},
        {MOHU_VR_MP_SELECTOR, 0x90u, 0x273C8059u},
        {MOHU_VR_MP_SELECTOR_HELPER, 0x428u, 0x77C2060Fu},
        {0x80082598u, 0x244u, 0x8B9E349Du},
    };
    for (unsigned i = 0; i < sizeof code / sizeof code[0]; ++i)
        if (guest_range_fnv1a(code[i].address, code[i].bytes) != code[i].hash)
            return false;
    return psx_mod_read_word(MOHU_VR_MP_FRAME_CALL) == MOHU_VR_MP_FRAME_CALL_WORD;
}

static int vr_mp_frustum_filter(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!cpu) {
        return 0;
    }
    if (g_mp_frustum && !g_mp_frustum_capture) {
        const uint32_t eye = g_stereo_current_eye;
        if (!g_stereo_mp || !g_stereo_active || !g_stereo_render_view ||
            !g_stereo_eye_view_valid || eye > 1u) {
            return 0;
        }
        if (!g_mp_replay_guard_valid) {
            g_mp_frustum_fallbacks[eye]++;
            psx_mod_counter_add(
                eye ? "mohu.vr.mp.frustum.fallback.right"
                    : "mohu.vr.mp.frustum.fallback.left", 1);
            psx_mod_counter_add(
                eye ? "mohu.vr.mp.frustum.replay_guard.right"
                    : "mohu.vr.mp.frustum.replay_guard.left", 1);
            return 0;
        }
        const uint32_t ra = cpu->gpr[31];
        const uint32_t node = cpu->gpr[4];
        if (ra != 0x8006C66Cu && ra != 0x8006C690u) {
            psx_mod_counter_add(
                eye ? "mohu.vr.mp.frustum.skip_caller.right"
                    : "mohu.vr.mp.frustum.skip_caller.left", 1);
            return 0;
        }
        if (!mohu_vr_mp_actor_address(node)) {
            if (!g_mp_frustum_failure_reported) {
                g_mp_frustum_failure_reported = true;
                fprintf(stdout,
                        "mohu-vr-mp: frustum caller fallback eye=%u "
                        "ra=0x%08X node=0x%08X callback=0x%08X\n",
                        eye, ra, node, 0u);
                fflush(stdout);
            }
            g_mp_frustum_fallbacks[eye]++;
            psx_mod_counter_add(
                eye ? "mohu.vr.mp.frustum.fallback.right"
                    : "mohu.vr.mp.frustum.fallback.left", 1);
            psx_mod_counter_add(
                eye ? "mohu.vr.mp.frustum.caller.right"
                    : "mohu.vr.mp.frustum.caller.left", 1);
            return 0;
        }
        if (psx_mod_read_word(node + MOHU_VR_MP_NODE_CALLBACK) !=
            MOHU_VR_MP_SCENE_CALLBACK) {
            psx_mod_counter_add(
                eye ? "mohu.vr.mp.frustum.skip_node.right"
                    : "mohu.vr.mp.frustum.skip_node.left", 1);
            return 0;
        }
        const uint32_t width = psx_mod_read_word(0x800A2D10u);
        const uint32_t height = psx_mod_read_word(0x800A2D14u);
        if (!mohu_vr_mp_view_valid(
                &g_stereo_eye_view, (int)width, (int)height)) {
            g_mp_frustum_fallbacks[eye]++;
            psx_mod_counter_add(
                eye ? "mohu.vr.mp.frustum.fallback.right"
                    : "mohu.vr.mp.frustum.fallback.left", 1);
            psx_mod_counter_add(
                eye ? "mohu.vr.mp.frustum.view.right"
                    : "mohu.vr.mp.frustum.view.left", 1);
            return 0;
        }
        const double cx = (int32_t)cpu->gte_ctrl[24] / 65536.0;
        const double cy = (int32_t)cpu->gte_ctrl[25] / 65536.0;
        if (!isfinite(cx) || !isfinite(cy) || cx <= 0.0 ||
            cx >= (double)width || cy <= 0.0 || cy >= (double)height) {
            g_mp_frustum_fallbacks[eye]++;
            psx_mod_counter_add(
                eye ? "mohu.vr.mp.frustum.fallback.right"
                    : "mohu.vr.mp.frustum.fallback.left", 1);
            psx_mod_counter_add(
                eye ? "mohu.vr.mp.frustum.projection.right"
                    : "mohu.vr.mp.frustum.projection.left", 1);
            return 0;
        }
        double matrix[9];
        double tr[3];
        for (unsigned i = 0; i < 9u; ++i) {
            matrix[i] = (int16_t)(cpu->gte_ctrl[i / 2u] >>
                                  ((i & 1u) * 16u)) /
                        4096.0;
        }
        for (unsigned i = 0; i < 3u; ++i) {
            tr[i] = (int32_t)cpu->gte_ctrl[5u + i];
        }
        int16_t center[3];
        for (unsigned axis = 0; axis < 3u; ++axis) {
            center[axis] = (int16_t)psx_mod_read_half(
                node + MOHU_VR_MP_NODE_CENTER + axis * 2u);
        }
        const int16_t radius =
            (int16_t)psx_mod_read_half(node + MOHU_VR_MP_NODE_RADIUS);
        const int visible = mohu_vr_mp_box_visible(
            center, radius, matrix, tr, &g_stereo_eye_view, cx, cy,
            (int)width, (int)height);
        if (visible < 0) {
            g_mp_frustum_fallbacks[eye]++;
            psx_mod_counter_add(
                eye ? "mohu.vr.mp.frustum.fallback.right"
                    : "mohu.vr.mp.frustum.fallback.left", 1);
            psx_mod_counter_add(
                eye ? "mohu.vr.mp.frustum.bounds.right"
                    : "mohu.vr.mp.frustum.bounds.left", 1);
            return 0;
        }
        cpu->gpr[2] = visible ? 1u : 0u;
        g_mp_frustum_overrides[eye]++;
        psx_mod_counter_add(
            eye ? "mohu.vr.mp.frustum.override.right"
                : "mohu.vr.mp.frustum.override.left", 1);
        return 1;
    }
    if (!g_mp_frustum_capture || !cpu ||
        g_mp_frustum_capture_count >=
            sizeof g_mp_frustum_samples / sizeof g_mp_frustum_samples[0]) {
        return 0;
    }
    const uint32_t ra = cpu->gpr[31];
    if (ra != 0x8006C66Cu && ra != 0x8006C690u) {
        return 0;
    }
    const uint32_t eye = g_stereo_current_eye;
    if (eye > 1u) {
        return 0;
    }
    const uint32_t node = cpu->gpr[4];
    if (!mohu_vr_mp_actor_address(node) ||
        psx_mod_read_word(node + MOHU_VR_MP_NODE_CALLBACK) !=
            MOHU_VR_MP_SCENE_CALLBACK) {
        return 0;
    }
    for (uint32_t i = 0; i < g_mp_frustum_capture_count; ++i) {
        if (g_mp_frustum_samples[i].node == node &&
            g_mp_frustum_samples[i].eye == eye) {
            return 0;
        }
    }
    MohuVrMpState state;
    if (!vr_mp_snapshot(&state)) {
        return 0;
    }
    const uint32_t camera = psx_mod_read_word(MOHU_VR_MP_CAMERA_VIEW_ROOT);
    if (!mohu_vr_mp_actor_address(camera)) {
        return 0;
    }
    const uint32_t input = psx_mod_read_word(camera + 0x39Cu);
    if (input != camera + 0x400u) {
        return 0;
    }
    const uint32_t view =
        psx_mod_read_word(input + MOHU_VR_MP_CAMERA_VIEW_POINTER);
    if (!mohu_vr_mp_actor_address(view)) {
        return 0;
    }

    MohuVrMpFrustumSample* sample =
        &g_mp_frustum_samples[g_mp_frustum_capture_count];
    memset(sample, 0, sizeof *sample);
    sample->node = node;
    sample->return_address = ra;
    sample->eye = eye;
    for (unsigned axis = 0; axis < 3u; ++axis) {
        sample->center[axis] = (int16_t)psx_mod_read_half(
            node + MOHU_VR_MP_NODE_CENTER + axis * 2u);
    }
    sample->radius =
        (int16_t)psx_mod_read_half(node + MOHU_VR_MP_NODE_RADIUS);
    for (unsigned i = 0; i < 8u; ++i) {
        sample->control[i] = cpu->gte_ctrl[i];
    }
    sample->screen_width = psx_mod_read_word(0x800A2D10u);
    sample->screen_height = psx_mod_read_word(0x800A2D14u);
    sample->projection_h = (uint16_t)cpu->gte_ctrl[26];
    sample->ofx_q16 = cpu->gte_ctrl[24];
    sample->ofy_q16 = cpu->gte_ctrl[25];
    sample->camera = camera;
    sample->input = input;
    sample->view = view;
    g_mp_frustum_capture_last = g_mp_frustum_capture_count++;
    return 0;
}

static void vr_mp_frustum_result_capture(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!g_mp_frustum_capture || !cpu || !g_mp_frustum_capture_count) {
        return;
    }
    MohuVrMpFrustumSample* sample =
        &g_mp_frustum_samples[g_mp_frustum_capture_last];
    if (!sample->result_valid) {
        sample->native_result = cpu->gpr[2] ? 1u : 0u;
        sample->result_valid = true;
        if (g_stereo_eye_view_valid &&
            mohu_vr_mp_view_valid(
                &g_stereo_eye_view, (int)sample->screen_width,
                (int)sample->screen_height)) {
            double matrix[9];
            double tr[3];
            for (unsigned i = 0; i < 9u; ++i) {
                matrix[i] = (int16_t)(sample->control[i / 2u] >>
                                      ((i & 1u) * 16u)) /
                            4096.0;
            }
            for (unsigned i = 0; i < 3u; ++i) {
                tr[i] = (int32_t)sample->control[5u + i];
            }
            const double cx =
                (int32_t)cpu->gte_ctrl[24] / 65536.0;
            const double cy =
                (int32_t)cpu->gte_ctrl[25] / 65536.0;
            const int visible = mohu_vr_mp_box_visible(
                sample->center, sample->radius, matrix, tr,
                &g_stereo_eye_view, cx, cy,
                (int)sample->screen_width, (int)sample->screen_height);
            if (visible >= 0) {
                sample->override_result = visible ? 1u : 0u;
                sample->override_valid = true;
            }
        }
    }
}

static int vr_mp_frustum_command(const char* args, char* reply, int cap) {
    if (!args || !reply || cap < 1) {
        return -1;
    }
    unsigned index = 0u;
    if (strcmp(args, "start") == 0) {
        memset(g_mp_frustum_samples, 0, sizeof g_mp_frustum_samples);
        g_mp_frustum_capture_count = 0u;
        g_mp_frustum_capture_last = 0u;
        g_mp_frustum_capture = true;
        (void)snprintf(reply, (size_t)cap, "capture=1");
        return 1;
    }
    if (strcmp(args, "enable") == 0) {
        g_mp_frustum_capture = false;
        g_mp_frustum = true;
        (void)snprintf(reply, (size_t)cap, "capture=0 override=1");
        return 1;
    }
    if (strcmp(args, "disable") == 0) {
        g_mp_frustum_capture = false;
        g_mp_frustum = false;
        (void)snprintf(reply, (size_t)cap, "capture=0 override=0");
        return 1;
    }
    if (strcmp(args, "status") == 0) {
        (void)snprintf(reply, (size_t)cap, "capture=%u override=%u count=%u",
                       g_mp_frustum_capture ? 1u : 0u,
                       g_mp_frustum ? 1u : 0u,
                       g_mp_frustum_capture_count);
        return 1;
    }
    if (strcmp(args, "stop") == 0) {
        g_mp_frustum_capture = false;
        (void)snprintf(reply, (size_t)cap, "capture=0 count=%u",
                       g_mp_frustum_capture_count);
        return 1;
    }
    if (strcmp(args, "count") == 0) {
        (void)snprintf(reply, (size_t)cap, "capture=%u count=%u",
                       g_mp_frustum_capture ? 1u : 0u,
                       g_mp_frustum_capture_count);
        return 1;
    }
    if (sscanf(args, "read=%u", &index) != 1 ||
        index >= g_mp_frustum_capture_count) {
        return -1;
    }
    const MohuVrMpFrustumSample* sample = &g_mp_frustum_samples[index];
    int used = snprintf(
        reply, (size_t)cap,
        "node=%08X ra=%08X eye=%u center=%d,%d,%d radius=%d "
        "control=%08X,%08X,%08X,%08X,%08X,%08X,%08X,%08X "
        "screen=%u,%u projection=%u,%u,%u "
        "camera=%08X input=%08X view=%08X "
        "native_result=%u result_valid=%u "
        "override_result=%u override_valid=%u",
        sample->node, sample->return_address, sample->eye, sample->center[0],
        sample->center[1], sample->center[2], sample->radius,
        sample->control[0], sample->control[1], sample->control[2],
        sample->control[3], sample->control[4], sample->control[5],
        sample->control[6], sample->control[7], sample->screen_width,
        sample->screen_height, sample->projection_h, sample->ofx_q16,
        sample->ofy_q16, sample->camera, sample->input, sample->view,
        sample->native_result, sample->result_valid ? 1u : 0u,
        sample->override_result, sample->override_valid ? 1u : 0u);
    if (used < 0 || used >= cap) {
        return -1;
    }
    return 1;
}

/* Read-only native-shot instrumentation. Kept separate from the eye-only laser
 * cache: the canonical matrix must come from natural P1 level drawing. */
typedef struct {
    MohuVrShotGuard guard;
    uint32_t control[8], basis[8];
    int32_t position[3], angles[3];
    int eligible;
    int aimed;
    uint32_t weapon_control[8];
    int32_t aimed_position[3], aimed_angles[3];
} MohuVrShotSample;
static bool g_shot_capture;
static unsigned g_shot_count, g_shot_overflow;
static MohuVrShotSample g_shot_samples[64];
static uint32_t g_shot_camera[8], g_shot_camera_owner;
static int32_t g_shot_native_camera_position[3];
static uint64_t g_shot_camera_cycle;
static bool g_shot_camera_valid;
static bool g_shot_capture_p1_only;

static void vr_shot_camera_entry(CPUState* cpu, uint32_t address) {
    (void)address;
    if ((!g_shot_capture && !g_p38_aim) || !cpu || g_stereo_active) return;
    MohuVrMpState state;
    const uint32_t owner = psx_mod_read_word(MOHU_VR_MP_P1_ROOT);
    if (psx_mod_read_word(MOHU_VR_MP_CURRENT_PLAYER) != owner ||
        !vr_mp_snapshot(&state) || !vr_mp_code_valid()) return;
    uint32_t control[8];
    for (unsigned i=0; i<8; ++i)
        control[i] = psx_mod_read_word(MOHU_VR_SHOT_CAMERA_MATRIX + 4u*i);
    double rt[9], inverse[9];
    for (unsigned i = 0; i < 9u; ++i)
        rt[i] = (int16_t)(control[i / 2u] >> ((i & 1u) * 16u)) / 4096.0;
    g_shot_camera_valid = mohu_vr_laser_inverse(rt, inverse) != 0;
    if (!g_shot_camera_valid) return;
    /* Entry GTE state can belong to the previous scene object. The guarded
     * native visibility helper explicitly loads this canonical global RT/TR. */
    memcpy(g_shot_camera, control, sizeof g_shot_camera);
    g_shot_camera_owner = owner;
    for (unsigned i=0; i<3; ++i)
        g_shot_native_camera_position[i] = (int32_t)psx_mod_read_word(state.camera+0x220u+4u*i);
    g_shot_camera_cycle = psx_cycle_count;
    psx_mod_counter_add("mohu.vr.shot.camera.native", 1);
}

static bool vr_p38_model_valid(uint32_t owner) {
    const MohuVrWeaponProfile* p = mohu_vr_weapon_profile_find(0);
    const uint32_t object = psx_mod_read_word(owner + 0x114u);
    if (object != owner + 0xDF0u || psx_mod_read_word(object+0x70u) != p->mesh_magic ||
        psx_mod_read_half(object+0xB6u) != p->face_count) return false;
    const uint32_t header = psx_mod_read_word(object+0x80u);
    if (!mohu_vr_mp_actor_address(header) || psx_mod_read_word(header+4u) != p->node_count)
        return false;
    const uint32_t nodes = psx_mod_read_word(header);
    if (!mohu_vr_mp_actor_address(nodes)) return false;
    uint32_t hash = 2166136261u;
    for (unsigned i=0; i<p->node_count; ++i) {
        const uint32_t count = psx_mod_read_word(nodes+i*8u+4u);
        const uint32_t data = psx_mod_read_word(nodes+i*8u);
        if (count != p->vertices[i] ||
            (count && (data < 0x80000000u || data > 0x80200000u-count*8u))) return false;
        for (unsigned k=0; k<4; ++k)
            hash = (hash ^ ((count >> (k*8u)) & 255u)) * 16777619u;
        for (unsigned k=0; k<count*8u; ++k)
            hash = (hash ^ psx_mod_read_byte(data+k)) * 16777619u;
    }
    const uint32_t faces = psx_mod_read_word(object+0xB8u);
    return hash == p->geometry_fnv32 && faces >= 0x80000000u &&
        faces <= 0x80200000u - MOHU_VR_P38_TRIANGLE_STREAM_BYTES &&
        guest_range_fnv1a(faces,MOHU_VR_P38_TRIANGLE_STREAM_BYTES) == MOHU_VR_P38_TRIANGLE_STREAM_FNV;
}

static void vr_shot_basis_entry(CPUState* cpu, uint32_t address) {
    (void)address;
    if ((!g_shot_capture && !g_p38_aim) || !cpu) return;
    if (g_stereo_active) {
        psx_mod_counter_add("mohu.vr.shot.replay_blocked", 1);
        return;
    }
    /*
     * W5.3 family discovery records every actor-valid basis candidate while
     * capture is enabled. The override path remains restricted to the exact
     * measured P38 caller below; unknown families can only be sampled.
     */
    if ((!g_shot_capture && cpu->gpr[31] != MOHU_VR_SHOT_BASIS_RA) ||
        !mohu_vr_mp_actor_address(cpu->gpr[4]) ||
        !mohu_vr_mp_actor_address(cpu->gpr[18])) return;
    if (g_shot_capture_p1_only &&
        cpu->gpr[18] != psx_mod_read_word(MOHU_VR_MP_P1_ROOT)) return;
    if (cpu->gpr[4] != cpu->gpr[16]) return;
    if (g_shot_capture && g_shot_count >= sizeof g_shot_samples / sizeof g_shot_samples[0]) {
        ++g_shot_overflow;
    }
    MohuVrShotSample temporary;
    MohuVrShotSample* s = &temporary;
    memset(s, 0, sizeof *s);
    s->guard.p1 = psx_mod_read_word(MOHU_VR_MP_P1_ROOT);
    s->guard.owner = cpu->gpr[18];
    s->guard.owner_class = psx_mod_read_word(s->guard.owner + 8u);
    s->guard.owner_input = psx_mod_read_word(s->guard.owner + 0x39Cu);
    s->guard.weapon_id = s->guard.owner_input == s->guard.owner + 0x400u
        ? psx_mod_read_byte(s->guard.owner_input + 93u) : UINT32_MAX;
    s->guard.shot = cpu->gpr[16];
    s->guard.argument = cpu->gpr[4];
    s->guard.type = psx_mod_read_word(s->guard.argument + 8u);
    s->guard.caller = cpu->gpr[31];
    s->guard.camera_owner = g_shot_camera_owner;
    s->guard.cycle = psx_cycle_count;
    s->guard.camera_cycle = g_shot_camera_cycle;
    s->guard.camera_valid = g_shot_camera_valid;
    MohuVrMpInputState mp;
    s->guard.multiplayer = vr_mp_input_snapshot(&mp);
    s->guard.code_valid =
        guest_range_fnv1a(MOHU_VR_SHOT_CONSTRUCTOR,
            MOHU_VR_SHOT_CONSTRUCTOR_SIZE) == MOHU_VR_SHOT_CONSTRUCTOR_FNV &&
        guest_range_fnv1a(MOHU_VR_SHOT_BASIS,
            MOHU_VR_SHOT_BASIS_SIZE) == MOHU_VR_SHOT_BASIS_FNV &&
        psx_mod_read_word(MOHU_VR_SHOT_BASIS_CALL) == MOHU_VR_SHOT_BASIS_CALL_WORD &&
        psx_mod_read_word(MOHU_VR_SHOT_BASIS_CALL + 4u) == 0xAE200048u;
    s->eligible = mohu_vr_shot_guard(&s->guard);
    memcpy(s->control, g_shot_camera, sizeof s->control);
    for (unsigned i = 0; i < 3u; ++i) {
        s->position[i] = (int32_t)psx_mod_read_word(s->guard.argument + 0x220u + 4u*i);
        s->angles[i] = (int32_t)psx_mod_read_word(s->guard.argument + 0x23Cu + 4u*i);
    }
    if (g_p38_aim && s->eligible && vr_p38_model_valid(s->guard.owner)) {
        PSXModOpenXRHands hands = {0};
        hands.struct_size = sizeof hands;
        double r[9], t[3], camera[9], inverse[9], tr[3];
        for (unsigned i=0; i<9; ++i)
            camera[i] = (int16_t)(s->control[i/2u] >> ((i&1u)*16u)) / 4096.0;
        for (unsigned i=0; i<3; ++i) tr[i] = (int32_t)s->control[5+i];
        const MohuVrWeaponCalibration* c = mohu_vr_weapon_calibration_find(0);
        if (psx_mod_openxr_hands(&hands) && !g_weapon_force_tracking_loss &&
            mohu_vr_weapon_track_delta(&hands,g_openxr_units_per_meter,r,t) &&
            mohu_vr_weapon_calibrated_control(s->weapon_control,r,t,g_openxr_units_per_meter,c) &&
            mohu_vr_laser_inverse(camera,inverse) &&
            mohu_vr_weapon_muzzle_shot(s->weapon_control,c,inverse,tr,
                                      s->aimed_position,s->aimed_angles)) {
            /* Exactly six pose fields, before native basis/history init.
             * Ammo, speed, spread policy, owner, collision and damage stay native. */
            for (unsigned i=0; i<3; ++i) {
                psx_mod_write_word(s->guard.shot+0x220u+4u*i,(uint32_t)s->aimed_position[i]);
                psx_mod_write_word(s->guard.shot+0x23Cu+4u*i,(uint32_t)s->aimed_angles[i]);
            }
            s->aimed = 1;
            psx_mod_counter_add("mohu.vr.shot.p38.aimed", 1);
        } else psx_mod_counter_add("mohu.vr.shot.p38.tracking_fallback", 1);
    }
    if (g_shot_capture && g_shot_count < sizeof g_shot_samples / sizeof g_shot_samples[0])
        g_shot_samples[g_shot_count++] = *s;
    psx_mod_counter_add(s->eligible ? "mohu.vr.shot.p1.eligible"
                                  : "mohu.vr.shot.native.rejected", 1);
}

static int vr_shot_command(const char* args, char* reply, int cap) {
    if (!args || !reply || cap < 1) return -1;
    if (!strcmp(args, "render")) {
        (void)snprintf(reply,(size_t)cap,
            "{\"calibrated\":%d,\"aim\":%d,\"masked_arm_vertices\":[%u,%u],\"visible_gun_vertices\":[%u,%u]}",
            g_p38_calibrated,g_p38_aim,g_p38_masked_vertices[0],g_p38_masked_vertices[1],
            g_p38_gun_vertices[0],g_p38_gun_vertices[1]);
        return 1;
    }
    if (!strcmp(args, "camera")) {
        (void)snprintf(reply,(size_t)cap,
            "{\"valid\":%d,\"owner\":%u,\"cycle\":%llu,\"control\":[%u,%u,%u,%u,%u,%u,%u,%u],"
            "\"native_position\":[%d,%d,%d]}",
            g_shot_camera_valid,g_shot_camera_owner,(unsigned long long)g_shot_camera_cycle,
            g_shot_camera[0],g_shot_camera[1],g_shot_camera[2],g_shot_camera[3],
            g_shot_camera[4],g_shot_camera[5],g_shot_camera[6],g_shot_camera[7],
            g_shot_native_camera_position[0],g_shot_native_camera_position[1],g_shot_native_camera_position[2]);
        return 1;
    }
    if (!strcmp(args, "start")) {
        g_shot_capture = true;
        g_shot_capture_p1_only = false;
        g_shot_count = g_shot_overflow = 0;
        g_shot_camera_valid = false;
    } else if (!strcmp(args, "start-p1")) {
        g_shot_capture = true;
        g_shot_capture_p1_only = true;
        g_shot_count = g_shot_overflow = 0;
        g_shot_camera_valid = false;
    } else if (!strcmp(args, "stop")) {
        g_shot_capture = false;
        g_shot_capture_p1_only = false;
        g_shot_camera_valid = false;
    } else if (strcmp(args, "status")) {
        unsigned index;
        if (sscanf(args, "read=%u", &index) != 1 || index >= g_shot_count) return -1;
        const MohuVrShotSample* s = &g_shot_samples[index];
        const MohuVrShotGuard* q = &s->guard;
        const int used = snprintf(reply, (size_t)cap,
            "{\"shot\":%u,\"owner\":%u,\"p1\":%u,\"type\":%u,\"weapon\":%u,"
            "\"caller\":%u,\"argument\":%u,\"eligible\":%d,\"code_valid\":%d,"
            "\"camera_valid\":%d,\"camera_owner\":%u,\"cycle\":%llu,\"camera_cycle\":%llu,"
            "\"position\":[%d,%d,%d],\"angles\":[%d,%d,%d],\"aimed\":%d,"
            "\"aimed_position\":[%d,%d,%d],\"aimed_angles\":[%d,%d,%d],"
            "\"weapon_control\":[%u,%u,%u,%u,%u,%u,%u,%u],"
            "\"camera\":[%u,%u,%u,%u,%u,%u,%u,%u]}",
            q->shot,q->owner,q->p1,q->type,q->weapon_id,q->caller,q->argument,
            s->eligible,q->code_valid,q->camera_valid,q->camera_owner,
            (unsigned long long)q->cycle,(unsigned long long)q->camera_cycle,
            s->position[0],s->position[1],s->position[2],
            s->angles[0],s->angles[1],s->angles[2],
            s->aimed,s->aimed_position[0],s->aimed_position[1],s->aimed_position[2],
            s->aimed_angles[0],s->aimed_angles[1],s->aimed_angles[2],
            s->weapon_control[0],s->weapon_control[1],s->weapon_control[2],s->weapon_control[3],
            s->weapon_control[4],s->weapon_control[5],s->weapon_control[6],s->weapon_control[7],
            s->control[0],s->control[1],s->control[2],s->control[3],
            s->control[4],s->control[5],s->control[6],s->control[7]);
        return used >= 0 && used < cap ? 1 : -1;
    }
    (void)snprintf(reply, (size_t)cap, "{\"capture\":%d,\"count\":%u,\"overflow\":%u}",
                   g_shot_capture ? 1 : 0, g_shot_count, g_shot_overflow);
    return 1;
}

static void vr_mp_frame_entry(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!g_active || !g_mp_control || !g_stereo_proof || g_stereo_active ||
        !cpu || cpu->gpr[31] != MOHU_VR_MP_FRAME_RA) return;
    MohuVrMpState state;
    if (!vr_mp_code_valid() || !vr_mp_snapshot(&state)) {
        psx_mod_counter_add("mohu.vr.mp.guard_fail", 1);
        return;
    }
    if (!g_mp_reported) {
        g_mp_reported = true;
        fprintf(stdout, "mohu-vr-mp: native frame=0x%08X ra=0x%08X "
                        "camera=0x%08X player=0x%08X list=0x%08X index=%u\n",
                MOHU_VR_MP_FRAME, cpu->gpr[31], state.camera, state.player,
                state.scene, state.index);
        fflush(stdout);
    }
    g_stereo_mp = true;
    run_stereo_proof(cpu);
    g_stereo_mp = false;
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
    return psx_mod_read_word((g_stereo_mp ? MOHU_VR_MP_CONTEXT :
                              MOHU_VR_FRAME_CONTEXT_ADDR) + 0x2218u);
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
    const uint32_t context = g_stereo_mp ? MOHU_VR_MP_CONTEXT : MOHU_VR_FRAME_CONTEXT_ADDR;
    uint32_t index = psx_mod_read_word(context + 0x2204u);
    if (!put_draw_env || index > 1u || !ensure_binding_verified(put_draw_env)) {
        return false;
    }
    uint32_t env = context + 16u + 184u * index;
    if (g_stereo_mp) {
        psx_mod_write_half(env + 2u, 0u);
        psx_mod_write_half(env + 6u, 120u);
        psx_mod_write_half(env + 10u, 0u);
    }
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
    psx_mod_counter_add(
        enabled ? "mohu.vr.native_surface.resume"
                : "mohu.vr.native_surface.suspend",
        1);
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
    g_weapon_viewmodel_pending = false;
    g_weapon_viewmodel_applied = false;
    g_weapon_viewmodel_view = false;
    g_mp_weapon_draws[eye] = 0u;
    g_stereo_current_eye = eye;
    g_stereo_base_valid = false;
    g_stereo_eye_view_valid = false;
    g_mp_replay_guard_valid = false;
    g_laser_level_valid = false;
    g_laser_level_root = 0u;

    uint32_t ra = cpu->gpr[31];
    if (g_stereo_mp) {
        /* The natural entry may retain P2's last weapon H/centre. The
         * reconstructed world view uses the measured P1 context instead. */
        cpu->gte_ctrl[26] = 400u;
        cpu->gte_ctrl[24] = 256u << 16;
        cpu->gte_ctrl[25] = 60u << 16;
    }
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

    if (g_stereo_mp) {
        MohuVrMpState state;
        const MohuVrEngineBinding* draw = mohu_vr_engine_map_find(MOHU_VR_ROLE_DRAW_OTAG);
        if (!vr_mp_code_valid() || !vr_mp_snapshot(&state) || !draw ||
            !ensure_binding_verified(draw)) return 0;
        stereo_guest_call(cpu, MOHU_VR_MP_SELECT, state.camera, 0u, 0u, ra);
        if (psx_mod_read_word(MOHU_VR_MP_CURRENT_PLAYER) != state.player) return 0;
        g_mp_replay_guard_valid = true;
        cpu->gte_ctrl[24] = 256u << 16;
        cpu->gte_ctrl[25] = 60u << 16;
        stereo_guest_call(cpu, MOHU_VR_MP_SCENE, MOHU_VR_MP_CONTEXT, state.scene, 0u, ra);
        if (g_weapon_viewmodel_pending || g_weapon_viewmodel_applied ||
            g_weapon_viewmodel_view || !g_mp_weapon_draws[eye]) return 0;
        ot = stereo_ot_base();
        if (ot < 0x80000000u || ot > 0x801FF800u || (ot & 3u)) return 0;
        stereo_guest_call(cpu, draw->target_address, ot + 511u * 4u, 0u, 0u, ra);
        g_stereo_guest_submits++;
        psx_mod_counter_add(eye ? "mohu.vr.mp.draw.right" : "mohu.vr.mp.draw.left", 1);
        return 1;
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
    if (g_weapon_viewmodel_pending || g_weapon_viewmodel_applied ||
        g_weapon_viewmodel_view) {
        psx_mod_counter_add("mohu.vr.weapon.unclosed_scope", 1);
        return 0;
    }
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
    uint32_t index = psx_mod_read_word((g_stereo_mp ? MOHU_VR_MP_CONTEXT :
                                             MOHU_VR_FRAME_CONTEXT_ADDR) + 0x2204u);
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
    frame.h = g_stereo_mp ? 120u : 240u;
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
    /* The transaction restored guest CPU state even on an aborted eye.
     * Discard host scope markers so canonical execution cannot inherit them. */
    g_weapon_viewmodel_pending = false;
    g_weapon_viewmodel_applied = false;
    g_weapon_viewmodel_view = false;
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

static void vr_weapon_identity_rotation(double rotation[9]) {
    memset(rotation, 0, 9u * sizeof rotation[0]);
    rotation[0] = 1.0;
    rotation[4] = 1.0;
    rotation[8] = 1.0;
}

static bool vr_weapon_calibrated_active(void) {
    return g_p38_calibrated || g_weapon_calibrated_all;
}

static bool vr_weapon_prepare_delta(void) {
    vr_weapon_identity_rotation(g_weapon_delta_rotation);
    memset(g_weapon_delta_translation, 0,
           sizeof g_weapon_delta_translation);
    g_weapon_absolute = false;

    if (g_weapon_force_tracking_loss) {
        return false;
    }
    if (g_weapon_flat_probe || g_weapon_synthetic_x || g_weapon_synthetic_yaw_mdeg) {
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
    if (!mohu_vr_weapon_calibration_find(
            (uint8_t)g_weapon_profile_last_id) ||
        (g_weapon_profile_last_id != 0u && !g_weapon_calibrated_all)) {
        return false;
    }
    memcpy(g_weapon_delta_rotation, rotation, sizeof rotation);
    memcpy(g_weapon_delta_translation, translation, sizeof translation);
    g_weapon_absolute = true;
    return true;
}

static bool vr_weapon_scope(uint32_t* eye_out) {
    if ((!g_weapon_pose && !(g_stereo_mp && g_stereo_render_view)) || !eye_out) {
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

static void vr_weapon_viewmodel_project(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!g_weapon_viewmodel_pending || g_weapon_viewmodel_applied || !cpu ||
        cpu->gpr[29] != g_weapon_viewmodel_sp - 0x48u ||
        cpu->gpr[20] != g_weapon_profile_last_object) {
        return;
    }
    if (g_stereo_mp) {
        if (g_stereo_render_view) {
            PSXModRenderView weapon_view = g_stereo_eye_view;
            /* Preserve native weapon H / world H until grip/scale calibration
             * replaces the authored camera-relative weapon placement. */
            weapon_view.projection_h_ref =
                vr_weapon_calibrated_active() && g_weapon_absolute &&
                        g_weapon_delta_valid
                    ? 133u
                    : 400u;
            if (!psx_mod_render_view(&weapon_view)) return;
            g_weapon_viewmodel_view = true;
        }
        ++g_mp_weapon_draws[g_stereo_current_eye];
    }
    if (!g_weapon_delta_valid && !g_weapon_gun_only) {
        g_weapon_viewmodel_pending = false;
        return;
    }
    for (unsigned i = 0; i < 8u; ++i) {
        g_weapon_viewmodel_saved_control[i] = cpu->gte_ctrl[i];
    }
    g_weapon_capture_valid = false;
    g_weapon_capture_tracked_valid = false;
    g_weapon_capture_restored_valid = false;
    g_weapon_capture_eye_view_valid = false;
    g_weapon_capture_frame = g_stereo_attempts;
    memcpy(g_weapon_capture_native_control, g_weapon_viewmodel_saved_control,
           sizeof g_weapon_capture_native_control);
    g_weapon_capture_ofx_q16 = (int32_t)cpu->gte_ctrl[24];
    g_weapon_capture_ofy_q16 = (int32_t)cpu->gte_ctrl[25];
    g_weapon_capture_bounds_valid = false;
    g_weapon_capture_vertex_count = 0u;
    g_weapon_capture_frame_vertex_count = 0u;
    g_weapon_capture_frame_valid = false;
    memset(g_weapon_capture_frame_local, 0,
           sizeof g_weapon_capture_frame_local);
    memset(g_weapon_capture_frame_animated, 0,
           sizeof g_weapon_capture_frame_animated);
    memset(g_weapon_capture_frame_nodes, 0,
           sizeof g_weapon_capture_frame_nodes);
    memset(g_weapon_capture_frame_indices, 0,
           sizeof g_weapon_capture_frame_indices);
    memset(g_weapon_capture_frame_node_counts, 0,
           sizeof g_weapon_capture_frame_node_counts);
    g_weapon_gun_only_ready = false;
    const uint32_t output_table = cpu->gpr[19];
    const uint32_t object = g_weapon_profile_last_object;
    const uint32_t node_header = psx_mod_read_word(object + 0x80u);
    const uint32_t node_count = psx_mod_read_word(node_header + 4u);
    if (node_header >= 0x80000000u && node_header <= 0x801FFFF8u &&
        output_table >= 0x80000000u && output_table <= 0x801FFFF8u &&
        node_count && node_count <= MOHU_VR_WEAPON_FP_MAX_NODES) {
        const uint32_t node_table = psx_mod_read_word(node_header);
        bool complete = node_table >= 0x80000000u &&
                        node_table <= 0x80200000u - node_count * 8u &&
                        output_table >= 0x80000000u &&
                        output_table <= 0x80200000u - node_count * 4u;
        memset(g_weapon_capture_local, 0, sizeof g_weapon_capture_local);
        memset(g_weapon_capture_animated, 0,
               sizeof g_weapon_capture_animated);
        memset(g_weapon_capture_local_vertices, 0,
               sizeof g_weapon_capture_local_vertices);
        memset(g_weapon_capture_animated_vertices, 0,
               sizeof g_weapon_capture_animated_vertices);
        memset(g_weapon_capture_local_addrs, 0,
               sizeof g_weapon_capture_local_addrs);
        memset(g_weapon_capture_output_addrs, 0,
               sizeof g_weapon_capture_output_addrs);
        for (uint32_t node = 0; complete && node < node_count; ++node) {
            const uint32_t local_addr =
                psx_mod_read_word(node_table + node * 8u);
            const uint32_t local_count =
                psx_mod_read_word(node_table + node * 8u + 4u);
            const uint32_t output_addr =
                psx_mod_read_word(output_table + node * 4u);
            if (local_count) {
                complete = complete &&
                           local_addr >= 0x80000000u &&
                           local_addr <= 0x80200000u - local_count * 8u &&
                           output_addr >= 0x80000000u &&
                           output_addr <= 0x801FFFF8u;
            }
            if (complete && local_count) {
                g_weapon_capture_local_addrs[node] = local_addr;
                g_weapon_capture_output_addrs[node] = output_addr;
                if (local_count > MOHU_VR_WEAPON_FRAME_VERTEX_LIMIT -
                        g_weapon_capture_frame_vertex_count) {
                    complete = false;
                    break;
                }
                for (unsigned i = 0; i < 4u; ++i) {
                    g_weapon_capture_local[node][i] =
                        (int16_t)psx_mod_read_half(local_addr + i * 2u);
                    g_weapon_capture_animated[node][i] =
                        (int16_t)psx_mod_read_half(output_addr + i * 2u);
                }
                if (node == g_weapon_capture_node) {
                    const uint32_t stored =
                        local_count < MOHU_VR_WEAPON_CAPTURE_VERTEX_LIMIT
                            ? local_count
                            : MOHU_VR_WEAPON_CAPTURE_VERTEX_LIMIT;
                    for (uint32_t vertex = 0; vertex < stored; ++vertex) {
                        for (unsigned i = 0; i < 4u; ++i) {
                            g_weapon_capture_local_vertices[vertex][i] =
                                (int16_t)psx_mod_read_half(
                                    local_addr + vertex * 8u + i * 2u);
                            g_weapon_capture_animated_vertices[vertex][i] =
                                (int16_t)psx_mod_read_half(
                                    output_addr + vertex * 8u + i * 2u);
                        }
                    }
                    g_weapon_capture_vertex_count = stored;
                }
                g_weapon_capture_frame_node_counts[node] =
                    (uint16_t)local_count;
                for (uint32_t vertex = 0; vertex < local_count; ++vertex) {
                    const uint32_t stored =
                        g_weapon_capture_frame_vertex_count++;
                    g_weapon_capture_frame_nodes[stored] = (uint8_t)node;
                    g_weapon_capture_frame_indices[stored] =
                        (uint16_t)vertex;
                    for (unsigned i = 0; i < 4u; ++i) {
                        g_weapon_capture_frame_local[stored][i] =
                            (int16_t)psx_mod_read_half(
                                local_addr + vertex * 8u + i * 2u);
                        g_weapon_capture_frame_animated[stored][i] =
                            (int16_t)psx_mod_read_half(
                                output_addr + vertex * 8u + i * 2u);
                    }
                }
            }
        }
        if (complete) {
            g_weapon_capture_node_table = node_table;
            g_weapon_capture_output_table = output_table;
            g_weapon_capture_node_count = node_count;
            memcpy(g_weapon_capture_frame_native_control,
                   g_weapon_capture_native_control,
                   sizeof g_weapon_capture_frame_native_control);
            g_weapon_capture_frame_valid = true;
            if (g_weapon_capture_frame_requested) {
                memcpy(g_weapon_capture_frame_snapshot_local,
                       g_weapon_capture_frame_local,
                       sizeof g_weapon_capture_frame_snapshot_local);
                memcpy(g_weapon_capture_frame_snapshot_animated,
                       g_weapon_capture_frame_animated,
                       sizeof g_weapon_capture_frame_snapshot_animated);
                memcpy(g_weapon_capture_frame_snapshot_nodes,
                       g_weapon_capture_frame_nodes,
                       sizeof g_weapon_capture_frame_snapshot_nodes);
                memcpy(g_weapon_capture_frame_snapshot_indices,
                       g_weapon_capture_frame_indices,
                       sizeof g_weapon_capture_frame_snapshot_indices);
                memcpy(g_weapon_capture_frame_snapshot_node_counts,
                       g_weapon_capture_frame_node_counts,
                       sizeof g_weapon_capture_frame_snapshot_node_counts);
                memcpy(g_weapon_capture_frame_snapshot_native_control,
                       g_weapon_capture_frame_native_control,
                       sizeof
                           g_weapon_capture_frame_snapshot_native_control);
                g_weapon_capture_frame_snapshot_vertex_count =
                    g_weapon_capture_frame_vertex_count;
                g_weapon_capture_frame_snapshot_sequence =
                    g_weapon_capture_sequence;
                g_weapon_capture_frame_snapshot_frame =
                    g_weapon_capture_frame;
                g_weapon_capture_frame_snapshot_id =
                    g_weapon_profile_last_id;
                g_weapon_capture_frame_snapshot_node_count =
                    g_weapon_capture_node_count;
                g_weapon_capture_frame_snapshot_valid = true;
                g_weapon_capture_frame_requested = false;
            }
            g_weapon_capture_eye_view_valid = g_stereo_eye_view_valid;
            if (g_weapon_capture_eye_view_valid) {
                g_weapon_capture_eye_view = g_stereo_eye_view;
                g_weapon_capture_eye_view.projection_h_ref =
                    vr_weapon_calibrated_active() && g_weapon_absolute &&
                            g_weapon_delta_valid
                        ? 133u
                        : 400u;
            }
            double rotation[9];
            for (unsigned i = 0; i < 9u; ++i) {
                rotation[i] =
                    (int16_t)(g_weapon_capture_native_control[i / 2u] >>
                              ((i & 1u) * 16u)) /
                    4096.0;
            }
            bool have_point = false;
            bool have_screen = false;
            for (uint32_t node = 0; node < node_count; ++node) {
                const uint32_t local_count =
                    psx_mod_read_word(node_table + node * 8u + 4u);
                const uint32_t output_addr =
                    g_weapon_capture_output_addrs[node];
                if (!local_count || !output_addr) {
                    continue;
                }
                for (uint32_t vertex = 0; vertex < local_count; ++vertex) {
                    int16_t input[3];
                    for (unsigned axis = 0; axis < 3u; ++axis) {
                        input[axis] = (int16_t)psx_mod_read_half(
                            output_addr + vertex * 8u + axis * 2u);
                    }
                    double camera[3];
                    for (unsigned row = 0; row < 3u; ++row) {
                        camera[row] =
                            (double)(int32_t)g_weapon_capture_native_control[
                                5u + row];
                        for (unsigned col = 0; col < 3u; ++col) {
                            camera[row] += rotation[row * 3u + col] *
                                           input[col];
                        }
                        if (!have_point) {
                            g_weapon_capture_camera_min[row] = camera[row];
                            g_weapon_capture_camera_max[row] = camera[row];
                        } else {
                            g_weapon_capture_camera_min[row] =
                                fmin(g_weapon_capture_camera_min[row],
                                     camera[row]);
                            g_weapon_capture_camera_max[row] =
                                fmax(g_weapon_capture_camera_max[row],
                                     camera[row]);
                        }
                    }
                    have_point = true;
                    if (camera[2] > 1.0) {
                        const double sx =
                            (double)g_weapon_capture_ofx_q16 / 65536.0 +
                            133.0 * camera[0] / camera[2];
                        const double sy =
                            (double)g_weapon_capture_ofy_q16 / 65536.0 +
                            133.0 * camera[1] / camera[2];
                        if (!have_screen) {
                            g_weapon_capture_screen_min[0] = sx;
                            g_weapon_capture_screen_min[1] = sy;
                            g_weapon_capture_screen_max[0] = sx;
                            g_weapon_capture_screen_max[1] = sy;
                        } else {
                            g_weapon_capture_screen_min[0] =
                                fmin(g_weapon_capture_screen_min[0], sx);
                            g_weapon_capture_screen_min[1] =
                                fmin(g_weapon_capture_screen_min[1], sy);
                            g_weapon_capture_screen_max[0] =
                                fmax(g_weapon_capture_screen_max[0], sx);
                            g_weapon_capture_screen_max[1] =
                                fmax(g_weapon_capture_screen_max[1], sy);
                        }
                        have_screen = true;
                    }
                }
            }
            g_weapon_capture_bounds_valid = have_point && have_screen;
            g_weapon_capture_valid = true;
            if (!g_weapon_delta_valid) {
                memcpy(g_weapon_capture_tracked_control,
                       g_weapon_viewmodel_saved_control,
                       sizeof g_weapon_capture_tracked_control);
                g_weapon_capture_tracked_valid = true;
                g_weapon_gun_only_ready =
                    g_weapon_gun_only && g_stereo_active;
                g_weapon_viewmodel_pending = false;
                return;
            }
        }
    }
    const int32_t pivot[3] = {
        (int32_t)g_weapon_viewmodel_saved_control[5],
        (int32_t)g_weapon_viewmodel_saved_control[6],
        (int32_t)g_weapon_viewmodel_saved_control[7],
    };
    uint32_t tracked[8];
    memcpy(tracked, g_weapon_viewmodel_saved_control, sizeof tracked);
    const double absolute_pivot[3] = {98.0, 296.0, 193.0};
    const int composed = g_weapon_absolute
        ? (vr_weapon_calibrated_active()
           ? mohu_vr_weapon_calibrated_control(tracked,g_weapon_delta_rotation,
               g_weapon_delta_translation,g_openxr_units_per_meter,
               mohu_vr_weapon_calibration_find(g_weapon_profile_last_id))
           : mohu_vr_weapon_compose_absolute_gte_control(
              tracked, g_weapon_delta_rotation, g_weapon_delta_translation,
              absolute_pivot))
        : mohu_vr_weapon_compose_gte_control(
              tracked, g_weapon_delta_rotation, pivot,
              g_weapon_delta_translation);
    if (!composed) {
        g_weapon_viewmodel_pending = false;
        g_weapon_gun_only_ready = false;
        psx_mod_counter_add("mohu.vr.weapon.viewmodel_compose_fail", 1);
        return;
    }
    for (unsigned i = 0; i < 8u; ++i) {
        cpu->gte_ctrl[i] = tracked[i];
    }
    memcpy(g_weapon_capture_tracked_control, tracked,
           sizeof g_weapon_capture_tracked_control);
    g_weapon_capture_tracked_valid = true;
    g_weapon_capture_sequence++;
    g_weapon_viewmodel_pending = false;
    g_weapon_viewmodel_applied = true;
    g_weapon_gun_only_ready = g_weapon_gun_only && g_stereo_active;
    const unsigned eye = g_stereo_active ? g_stereo_current_eye : 0u;
    ++g_weapon_profile_hits[eye];
    psx_mod_counter_add("mohu.vr.weapon.viewmodel_apply", 1);
    if (g_stereo_active)
        psx_mod_counter_add(eye ? "mohu.vr.weapon.apply.right" : "mohu.vr.weapon.apply.left", 1);
}

/* The native triangle/strip reader rejects a vertex with negative SZ at +4.
 * Mask only projected non-gun vertices, after projection and before faces.
 * Source geometry, strip topology and animations remain untouched; rollback
 * owns the projected buffer. Profiles preserve complete measured gun islands. */
static void vr_weapon_hide_arms(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!cpu || !g_weapon_gun_only || !g_weapon_gun_only_ready ||
        !g_stereo_active ||
        cpu->gpr[29] != g_weapon_viewmodel_sp - 0x48u) return;
    const MohuVrWeaponProfile* profile =
        mohu_vr_weapon_profile_find((uint8_t)g_weapon_profile_last_id);
    if (!profile) return;
    if (!g_weapon_gun_only_all && profile->id != 0u) return;
    const unsigned eye=g_stereo_current_eye;
    g_p38_masked_vertices[eye] = g_p38_gun_vertices[eye] = 0;
    for (unsigned node=0; node<profile->node_count; ++node) {
        const uint32_t output = g_weapon_capture_output_addrs[node];
        const unsigned count = profile->vertices[node];
        if (!count || output < 0x80000000u || output > 0x80200000u-count*8u) continue;
        for (unsigned i=0; i<count; ++i) {
            if (mohu_vr_weapon_gun_vertex(profile,node,i)) {
                if ((int16_t)psx_mod_read_half(output+i*8u+4u) >= 0)
                    ++g_p38_gun_vertices[eye];
            } else {
                psx_mod_write_half(output+i*8u+4u, 0xFFFFu);
                ++g_p38_masked_vertices[eye];
            }
        }
    }
    psx_mod_counter_add("mohu.vr.weapon.gun_only", 1);
    psx_mod_counter_add(eye ? "mohu.vr.weapon.gun_only.right"
                            : "mohu.vr.weapon.gun_only.left", 1);
}

static void vr_weapon_viewmodel_restore(CPUState* cpu) {
    if (!cpu) {
        return;
    }
    if (g_weapon_viewmodel_applied) {
        for (unsigned i = 0; i < 8u; ++i) {
            cpu->gte_ctrl[i] = g_weapon_viewmodel_saved_control[i];
            g_weapon_capture_restored_control[i] =
                g_weapon_viewmodel_saved_control[i];
        }
        g_weapon_capture_restored_valid = true;
        g_weapon_viewmodel_applied = false;
        psx_mod_counter_add("mohu.vr.weapon.viewmodel_restore", 1);
    }
    if (g_weapon_viewmodel_view) {
        (void)psx_mod_render_view(&g_stereo_eye_view);
        g_weapon_viewmodel_view = false;
        psx_mod_counter_add("mohu.vr.weapon.view_restore", 1);
    }
    g_weapon_gun_only_ready = false;
    g_weapon_viewmodel_pending = false;
}

static void vr_weapon_viewmodel_return(CPUState* cpu, uint32_t address) {
    (void)address;
    if (cpu && cpu->gpr[29] == g_weapon_viewmodel_sp - 0x48u)
        vr_weapon_viewmodel_restore(cpu);
}

/* Multiplayer first-person candidate: actor+114 names input+9F0. The
 * actor+4AC object belongs to the third-person body. Scope the control delta
 * after native animated vertices, before the caller projects those vertices. */
static void vr_weapon_fp_enter(CPUState* cpu, uint32_t address) {
    (void)address;
    uint32_t eye;
    if (!cpu || !vr_weapon_scope(&eye) || g_weapon_viewmodel_pending ||
        g_weapon_viewmodel_applied) return;
    const uint32_t actor = psx_mod_read_word(0x800A3604u);
    if (actor < 0x800B0000u || actor > 0x801FC000u ||
        psx_mod_read_word(actor + 8u) != 1u) return;
    const uint32_t input = psx_mod_read_word(actor + 0x39Cu);
    const uint32_t object = psx_mod_read_word(actor + 0x114u);
    if (input != actor + 0x400u ||
        object != input + MOHU_VR_WEAPON_FP_INPUT_OFFSET ||
        cpu->gpr[4] != object || cpu->gte_ctrl[26] != 133u ||
        cpu->gpr[31] != MOHU_VR_WEAPON_FP_CALLER_RA ||
        psx_mod_read_word(MOHU_VR_WEAPON_FP_CALL_ADDR) !=
            MOHU_VR_WEAPON_FP_CALL_WORD) return;
    const uint8_t id = psx_mod_read_byte(input + 93u);
    const MohuVrWeaponProfile* profile = mohu_vr_weapon_profile_find(id);
    if (!profile ||
        guest_range_fnv1a(MOHU_VR_WEAPON_FP_RENDER_ADDR,
                          MOHU_VR_WEAPON_FP_RENDER_BYTES) !=
            MOHU_VR_WEAPON_FP_RENDER_FNV ||
        guest_range_fnv1a(MOHU_VR_WEAPON_FP_MODEL_ADDR,
                          MOHU_VR_WEAPON_FP_MODEL_BYTES) !=
            MOHU_VR_WEAPON_FP_MODEL_FNV) {
        ++g_weapon_profile_fallbacks[eye];
        psx_mod_counter_add("mohu.vr.weapon.code_guard_fail", 1);
        return;
    }
    const uint32_t header = psx_mod_read_word(object + 0x80u);
    if (header < 0x80000000u || header > 0x801FFFF8u || (header & 3u)) return;
    const uint32_t count = psx_mod_read_word(header + 4u);
    const uint32_t nodes = psx_mod_read_word(header);
    if (count != profile->node_count || count > MOHU_VR_WEAPON_FP_MAX_NODES ||
        nodes < 0x80000000u || nodes > 0x80200000u - count * 8u || (nodes & 3u)) return;
    uint16_t counts[MOHU_VR_WEAPON_FP_MAX_NODES];
    uint32_t geometry_hash = 2166136261u;
    for (unsigned i = 0; i < count; ++i) {
        const uint32_t vertices = psx_mod_read_word(nodes + i * 8u + 4u);
        const uint32_t data = psx_mod_read_word(nodes + i * 8u);
        if (vertices != profile->vertices[i] ||
            (vertices && (data < 0x80000000u ||
                          data > 0x80200000u - vertices * 8u || (data & 3u)))) return;
        counts[i] = (uint16_t)vertices;
        for (unsigned k = 0; k < 4u; ++k)
            geometry_hash = (geometry_hash ^ ((vertices >> (k * 8u)) & 255u)) * 16777619u;
        for (unsigned k = 0; k < vertices * 8u; ++k)
            geometry_hash = (geometry_hash ^ psx_mod_read_byte(data + k)) * 16777619u;
    }
    if (!mohu_vr_weapon_mesh_layout_valid(profile,
            psx_mod_read_word(object + 0x70u),
            psx_mod_read_half(object + 0xB6u), counts, count) ||
        geometry_hash != profile->geometry_fnv32) {
        ++g_weapon_profile_fallbacks[eye];
        psx_mod_counter_add("mohu.vr.weapon.mesh_guard_fail", 1);
        return;
    }
    g_weapon_profile_last_id = id;
    g_weapon_delta_valid = g_weapon_pose && vr_weapon_prepare_delta();
    if (g_p38_calibrated && g_weapon_absolute && !vr_p38_model_valid(actor))
        g_weapon_delta_valid = false;
    if (!g_weapon_delta_valid) {
        ++g_weapon_profile_fallbacks[eye];
        psx_mod_counter_add("mohu.vr.weapon.tracking_fallback", 1);
    }
    g_weapon_profile_last_id = id;
    g_weapon_profile_last_object = object;
    g_weapon_viewmodel_sp = cpu->gpr[29];
    g_weapon_viewmodel_pending = true;
    vr_weapon_trace_entry(cpu, "first-person");
    if (!g_weapon_pose_applied_reported) {
        g_weapon_pose_applied_reported = true;
        fprintf(stdout, "mohu-vr-weapon: first-person object=0x%08X id=%u "
                        "nodes=%u faces=%u ra=0x%08X H=133\n",
                object, id, count, profile->face_count, cpu->gpr[31]);
        fflush(stdout);
    }
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
    const char* mp = getenv("MOHU_VR_MP_CONTROL");
    g_mp_control = mp && *mp == '1';
    const char* mp_frustum_capture =
        getenv("MOHU_VR_MP_FRUSTUM_CAPTURE");
    g_mp_frustum_capture = mp_frustum_capture && *mp_frustum_capture &&
                           *mp_frustum_capture != '0';
    const char* mp_frustum = getenv("MOHU_VR_MP_FRUSTUM");
    g_mp_frustum = mp_frustum && *mp_frustum && *mp_frustum != '0';
    g_mp_frustum_failure_reported = false;
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
    const char* calibrated = getenv("MOHU_VR_P38_CALIBRATED");
    const char* aimed = getenv("MOHU_VR_P38_AIM");
    g_p38_calibrated = g_weapon_pose && calibrated && *calibrated && *calibrated != '0';
    g_p38_aim = g_p38_calibrated && aimed && *aimed && *aimed != '0';
    const char* calibrated_all = getenv("MOHU_VR_WEAPON_CALIBRATED");
    g_weapon_calibrated_all = g_weapon_pose && calibrated_all &&
        *calibrated_all && *calibrated_all != '0';
    const char* gun_only = getenv("MOHU_VR_WEAPON_GUN_ONLY");
    g_weapon_gun_only_all = g_weapon_calibrated_all ||
        (gun_only && *gun_only && *gun_only != '0');
    g_weapon_gun_only = g_p38_calibrated || g_weapon_gun_only_all;
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
    g_weapon_absolute = false;
    g_weapon_viewmodel_pending = false;
    g_weapon_viewmodel_applied = false;
    g_weapon_control_x = g_weapon_synthetic_x;
    g_weapon_control_yaw_mdeg = g_weapon_synthetic_yaw_mdeg;
    g_weapon_control_loss = g_weapon_force_tracking_loss ? 1 : 0;
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
    psx_mod_counter_add("mohu.vr.input.render_blocked", 0);
    psx_mod_counter_add("mohu.vr.input.guard_fallback", 0);
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
            "mp_frustum=%d mp_frustum_capture=%d flat_hud=%d weapon_pose=%d "
            "units_per_meter=%.3f\n",
            mohu_vr_engine_map_count(), hooks + 1u, g_stereo_proof ? 0 : 1,
            g_level_offset_x, g_stereo_proof ? 1 : 0, g_stereo_eye_offset,
            g_stereo_render_view ? 1 : 0, g_stereo_apply_all_spans ? 1 : 0,
            g_replay_frame_driver ? 1 : 0, g_stereo_yaw_mdeg,
            g_stereo_pitch_mdeg, g_stereo_head_milli[0],
            g_stereo_head_milli[1], g_stereo_head_milli[2],
            g_stereo_guest_submit ? 1 : 0, g_head_frustum ? 1 : 0,
            g_openxr ? 1 : 0, g_mp_frustum ? 1 : 0,
            g_mp_frustum_capture ? 1 : 0, g_suppress_flat_hud ? 1 : 0,
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
    (void)psx_mod_register_command(
        "mohu.vr.weapon.space", vr_weapon_space_command);
    (void)psx_mod_register_command(
        "mohu.vr.stereo.pose", vr_stereo_pose_command);
    (void)psx_mod_register_command(
        "mohu.vr.mp.frustum", vr_mp_frustum_command);
    (void)psx_mod_register_command("mohu.vr.shot", vr_shot_command);
    (void)psx_mod_register_function_entry_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, MOHU_VR_MP_SCENE_CALLBACK, vr_shot_camera_entry);
    (void)psx_mod_register_function_entry_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, MOHU_VR_SHOT_BASIS, vr_shot_basis_entry);
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
    (void)psx_mod_register_function_entry_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, MOHU_VR_MP_FRAME, vr_mp_frame_entry);
    (void)psx_mod_register_function_filter_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, MOHU_VR_MP_SELECTOR,
        vr_mp_frustum_filter);
    (void)psx_mod_register_instruction_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, MOHU_VR_MP_SELECTOR_RESULT,
        MOHU_VR_MP_SELECTOR_RESULT_WORD, vr_mp_frustum_result_capture);
    const int weapon_enter = psx_mod_register_instruction_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, MOHU_VR_WEAPON_FP_RENDER_ADDR,
        MOHU_VR_WEAPON_FP_RENDER_WORD, vr_weapon_fp_enter);
    const int weapon_project = psx_mod_register_instruction_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, MOHU_VR_WEAPON_FP_PROJECT_ADDR,
        MOHU_VR_WEAPON_FP_PROJECT_WORD, vr_weapon_viewmodel_project);
    const int weapon_return = psx_mod_register_instruction_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, MOHU_VR_WEAPON_FP_LEAVE_ADDR,
        MOHU_VR_WEAPON_FP_LEAVE_WORD,
        vr_weapon_viewmodel_return);
    (void)psx_mod_register_instruction_plugin(
        MOHU_VR_DIAG_PLUGIN_ID, 0x80089600u, 0x8FB60054u,
        vr_weapon_hide_arms);
    fprintf(stdout,
            "mohu-vr-weapon: viewmodel hooks enter=%d project=%d leave=%d\n",
            weapon_enter, weapon_project, weapon_return);
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
