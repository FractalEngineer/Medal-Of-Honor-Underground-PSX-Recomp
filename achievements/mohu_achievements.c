#include "mod_plugins.h"
#include "mohu_achievements_state.h"
#include "rl_achievements.h"

#include <stdint.h>

#define PLUGIN_ID "mohu.achievements"
#define MOHU_RECOMP_ID "medal-of-honor-underground-psx-recomp"

/* Verified in controls/mouse_keyboard/moh_mkb.c and vr/underground/vr_diagnostic.c. */
#define SP_PLAYER_ROOT 0x800AA17Cu
#define SP_PLAYER_INPUT_OFFSET 0x3FCu
#define SP_PLAYER_CLASS 1u
#define SP_GAMEPLAY_ACTIVE 0x800A0480u
#define PLAYER_HEALTH_OFFSET 0x10Au
#define INPUT_WEAPON_OFFSET 93u

#ifndef PSX_GAME_VERSION
#define PSX_GAME_VERSION "dev"
#endif

static MohuAchievementsState achievements;
static int initialized;
static int casual_sent;

/* rcheevos asks for console addresses. Main RAM is mirrored at 0x80000000;
 * accept the physical 2 MiB range too, and refuse scratchpad/BIOS ranges so a
 * bad list reads as broken instead of wrapping into unrelated memory. */
static uint32_t read_psx_ram(uint32_t address, uint8_t* buffer,
                             uint32_t num_bytes, void* user) {
    (void)user;
    if (!buffer || num_bytes == 0) return 0;
    uint32_t base;
    if (address >= 0x80000000u && address < 0x80200000u)
        base = address & 0x1FFFFFu;
    else if (address < 0x00200000u)
        base = address;
    else
        return 0;
    if (num_bytes > 0x200000u - base) return 0;
    for (uint32_t i = 0; i < num_bytes; ++i)
        buffer[i] = psx_mod_read_byte(0x80000000u | (base + i));
    return num_bytes;
}

static void emit_event(const char* event, void* user) {
    (void)user;
    if (event && event[0]) rl_ach_event(event);
}

static void sample(void) {
    int health = -1;
    int weapon = -1;
    const uint32_t player = psx_mod_read_word(SP_PLAYER_ROOT);
    if (player >= 0x800B0000u && player <= 0x801FC000u && (player & 3u) == 0 &&
        psx_mod_read_word(player + 8u) == SP_PLAYER_CLASS) {
        const uint32_t input = psx_mod_read_word(player + 0x39Cu);
        if (input == player + SP_PLAYER_INPUT_OFFSET) {
            health = (int)(int16_t)psx_mod_read_half(player + PLAYER_HEALTH_OFFSET);
            weapon = (int)psx_mod_read_byte(input + INPUT_WEAPON_OFFSET);
        }
    }
    mohu_achievements_state_sample(
        &achievements, psx_mod_read_word(SP_GAMEPLAY_ACTIVE) != 0u,
        health, weapon, emit_event, 0);
}

static void frame(void) {
    if (!initialized) return;
    rl_ach_frame();
    sample();
}

static void activate(void) {
    if (!initialized) {
        rl_ach_set_info(MOHU_RECOMP_ID, PSX_GAME_VERSION);
        (void)rl_ach_init("psx", read_psx_ram, 0);
        initialized = 1;
    }
    mohu_achievements_state_reset(&achievements);
    casual_sent = 0;
}

static void session_reset(void) {
    mohu_achievements_state_reset(&achievements);
    casual_sent = 0;
}

static void savestate_restored(void) {
    rl_ach_save_loaded();
    if (!casual_sent) {
        rl_ach_casual("save_state");
        casual_sent = 1;
    }
    mohu_achievements_state_reset(&achievements);
}

PSX_MOD_CONSTRUCTOR(register_mohu_achievements) {
    (void)psx_mod_register_activation_plugin(PLUGIN_ID, activate);
    (void)psx_mod_register_session_reset_plugin(PLUGIN_ID, session_reset);
    (void)psx_mod_register_savestate_plugin(PLUGIN_ID, savestate_restored);
    (void)psx_mod_register_vblank_plugin(PLUGIN_ID, frame);
}
