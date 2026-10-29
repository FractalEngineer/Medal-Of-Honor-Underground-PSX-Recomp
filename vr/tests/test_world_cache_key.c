#include "world_cache_key.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    PSXModRenderView a={0},b={0};a.struct_size=b.struct_size=sizeof a;
    a.precise=b.precise=1;a.projection=b.projection=1;a.fx_q16=b.fx_q16=100;
    assert(mohu_vr_same_view(&a,&b));
    b.translation_precise[0]=-0.0;assert(mohu_vr_same_view(&a,&b));
    b.translation_precise[0]=0.00001;assert(!mohu_vr_same_view(&a,&b));
    b=a;b.rotation[0]=NAN;assert(!mohu_vr_same_view(&a,&b));
    b=a;b.fx_q16++;assert(!mohu_vr_same_view(&a,&b));
    b=a;b.projection_h_ref++;assert(!mohu_vr_same_view(&a,&b));
    b=a;b.rotation_q12[0]++;assert(!mohu_vr_same_view(&a,&b));
    b=a;b.translation[0]++;assert(!mohu_vr_same_view(&a,&b));
    assert(!mohu_vr_same_view(NULL,&b));
    puts("world cache exact numeric pose/projection guards passed");
}
