#include "cpu_state.h"
#include "camera_map.h"
#include "engine_map.h"
#include "mod_plugins.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define MOHU_VR_DIAG_PLUGIN_ID "mohu.vr.diagnostic"
#define MOHU_VR_LEVEL_OFFSET_ENV "MOHU_VR_LEVEL_OFFSET_X"
#define MOHU_VR_LEVEL_OFFSET_LIMIT 2048

static bool g_active;
static bool g_checked[MOHU_VR_ROLE_COUNT];
static bool g_mismatch[MOHU_VR_ROLE_COUNT];
static bool g_reported[MOHU_VR_ROLE_COUNT];
static bool g_camera_reported;
static bool g_level_offset_applied;
static uint32_t g_saved_trx;
static int32_t g_level_offset_x;

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
        binding->status != MOHU_VR_STATUS_LIVE_CONFIRMED) {
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
        if (g_level_offset_x != 0 && !g_level_offset_applied) {
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
        char* end = NULL;
        long parsed = strtol(offset, &end, 0);
        if (end && !*end && parsed >= -MOHU_VR_LEVEL_OFFSET_LIMIT &&
            parsed <= MOHU_VR_LEVEL_OFFSET_LIMIT) {
            g_level_offset_x = (int32_t)parsed;
        } else {
            fprintf(stdout,
                    "mohu-vr-diag: ignored invalid %s=%s "
                    "(range -%d..%d)\n",
                    MOHU_VR_LEVEL_OFFSET_ENV, offset,
                    MOHU_VR_LEVEL_OFFSET_LIMIT,
                    MOHU_VR_LEVEL_OFFSET_LIMIT);
        }
    }
    size_t hooks = 0;
    for (size_t i = 0; i < mohu_vr_engine_map_count(); ++i) {
        const MohuVrEngineBinding* binding = mohu_vr_engine_map_at(i);
        if (binding && binding->container_kind == MOHU_VR_CONTAINER_OVERLAY &&
            binding->status == MOHU_VR_STATUS_LIVE_CONFIRMED) {
            hooks++;
        }
    }
    fprintf(stdout,
            "mohu-vr-diag: active bindings=%zu overlay_hooks=%zu read_only=1 "
            "level_offset_x=%d\n",
            mohu_vr_engine_map_count(), hooks, g_level_offset_x);
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
        if (binding &&
            binding->container_kind == MOHU_VR_CONTAINER_OVERLAY &&
            binding->status == MOHU_VR_STATUS_LIVE_CONFIRMED) {
            (void)psx_mod_register_function_entry_plugin(
                MOHU_VR_DIAG_PLUGIN_ID, binding->target_address,
                vr_diagnostic_entry);
        }
    }
}
