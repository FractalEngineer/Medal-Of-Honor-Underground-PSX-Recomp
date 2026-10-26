#include "shot.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    const uint32_t single[] = {0u, 5u, 8u, 9u, 12u};
    const uint32_t repeating[] = {1u, 4u, 16u, 17u};
    for (unsigned i = 0; i < sizeof single / sizeof single[0]; ++i) {
        assert(mohu_vr_shot_type(single[i]) == MOHU_VR_SHOT_TYPE_SINGLE);
        assert(mohu_vr_shot_family(mohu_vr_shot_type(single[i])) ==
               MOHU_VR_SHOT_FAMILY_SINGLE);
    }
    for (unsigned i = 0; i < sizeof repeating / sizeof repeating[0]; ++i) {
        assert(mohu_vr_shot_type(repeating[i]) ==
               MOHU_VR_SHOT_TYPE_REPEATING);
        assert(mohu_vr_shot_family(mohu_vr_shot_type(repeating[i])) ==
               MOHU_VR_SHOT_FAMILY_REPEATING);
    }
    assert(mohu_vr_shot_type(10u) == MOHU_VR_SHOT_TYPE_THROWN);
    assert(mohu_vr_shot_type(15u) == MOHU_VR_SHOT_TYPE_THROWN);
    assert(mohu_vr_shot_family(mohu_vr_shot_type(10u)) ==
           MOHU_VR_SHOT_FAMILY_THROWN);
    assert(mohu_vr_shot_type(13u) == MOHU_VR_SHOT_TYPE_ROCKET);
    assert(mohu_vr_shot_family(mohu_vr_shot_type(13u)) ==
           MOHU_VR_SHOT_FAMILY_ROCKET);
    assert(mohu_vr_shot_type(14u) == MOHU_VR_SHOT_TYPE_BOLT);
    assert(mohu_vr_shot_family(mohu_vr_shot_type(14u)) ==
           MOHU_VR_SHOT_FAMILY_BOLT);
    assert(mohu_vr_shot_type(2u) == 0u);
    assert(mohu_vr_shot_type(3u) == 0u);
    assert(mohu_vr_shot_type(6u) == 0u);
    assert(mohu_vr_shot_type(7u) == 0u);
    assert(mohu_vr_shot_type(11u) == 0u);
    assert(mohu_vr_shot_type(255u) == 0u);
    assert(mohu_vr_shot_family(0u) == MOHU_VR_SHOT_FAMILY_UNKNOWN);
    assert(mohu_vr_shot_family(MOHU_VR_SHOT_TYPE_BOLT + 1u) ==
           MOHU_VR_SHOT_FAMILY_UNKNOWN);

    const MohuVrShotGuard good = {
        .p1=0x801483D0u, .owner=0x801483D0u, .owner_class=1u,
        .owner_input=0x801487D0u, .weapon_id=0u,
        .shot=0x801103C0u, .argument=0x801103C0u,
        .type=MOHU_VR_SHOT_P38_TYPE, .caller=MOHU_VR_SHOT_BASIS_RA,
        .camera_owner=0x801483D0u, .cycle=3000000u, .camera_cycle=2900000u,
        .replay=0, .camera_valid=1, .code_valid=1, .multiplayer=1,
    };
    assert(mohu_vr_shot_guard(&good));
    assert(!mohu_vr_shot_guard(NULL));
#define REJECT(field, value) do { MohuVrShotGuard s=good; s.field=value; \
    assert(!mohu_vr_shot_guard(&s)); } while (0)
    REJECT(owner, 0x80145810u); /* live P2 contract */
    REJECT(owner_class, 2u);   /* non-player/NPC class */
    REJECT(owner_input, 0x801487D4u);
    REJECT(weapon_id, 1u);
    REJECT(shot, good.owner);
    REJECT(argument, 0x80128430u);
    REJECT(type, MOHU_VR_SHOT_P38_TYPE + 1u);
    REJECT(caller, MOHU_VR_SHOT_BASIS_RA + 4u);
    REJECT(camera_owner, 0x80145810u);
    REJECT(camera_cycle, good.cycle + 1u); /* load/time reversal */
    REJECT(camera_cycle, good.cycle - MOHU_VR_SHOT_MAX_CAMERA_AGE - 1u);
    REJECT(replay, 1);
    REJECT(camera_valid, 0);
    REJECT(code_valid, 0);
    REJECT(multiplayer, 0);
#undef REJECT
    puts("native shot families and ownership/freshness: PASS (17 controls)");
    return 0;
}
