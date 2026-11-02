#ifndef MOHU_WORLD_CACHE_KEY_H
#define MOHU_WORLD_CACHE_KEY_H
#include "mod_plugins.h"
#include <math.h>
#include <string.h>

/* Exact numeric equality, not object-representation equality: +0 and -0
 * describe the same rigid pose, and structure padding is not camera state. */
static inline int mohu_vr_same_view(const PSXModRenderView *a,const PSXModRenderView *b) {
    if(!a || !b || a->struct_size!=b->struct_size || a->precise!=b->precise ||
       a->projection!=b->projection || a->projection_h_ref!=b->projection_h_ref ||
       a->fx_q16!=b->fx_q16 || a->fy_q16!=b->fy_q16 ||
       a->cx_delta_q16!=b->cx_delta_q16 || a->cy_delta_q16!=b->cy_delta_q16 ||
       memcmp(a->rotation_q12,b->rotation_q12,sizeof a->rotation_q12) ||
       memcmp(a->translation,b->translation,sizeof a->translation)) return 0;
    if(a->precise) {
        for(unsigned i=0;i<9;++i)
            if(!isfinite(a->rotation[i]) || a->rotation[i]!=b->rotation[i])return 0;
        for(unsigned i=0;i<3;++i)
            if(!isfinite(a->translation_precise[i]) || a->translation_precise[i]!=b->translation_precise[i])return 0;
    }
    return 1;
}
#endif
