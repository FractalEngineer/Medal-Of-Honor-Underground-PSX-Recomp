#include "cpu_state.h"
#include "engine_map.h"
#include "mod_plugins.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define MOHU_VR_DIAG_PLUGIN_ID "mohu.vr.diagnostic"

static bool g_active;
static bool g_checked[MOHU_VR_ROLE_COUNT];
static bool g_mismatch[MOHU_VR_ROLE_COUNT];
static bool g_reported[MOHU_VR_ROLE_COUNT];

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

static void vr_diagnostic_entry(CPUState* cpu, uint32_t address) {
    if (!g_active) {
        return;
    }

    MohuVrEngineRole role;
    const MohuVrEngineBinding* binding;
    if (!binding_for_address(address, &role, &binding) ||
        binding->status != MOHU_VR_STATUS_LIVE_CONFIRMED) {
        return;
    }

    size_t index = (size_t)role;
    if (index >= MOHU_VR_ROLE_COUNT) {
        return;
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
    if (g_mismatch[index] || g_reported[index]) {
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
    size_t hooks = 0;
    for (size_t i = 0; i < mohu_vr_engine_map_count(); ++i) {
        const MohuVrEngineBinding* binding = mohu_vr_engine_map_at(i);
        if (binding && binding->container_kind == MOHU_VR_CONTAINER_OVERLAY &&
            binding->status == MOHU_VR_STATUS_LIVE_CONFIRMED) {
            hooks++;
        }
    }
    fprintf(stdout,
            "mohu-vr-diag: active bindings=%zu overlay_hooks=%zu read_only=1\n",
            mohu_vr_engine_map_count(), hooks);
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
