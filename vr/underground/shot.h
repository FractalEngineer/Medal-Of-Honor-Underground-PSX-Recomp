#ifndef MOHU_VR_SHOT_H
#define MOHU_VR_SHOT_H

#include "mp_view.h"
#include <stdint.h>

/* Measured Underground MP overlay; reference constructor/basis strategy, with
 * Underground's +0x14 actor-layout shift. SP has a separate guarded basis
 * caller below even though the native basis function is shared. */
#define MOHU_VR_SHOT_CONSTRUCTOR 0x800486D0u
#define MOHU_VR_SHOT_CONSTRUCTOR_SIZE 1052u
#define MOHU_VR_SHOT_CONSTRUCTOR_FNV 0x5F58030Bu
#define MOHU_VR_SHOT_BASIS 0x8006C8B0u
#define MOHU_VR_SHOT_BASIS_SIZE 260u
#define MOHU_VR_SHOT_BASIS_FNV 0x82E385D7u
#define MOHU_VR_SHOT_BASIS_CALL 0x800488D0u
#define MOHU_VR_SHOT_BASIS_CALL_WORD 0x0C01B22Cu
#define MOHU_VR_SHOT_BASIS_RA 0x800488D8u
#define MOHU_VR_SP_SHOT_BASIS 0x80076C28u
#define MOHU_VR_SP_SHOT_BASIS_CALL 0x80048604u
#define MOHU_VR_SP_SHOT_BASIS_CALL_WORD 0x0C01DB0Au
#define MOHU_VR_SP_SHOT_BASIS_CALL_RA 0x8004860Cu
#define MOHU_VR_SHOT_THROW_FLOW 0x8008468Cu
#define MOHU_VR_SHOT_THROW_FLOW_SIZE 0x750u
#define MOHU_VR_SHOT_THROW_FLOW_FNV 0xE77DB501u
#define MOHU_VR_SHOT_GRENADE_STAGE 0x80084CDCu
#define MOHU_VR_SHOT_GRENADE_STAGE_WORD 0x0C0145EDu
#define MOHU_VR_SHOT_PETROL_STAGE 0x80084B74u
#define MOHU_VR_SHOT_PETROL_STAGE_WORD 0xAE2B026Cu
#define MOHU_VR_SHOT_ROCKET_STAGE 0x80048AACu
#define MOHU_VR_SHOT_ROCKET_STAGE_WORD 0x8E090220u
#define MOHU_VR_SHOT_P38_TYPE 0x13F6u
#define MOHU_VR_SHOT_TYPE_ROCKET 0x13F1u
#define MOHU_VR_SHOT_TYPE_THROWN 0x13F3u
#define MOHU_VR_SHOT_TYPE_SINGLE 0x13F6u
#define MOHU_VR_SHOT_TYPE_REPEATING 0x13F7u
#define MOHU_VR_SHOT_TYPE_BOLT 0x13FAu
#define MOHU_VR_SHOT_MAX_CAMERA_AGE 2257920u /* four NTSC VBlanks */
#define MOHU_VR_SHOT_CAMERA_MATRIX 0x800A2CECu /* loaded by native 80096AC8 */

typedef enum {
    MOHU_VR_SHOT_FAMILY_UNKNOWN = 0,
    MOHU_VR_SHOT_FAMILY_ROCKET,
    MOHU_VR_SHOT_FAMILY_THROWN,
    MOHU_VR_SHOT_FAMILY_SINGLE,
    MOHU_VR_SHOT_FAMILY_REPEATING,
    MOHU_VR_SHOT_FAMILY_BOLT,
} MohuVrShotFamily;

typedef struct {
    uint32_t p1, owner, owner_class, owner_input, weapon_id;
    uint32_t shot, argument, type, caller, camera_owner;
    uint64_t cycle, camera_cycle;
    int replay, camera_valid, code_valid, multiplayer;
} MohuVrShotGuard;

/* Measured on copied MP cycles 1-4 with the shared basis caller above. */
static inline uint16_t mohu_vr_shot_type(uint32_t weapon_id) {
    switch (weapon_id) {
    case 0u: case 5u: case 8u: case 9u: case 12u:
        return MOHU_VR_SHOT_TYPE_SINGLE;
    case 1u: case 4u: case 16u: case 17u:
        return MOHU_VR_SHOT_TYPE_REPEATING;
    case 10u: case 15u:
        return MOHU_VR_SHOT_TYPE_THROWN;
    case 13u:
        return MOHU_VR_SHOT_TYPE_ROCKET;
    case 14u:
        return MOHU_VR_SHOT_TYPE_BOLT;
    default:
        return 0u;
    }
}

static inline MohuVrShotFamily mohu_vr_shot_family(uint32_t type) {
    switch (type) {
    case MOHU_VR_SHOT_TYPE_ROCKET: return MOHU_VR_SHOT_FAMILY_ROCKET;
    case MOHU_VR_SHOT_TYPE_THROWN: return MOHU_VR_SHOT_FAMILY_THROWN;
    case MOHU_VR_SHOT_TYPE_SINGLE: return MOHU_VR_SHOT_FAMILY_SINGLE;
    case MOHU_VR_SHOT_TYPE_REPEATING:
        return MOHU_VR_SHOT_FAMILY_REPEATING;
    case MOHU_VR_SHOT_TYPE_BOLT: return MOHU_VR_SHOT_FAMILY_BOLT;
    default: return MOHU_VR_SHOT_FAMILY_UNKNOWN;
    }
}

/* SP uses the same family types at 80048604 -> 80076C28. P38 and Sten are
 * observed live. The rocket is admitted separately below after its SP basis
 * call; thrown families remain native until their final-origin path is bound. */
static inline int mohu_vr_sp_firearm_type_valid(uint32_t id, uint32_t type) {
    const uint32_t expected = mohu_vr_shot_type(id);
    return expected == type &&
           (type == MOHU_VR_SHOT_TYPE_SINGLE ||
            type == MOHU_VR_SHOT_TYPE_REPEATING ||
            type == MOHU_VR_SHOT_TYPE_BOLT);
}

/* The rocket enters the same measured SP basis seam before its final origin
 * adjustment. Thrown families remain excluded until their SP constructor and
 * release path are bound independently. */
static inline int mohu_vr_sp_tracked_type_valid(uint32_t id, uint32_t type) {
    const uint32_t expected = mohu_vr_shot_type(id);
    return expected == type &&
           (type == MOHU_VR_SHOT_TYPE_SINGLE ||
            type == MOHU_VR_SHOT_TYPE_REPEATING ||
            type == MOHU_VR_SHOT_TYPE_BOLT ||
            type == MOHU_VR_SHOT_TYPE_ROCKET);
}

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

/* W5.3d candidate guard. Unlike the retained P38 guard above, this admits only
 * the 13 measured IDs and requires the live native type to match that ID. */
static inline int mohu_vr_family_shot_guard(const MohuVrShotGuard* s) {
    if (!s || !s->multiplayer || s->replay || !s->code_valid ||
        !s->camera_valid || s->caller != MOHU_VR_SHOT_BASIS_RA ||
        !mohu_vr_mp_actor_address(s->p1) || s->owner != s->p1 ||
        s->camera_owner != s->p1 || s->owner_class != 1u ||
        s->owner_input != s->owner + 0x400u ||
        s->weapon_id >= 256u ||
        !mohu_vr_mp_actor_address(s->shot) || s->shot == s->owner ||
        s->argument != s->shot ||
        s->type != mohu_vr_shot_type(s->weapon_id) ||
        s->cycle < s->camera_cycle ||
        s->cycle - s->camera_cycle > MOHU_VR_SHOT_MAX_CAMERA_AGE) {
        return 0;
    }
    return s->type != 0u;
}

#endif
