/* Debug-only research harness. No mouse capture, binding changes or automatic
 * guest writes. A command explicitly arms a bounded owned player-update observation.
 * The runtime's supported instruction hooks execute on the emulation thread. */
#include "mod_plugins.h"
#include "cpu_state.h"
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#ifdef PSX_NO_DEBUG_TOOLS
#error "The native aim research harness must never ship in a release build"
#endif

#define ID "mohu.controls.research"
#define ROOT 0x800AA17Cu
#define UPDATE 0x800892C8u
#define LOOK_END 0x8008F984u
#define ADJUST_END 0x8008F9BCu
#define INTEGRATE 0x80078FBCu
#define BASIS 0x80076C28u
#define CAMERA_UPDATE 0x8004A744u
#define RAY 0x8008D81Cu
#define PREPARE 0x8008AD04u
#define CONSTRUCT 0x8004815Cu
/* Synthetic observations, never guest instruction addresses. */
#define CAMERA_PREPARED 0xFF000018u
#define PREPARE_SKIPPED 0xFF00001Cu
#define CAPACITY 128
#define FIELDS 40

enum { IDLE, ARMED, RECORDING, READY, CONFIGURING };
static atomic_uint state, active;
static atomic_uint direct_mode, prepare_mode, fire_gate;
static unsigned last_direct_mode;
static unsigned preparing;
static unsigned prepared_sequence;
static uint32_t prepared_result;
static unsigned ray_calls;
/* Parameters transfer with ARMED release/acquire; observations with READY.
 * A serial debug command cannot re-arm while its previous dump is reading.
 * Guest restore/reset only changes state, never a published observations array. */
static unsigned requested_site;
static int requested_yaw, requested_pitch;
static unsigned requested_updates, remaining_updates;
static uint32_t rows[CAPACITY][FIELDS];
static unsigned row_count, dropped, applied, rejected, update_sequence;
extern uint64_t psx_cycle_count;

static uint32_t code_hash(uint32_t address, unsigned size) {
    uint32_t h = 2166136261u;
    for (unsigned i = 0; i < size; ++i) {
        h = (h ^ psx_mod_read_byte(address + i)) * 16777619u;
    }
    return h;
}
static uint32_t owned_player(void) {
    uint32_t p = psx_mod_read_word(ROOT);
    if ((p & 3u) || p < 0x800B0000u || p > 0x801FC000u ||
        psx_mod_read_word(p + 8) != 1 ||
        psx_mod_read_word(p + 0x39C) != p + 0x3FCu ||
        code_hash(UPDATE, 0xF20) != 0xF4D6C439u) return 0;
    return p;
}
static uint32_t owned_camera(uint32_t p) {
    uint32_t camera = psx_mod_read_word(0x800AA160u);
    if (camera < 0x800B0000u || camera > 0x801FC000u || (camera & 3u) ||
        psx_mod_read_word(camera + 8) != 2 ||
        psx_mod_read_word(camera + 0x39C) != camera + 0x3FCu ||
        psx_mod_read_word(camera + 0x380) != CAMERA_UPDATE ||
        code_hash(CAMERA_UPDATE, 0x1E8u) != 0xA707D113u) return 0;
    uint32_t handle = psx_mod_read_word(camera + 0x3FC + 12);
    if (!handle || (handle & 0xFFFFu) >= 512 ||
        psx_mod_read_word(0x800AA1A0u + (handle & 0xFFFFu) * 4) != p) return 0;
    return camera;
}
static void record(CPUState *cpu, uint32_t site, uint32_t p, uint32_t object) {
    if (row_count == CAPACITY) { ++dropped; return; }
    uint32_t *r = rows[row_count++];
    uint32_t in = p + 0x3FCu;
    r[0] = site; r[1] = (uint32_t)psx_cycle_count;
    r[2] = (uint32_t)(psx_cycle_count >> 32);
    r[3] = update_sequence + ((site & ~1u) == CAMERA_UPDATE || site == CAMERA_PREPARED);
    r[4] = p; r[5] = cpu->gpr[31]; r[6] = object;
    r[7] = psx_mod_read_word(in);
    r[8] = psx_mod_read_word(object + 0x23C);
    r[9] = psx_mod_read_word(object + 0x240);
    r[10] = psx_mod_read_word(p + 0x248);
    r[11] = psx_mod_read_word(p + 0x24C);
    r[12] = psx_mod_read_word(in + 0x184);
    r[13] = psx_mod_read_word(in + 0x190);
    r[14] = psx_mod_read_word(in + 0x188);
    r[15] = psx_mod_read_word(in + 0x194);
    r[16] = psx_mod_read_word(in + 0x18C);
    r[17] = psx_mod_read_word(in + 0x198);
    r[18] = psx_mod_read_word(in + 0x1D4);
    r[19] = psx_mod_read_word(in + 0x1D8);
    r[20] = cpu->gpr[21]; r[21] = applied;
    r[22] = psx_mod_read_word(p + 0x23C); r[23] = psx_mod_read_word(p + 0x240);
    r[24] = cpu->gpr[7];
    for (unsigned i = 0; i < 6; ++i) r[25 + i] = psx_mod_read_word(in + 0x1A4 + 4 * i);
    r[31] = 0; r[32] = 0; /* Retired early-ray experiment counters. */
    r[33] = ray_calls;
    r[34] = psx_mod_read_word(0x800A04B4u);
    r[35] = psx_mod_read_word(0x800A04BCu);
    for (unsigned i = 0; i < 3; ++i) r[36 + i] = psx_mod_read_word(object + 0x220 + 4 * i);
    r[39] = psx_mod_read_word(object + 8);
}
static int observe_ray(CPUState *cpu, uint32_t site) {
    if (!cpu || !atomic_load_explicit(&active, memory_order_relaxed)) return 0;
    uint32_t p = owned_player();
    if (!p || !owned_camera(p) || site != RAY || cpu->gpr[4] != p ||
        cpu->gpr[5] != p + 0x3FCu || cpu->gpr[31] != 0x8008F99Cu ||
        code_hash(RAY, 0x1058u) != 0x787AC4B0u) return 0;
    if (atomic_load_explicit(&state, memory_order_acquire) == RECORDING) {
        ++ray_calls;
        record(cpu, RAY, p, p);
    }
    return 0;
}
static int prepare_filter(CPUState *cpu, uint32_t site) {
    if (!cpu || preparing || !prepared_sequence || prepared_sequence != update_sequence ||
        !atomic_load_explicit(&active, memory_order_relaxed)) return 0;
    uint32_t p = owned_player(), camera = p ? owned_camera(p) : 0;
    if (!camera || site != PREPARE || cpu->gpr[4] != p || cpu->gpr[5] != p + 0x3FCu ||
        cpu->gpr[6] != camera + 0x3FCu || cpu->gpr[31] != 0x8008F9C8u ||
        code_hash(PREPARE, 0x130u) != 0xC1B54110u) return 0;
    prepared_sequence = 0;
    if (atomic_load_explicit(&state, memory_order_acquire) == RECORDING)
        record(cpu, PREPARE_SKIPPED, p, p);
    cpu->gpr[2] = prepared_result;
    return 1;
}
static void perturb(CPUState *cpu, uint32_t site, uint32_t p) {
    if (applied || requested_site != site || (!requested_yaw && !requested_pitch)) return;
    uint32_t addresses[] = {p + 0x23C, p + 0x240, p + 0x3FC + 0x184, p + 0x3FC + 0x190};
    int deltas[] = {requested_pitch, requested_yaw, requested_pitch, requested_yaw};
    int64_t values[4];
    for (unsigned i = 0; i < 4; ++i) {
        values[i] = (int32_t)psx_mod_read_word(addresses[i]) + (int64_t)deltas[i] * 65536;
        if (values[i] < INT32_MIN || values[i] > INT32_MAX ||
            (!(i & 1u) && (values[i] < -0x02AA0000 || values[i] > 0x02AA0000))) {
            ++rejected;
            return;
        }
    }
    for (unsigned i = 0; i < 4; ++i) psx_mod_write_word(addresses[i], (uint32_t)values[i]);
    applied = 1;
    record(cpu, site | 1u, p, p);
}
static void entry(CPUState *cpu, uint32_t site) {
    if (!atomic_load_explicit(&active, memory_order_relaxed) || !cpu) return;
    uint32_t p = owned_player();
    if (!p) return;
    unsigned direct = atomic_load_explicit(&direct_mode, memory_order_acquire);
    if (site == 0x8008D8C8u || site == 0x8008D8F4u || site == 0x8008D910u ||
        site == 0x8008E660u || site == 0x8008E7A8u) {
        uint32_t mode = psx_mod_read_word(p + 0x3FC + 0x1D4);
        if (direct && cpu->gpr[22] == p && cpu->gpr[19] == p + 0x3FCu &&
            (mode == 7 || mode == 8)) cpu->gpr[2] = 0;
        return;
    }
    if (site == UPDATE) {
        if (cpu->gpr[4] != p || cpu->gpr[31] != 0x800784DCu) return;
        if (direct && !last_direct_mode) {
            psx_mod_write_word(p + 0x3FC + 0x184, psx_mod_read_word(p + 0x23C));
            psx_mod_write_word(p + 0x3FC + 0x190, psx_mod_read_word(p + 0x240));
        }
        last_direct_mode = direct;
        ++update_sequence;
    } else if (site == CAMERA_UPDATE) {
        uint32_t camera = owned_camera(p);
        if (!camera || cpu->gpr[4] != camera || cpu->gpr[31] != 0x800784DCu) return;
    }
    unsigned s = atomic_load_explicit(&state, memory_order_acquire);
    unsigned anchor = (s == ARMED || s == RECORDING) && requested_site == CAMERA_UPDATE ? CAMERA_UPDATE : UPDATE;
    if (site == anchor) {
        if (s == RECORDING) {
            if (!--remaining_updates) {
                atomic_store_explicit(&state, READY, memory_order_release);
                s = READY;
            }
        } else if (s == ARMED) {
            /* The isolated runner supplies only neutral -> Cross. Wait for
             * the native sampled button word, not debugger command timing. */
            if (atomic_load_explicit(&fire_gate, memory_order_acquire) &&
                (code_hash(0x800834FCu, 0x6Cu) != 0x141AED00u ||
                 !(psx_mod_read_word(0x800A04B4u) & 0xFFFFu))) return;
            row_count = dropped = applied = rejected = 0;
            ray_calls = 0;
            remaining_updates = requested_updates;
            atomic_store_explicit(&state, RECORDING, memory_order_release);
            s = RECORDING;
        }
    }

    if (s != RECORDING) return;

    uint32_t object = p;
    if (site == CAMERA_UPDATE) {
        uint32_t camera = owned_camera(p);
        if (!camera || cpu->gpr[4] != camera || cpu->gpr[31] != 0x800784DCu) return;
    } else if (site == LOOK_END || site == ADJUST_END) {
        if (cpu->gpr[20] != p || cpu->gpr[16] != p + 0x3FCu) return;
    } else if (site == INTEGRATE) {
        if (cpu->gpr[4] != p || cpu->gpr[31] != 0x8007862Cu) return;
    } else if (site == BASIS) {
        object = cpu->gpr[4];
        if (object != p && (cpu->gpr[18] != p || cpu->gpr[31] != 0x8004860Cu ||
            object != cpu->gpr[16] || object < 0x800B0000u || object > 0x801FC000u || (object & 3))) return;
    } else if (site == CONSTRUCT) {
        object = cpu->gpr[5];
        if (cpu->gpr[4] != p || cpu->gpr[31] != 0x800482CCu ||
            object < 0x800B0000u || object > 0x801FC000u || (object & 3) ||
            psx_mod_read_word(object + 8) != 0x13F6u ||
            code_hash(CONSTRUCT, 0xDCu) != 0x073B3393u) return;
    }
    record(cpu, site, p, object);
    unsigned was_applied = applied;
    perturb(cpu, site, p);
    if (site == CAMERA_UPDATE && !was_applied && applied && requested_pitch &&
        atomic_load_explicit(&prepare_mode, memory_order_acquire) &&
        code_hash(PREPARE, 0x130u) == 0xC1B54110u &&
        psx_mod_read_word(p + 0x3FC + 0x1D4) == 7) {
        uint32_t in = owned_camera(p) + 0x3FCu;
        uint32_t target = psx_mod_read_word(in + 0x28);
        preparing = 1;
        prepared_result = psx_mod_call_guest(cpu, PREPARE, 0x8008F9C8u, p, p + 0x3FCu, in, 0);
        preparing = 0;
        /* Carry only this explicit angle change through the existing native
         * smoothing residual; do not replace the camera's world position. */
        psx_mod_write_word(in + 0x1C, psx_mod_read_word(in + 0x1C) + psx_mod_read_word(in + 0x28) - target);
        prepared_sequence = update_sequence + 1;
        record(cpu, CAMERA_PREPARED, p, p);
    }
}
static void reset(void) {
    atomic_store_explicit(&active, 0, memory_order_relaxed);
    atomic_store_explicit(&state, IDLE, memory_order_release);
    atomic_store_explicit(&direct_mode, 0, memory_order_release);
    atomic_store_explicit(&prepare_mode, 0, memory_order_release);
    atomic_store_explicit(&fire_gate, 0, memory_order_release);
    prepared_sequence = 0;
    preparing = 0;
    last_direct_mode = 0;
}
static void restored(void) {
    atomic_store_explicit(&state, IDLE, memory_order_release);
    atomic_store_explicit(&direct_mode, 0, memory_order_release);
    atomic_store_explicit(&prepare_mode, 0, memory_order_release);
    atomic_store_explicit(&fire_gate, 0, memory_order_release);
    prepared_sequence = 0;
    preparing = 0;
    last_direct_mode = 0;
}
static void activate(void) { reset(); atomic_store_explicit(&active, 1, memory_order_release); }

static int command(const char *args, char *reply, int capacity) {
    if (!atomic_load_explicit(&active, memory_order_acquire)) {
        snprintf(reply, capacity, "{\"active\":false}"); return 1;
    }
    unsigned direct_value; char direct_extra;
    if (sscanf(args, "fire_gate %u %c", &direct_value, &direct_extra) == 1) {
        if (direct_value > 1) return 0;
        atomic_store_explicit(&fire_gate, direct_value, memory_order_release);
        snprintf(reply, capacity, "{\"fire_gate\":%u}", direct_value); return 1;
    }
    if (sscanf(args, "prepare %u %c", &direct_value, &direct_extra) == 1) {
        if (direct_value > 1) return 0;
        atomic_store_explicit(&prepare_mode, direct_value, memory_order_release);
        snprintf(reply, capacity, "{\"prepare\":%u}", direct_value); return 1;
    }
    if (sscanf(args, "direct %u %c", &direct_value, &direct_extra) == 1) {
        if (direct_value > 1) return 0;
        atomic_store_explicit(&direct_mode, direct_value, memory_order_release);
        snprintf(reply, capacity, "{\"direct\":%u}", direct_value); return 1;
    }
    unsigned row_index = 0; char trailing;
    int row_request = sscanf(args, "row %u %c", &row_index, &trailing) == 1;
    if (!strcmp(args, "dump") || row_request) {
        unsigned s = atomic_load_explicit(&state, memory_order_acquire);
        if (s != READY) { snprintf(reply, capacity, "{\"state\":%u}", s); return 1; }
        if (!row_request) {
            snprintf(reply, capacity, "{\"state\":%u,\"applied\":%u,\"rejected\":%u,\"count\":%u,\"dropped\":%u}", s, applied, rejected, row_count, dropped);
            return 1;
        }
        if (row_index >= row_count || capacity < FIELDS * 11 + 20) return 0;
        int n = snprintf(reply, capacity, "{\"values\":[");
        for (unsigned j = 0; j < FIELDS; ++j)
            n += snprintf(reply + n, capacity - n, "%s%u", j ? "," : "", rows[row_index][j]);
        snprintf(reply + n, capacity - n, "]}"); return 1;
    }
    unsigned site = 0, updates = 1; int yaw = 0, pitch = 0, consumed = 0;
    if (strcmp(args, "arm") && !(sscanf(args, "arm %u %n", &updates, &consumed) == 1 && !args[consumed])) {
        consumed = 0;
        int parsed = sscanf(args, "inject %x %d %d %u %n", &site, &yaw, &pitch, &updates, &consumed);
        if (parsed != 4 || !consumed || args[consumed]) {
            updates = 1; consumed = 0;
            parsed = sscanf(args, "inject %x %d %d %n", &site, &yaw, &pitch, &consumed);
            if (parsed != 3 || !consumed || args[consumed]) return 0;
        }
    }
    if ((site && site != UPDATE && site != LOOK_END && site != ADJUST_END && site != CAMERA_UPDATE) ||
        yaw < -256 || yaw > 256 || pitch < -256 || pitch > 256 || !updates || updates > 8 ||
        (!site && (yaw || pitch))) return 0;
    unsigned s = atomic_load_explicit(&state, memory_order_acquire);
    if (s != IDLE && s != READY) { snprintf(reply, capacity, "{\"busy\":true}"); return 1; }
    if (!atomic_compare_exchange_strong_explicit(&state, &s, CONFIGURING, memory_order_acq_rel, memory_order_acquire)) return 0;
    requested_site = site; requested_yaw = yaw; requested_pitch = pitch;
    requested_updates = updates;
    atomic_store_explicit(&state, ARMED, memory_order_release);
    snprintf(reply, capacity, "{\"armed\":true}"); return 1;
}
PSX_MOD_CONSTRUCTOR(register_mkb_research) {
    psx_mod_register_activation_plugin(ID, activate);
    psx_mod_register_session_reset_plugin(ID, reset);
    psx_mod_register_savestate_plugin(ID, restored);
    psx_mod_register_function_entry_plugin(ID, UPDATE, entry);
    psx_mod_register_function_entry_plugin(ID, INTEGRATE, entry);
    psx_mod_register_function_entry_plugin(ID, BASIS, entry);
    psx_mod_register_function_entry_plugin(ID, CAMERA_UPDATE, entry);
    psx_mod_register_function_entry_plugin(ID, CONSTRUCT, entry);
    psx_mod_register_function_filter_plugin(ID, RAY, observe_ray);
    psx_mod_register_function_filter_plugin(ID, PREPARE, prepare_filter);
    psx_mod_register_instruction_plugin(ID, LOOK_END, 0x26A2FFF9u, entry);
    psx_mod_register_instruction_plugin(ID, 0x8008D8C8u, 0xAEC20248u, entry);
    psx_mod_register_instruction_plugin(ID, 0x8008D8F4u, 0xAEC20248u, entry);
    psx_mod_register_instruction_plugin(ID, 0x8008D910u, 0xAEC2024Cu, entry);
    psx_mod_register_instruction_plugin(ID, 0x8008E660u, 0xAEC2024Cu, entry);
    psx_mod_register_instruction_plugin(ID, 0x8008E7A8u, 0xAEC20248u, entry);
    psx_mod_register_instruction_plugin(ID, ADJUST_END, 0x02002821u, entry);
    psx_mod_register_command("mohu.mkb.research", command);
}
