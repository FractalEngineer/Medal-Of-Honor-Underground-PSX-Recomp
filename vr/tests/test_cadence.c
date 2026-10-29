#include "cadence.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    MohuVrCadence s={0};
    assert(!mohu_vr_cadence_take(&s,1,2,3));
    mohu_vr_cadence_arm(&s,100,2,3);
    assert(!mohu_vr_cadence_take(&s,100,2,3));
    assert(mohu_vr_cadence_take(&s,101,2,3));
    assert(!mohu_vr_cadence_take(&s,102,2,3));
    mohu_vr_cadence_arm(&s,200,2,3);
    assert(!mohu_vr_cadence_take(&s,201,4,3));
    assert(!mohu_vr_cadence_take(&s,202,2,3));
    mohu_vr_cadence_arm(&s,200,2,3);
    assert(!mohu_vr_cadence_take(&s,201,2,4));
    mohu_vr_cadence_arm(&s,200,2,3);
    assert(!mohu_vr_cadence_take(&s,203,2,3));
    mohu_vr_cadence_arm(&s,200,2,3);
    assert(!mohu_vr_cadence_take(&s,199,2,3));
    mohu_vr_cadence_arm(&s,UINT32_MAX,2,3);
    assert(mohu_vr_cadence_take(&s,0,2,3));
    mohu_vr_cadence_arm(&s,200,2,3);
    assert(mohu_vr_cadence_take(&s,202,2,3));
    puts("cadence ownership, discontinuity and single-consumption controls passed");
}
