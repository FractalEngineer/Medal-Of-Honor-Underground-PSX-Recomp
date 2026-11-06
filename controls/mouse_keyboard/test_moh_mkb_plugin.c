/* Exercise the real plugin against controlled host/guest services. */
#include "psx_keybinds.h"
#include <stdio.h>
#include <string.h>

static uint8_t keys[SDL_NUM_SCANCODES];
static uint32_t mouse_buttons;
static uint32_t test_mouse(float* x, float* y) {
    (void)x; (void)y; return mouse_buttons;
}
static const uint8_t* test_keyboard(int* count) {
    if (count) *count = SDL_NUM_SCANCODES;
    return keys;
}
#undef SDL_GetKeyboardState
#define SDL_GetKeyboardState test_keyboard
#undef SDL_GetMouseState
#define SDL_GetMouseState test_mouse
#include "moh_mkb.c"

static uint32_t test_player = 0x800F0BE0u;
static uint32_t test_pause, test_split, test_vr, test_weapon;
static uint32_t test_mode = 7;
static uint32_t registered_adjust[8];
static unsigned registered_adjust_count;
static PSXModPadTransform installed_transform;
static PSXModActivationCallback on_activate, on_reset, on_frame;
static PSXModMousePolicy installed_mouse;
static PsxPlayerBinds installed_profile;
static uint8_t suppressed_keys[PSXKB_MOUSE_SC_BASE + 6];
static const char *override_id, *override_value;
static int test_started = 1;
int g_psx_render_pass_active;

void psx_mod_write_word(uint32_t address, uint32_t value) { (void)address; (void)value; }
void psx_mod_write_half(uint32_t address, uint16_t value) { (void)address; (void)value; }
int psx_mod_option_value(const char* package, const char* feature,
        const char* option, char* out, uint32_t size) {
    (void)package; (void)feature;
    if (override_id && !strcmp(option, override_id)) {
        snprintf(out, size, "%s", override_value); return 1;
    }
    if (size) out[0] = 0;
    return 0;
}
int psx_mod_register_option_changed_plugin(const char* id, PSXModOptionChangedCallback fn) {
    (void)id; (void)fn; return 1;
}
uint32_t psx_mod_call_guest(CPUState* cpu, uint32_t fn, uint32_t ra,
        uint32_t a0, uint32_t a1, uint32_t a2, uint32_t a3) {
    (void)cpu; (void)fn; (void)ra; (void)a0; (void)a1; (void)a2; (void)a3;
    return 0;
}
int psx_mod_register_savestate_plugin(const char* id, PSXModActivationCallback fn) {
    (void)id; (void)fn; return 1;
}
int psx_mod_register_function_entry_plugin(const char* id, uint32_t addr, PSXModFunctionEntryCallback fn) {
    (void)id; (void)addr; (void)fn; return 1;
}
int psx_mod_register_function_filter_plugin(const char* id, uint32_t addr, PSXModFunctionFilterCallback fn) {
    (void)id; (void)addr; (void)fn; return 1;
}
int psx_mod_register_command(const char* name, PSXModCommandFn fn) {
    (void)name; (void)fn; return 1;
}

int psx_mod_game_started(void) { return test_started; }
int psx_openxr_session_active(void) { return (int)test_vr; }
uint32_t psx_mod_read_word(uint32_t address) {
    if (address == SP_PLAYER_ROOT) return test_player;
    if (address == MP_PLAYER2_ROOT) return test_split ? 0x80100000u : 0;
    if (address == 0x80100008u) return 1;
    if (address == 0x8010039Cu) return 0x80100400u;
    if (address == test_player + 8u) return 1;
    if (address == test_player + 0x39Cu) return test_player + SP_PLAYER_INPUT_OFFSET;
    if (address == test_player + SP_PLAYER_INPUT_OFFSET + 0x1D4u) return test_mode;
    if (address == SP_PAUSE) return test_pause;
    return 0;
}
uint8_t psx_mod_read_byte(uint32_t address) {
    return address == test_player + SP_PLAYER_INPUT_OFFSET + 93u ? (uint8_t)test_weapon : 0;
}
uint16_t psx_mod_read_half(uint32_t address) { (void)address; return 0xFFFFu; }
int psx_keybinds_set_session_player(int player, const PsxPlayerBinds* binds) {
    if (binds) installed_profile = *binds;
    return player == 1 && binds != NULL;
}
void psx_keybinds_clear_session_players(void) {}
void psx_keybinds_suppress_control(int player, SDL_Scancode sc) {
    (void)player; suppressed_keys[sc] = 1;
}
void psx_keybinds_release_control(int player, SDL_Scancode sc) {
    (void)player; suppressed_keys[sc] = 0;
}
int psx_keybinds_control_suppressed(int player, SDL_Scancode sc) {
    (void)player; return suppressed_keys[sc];
}
void psx_keybinds_host_keys(const uint8_t* input, uint8_t out[SDL_NUM_SCANCODES]) {
    for (unsigned i = 0; i < SDL_NUM_SCANCODES; ++i)
        out[i] = input && !suppressed_keys[i] ? input[i] : 0;
}
int psx_mod_set_controller_mode_override(uint32_t player, uint32_t mode) {
    return player == 0 && mode == PSX_MOD_CONTROLLER_ANALOG;
}
int psx_mod_set_pad_transform(uint32_t player, const PSXModPadTransform* transform) {
    (void)player;
    if (transform) installed_transform = *transform;
    else memset(&installed_transform, 0, sizeof installed_transform);
    return 1;
}
int psx_mod_set_local_mouse_policy(const PSXModMousePolicy* policy) {
    installed_mouse = *policy; return 1;
}
int psx_mod_set_local_mouse_persistent_capture(int enabled) { (void)enabled; return 1; }
int psx_mod_set_local_mouse_capture_across_transitions(int enabled) { (void)enabled; return 1; }
void psx_mod_counter_add(const char* name, uint32_t count) { (void)name; (void)count; }
int psx_mod_register_activation_plugin(const char* id, PSXModActivationCallback fn) {
    (void)id; on_activate = fn; return 1;
}
int psx_mod_register_session_reset_plugin(const char* id, PSXModActivationCallback fn) {
    (void)id; on_reset = fn; return 1;
}
int psx_mod_register_vblank_plugin(const char* id, PSXModVBlankCallback fn) {
    (void)id; on_frame = fn; return 1;
}
int psx_mod_register_instruction_plugin(const char* id, uint32_t addr,
        uint32_t expected, PSXModFunctionEntryCallback fn) {
    (void)id;
    if (fn == direct_adjust && addr != 0x8008F984u && registered_adjust_count < 8)
        registered_adjust[registered_adjust_count++] = addr;
    return addr == 0x8008C1B4u && expected == 0x30420020u;
}

#define CHECK(value) do { if (!(value)) { \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #value); return 1; \
} } while (0)

static uint32_t transformed_buttons(void) {
    PSXModPadFrame frame = {.struct_size = sizeof(frame), .buttons = 0xBDFFu};
    PSXModPadOutput out = {.struct_size = sizeof(out), .buttons = frame.buttons};
    installed_transform.transform(&frame, &out);
    return out.buttons;
}

int main(void) {
    CHECK(on_activate && on_reset);
    CHECK(direct_mode_supported(9)); /* Petrol bomb / throwable native look. */
    CHECK(!direct_mode_supported(6));
    on_activate();
    CHECK(active && installed_transform.transform);
    CHECK(registered_adjust_count == 8);
    CPUState cpu = {0};
    cpu.gpr[22] = test_player;
    cpu.gpr[19] = test_player + SP_PLAYER_INPUT_OFFSET;
    mouse_captured = 1;
    direct_player = test_player;
    unsigned near_wall_stores = 0;
    for (unsigned i = 0; i < registered_adjust_count; ++i) {
        cpu.gpr[2] = 0x123456u;
        direct_adjust(&cpu, registered_adjust[i]);
        CHECK(cpu.gpr[2] == 0);
        if (registered_adjust[i] == 0x8008E4A0u || registered_adjust[i] == 0x8008E4A8u ||
            registered_adjust[i] == 0x8008E4F4u) ++near_wall_stores;
    }
    CHECK(near_wall_stores == 3);
    test_mode = 6;
    cpu.gpr[2] = 0x123456u;
    direct_adjust(&cpu, 0x8008E4A0u);
    CHECK(cpu.gpr[2] == 0x123456u);
    test_mode = 7;
    restored();
    mouse_captured = 1;
    CHECK(transformed_buttons() == 0xBFFFu);
    CHECK(firearm_aiming(owned_player_input()));
    test_weapon = 10;
    CHECK(transformed_buttons() == 0xBFFFu);
    CHECK(!firearm_zooming(owned_player_input()));
    test_weapon = 5;
    CHECK(transformed_buttons() == 0xBDFFu);
    CHECK(!firearm_zooming(owned_player_input()));
    test_weapon = 0;
    restored();
    CHECK(!zoom_held && !firearm_zooming(owned_player_input()));
    /* Final input has physical R2 and fire asserted: only R2 is released. */
    CHECK(transformed_buttons() == 0xBFFFu);
    test_weapon = SNIPER_WEAPON_ID;
    CHECK(transformed_buttons() == 0xBDFFu);
    test_weapon = 0; test_pause = 1;
    CHECK(transformed_buttons() == 0xBDFFu);
    CHECK(on_frame);
    on_frame();
    CHECK(installed_profile.triangle == SDL_SCANCODE_UNKNOWN);
    CHECK(installed_profile.circle == SDL_SCANCODE_UNKNOWN);
    CHECK(installed_profile.square == SDL_SCANCODE_UNKNOWN);
    keys[SDL_SCANCODE_W] = keys[SDL_SCANCODE_D] = 1;
    keys[SDL_SCANCODE_E] = keys[SDL_SCANCODE_Q] = 1;
    PSXModPadFrame menu_frame = {.struct_size = sizeof(menu_frame)};
    PSXModPadOutput menu = {.struct_size = sizeof(menu), .buttons = 0xFFFF,
                           .lx = 255, .ly = 0, .rx = 0, .ry = 255};
    CHECK(installed_transform.transform(&menu_frame, &menu));
    CHECK(menu.buttons == 0xAFCFu); /* Up + right + Cross + Triangle only. */
    CHECK(menu.lx == 128 && menu.ly == 128 && menu.rx == 128 && menu.ry == 128);
    test_pause = 0;
    on_frame();
    CHECK(suppressed_keys[SDL_SCANCODE_E] && suppressed_keys[SDL_SCANCODE_Q]);
    menu.buttons = 0xFFFF;
    CHECK(installed_transform.transform(&menu_frame, &menu));
    CHECK((menu.buttons & 0x8000u) != 0); /* Held menu E cannot become gameplay use. */
    memset(keys, 0, sizeof keys);
    on_frame();
    CHECK(!suppressed_keys[SDL_SCANCODE_E] && !suppressed_keys[SDL_SCANCODE_Q]);
    test_pause = 0;
    test_started = 0;
    CHECK(in_menu());
    test_started = 1;
    on_frame();
    CHECK(installed_profile.square == SDL_SCANCODE_UNKNOWN && installed_profile.circle == SDL_SCANCODE_UNKNOWN);
    test_pause = 0; test_split = 1;
    CHECK(!installed_mouse.eligible(0xFFFFu));
    test_split = 0; test_vr = 1;
    CHECK(!installed_mouse.eligible(0xFFFFu));
    test_vr = 0;
    CHECK(installed_mouse.eligible(0xFFFFu));
    CHECK(!installed_mouse.eligible(0xFFF7u));

    PSXModPadFrame frame = {.struct_size = sizeof(frame)};
    PSXModPadOutput state = {.struct_size = sizeof(state), .buttons = 0xFFFF,
                            .lx = 42, .ly = 128, .rx = 200, .ry = 128};
    CHECK(installed_transform.transform(&frame, &state));
    CHECK(state.lx == 42 && state.rx == 200);
    keys[SDL_SCANCODE_W] = keys[SDL_SCANCODE_D] = 1;
    CHECK(installed_transform.transform(&frame, &state));
    CHECK(state.lx == 128 && state.ly == 0 && state.rx == 255);
    keys[SDL_SCANCODE_A] = keys[SDL_SCANCODE_S] = 1;
    CHECK(installed_transform.transform(&frame, &state));
    CHECK(state.lx == 128 && state.ly == 128 && state.rx == 128);

    keys[SDL_SCANCODE_3] = 1;
    CHECK(installed_transform.transform(&frame, &state));
    CHECK(requested_slot == -1); /* Number keys belong to framework shortcuts. */
    requested_slot = -1;
    CHECK(installed_transform.transform(&frame, &state));
    CHECK(requested_slot == -1);

    memset(keys, 0, sizeof keys);
    PSXModMouseEvent acquired = {.struct_size = sizeof(acquired),
                                .type = PSX_MOD_MOUSE_ACQUIRED};
    installed_mouse.event(&acquired);
    keys[SDL_SCANCODE_A] = 1;

    PSXModMouseEvent wheel = {.struct_size = sizeof(wheel),
                             .type = PSX_MOD_MOUSE_WHEEL, .dy = -1};
    installed_mouse.event(&wheel);
    CHECK(wheel_steps == 1);
    wheel.dy = 1;
    installed_mouse.event(&wheel);
    CHECK(wheel_steps == 0);

    PSXModMouseEvent event = {.struct_size = sizeof(event),
        .type = PSX_MOD_MOUSE_MOTION, .dx = 90, .dy = 20};
    installed_mouse.event(&event);
    CHECK(installed_transform.transform(&frame, &state));
    CHECK(state.lx == 128 && state.rx == 128);
    PSXModMouseOutput strafe = {.struct_size = sizeof(strafe)};
    installed_mouse.sample(0, &strafe);
    CHECK(strafe.rx == 0 && strafe.ry == 128);
    /* Mouse displacement is retained for exactly one owned camera update;
     * sampling the pad does not turn it into capped analog-stick bytes. */
    int64_t yaw_delta, pitch_delta;
    mohu_mkb_mouse_take(&mouse, &yaw_delta, &pitch_delta);
    CHECK(yaw_delta == 90 * 65536 && pitch_delta == -20 * 65536);
    mohu_mkb_mouse_take(&mouse, &yaw_delta, &pitch_delta);
    CHECK(yaw_delta == 0 && pitch_delta == 0);
    event.type = PSX_MOD_MOUSE_RESET;
    installed_mouse.event(&event);
    PSXModMouseOutput output = {.struct_size = sizeof(output)};
    installed_mouse.sample(0, &output);
    CHECK(output.rx == 128 && output.ry == 128);
    CHECK(wheel_steps == 0 && requested_slot == -1);

    PSXModInputBindings parsed;
    CHECK(psx_mod_parse_input_bindings("key:511,mouse:5,wheel:up", &parsed));
    CHECK(parsed.count == 3 && parsed.input[2].code == 1);
    const char* invalid[] = {"", "key:0", "key:512", "key:01", "mouse:6", "wheel:left",
                            "none,", "none,none,none,none", "key: 2", "key:2x"};
    for (unsigned i = 0; i < sizeof(invalid) / sizeof(invalid[0]); ++i)
        CHECK(!psx_mod_parse_input_bindings(invalid[i], &parsed));
    CHECK(psx_mod_parse_input_bindings("none", &parsed));

    /* Rebinding removes the old source, survives refresh, and leaves the
     * temporary framework profile empty instead of retaining hidden aliases. */
    memset(keys, 0, sizeof keys);
    keys[SDL_SCANCODE_W] = 1;
    override_id = "bind_forward"; override_value = "key:12"; /* I */
    CHECK(sensitivity_changed(override_id, override_value));
    CHECK(suppressed_keys[SDL_SCANCODE_W]);
    keys[SDL_SCANCODE_W] = 0; on_frame();
    CHECK(!suppressed_keys[SDL_SCANCODE_W]);
    keys[SDL_SCANCODE_W] = 1;
    state.ly = state.rx = 128; state.buttons = 0xFFFF;
    CHECK(installed_transform.transform(&frame, &state) && state.ly == 128);
    keys[SDL_SCANCODE_W] = 0; keys[SDL_SCANCODE_I] = 1;
    state.ly = 128;
    CHECK(installed_transform.transform(&frame, &state) && state.ly == 0);
    test_pause = 1; on_frame();
    CHECK(suppressed_keys[SDL_SCANCODE_I]);
    keys[SDL_SCANCODE_I] = 0; on_frame();
    CHECK(!suppressed_keys[SDL_SCANCODE_I]);
    test_pause = 0; on_frame();
    override_id = "bind_fire"; override_value = "key:9"; /* F */
    CHECK(sensitivity_changed(override_id, override_value));
    mouse_buttons = 1; state.buttons = 0xFFFF;
    CHECK(installed_transform.transform(&frame, &state) && (state.buttons & 0x4000));
    mouse_buttons = 0; keys[SDL_SCANCODE_F] = 1; state.buttons = 0xFFFF;
    CHECK(installed_transform.transform(&frame, &state) && !(state.buttons & 0x4000));
    keys[SDL_SCANCODE_F] = 0; on_frame();
    override_id = "bind_fire"; override_value = "none";
    CHECK(sensitivity_changed(override_id, override_value));
    keys[SDL_SCANCODE_RETURN] = keys[SDL_SCANCODE_F] = 1; mouse_buttons = 1;
    state.buttons = 0xFFFF;
    CHECK(installed_transform.transform(&frame, &state) && (state.buttons & 0x4000));
    memset(keys, 0, sizeof keys); mouse_buttons = 0; on_frame();
    override_id = "bind_next_weapon"; override_value = "wheel:up";
    CHECK(sensitivity_changed(override_id, override_value));
    /* Both cycle actions may intentionally use the same direction; they cancel. */
    installed_mouse.event(&acquired); wheel.dy = 1; installed_mouse.event(&wheel);
    CHECK(wheel_steps == 0);
    override_id = "bind_prev_weapon"; override_value = "none";
    CHECK(sensitivity_changed(override_id, override_value));
    (void)psx_mod_parse_input_bindings("wheel:up", &bindings[NEXT_WEAPON]);
    installed_mouse.event(&wheel);
    CHECK(wheel_steps == 1);
    wheel.dy = -1; installed_mouse.event(&wheel);
    CHECK(wheel_steps == 1); /* Old wheel-down binding is gone. */

    override_id = NULL; refresh_bindings(); refresh_sensitivity();
    test_weapon = 0; zoom_amount = 0;
    CHECK(fabs(look_gain(owned_player_input()) - 0.5) < 1e-9);
    zoom_amount = 1;
    CHECK(fabs(look_gain(owned_player_input()) - 0.32) < 1e-9);
    override_id = "look_sensitivity"; override_value = "10";
    CHECK(sensitivity_changed(override_id, override_value));
    CHECK(mouse_gain == 1 && fabs(look_gain(owned_player_input()) - 0.32) < 1e-9);
    zoom_amount = 0;
    CHECK(look_gain(owned_player_input()) == 1);
    override_id = "aim_sensitivity"; override_value = "2";
    CHECK(sensitivity_changed(override_id, override_value));
    CHECK(look_gain(owned_player_input()) == 0.5);
    zoom_amount = 1;
    CHECK(fabs(look_gain(owned_player_input()) - 0.16) < 1e-9);
    on_reset();
    CHECK(!active && !installed_transform.transform);
    puts("mouse keyboard plugin: PASS");
    return 0;
}
