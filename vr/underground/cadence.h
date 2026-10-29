#ifndef MOHU_VR_CADENCE_H
#define MOHU_VR_CADENCE_H
#include <stdint.h>

/* One additional fresh-pose view between native SP draws. Never advances a
 * native counter or makes more than one request per completed draw interval. */
typedef struct MohuVrCadence {
    uint32_t tick,owner,generation,ready;
} MohuVrCadence;
static inline void mohu_vr_cadence_arm(MohuVrCadence *s,uint32_t tick,
                                     uint32_t owner,uint32_t generation) {
    *s=(MohuVrCadence){tick,owner,generation,1};
}
static inline int mohu_vr_cadence_take(MohuVrCadence *s,uint32_t tick,
                                     uint32_t owner,uint32_t generation) {
    if(!s->ready) return 0;
    uint32_t elapsed=tick-s->tick;
    if(owner!=s->owner || generation!=s->generation || elapsed>2u) {
        s->ready=0;return 0;
    }
    if(!elapsed) return 0;
    s->ready=0;return 1;
}
#endif
