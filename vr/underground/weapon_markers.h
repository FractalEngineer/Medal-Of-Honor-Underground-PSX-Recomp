#ifndef MOHU_VR_WEAPON_MARKERS_H
#define MOHU_VR_WEAPON_MARKERS_H

#include "weapon.h"
#include <string.h>

#define MOHU_VR_MARKER_VERTEX_LIMIT 64u
#define MOHU_VR_MARKER_MAX_AGE 2257920u /* Four NTSC VBlanks; measured at shots. */

typedef struct {
    uint8_t id, counts[3]; /* grip, tip, axis-base; zero base aliases grip */
    uint16_t vertices[MOHU_VR_MARKER_VERTEX_LIMIT][2]; /* node, index */
} MohuVrMarkerGroup;

/* Measured W3.4 groups; P38 axis-base uses its complete barrel's rear ring.
 * Other axes are provisional grip-to-tip marker axes, not measured bore axes. */
#include "weapon_marker_groups.inc"

typedef struct {
    uint32_t owner, input, object, id, geometry_fnv32, generation;
} MohuVrMarkerKey;

typedef struct {
    MohuVrMarkerKey key;
    uint64_t cycle;
    uint32_t sequence, vertex_count;
    int valid;
    int16_t vertices[MOHU_VR_MARKER_VERTEX_LIMIT][3];
    double points[3][3];
} MohuVrMarkerSample;

static inline const MohuVrMarkerGroup* mohu_vr_marker_group(unsigned id) {
    for (unsigned i=0; i<sizeof k_marker_groups/sizeof k_marker_groups[0]; ++i)
        if (k_marker_groups[i].id == id) return &k_marker_groups[i];
    return NULL;
}

static inline int mohu_vr_marker_points(const MohuVrMarkerGroup* group,
    const int16_t vertices[][3], unsigned count, double points[3][3]) {
    if (!group || !vertices || !points || !group->counts[0] || !group->counts[1] ||
        count > MOHU_VR_MARKER_VERTEX_LIMIT ||
        count != (unsigned)group->counts[0]+group->counts[1]+group->counts[2]) return 0;
    double result[3][3]={{0}};
    unsigned offset=0;
    for (unsigned g=0; g<3; ++g) {
        if (!group->counts[g]) {
            memcpy(result[g],result[0],sizeof result[g]);
            continue;
        }
        for (unsigned i=0; i<group->counts[g]; ++i,++offset)
            for (unsigned axis=0; axis<3; ++axis)
                result[g][axis]+=(double)vertices[offset][axis]/group->counts[g];
    }
    memcpy(points,result,sizeof result);
    return 1;
}

static inline int mohu_vr_marker_usable(const MohuVrMarkerSample* sample,
    const MohuVrMarkerKey* current, uint64_t cycle) {
    return sample && current && sample->valid &&
        current->owner >= 0x800B0000u && current->owner <= 0x801FC000u &&
        current->input == current->owner+0x400u &&
        current->object == current->input+MOHU_VR_WEAPON_FP_INPUT_OFFSET &&
        current->geometry_fnv32 && mohu_vr_marker_group(current->id) &&
        sample->key.owner == current->owner && sample->key.input == current->input &&
        sample->key.object == current->object && sample->key.id == current->id &&
        sample->key.geometry_fnv32 == current->geometry_fnv32 &&
        sample->key.generation == current->generation &&
        cycle >= sample->cycle && cycle-sample->cycle <= MOHU_VR_MARKER_MAX_AGE;
}

#endif
