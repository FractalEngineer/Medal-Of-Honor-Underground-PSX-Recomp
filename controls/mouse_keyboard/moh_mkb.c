#include "mod_plugins.h"
#include "moh_mkb.h"
#include "psx_keybinds.h"
#include "cpu_state.h"
#include "psx_openxr.h"
#include "psx_cycle_freeze.h"

#include <stdint.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#ifndef PSX_NO_DEBUG_TOOLS
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
static atomic_uint diagnostic_request;
static int diagnostic_capture;
static int diagnostic_aim;
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
static int profile_context = -1;
static double mouse_gain = 0.5, scoped_gain = 0.8;
static int zoom_held;
static double zoom_amount;
static uint32_t reticle_stack;
static void reset_look(void);

static int sensitivity_option(const char* name, int fallback, int maximum) {
    char value[16], *end;
    if (!psx_mod_option_value(PLUGIN_ID, "mouse-keyboard", name, value, sizeof(value)))
        return fallback;
    const long percent = strtol(value, &end, 10);
    return end != value && !*end && percent >= 1 && percent <= maximum ? (int)percent : fallback;
}

static void refresh_sensitivity(void) {
    mouse_gain = sensitivity_option("sensitivity", 50, 400) / 100.0;
    scoped_gain = sensitivity_option("scoped_sensitivity", 80, 200) / 100.0;
}

static int sensitivity_changed(const char* option, const char* value) {
    (void)value;
    if (strcmp(option, "sensitivity") && strcmp(option, "scoped_sensitivity")) return 0;
    reset_look();
    refresh_sensitivity();
    return 1;
}

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
    reticle_stack = 0;
}

static void reset_weapon_input(void) {
    wheel_steps = 0;
    wheel_remainder = 0;
    requested_slot = selecting_slot = -1;
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

static int firearm_zoom_eligible(uint32_t input) {
    return input && captured() && !psx_mod_read_word(SP_PAUSE) &&
        mohu_mkb_firearm_zoom_supported(psx_mod_read_byte(input + 93u));
}

static int firearm_zooming(uint32_t input) {
    return firearm_zoom_eligible(input) && zoom_amount > 0;
}

static int firearm_aiming(uint32_t input) {
    int held = zoom_held;
#ifndef PSX_NO_DEBUG_TOOLS
    held |= diagnostic_aim;
#endif
    return firearm_zoom_eligible(input) && held;
}

static void firearm_focal(CPUState* cpu, uint32_t site) {
    if (!cpu || !active || g_psx_render_pass_active) return;
    const uint32_t input = owned_player_input();
    if (!firearm_zoom_eligible(input)) return;
    if (site == 0x8008A0E8u && cpu->gpr[16] == input &&
        cpu->gpr[17] == input - SP_PLAYER_INPUT_OFFSET && cpu->gpr[2] == 400u &&
        code_hash(0x800892C8u, 0xF20u) == 0xF4D6C439u) {
        zoom_amount = mohu_mkb_zoom_step(zoom_amount, firearm_aiming(input));
        cpu->gpr[2] = 400u + (uint32_t)lround(100 * mohu_mkb_zoom_ease(zoom_amount));
        if (zoom_amount > 0) psx_mod_counter_add("mohu.mkb.firearm.zoom", 1);
    } else if (site == 0x8008D854u && cpu->gpr[4] == input - SP_PLAYER_INPUT_OFFSET &&
               cpu->gpr[19] == input &&
               code_hash(0x8008D81Cu, 0x1058u) == 0x787AC4B0u) {
        cpu->gpr[2] = 400u; /* Refresh the ordinary crosshair ray at zoom >400. */
    } else if (site == 0x8008ABACu && cpu->gpr[16] == input &&
               cpu->gpr[17] == input - SP_PLAYER_INPUT_OFFSET &&
               code_hash(0x8008AB84u, 0x160u) == 0xED5849B4u) {
        /* Native held-weapon rendering normally requires focal length 400.
         * Bypass only that visibility comparison, keeping the real zoom. */
        cpu->gpr[3] = 400u;
        psx_mod_counter_add("mohu.mkb.firearm.weapon.visible", 1);
    }
}

/* R2 still owns native sniper zoom and its overlay. Only the control-mode
 * result and the two locomotion tests see ordinary walking semantics; the
 * real aim flags remain available to camera, weapon and HUD consumers. */
static void sniper_controls(CPUState* cpu, uint32_t site) {
    if (!cpu || !active || !captured() || g_psx_render_pass_active ||
        psx_mod_read_word(SP_PAUSE)) return;
    firearm_focal(cpu, site);
    const uint32_t input = owned_player_input();
    if (!input || psx_mod_read_byte(input + 93u) != SNIPER_WEAPON_ID) return;
    const uint32_t player = input - SP_PLAYER_INPUT_OFFSET;
    if (site == 0x800894FCu) {
        if (cpu->gpr[17] == player && cpu->gpr[16] == input && cpu->gpr[2] == 2u &&
            code_hash(0x80087790u, 0xBCu) == 0x8728EEBCu) {
            cpu->gpr[2] = 7u;
            psx_mod_counter_add("mohu.mkb.scope.walk", 1);
        }
    } else if (site == 0x8008D854u && cpu->gpr[4] == player &&
               cpu->gpr[19] == input && (psx_mod_read_word(input) & 0x20u) &&
               code_hash(0x8008D81Cu, 0x1058u) == 0x787AC4B0u) {
        /* Native walking normally skips its cached ray at scope zoom (>400).
         * Keep the actual zoom for projection and refresh the ray normally. */
        cpu->gpr[2] = 400u;
    } else if ((site == 0x8008D9D8u || site == 0x8008D9E4u ||
                site == 0x8008DA00u || site == 0x8008E06Cu) &&
               cpu->gpr[22] == player && cpu->gpr[19] == input &&
               (psx_mod_read_word(input) & 0x20u) &&
               code_hash(0x8008D81Cu, 0x1058u) == 0x787AC4B0u) {
        /* Scope artwork is centred. Its ray must not inherit the ordinary
         * weapon's movable reticle or native off-centre target-score blend. */
        if (site == 0x8008D9D8u) cpu->gpr[4] = 256u;
        else if (site == 0x8008D9E4u) cpu->gpr[3] = cpu->gpr[2];
        /* The focal-plane vector is signed 16-bit. Zoom >2047 would wrap Z
         * behind the player; centre rays can use the ordinary 400-unit plane. */
        else if (site == 0x8008DA00u) cpu->gpr[2] = 400u;
        else cpu->gpr[18] = cpu->gpr[30];
    } else if ((site == 0x8008EB3Cu || site == 0x8008EB50u) &&
               cpu->gpr[20] == player && cpu->gpr[16] == input &&
               code_hash(0x8008EAF0u, 0xF04u) == 0x389240BCu) {
        cpu->gpr[2] &= ~0x20u;
    }
}

static int precise_view(CPUState* cpu, uint32_t site) {
    if (!cpu || site != 0x8004C2BCu || !active || !captured() ||
        g_psx_render_pass_active || psx_mod_read_word(SP_PAUSE)) return 0;
    const uint32_t input = owned_player_input();
    const uint32_t player = input ? input - SP_PLAYER_INPUT_OFFSET : 0;
    const uint32_t camera = player ? owned_camera(player) : 0;
    if (!camera || direct_player != player || cpu->gpr[4] != camera + 0x4E0u ||
        cpu->gpr[5] != camera || cpu->gpr[31] != 0x8004C5B8u ||
        !direct_mode_supported(psx_mod_read_word(input + 0x1D4u)) ||
        (psx_mod_read_word(camera + 0x498u) & 0x1800u) ||
        code_hash(0x8004C2BCu, 0x250u) != 0xB7059F78u ||
        code_hash(0x8004C50Cu, 0x204u) != 0xFD960C32u) return 0;
    int32_t eye[3], translation[3];
    int16_t rotation[9];
    for (unsigned i = 0; i < 3; ++i)
        eye[i] = (int32_t)psx_mod_read_word(camera + 0x220u + 4u * i);
    mohu_mkb_view_matrix((int32_t)psx_mod_read_word(player + 0x23Cu),
        (int32_t)psx_mod_read_word(player + 0x240u), eye, rotation, translation);
    const uint32_t matrix = camera + 0x4FCu;
    for (unsigned i = 0; i < 9; ++i)
        psx_mod_write_half(matrix + 2u * i, (uint16_t)rotation[i]);
    for (unsigned i = 0; i < 3; ++i)
        psx_mod_write_word(matrix + 0x14u + 4u * i, (uint32_t)translation[i]);
    cpu->gpr[2] = (uint32_t)translation[2];
    psx_mod_counter_add("mohu.mkb.view.precise", 1);
    return 1;
}

static void precise_shot(CPUState* cpu, uint32_t site) {
    if (!cpu || site != 0x80076CB8u || !active || !captured() ||
        g_psx_render_pass_active || psx_mod_read_word(SP_PAUSE)) return;
    const uint32_t input = owned_player_input();
    if (!input || psx_mod_read_byte(input + 93u) != SNIPER_WEAPON_ID ||
        !(psx_mod_read_word(input) & 0x20u)) return;
    const uint32_t shot = cpu->gpr[16], sp = cpu->gpr[29];
    if (shot < 0x800B0000u || shot > 0x801FC000u || (shot & 3u) ||
        psx_mod_read_word(shot + 8u) != 0x13F6u || cpu->gpr[17] != shot + 0x354u ||
        sp < 0x800B0000u || sp > 0x801FFF00u ||
        psx_mod_read_word(sp + 0x44u) != 0x8004860Cu ||
        psx_mod_read_word(sp + 0x40u) != input - SP_PLAYER_INPUT_OFFSET ||
        code_hash(0x80076C28u, 0x104u) != 0xD4FD2F11u) return;
    int32_t origin[3], target[3];
    int16_t rotation[9];
    for (unsigned i = 0; i < 3; ++i) {
        origin[i] = (int32_t)psx_mod_read_word(shot + 0x220u + 4u * i);
        target[i] = (int32_t)psx_mod_read_word(input + 0x1B0u + 4u * i);
    }
    if (!mohu_mkb_shot_matrix(origin, target, rotation)) return;
    for (unsigned i = 0; i < 9; ++i)
        psx_mod_write_half(shot + 0x354u + 2u * i, (uint16_t)rotation[i]);
    psx_mod_counter_add("mohu.mkb.scope.shot.precise", 1);
}

static void scoped_origin(CPUState* cpu, uint32_t site) {
    if (!cpu || !active || !captured() || g_psx_render_pass_active ||
        psx_mod_read_word(SP_PAUSE) || site < 0x800481A0u || site > 0x800481A8u) return;
    const uint32_t input = owned_player_input();
    const int scoped = input && psx_mod_read_byte(input + 93u) == SNIPER_WEAPON_ID &&
        (psx_mod_read_word(input) & 0x20u);
    if (!input || (!scoped && !firearm_zooming(input)) || cpu->gpr[2] != input ||
        cpu->gpr[17] != input + 0x1B0u) return;
    const uint32_t shot = cpu->gpr[16];
    const uint32_t camera = owned_camera(input - SP_PLAYER_INPUT_OFFSET);
    if (!camera || shot < 0x800B0000u || shot > 0x801FC000u || (shot & 3u)) return;
    const uint32_t type = psx_mod_read_word(shot + 8u);
    if (cpu->gpr[18] != shot + 0x220u ||
        (type != 0x13F6u && type != 0x13F7u && type != 0x13F1u) ||
        code_hash(0x8004815Cu, 0xDCu) != 0x073B3393u) return;
    /* A zoomed viewmodel may not refresh the normal muzzle cache.
     * Use this scope's current eye for construction, without changing that cache. */
    const unsigned axis = (site - 0x800481A0u) / 4u;
    cpu->gpr[8u + axis] = psx_mod_read_word(camera + 0x220u + 4u * axis);
    if (!axis) psx_mod_counter_add(scoped ? "mohu.mkb.scope.origin" : "mohu.mkb.firearm.origin", 1);
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
    } else if ((request & 15u) == 5u) {
        diagnostic_aim = (request >> 4) != 0;
        diagnostic_capture = 1;
    } else if (request) {
        reset_look();
        diagnostic_capture = request != 1u;
        if (!diagnostic_capture) diagnostic_aim = 0;
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
    double gain = mouse_gain;
    if (firearm_zooming(input)) {
        const double blend = mohu_mkb_zoom_ease(zoom_amount);
        gain *= (1 + blend * (scoped_gain - 1)) / (1 + 0.25 * blend);
    }
    else if (psx_mod_read_byte(input + 93u) == SNIPER_WEAPON_ID &&
        (psx_mod_read_word(input) & 0x20u)) {
        const uint32_t depth = psx_mod_read_word(input + 0xACu);
        gain *= scoped_gain * 400.0 / fmax(400.0, depth);
    }
    mohu_mkb_mouse_take_scaled(&mouse, gain, &dyaw, &dpitch);
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
    zoom_held = 0;
    zoom_amount = 0;
    mouse_strafe = 128;
#ifndef PSX_NO_DEBUG_TOOLS
    diagnostic_capture = 0;
    diagnostic_aim = 0;
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
    } else if (sscanf(args, "aim %d %n", &dx, &used) == 1 && used &&
               !args[used] && (dx == 0 || dx == 1)) {
        atomic_store_explicit(&diagnostic_request, ((unsigned)dx << 4) | 5u, memory_order_release);
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
    if (!active || !cpu || (address != 0x8008C1B4u && address != 0x8008C1FCu) || !input ||
        cpu->gpr[6] != input || cpu->gpr[16] != input - SP_PLAYER_INPUT_OFFSET ||
        psx_mod_read_word(SP_PAUSE) != 0 ||
        (psx_mod_read_byte(input + 93u) == SNIPER_WEAPON_ID &&
         (psx_mod_read_word(input) & 0x20u))) return;
    uint32_t hash = 2166136261u;
    for (uint32_t p = 0x8008C124u; p < 0x8008C620u; ++p)
        hash = (hash ^ psx_mod_read_byte(p)) * 16777619u;
    if (hash != 0x71C28163u) return;
    const int aiming = firearm_aiming(input);
    if (address == 0x8008C1B4u) {
        reticle_stack = aiming ? cpu->gpr[29] : 0;
        if (aiming) {
            cpu->gpr[2] |= 0x20u;
            psx_mod_counter_add("mohu.mkb.reticle.visible", 1);
        } else cpu->gpr[2] &= ~0x20u;
    } else if (!aiming) {
        cpu->gpr[2] = 0; /* Skip the optional non-aimed reticle path too. */
        psx_mod_counter_add("mohu.mkb.reticle.hidden", 1);
    }
}

static void tighten_reticle(CPUState* cpu, uint32_t site) {
    if (!cpu || !active || site != 0x8008C5D4u || !reticle_stack ||
        cpu->gpr[29] != reticle_stack || g_psx_render_pass_active ||
        !firearm_aiming(owned_player_input()) ||
        code_hash(0x8008C124u, 0x4FCu) != 0x71C28163u) return;
    const uint32_t base = cpu->gpr[22] - 48u;
    const uint32_t physical = base & 0x1FFFFFFFu;
    if (physical < 0xB0000u || physical > 0x1FFFC0u || (base & 3u)) return;
    const int16_t centre[2] = {(int16_t)cpu->gpr[19], (int16_t)cpu->gpr[20]};
    const int16_t original[8][2] = {{0,-12},{0,-5},{0,12},{0,5},
                                   {-18,0},{-8,0},{18,0},{8,0}};
    const int16_t tight[8][2] = {{0,-8},{0,-3},{0,8},{0,3},
                                {-12,0},{-5,0},{12,0},{5,0}};
    /* Only the four ordinary line packets, with every original coordinate
     * validated. Scope/special reticles and weapon accuracy are untouched. */
    for (unsigned p = 0; p < 8; ++p)
        for (unsigned axis = 0; axis < 2; ++axis)
            if ((int16_t)psx_mod_read_half(base + 16u * (p / 2u) + 8u + 4u * (p % 2u) + 2u * axis)
                != centre[axis] + original[p][axis]) return;
    for (unsigned p = 0; p < 8; ++p)
        for (unsigned axis = 0; axis < 2; ++axis)
            psx_mod_write_half(base + 16u * (p / 2u) + 8u + 4u * (p % 2u) + 2u * axis,
                (uint16_t)(centre[axis] + original[p][axis] +
                    lround((tight[p][axis] - original[p][axis]) * mohu_mkb_zoom_ease(zoom_amount))));
    reticle_stack = 0;
    psx_mod_counter_add("mohu.mkb.firearm.reticle.tight", 1);
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
#ifndef PSX_NO_DEBUG_TOOLS
        if (!diagnostic_capture) {
#endif
        zoom_held = 0;
        zoom_amount = 0;
#ifndef PSX_NO_DEBUG_TOOLS
        }
#endif
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
    zoom_held = 0;
    if (!frame || !out || frame->struct_size != sizeof(*frame) ||
        out->struct_size != sizeof(*out)) return 0;
    if (psx_openxr_session_active() || split_screen_player2()) return 0;

    uint8_t filtered_keys[SDL_NUM_SCANCODES];
    psx_keybinds_host_keys(SDL_GetKeyboardState(NULL), filtered_keys);
    const uint8_t* keys = filtered_keys;
    if (in_menu()) {
        zoom_amount = 0;
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
#ifndef PSX_NO_DEBUG_TOOLS
    if (diagnostic_aim) out->buttons &= ~PSX_R2;
#endif
    zoom_held = input && (out->buttons & PSX_R2) == 0;
    if (!input || !mohu_mkb_firearm_zoom_supported(psx_mod_read_byte(input + 93u)))
        zoom_amount = 0;
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
    refresh_sensitivity();
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
    (void)psx_mod_register_option_changed_plugin(PLUGIN_ID, sensitivity_changed);
    (void)psx_mod_register_function_filter_plugin(PLUGIN_ID, 0x8004C2BCu, precise_view);
    (void)psx_mod_register_function_entry_plugin(PLUGIN_ID, 0x8004A744u, direct_camera);
    (void)psx_mod_register_function_entry_plugin(PLUGIN_ID, 0x800892C8u, weapon_update);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x800891D0u, 0x00408021u, selected_weapon);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x800894FCu, 0xAE0201D4u, sniper_controls);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x8008A0E8u, 0xAE0200ACu, firearm_focal);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x8008ABACu, 0x1462002Cu, firearm_focal);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x8008C5D4u, 0x8FC20004u, tighten_reticle);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x8008D854u, 0x2C420191u, sniper_controls);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x8008D9D8u, 0x2484FF00u, sniper_controls);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x8008D9E4u, 0x00621823u, sniper_controls);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x8008DA00u, 0x00021180u, sniper_controls);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x8008E06Cu, 0x125E0059u, sniper_controls);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x80076CB8u, 0x86020222u, precise_shot);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x800481A0u, 0xAE080220u, scoped_origin);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x800481A4u, 0xAE090224u, scoped_origin);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x800481A8u, 0xAE0A0228u, scoped_origin);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x8008EB3Cu, 0x30420020u, sniper_controls);
    (void)psx_mod_register_instruction_plugin(PLUGIN_ID, 0x8008EB50u, 0x30420020u, sniper_controls);
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
    (void)psx_mod_register_instruction_plugin(
        PLUGIN_ID, 0x8008C1FCu, 0x104000FCu, native_reticle);
}
