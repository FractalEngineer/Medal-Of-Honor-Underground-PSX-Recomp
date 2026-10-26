#ifndef MOHU_VR_SHOT_H
#define MOHU_VR_SHOT_H

#include "mp_view.h"
#include <stdint.h>

/* Measured Underground MP overlay; reference constructor/basis strategy, with
 * Underground's +0x14 actor-layout shift. Never use these bindings in SP. */
#define MOHU_VR_SHOT_CONSTRUCTOR 0x800486D0u
#define MOHU_VR_SHOT_CONSTRUCTOR_SIZE 1052u
#define MOHU_VR_SHOT_CONSTRUCTOR_FNV 0x5F58030Bu
#define MOHU_VR_SHOT_BASIS 0x8006C8B0u
#define MOHU_VR_SHOT_BASIS_SIZE 260u
#define MOHU_VR_SHOT_BASIS_FNV 0x82E385D7u
#define MOHU_VR_SHOT_BASIS_CALL 0x800488D0u
#define MOHU_VR_SHOT_BASIS_CALL_WORD 0x0C01B22Cu
#define MOHU_VR_SHOT_BASIS_RA 0x800488D8u
#define MOHU_VR_SHOT_P38_TYPE 0x13F6u
#define MOHU_VR_SHOT_MAX_CAMERA_AGE 2257920u /* four NTSC VBlanks */
#define MOHU_VR_SHOT_CAMERA_MATRIX 0x800A2CECu /* loaded by native 80096AC8 */

typedef struct {
    uint32_t p1, owner, owner_class, owner_input, weapon_id;
    uint32_t shot, argument, type, caller, camera_owner;
    uint64_t cycle, camera_cycle;
    int replay, camera_valid, code_valid, multiplayer;
} MohuVrShotGuard;

static inline int mohu_vr_shot_guard(const MohuVrShotGuard* s) {
    return s && s->multiplayer && !s->replay && s->code_valid &&
           s->camera_valid && s->caller == MOHU_VR_SHOT_BASIS_RA &&
           mohu_vr_mp_actor_address(s->p1) && s->owner == s->p1 &&
           s->camera_owner == s->p1 && s->owner_class == 1u &&
           s->owner_input == s->owner + 0x400u && s->weapon_id == 0u &&
           mohu_vr_mp_actor_address(s->shot) && s->shot != s->owner &&
           s->argument == s->shot && s->type == MOHU_VR_SHOT_P38_TYPE &&
           s->cycle >= s->camera_cycle &&
           s->cycle - s->camera_cycle <= MOHU_VR_SHOT_MAX_CAMERA_AGE;
}

#endif
