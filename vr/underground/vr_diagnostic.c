#include "cpu_state.h"
#include "camera_map.h"
#include "engine_map.h"
#include "mod_plugins.h"

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
#define MOHU_VR_REPLAY_DRIVER_ENV "MOHU_VR_REPLAY_FRAME_DRIVER"
#define MOHU_VR_OT_ONLY_ENV "MOHU_VR_STEREO_OT_ONLY"
#define MOHU_VR_EYE_OFFSET_LIMIT 256

#define MOHU_VR_FRAME_CONTEXT_ADDR 0x800A7138u
#define MOHU_VR_WORLD_POINTER_ADDR 0x800A977Cu
#define MOHU_VR_WORLD_READY_ADDR 0x800A4914u

static bool g_active;
static bool g_checked[MOHU_VR_ROLE_COUNT];
static bool g_mismatch[MOHU_VR_ROLE_COUNT];
static bool g_reported[MOHU_VR_ROLE_COUNT];
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
static uint32_t g_stereo_view_apps[2];
static uint32_t g_stereo_waits_skipped;
static uint32_t g_stereo_ot_words;
static uint32_t g_stereo_attempts;
static uint32_t g_stereo_pairs;
static uint32_t g_stereo_frame_x;
static uint32_t g_stereo_frame_y;
static uint32_t g_stereo_frame_w;
static uint32_t g_stereo_frame_h;
static bool g_stereo_ot_reported;
static bool g_replay_frame_driver;
static bool g_stereo_ot_only;
static bool g_frame_driver_args_valid;
static uint32_t g_frame_driver_args[4];
static bool g_frame_render_args_valid;
static uint32_t g_frame_render_args[4];

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

static uint32_t guest_function_fnv1a(const MohuVrEngineBinding* binding) {
    uint32_t hash = 2166136261u;
    uint32_t words = binding->function_size / 4u;
    for (uint32_t i = 0; i < words; ++i) {
        uint32_t word = psx_mod_read_word(binding->target_address + i * 4u);
        for (unsigned shift = 0; shift < 32; shift += 8) {
            hash ^= (word >> shift) & 0xFFu;
            hash *= 16777619u;
        }
    }
    return hash;
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
    psx_mod_write_word(0x1F801810u, 0x02000000u);
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

static int vr_stereo_eye_draw(CPUState* cpu, void* user, uint32_t eye) {
    (void)user;
    if (!g_stereo_proof || !g_stereo_active || eye > 1u) {
        return 0;
    }
    g_stereo_current_eye = eye;
    g_stereo_base_valid = false;

    uint32_t ra = cpu->gpr[31];
    uint32_t ctx = MOHU_VR_FRAME_CONTEXT_ADDR;
    if (!prepare_stereo_draw_env(cpu, ra)) {
        return 0;
    }
    clear_stereo_rect();

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
    psx_dispatch_call(cpu, 0x80053BB4u, ra);

    ot = stereo_ot_base();
    if (ot < 0x80000000u || ot >= 0x80200000u) {
        return 0;
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
    frame.y = index == 0u ? 240u : 0u;
    frame.w = 512u;
    frame.h = 240u;
    g_stereo_frame_x = frame.x;
    g_stereo_frame_y = frame.y;
    g_stereo_frame_w = frame.w;
    g_stereo_frame_h = frame.h;

    g_stereo_attempts++;
    g_stereo_active = true;
    int rendered = psx_mod_render_stereo(cpu, &frame, vr_stereo_eye_draw, NULL);
    g_stereo_active = false;
    if (rendered) {
        g_stereo_pairs++;
    }
    if (g_stereo_attempts <= 3u || (g_stereo_attempts % 60u) == 0u) {
        fprintf(stdout,
                "mohu-vr-diag: stereo_proof attempt=%u pairs=%u rendered=%d "
                "status=%u y=%u offset=%d level_hits=%u/%u view_apps=%u/%u "
                "ot_words=%u\n",
                g_stereo_attempts, g_stereo_pairs, rendered,
                psx_mod_render_stereo_status(), frame.y, g_stereo_eye_offset,
                g_stereo_level_hits[0], g_stereo_level_hits[1],
                g_stereo_view_apps[0], g_stereo_view_apps[1],
                g_stereo_ot_words);
        fflush(stdout);
        if (g_replay_frame_driver) {
            fprintf(stdout, "mohu-vr-diag: stereo waits_skipped=%u\n",
                    g_stereo_waits_skipped);
            fflush(stdout);
        }
    }
}

static void vr_diagnostic_entry(CPUState* cpu, uint32_t address) {
    if (!g_active) {
        return;
    }

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
        if (g_stereo_active) {
            size_t eye = g_stereo_current_eye < 2u ? g_stereo_current_eye : 0u;
            g_stereo_level_hits[eye]++;
            if (!g_stereo_base_valid) {
                g_stereo_base_trx = cpu->gte_ctrl[5];
                g_stereo_base_valid = true;
            }
            if (g_stereo_eye_offset != 0 &&
                cpu->gte_ctrl[5] == g_stereo_base_trx) {
                int32_t signed_offset =
                    g_stereo_current_eye == 0u ? -g_stereo_eye_offset
                                              : g_stereo_eye_offset;
                cpu->gte_ctrl[5] =
                    (uint32_t)((int32_t)cpu->gte_ctrl[5] + signed_offset);
                g_stereo_view_apps[eye]++;
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

static void vr_diagnostic_activate(void) {
    g_active = true;
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
    const char* ot_only = getenv(MOHU_VR_OT_ONLY_ENV);
    g_stereo_ot_only = ot_only && *ot_only && *ot_only != '0';
    if (g_replay_frame_driver) {
        g_frame_driver_args[0] = MOHU_VR_FRAME_CONTEXT_ADDR;
        g_frame_driver_args_valid = true;
    }
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
            "level_offset_x=%d stereo_proof=%d eye_offset=%d replay_driver=%d\n",
            mohu_vr_engine_map_count(), hooks, g_stereo_proof ? 0 : 1,
            g_level_offset_x, g_stereo_proof ? 1 : 0, g_stereo_eye_offset,
            g_replay_frame_driver ? 1 : 0);
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
    for (size_t i = 0; i < mohu_vr_engine_map_count(); ++i) {
        const MohuVrEngineBinding* binding = mohu_vr_engine_map_at(i);
        if (binding && binding->status >= MOHU_VR_STATUS_STATIC_CONFIRMED) {
            (void)psx_mod_register_function_entry_plugin(
                MOHU_VR_DIAG_PLUGIN_ID, binding->target_address,
                vr_diagnostic_entry);
        }
    }
}
