#ifndef MOHU_VR_WEAPON_H
#define MOHU_VR_WEAPON_H

#include "mod_plugins.h"

#include <stddef.h>
#include <stdint.h>

/*
 * The multiplayer fixture roots point at the player actor. The first-person
 * model object is at actor + 0x4AC. Its 22-node table is shared by the measured
 * multiplayer weapon IDs, while the selected weapon data is referenced through
 * the object's per-frame geometry state.
 */
#define MOHU_VR_WEAPON_OBJECT_OFFSET 0x4ACu
#define MOHU_VR_WEAPON_UPDATE_ADDR 0x800892E8u
#define MOHU_VR_WEAPON_UPDATE_WORD 0x27BDFFB8u
#define MOHU_VR_WEAPON_UPDATE_LEAVE_ADDR 0x80089D30u
#define MOHU_VR_WEAPON_UPDATE_LEAVE_WORD 0x8FBF0040u
#define MOHU_VR_WEAPON_OBJECT_UPDATE_RA 0x8008A7C8u
#define MOHU_VR_WEAPON_SP_OBJECT_OFFSET 0x1E0u
#define MOHU_VR_WEAPON_SP_RENDER_ADDR 0x8007A554u
#define MOHU_VR_WEAPON_SP_RENDER_WORD 0x27BDFF68u
#define MOHU_VR_WEAPON_SP_RENDER_LEAVE_ADDR 0x8007A7F0u
#define MOHU_VR_WEAPON_SP_RENDER_LEAVE_WORD 0x8FBF0090u
#define MOHU_VR_WEAPON_NODE_COUNT 22u

typedef struct {
    uint8_t id;
    uint8_t source_slot;
    uint8_t source_switch;
    const char* name;
} MohuVrWeaponProfile;

size_t mohu_vr_weapon_profile_count(void);
const MohuVrWeaponProfile* mohu_vr_weapon_profile_at(size_t index);
const MohuVrWeaponProfile* mohu_vr_weapon_profile_find(uint8_t id);
int mohu_vr_weapon_node_layout_valid(const uint16_t counts[22],
                                     unsigned count);

/*
 * Build an experimental render-only camera-space attachment around the measured
 * native object origin. The result preserves the caller's projection and
 * changes only rotation/translation. Invalid or stale tracking returns zero.
 * Applying this at the current single-player draw wrapper is not accepted:
 * the later model projection does not consume that temporary view override.
 */
int mohu_vr_weapon_track_view(const PSXModOpenXRHands* hands,
                              const PSXModRenderView* base,
                              double units_per_meter,
                              const double pivot[3],
                              PSXModRenderView* out);

#endif
