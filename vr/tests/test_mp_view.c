#include "mp_view.h"

#include <assert.h>
#include <stdio.h>

int main(void) {
    const MohuVrMpState native = {
        .index = 1, .width = 512, .height = 120, .focal = 400,
        .camera = 0x8014A450u, .camera_input = 0x8014A850u,
        .camera_class = 2, .camera_owner = 0x801483D0u,
        .player = 0x801483D0u, .player_input = 0x801487D0u,
        .player_class = 1, .scene = 0x8014A450u,
    };
    assert(mohu_vr_mp_state_valid(&native));
    assert(!mohu_vr_mp_state_valid(NULL));
    MohuVrMpState wrong = native;
    wrong.camera_owner = 0x80145810u; /* Native P2, not the selected P1. */
    assert(!mohu_vr_mp_state_valid(&wrong));

    MohuVrMpInputState input = {
        0x80100000u, 0x80101000u, 0x80101000u,
        0x80100400u, 0x80101400u, 1u, 1u, 512u, 120u, 400u,
    };
    assert(mohu_vr_mp_input_state_valid(&input));
    assert(!mohu_vr_mp_input_state_valid(NULL));
    MohuVrMpInputState input_wrong = input;
    input_wrong.width = 640u;
    assert(!mohu_vr_mp_input_state_valid(&input_wrong));
    input_wrong = input;
    input_wrong.current_player = 0x80102000u;
    assert(!mohu_vr_mp_input_state_valid(&input_wrong));
    input_wrong = input;
    input_wrong.player_class = 2u;
    assert(!mohu_vr_mp_input_state_valid(&input_wrong));
    input_wrong = input;
    input_wrong.other_class = 2u;
    assert(!mohu_vr_mp_input_state_valid(&input_wrong));
    input_wrong = input;
    input_wrong.player_input += 4u;
    assert(!mohu_vr_mp_input_state_valid(&input_wrong));
    input_wrong = input;
    input_wrong.player = 0x1000u;
    assert(!mohu_vr_mp_input_state_valid(&input_wrong));
    input_wrong = input;
    input_wrong.other_player = input.player;
    assert(!mohu_vr_mp_input_state_valid(&input_wrong));
    wrong = native; wrong.index = 2;
    assert(!mohu_vr_mp_state_valid(&wrong));
    wrong = native; wrong.height = 240;
    assert(!mohu_vr_mp_state_valid(&wrong));
    wrong = native; wrong.focal = 133;
    assert(!mohu_vr_mp_state_valid(&wrong));
    wrong = native; wrong.player_input = native.player + 0x39Cu;
    assert(!mohu_vr_mp_state_valid(&wrong));
    wrong = native; wrong.camera_class = 1;
    assert(!mohu_vr_mp_state_valid(&wrong));
    wrong = native; wrong.scene = 0x801FC004u;
    assert(!mohu_vr_mp_state_valid(&wrong));
    wrong = native; wrong.camera += 2u;
    assert(!mohu_vr_mp_state_valid(&wrong));
    puts("PASS: MP view ownership, mode, projection and pointer guards");
    return 0;
}
