#include "mod_plugins.h"
#include "moh_mkb.h"
#include "psx_keybinds.h"
#include "cpu_state.h"
#include "psx_openxr.h"
#include "psx_cycle_freeze.h"

#include <stdint.h>
#include <math.h>
#ifndef PSX_NO_DEBUG_TOOLS
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
static atomic_uint diagnostic_request;
static int diagnostic_capture;
#endif

#define PLUGIN_ID "mohu.input.mouse-keyboard"
#define SP_PLAYER_ROOT 0x800AA17Cu
#define SP_PLAYER_INPUT_OFFSET 0x3FCu
#define SP_PLAYER_CLASS 1u
#define SP_PAUSE 0x800A70F0u
#define MP_PLAYER2_ROOT 0x800A3608u
#define MP_PLAYER_INPUT_OFFSET 0x400u

#define PSX_R2 0x0200u
#define PSX_START 0x0008u

#define SNIPER_WEAPON_ID 5u

static int active;
static int mouse_captured;
static uint32_t mouse_strafe = 128;
static MohuMkbMouse mouse;
static uint32_t direct_player, prepared_camera, prepared_result;
static int preparing;
static int wheel_steps, requested_slot = -1, selecting_slot = -1;
static double wheel_remainder;
static unsigned number_keys;
static int profile_context = -1;

static int direct_mode_supported(uint32_t mode) {
    return mode == 7u || mode == 8u || mode == 9u;
}

static uint32_t code_hash(uint32_t address, uint32_t size) {
    uint32_t hash = 2166136261u;
    for (uint32_t i = 0; i < size; ++i)
        hash = (hash ^ psx_mod_read_byte(address + i)) * 16777619u;
    return hash;
}

static void reset_look(void) {
    mohu_mkb_mouse_reset(&mouse);
    direct_player = prepared_camera = 0;
    preparing = 0;
}

static void reset_weapon_input(void) {
    wheel_steps = 0;
    wheel_remainder = 0;
    requested_slot = selecting_slot = -1;
    number_keys = 0;
}

static const PsxPlayerBinds profile = {
    .up = SDL_SCANCODE_UP,
    .down = SDL_SCANCODE_DOWN,
    .left = SDL_SCANCODE_LEFT,
    .right = SDL_SCANCODE_RIGHT,
    .cross = PSXKB_MOUSE_SC(SDL_BUTTON_LEFT),
    .circle = SDL_SCANCODE_Q,
    .square = SDL_SCANCODE_R,
    .triangle = SDL_SCANCODE_SPACE,
    .l1 = SDL_SCANCODE_UNKNOWN,
    .r1 = SDL_SCANCODE_UNKNOWN,
    .l2 = SDL_SCANCODE_LCTRL,
    .r2 = PSXKB_MOUSE_SC(SDL_BUTTON_RIGHT),
    .l3 = SDL_SCANCODE_UNKNOWN,
    .r3 = SDL_SCANCODE_UNKNOWN,
    .start = SDL_SCANCODE_P,
    .select = SDL_SCANCODE_TAB,
    .ls_up = SDL_SCANCODE_W,
    .ls_down = SDL_SCANCODE_S,
    .ls_left = SDL_SCANCODE_A,
    .ls_right = SDL_SCANCODE_D,
    .rs_up = SDL_SCANCODE_UNKNOWN,
    .rs_down = SDL_SCANCODE_UNKNOWN,
    .rs_left = SDL_SCANCODE_UNKNOWN,
    .rs_right = SDL_SCANCODE_UNKNOWN,
};

/* The profile is selected before physical folding, so menu Q does not also
 * assert the gameplay Circle binding. The user's saved profiles stay intact. */
static const PsxPlayerBinds menu_profile = {
    .up = SDL_SCANCODE_UP, .down = SDL_SCANCODE_DOWN,
    .left = SDL_SCANCODE_LEFT, .right = SDL_SCANCODE_RIGHT,
    .cross = PSXKB_MOUSE_SC(SDL_BUTTON_LEFT),
    .triangle = SDL_SCANCODE_Q,
    .start = SDL_SCANCODE_P, .select = SDL_SCANCODE_TAB,
};

static uint32_t split_screen_player2(void) {
    const uint32_t player = psx_mod_read_word(MP_PLAYER2_ROOT);
    if (player < 0x800B0000u || player > 0x801FC000u || (player & 3u) ||
        psx_mod_read_word(player + 8u) != SP_PLAYER_CLASS)
        return 0;
    const uint32_t input = psx_mod_read_word(player + 0x39Cu);
    return input == player + MP_PLAYER_INPUT_OFFSET ? player : 0;
}

static uint32_t owned_player_input(void) {
    if (!psx_mod_game_started() || psx_openxr_session_active() ||
        split_screen_player2()) return 0;
    const uint32_t player = psx_mod_read_word(SP_PLAYER_ROOT);
    if (player < 0x800B0000u || player > 0x801FC000u || (player & 3u) ||
        psx_mod_read_word(player + 8u) != SP_PLAYER_CLASS)
        return 0;
    const uint32_t input = psx_mod_read_word(player + 0x39Cu);
    return input == player + SP_PLAYER_INPUT_OFFSET ? input : 0;
}

static int in_menu(void) {
    return !owned_player_input() || psx_mod_read_word(SP_PAUSE) != 0;
}

static int refresh_profile(void) {
    const int menu = in_menu();
    const uint8_t* keys = SDL_GetKeyboardState(NULL);
    const SDL_Scancode contextual[] = {SDL_SCANCODE_E, SDL_SCANCODE_Q};
    for (unsigned i = 0; i < sizeof(contextual) / sizeof(contextual[0]); ++i)
        if (!keys || !keys[contextual[i]]) psx_keybinds_release_control(1, contextual[i]);
    if (profile_context == menu) return 1;
    if (!psx_keybinds_set_session_player(1, menu ? &menu_profile : &profile)) return 0;
    if (profile_context >= 0)
        for (unsigned i = 0; i < sizeof(contextual) / sizeof(contextual[0]); ++i)
            if (keys && keys[contextual[i]]) psx_keybinds_suppress_control(1, contextual[i]);
    profile_context = menu;
    return 1;
}

static void input_context(void) {
    (void)refresh_profile();
}

static uint32_t owned_camera(uint32_t player) {
    const uint32_t camera = psx_mod_read_word(0x800AA160u);
    if ((camera & 3u) || camera < 0x800B0000u || camera > 0x801FC000u ||
        psx_mod_read_word(camera + 8u) != 2u ||
        psx_mod_read_word(camera + 0x39Cu) != camera + 0x3FCu ||
        psx_mod_read_word(camera + 0x380u) != 0x8004A744u) return 0;
    const uint32_t handle = psx_mod_read_word(camera + 0x408u);
    if (!handle || (handle & 0xFFFFu) >= 512u ||
        psx_mod_read_word(0x800AA1A0u + 4u * (handle & 0xFFFFu)) != player)
        return 0;
    return camera;
}

static int captured(void) {
#ifndef PSX_NO_DEBUG_TOOLS
    return mouse_captured || diagnostic_capture;
#else
    return mouse_captured;
#endif
}

/* This is the previously measured camera-before-player boundary. Apply the
 * complete displacement here, before the native view matrix and firing ray
 * are rebuilt. No pad curve, VBlank pulse, delta-time multiplier or turn cap. */
static void direct_camera(CPUState* cpu, uint32_t site) {
    if (!cpu || site != 0x8004A744u || !active || g_psx_render_pass_active) return;
#ifndef PSX_NO_DEBUG_TOOLS
    const unsigned request = atomic_exchange_explicit(&diagnostic_request, 0, memory_order_acquire);
    if ((request & 15u) == 3u) {
        requested_slot = (int)(request >> 4) - 1;
    } else if ((request & 15u) == 4u) {
        wheel_steps = (int)(request >> 4) - 16;
    } else if (request) {
        reset_look();
        diagnostic_capture = request != 1u;
        if (diagnostic_capture) {
            const int dx = (int)((request >> 16) & 0xFFFu) - 2048;
            const int dy = (int)((request >> 4) & 0xFFFu) - 2048;
            mohu_mkb_mouse_motion(&mouse, dx, dy);
        }
    }
#endif
    if (!cpu || site != 0x8004A744u || !active || !captured() ||
        g_psx_render_pass_active) return;
    const uint32_t input = owned_player_input();
    const uint32_t player = input ? input - SP_PLAYER_INPUT_OFFSET : 0;
    const uint32_t camera = player ? owned_camera(player) : 0;
    const uint32_t mode = input ? psx_mod_read_word(input + 0x1D4u) : 0;
    if (!camera || cpu->gpr[4] != camera || cpu->gpr[31] != 0x800784DCu ||
        psx_mod_read_word(SP_PAUSE) || !direct_mode_supported(mode) ||
        code_hash(0x800892C8u, 0xF20u) != 0xF4D6C439u ||
        code_hash(0x8004A744u, 0x1E8u) != 0xA707D113u ||
        code_hash(0x8008D81Cu, 0x1058u) != 0x787AC4B0u ||
        code_hash(0x8008AD04u, 0x130u) != 0xC1B54110u) {
        reset_look();
        return;
    }
    prepared_camera = 0;
    direct_player = player;
    int64_t dyaw = 0, dpitch = 0;
    mohu_mkb_mouse_take(&mouse, &dyaw, &dpitch);
    const int32_t old_pitch = (int32_t)psx_mod_read_word(player + 0x23Cu);
    int32_t pitch, yaw;
    mohu_mkb_angles(old_pitch, (int32_t)psx_mod_read_word(player + 0x240u),
                    dpitch, dyaw, &pitch, &yaw);
    psx_mod_write_word(player + 0x23Cu, (uint32_t)pitch);
    psx_mod_write_word(player + 0x240u, (uint32_t)yaw);
    psx_mod_write_word(input + 0x184u, (uint32_t)pitch);
    psx_mod_write_word(input + 0x190u, (uint32_t)yaw);
    if (pitch != old_pitch && (mode == 7u || mode == 9u)) {
        const uint32_t camera_input = camera + 0x3FCu;
        const uint32_t old_target = psx_mod_read_word(camera_input + 0x28u);
        preparing = 1;
        prepared_result = psx_mod_call_guest(cpu, 0x8008AD04u, 0x8008F9C8u,
            player, input, camera_input, 0);
        preparing = 0;
        psx_mod_write_word(camera_input + 0x1Cu,
            psx_mod_read_word(camera_input + 0x1Cu) +
            psx_mod_read_word(camera_input + 0x28u) - old_target);
        prepared_camera = camera;
    }
    psx_mod_counter_add("mohu.mkb.look.update", 1);
    if (dyaw || dpitch) psx_mod_counter_add("mohu.mkb.look.motion", 1);
}

static void direct_adjust(CPUState* cpu, uint32_t site) {
    if (!cpu || !active || !captured() || !direct_player ||
        g_psx_render_pass_active || psx_mod_read_word(SP_PAUSE) ||
        owned_player_input() != direct_player + SP_PLAYER_INPUT_OFFSET) return;
    const uint32_t input = direct_player + SP_PLAYER_INPUT_OFFSET;
    const uint32_t mode = psx_mod_read_word(input + 0x1D4u);
    if (!direct_mode_supported(mode)) return;
    if (site == 0x8008F984u) {
        if (cpu->gpr[20] != direct_player || cpu->gpr[16] != input) return;
        /* The neutral pad's pitch-centering must not pull the mouse target
         * back after the camera update. Keep native ray construction intact. */
        psx_mod_write_word(input + 0x184u, psx_mod_read_word(direct_player + 0x23Cu));
        psx_mod_write_word(input + 0x190u, psx_mod_read_word(direct_player + 0x240u));
    } else if (cpu->gpr[22] == direct_player && cpu->gpr[19] == input) {
        cpu->gpr[2] = 0; /* Suppress only the measured angular increment store. */
    }
}

static int prepared_pitch(CPUState* cpu, uint32_t site) {
    if (!cpu || preparing || !prepared_camera || !direct_player ||
        site != 0x8008AD04u || cpu->gpr[4] != direct_player ||
        cpu->gpr[5] != direct_player + SP_PLAYER_INPUT_OFFSET ||
        cpu->gpr[6] != prepared_camera + 0x3FCu ||
        cpu->gpr[31] != 0x8008F9C8u) return 0;
    prepared_camera = 0;
    cpu->gpr[2] = prepared_result;
    return 1;
}

static void restored(void) {
    reset_look();
    reset_weapon_input();
    mouse_captured = 0;
    mouse_strafe = 128;
#ifndef PSX_NO_DEBUG_TOOLS
    diagnostic_capture = 0;
    atomic_store_explicit(&diagnostic_request, 0, memory_order_release);
#endif
}

static void selected_weapon(CPUState* cpu, uint32_t site) {
    if (cpu && selecting_slot >= 0 && site == 0x800891D0u &&
        cpu->gpr[17] == owned_player_input() &&
        cpu->gpr[18] == cpu->gpr[17] - SP_PLAYER_INPUT_OFFSET)
        cpu->gpr[2] = (uint32_t)selecting_slot;
}

static void weapon_update(CPUState* cpu, uint32_t site) {
    if (!active || !cpu || site != 0x800892C8u || g_psx_render_pass_active) return;
    const uint32_t input = owned_player_input();
    if (!input || psx_mod_read_word(SP_PAUSE) ||
        cpu->gpr[4] != input - SP_PLAYER_INPUT_OFFSET || cpu->gpr[31] != 0x800784DCu)
        return;
    if (requested_slot < 0 && !wheel_steps) return;
    const uint32_t count = psx_mod_read_word(0x800AB5B4u);
    const uint32_t current = psx_mod_read_byte(input + 92u);
    if (!count || count > 8 || current >= count ||
        code_hash(0x800891ACu, 0x11Cu) != 0x5A361CFBu) {
        reset_weapon_input(); return;
    }
    int16_t reserve[8];
    for (unsigned i = 0; i < count; ++i)
        reserve[i] = (int16_t)psx_mod_read_half(input + 0x5Eu + 2u * i);
    const int slot = mohu_mkb_weapon_slot(reserve, count, current, wheel_steps, requested_slot);
    if (requested_slot >= 0) requested_slot = -1;
    else wheel_steps += wheel_steps > 0 ? -1 : 1;
    if (slot < 0 || (unsigned)slot == current) return;
    /* Reuse the full native switch routine. Only its next-slot result is
     * replaced for this call; inventory, ammo and viewmodel setup stay native. */
    selecting_slot = slot;
    (void)psx_mod_call_guest(cpu, 0x800891ACu, 0x800784DCu,
        input - SP_PLAYER_INPUT_OFFSET, input, 0, 0);
    selecting_slot = -1;
    psx_mod_counter_add("mohu.mkb.weapon.select", 1);
}

#ifndef PSX_NO_DEBUG_TOOLS
/* Explicit diagnostic input to this same update path; the debug thread only
 * queues a request. It never reads or writes guest state. */
static int test_motion(const char* args, char* reply, int capacity) {
    int dx, dy, used = 0;
    if (!strcmp(args, "release")) {
        atomic_store_explicit(&diagnostic_request, 1, memory_order_release);
    } else if (sscanf(args, "motion %d %d %n", &dx, &dy, &used) == 2 &&
               used && !args[used] && dx >= -2048 && dx < 2048 &&
               dy >= -2048 && dy < 2048) {
        const unsigned request = ((unsigned)(dx + 2048) << 16) |
                                 ((unsigned)(dy + 2048) << 4) | 2u;
        atomic_store_explicit(&diagnostic_request, request, memory_order_release);
    } else if (sscanf(args, "select %d %n", &dx, &used) == 1 && used &&
               !args[used] && dx >= 1 && dx <= 8) {
        atomic_store_explicit(&diagnostic_request, ((unsigned)dx << 4) | 3u, memory_order_release);
    } else if (sscanf(args, "wheel %d %n", &dx, &used) == 1 && used &&
               !args[used] && dx >= -8 && dx <= 8 && dx) {
        atomic_store_explicit(&diagnostic_request, ((unsigned)(dx + 16) << 4) | 4u, memory_order_release);
    } else return 0;
    snprintf(reply, capacity, "queued");
    return 1;
}
#endif

/* Only this renderer's visibility-test scratch register changes. Later reads
 * of the real flags retain native scope/style selection; no aim flag is ever
 * written to the player. The complete supported renderer is byte-guarded. */
static void native_reticle(CPUState* cpu, uint32_t address) {
    const uint32_t input = owned_player_input();
    if (!active || !cpu || address != 0x8008C1B4u || !input ||
        cpu->gpr[6] != input || cpu->gpr[16] != input - SP_PLAYER_INPUT_OFFSET ||
        psx_mod_read_word(SP_PAUSE) != 0 ||
        psx_mod_read_byte(input + 93u) == SNIPER_WEAPON_ID) return;
    uint32_t hash = 2166136261u;
    for (uint32_t p = 0x8008C124u; p < 0x8008C620u; ++p)
        hash = (hash ^ psx_mod_read_byte(p)) * 16777619u;
    if (hash != 0x71C28163u) return;
    cpu->gpr[2] |= 0x20u;
    psx_mod_counter_add("mohu.mkb.reticle.visible", 1);
}

static int mouse_eligible(uint32_t native_buttons) {
    if ((native_buttons & PSX_START) == 0) return 0;
    const uint32_t input = owned_player_input();
    return input && psx_mod_read_word(SP_PAUSE) == 0 ? 1 : 0;
}

static void mouse_event(const PSXModMouseEvent* event) {
    if (!event || event->struct_size != sizeof(*event)) return;
    if (event->type == PSX_MOD_MOUSE_RESET ||
        event->type == PSX_MOD_MOUSE_ACQUIRED ||
        event->type == PSX_MOD_MOUSE_HOLD_RELEASE) {
        reset_look();
        reset_weapon_input();
        mouse_captured = event->type == PSX_MOD_MOUSE_ACQUIRED;
        mouse_strafe = 128;
    } else if (event->type == PSX_MOD_MOUSE_MOTION) {
        mohu_mkb_mouse_motion(&mouse, event->dx, event->dy);
    } else if (event->type == PSX_MOD_MOUSE_WHEEL && mouse_captured) {
        double whole;
        wheel_remainder = modf(wheel_remainder - event->dy, &whole);
        wheel_steps = (int)fmax(-16, fmin(16, wheel_steps + whole));
    }
}

static void mouse_sample(uint64_t now_ns, PSXModMouseOutput* output) {
    (void)now_ns;
    if (!output || output->struct_size != sizeof(*output)) return;
    output->override_right = 1;
    output->ry = 128;
    /* Underground strafes on RX. Keyboard strafe is presented here so the
     * generic right-stick takeover gate does not mistake A/D for mouse-look. */
    output->rx = mouse_strafe;
}

/* Work on the resolved pad so native sticks survive and R2 cannot be
 * reasserted by the physical-button merge after our suppression. */
static int gameplay_pad(const PSXModPadFrame* frame, PSXModPadOutput* out) {
    if (!frame || !out || frame->struct_size != sizeof(*frame) ||
        out->struct_size != sizeof(*out)) return 0;
    if (psx_openxr_session_active() || split_screen_player2()) return 0;

    uint8_t filtered_keys[SDL_NUM_SCANCODES];
    psx_keybinds_host_keys(SDL_GetKeyboardState(NULL), filtered_keys);
    const uint8_t* keys = filtered_keys;
    if (in_menu()) {
        out->buttons = mohu_mkb_menu_buttons((uint16_t)out->buttons,
            keys && keys[SDL_SCANCODE_A], keys && keys[SDL_SCANCODE_D],
            keys && keys[SDL_SCANCODE_W], keys && keys[SDL_SCANCODE_S],
            keys && (keys[SDL_SCANCODE_E] || keys[SDL_SCANCODE_RETURN]),
            keys && (keys[SDL_SCANCODE_Q] || keys[SDL_SCANCODE_BACKSPACE]));
        mouse_strafe = 128;
        wheel_steps = 0;
        requested_slot = -1;
        if (keys && (keys[SDL_SCANCODE_W] || keys[SDL_SCANCODE_A] ||
                     keys[SDL_SCANCODE_S] || keys[SDL_SCANCODE_D]))
            out->lx = out->ly = out->rx = out->ry = 128;
        return 1;
    }
    if (keys) {
        out->buttons = mohu_mkb_action_aliases(
            (uint16_t)out->buttons,
            keys[SDL_SCANCODE_RETURN] != 0,
            keys[SDL_SCANCODE_BACKSPACE] != 0,
            keys[SDL_SCANCODE_E] != 0);
        unsigned held = 0;
        for (unsigned i = 0; i < 8; ++i) {
            if (keys[SDL_SCANCODE_1 + i]) held |= 1u << i;
            if (((held & ~number_keys) & (1u << i)) && mouse_eligible(out->buttons))
                requested_slot = (int)i;
        }
        number_keys = held;
    }

    uint8_t lx = 128, ly = 128;
    mohu_mkb_stick_pair(
        keys && keys[SDL_SCANCODE_A], keys && keys[SDL_SCANCODE_D],
        keys && keys[SDL_SCANCODE_W], keys && keys[SDL_SCANCODE_S],
        &lx, &ly);
    const int movement = keys && (keys[SDL_SCANCODE_A] || keys[SDL_SCANCODE_D] ||
                                 keys[SDL_SCANCODE_W] || keys[SDL_SCANCODE_S]);
    if (movement) {
        out->lx = 128;
        out->rx = lx; /* Native RX strafes; native LX turns. */
        out->ly = ly;
    }
    const uint32_t input = owned_player_input();
    mouse_strafe = out->rx;
    if (input && psx_mod_read_word(SP_PAUSE) == 0 && mouse_captured) {
        out->lx = 128;
        if (movement) out->rx = 128;
    }
    if (input && psx_mod_read_word(SP_PAUSE) == 0 &&
        psx_mod_read_byte(input + 93u) != SNIPER_WEAPON_ID)
        out->buttons |= PSX_R2; /* Active-low: release ordinary aim. */
    return 1;
}

static void deactivate(void) {
    active = 0;
    mouse_captured = 0;
    mouse_strafe = 128;
    restored();
    (void)psx_mod_set_pad_transform(0, NULL);
    psx_keybinds_clear_session_players();
    profile_context = -1;
    (void)psx_mod_set_local_mouse_persistent_capture(0);
    (void)psx_mod_set_local_mouse_capture_across_transitions(0);
}

static void activate(void) {
    if (active) return;
    mohu_mkb_mouse_reset(&mouse);
    const PSXModPadTransform transform = {
        .struct_size = sizeof(transform),
        .allowed_types = PSX_MOD_PAD_TYPE_BIT(PSX_MOD_PAD_DUALSHOCK),
        .initial_type = PSX_MOD_PAD_DUALSHOCK,
        .transform = gameplay_pad,
    };
    if (!refresh_profile() ||
        !psx_mod_set_controller_mode_override(0, PSX_MOD_CONTROLLER_ANALOG) ||
        !psx_mod_set_pad_transform(0, &transform)) {
        deactivate();
        return;
    }

    const PSXModMousePolicy policy = {
        .struct_size = sizeof(policy),
        .hold_control = PSX_MOD_MOUSE_HOLD_NONE,
        .eligible = mouse_eligible,
        .event = mouse_event,
        .sample = mouse_sample,
    };
    if (!psx_mod_set_local_mouse_policy(&policy) ||
        !psx_mod_set_local_mouse_persistent_capture(1)) {
        deactivate();
        return;
    }
    active = 1;
}

PSX_MOD_CONSTRUCTOR(register_mohu_mkb) {
    (void)psx_mod_register_activation_plugin(PLUGIN_ID, activate);
    (void)psx_mod_register_session_reset_plugin(PLUGIN_ID, deactivate);
    (void)psx_mod_register_savestate_plugin(PLUGIN_ID, restored);
    (void)psx_mod_register_vblank_plugin(PLUGIN_ID, input_context);
    (void)psx_mod_register_function_entry_plugin(PLUGIN_ID, 0x8004A744u, direct_camera);
    (void)psx_mod_register_function_entry_plugin(PLUGIN_ID, 0x800892C8u, weapon_update);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x800891D0u, 0x00408021u, selected_weapon);
    (void)psx_mod_register_function_filter_plugin(PLUGIN_ID, 0x8008AD04u, prepared_pitch);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x8008F984u, 0x26A2FFF9u, direct_adjust);
    /* Every nonzero angular store in the guarded native adjustment routine,
     * including its near-collision / steep-pitch projection fallback. */
    const uint32_t stores[] = {
        0x8008D8C8u, 0x8008D8F4u, 0x8008D910u, 0x8008E660u,
        0x8008E7A8u, 0x8008E4A0u, 0x8008E4A8u, 0x8008E4F4u
    };
    for (unsigned i = 0; i < sizeof(stores) / sizeof(stores[0]); ++i)
        (void)psx_mod_register_instruction_plugin(PLUGIN_ID, stores[i],
            i == 2 || i == 3 || i == 5 || i == 6 ? 0xAEC2024Cu : 0xAEC20248u,
            direct_adjust);
#ifndef PSX_NO_DEBUG_TOOLS
    (void)psx_mod_register_command("mohu.mkb.test", test_motion);
#endif
    (void)psx_mod_register_instruction_plugin(
        PLUGIN_ID, 0x8008C1B4u, 0x30420020u, native_reticle);
}
