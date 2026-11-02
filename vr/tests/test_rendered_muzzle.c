#include "rendered_muzzle.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    const uint32_t control[8]={8192u,2048u,4096u,0,4096u,10u,20u,30u};
    PSXModRenderView view={0}; view.struct_size=sizeof view;
    view.precise=1;
    view.rotation[2]=1; view.rotation[4]=1; view.rotation[6]=-1;
    view.translation_precise[0]=3; view.translation_precise[1]=4;
    const double points[3][3]={{0,0,0},{1,2,4},{1,2,2}};
    MohuVrRenderedPoints result;
    assert(mohu_vr_rendered_points(control,&view,points,&result));
    assert(result.base[1][0]==14 && result.base[1][1]==22 && result.base[1][2]==34);
    assert(result.eye[1][0]==37 && result.eye[1][1]==26 && result.eye[1][2]==-14);
    assert(fabs(result.base_axis[0]-1.0/sqrt(5.0))<1e-12);
    assert(fabs(result.eye_axis[2]+1.0/sqrt(5.0))<1e-12);
    const MohuVrRenderedPoints before=result;
    view.rotation[0]=NAN;
    assert(!mohu_vr_rendered_points(control,&view,points,&result));
    assert(!memcmp(&result,&before,sizeof result));
    view.rotation[0]=0;
    const double degenerate[3][3]={{0,0,0},{1,2,4},{1,2,4}};
    assert(!mohu_vr_rendered_points(control,&view,degenerate,&result));
    assert(!memcmp(&result,&before,sizeof result));
    view.precise=0;
    view.rotation_q12[0]=view.rotation_q12[4]=view.rotation_q12[8]=4096;
    view.translation[0]=7;
    assert(mohu_vr_rendered_points(control,&view,points,&result));
    assert(result.eye[1][0]==21 && result.eye[1][1]==22 && result.eye[1][2]==34);
    MohuVrRenderedMuzzle pair[2]={0};
    for (unsigned i=0;i<2;++i) {
        pair[i].valid=pair[i].restored=1;
        pair[i].eye=i; pair[i].attempt=10;
    }
    assert(mohu_vr_rendered_pair_ready(pair,1));
    assert(!mohu_vr_rendered_pair_ready(pair,0));
    pair[1].restored=0; assert(!mohu_vr_rendered_pair_ready(pair,1));
    pair[1].restored=1; pair[1].attempt++;
    assert(!mohu_vr_rendered_pair_ready(pair,1));
    pair[1].attempt--; pair[1].animated.key.generation++;
    assert(!mohu_vr_rendered_pair_ready(pair,1));
    puts("PASS: rendered points, single eye transform, failure/restore/ownership guards");
    return 0;
}
