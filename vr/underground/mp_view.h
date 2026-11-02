#ifndef MOHU_VR_MP_VIEW_H
#define MOHU_VR_MP_VIEW_H

#include <stdint.h>

#define MOHU_VR_MP_CONTEXT 0x800A0B08u
#define MOHU_VR_MP_FRAME 0x80054BC4u
#define MOHU_VR_MP_FRAME_CALL 0x80063CF0u
#define MOHU_VR_MP_FRAME_CALL_WORD 0x0C0152F1u
#define MOHU_VR_MP_FRAME_RA 0x80063CF8u
#define MOHU_VR_MP_SELECT 0x80054E68u
#define MOHU_VR_MP_SCENE 0x8006E9D8u
#define MOHU_VR_MP_SCENE_CALLBACK 0x8006C61Cu
#define MOHU_VR_MP_SELECTOR 0x80096EF4u
#define MOHU_VR_MP_SELECTOR_HELPER 0x80096AC8u
#define MOHU_VR_MP_SELECTOR_RESULT 0x80096F78u
#define MOHU_VR_MP_SELECTOR_RESULT_WORD 0x8FBF0020u
#define MOHU_VR_MP_CAMERA_ROOT 0x800A35B0u
#define MOHU_VR_MP_CAMERA_VIEW_ROOT 0x800A35C0u
#define MOHU_VR_MP_CURRENT_PLAYER 0x800A35C4u
#define MOHU_VR_MP_SCENE_ROOT 0x800A35CCu
#define MOHU_VR_MP_P1_ROOT 0x800A3604u
#define MOHU_VR_MP_NODE_CALLBACK 0x384u
#define MOHU_VR_MP_NODE_CENTER 0x2F4u
#define MOHU_VR_MP_NODE_RADIUS 0x2FCu
#define MOHU_VR_MP_CAMERA_VIEW_POINTER 0xC8u

typedef struct {
    uint32_t index, width, height, focal;
    uint32_t camera, camera_input, camera_class, camera_owner;
    uint32_t player, player_input, player_class, scene;
} MohuVrMpState;

typedef struct {
    uint32_t player, other_player, current_player;
    uint32_t player_input, other_input, player_class, other_class;
    uint32_t width, height, focal;
} MohuVrMpInputState;

static inline int mohu_vr_mp_actor_address(uint32_t address) {
    return address >= 0x800B0000u && address <= 0x801FC000u && !(address & 3u);
}

/* Input is sampled outside the render transaction, where the camera/frame
 * ownership used by the eye replay can be between updates. Bind MP input to
 * the current P1 actor and its fixed +0x400 input block instead. */
static inline int mohu_vr_mp_input_state_valid(
        const MohuVrMpInputState* state) {
    return state && state->width == 512u && state->height == 120u &&
           state->focal == 400u &&
           mohu_vr_mp_actor_address(state->player) &&
           mohu_vr_mp_actor_address(state->other_player) &&
           state->player != state->other_player &&
           (state->current_player == state->player ||
            state->current_player == state->other_player) &&
           state->player_class == 1u &&
           state->other_class == 1u &&
           state->player_input == state->player + 0x400u &&
           state->other_input == state->other_player + 0x400u;
}

/* Native 512x120 first-view contract, before any rollback-scoped write. */
static inline int mohu_vr_mp_state_valid(const MohuVrMpState* state) {
    return state && state->index <= 1u && state->width == 512u &&
           state->height == 120u && state->focal == 400u &&
           mohu_vr_mp_actor_address(state->camera) &&
           mohu_vr_mp_actor_address(state->player) &&
           mohu_vr_mp_actor_address(state->scene) &&
           state->player != state->camera && state->player_class == 1u &&
           state->camera_class == 2u &&
           state->player_input == state->player + 0x400u &&
           state->camera_input == state->camera + 0x400u &&
           state->camera_owner == state->player;
}

#endif
