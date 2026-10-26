#include "weapon.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void point(const uint32_t c[8], const double v[3], double out[3]) {
    for (unsigned row=0; row<3; ++row) {
        out[row] = (int32_t)c[5+row];
        for (unsigned col=0; col<3; ++col) {
            unsigned i=row*3+col;
            out[row] += (int16_t)(c[i/2] >> ((i&1u)*16u))/4096.0*v[col];
        }
    }
}

int main(void) {
    const MohuVrWeaponCalibration* cal=mohu_vr_weapon_calibration_find(0);
    const double identity[9]={1,0,0,0,1,0,0,0,1};
    const double hand[3]={100,70,300};
    uint32_t c[8]={0,0,0,0,0xABCD0000u,0,0,0};
    assert(mohu_vr_weapon_calibrated_control(c,identity,hand,1000,cal));
    assert((c[4]&0xFFFF0000u)==0xABCD0000u);
    double grip[3],muzzle[3];
    point(c,cal->grip_pivot,grip);
    point(c,cal->muzzle,muzzle);
    for (unsigned i=0; i<3; ++i) assert(fabs(grip[i]-hand[i])<=.5);
    double expected_x=0,expected_y=0;
    for (unsigned i=0;i<3;++i) {
        expected_x+=(cal->muzzle[i]-cal->grip_pivot[i])*cal->right[i]*1000/cal->model_units_per_metre;
        expected_y-=(cal->muzzle[i]-cal->grip_pivot[i])*cal->up[i]*1000/cal->model_units_per_metre;
    }
    assert(fabs(muzzle[0]-grip[0]-expected_x)<.05);
    assert(fabs(muzzle[1]-grip[1]-expected_y)<.05);
    assert(mohu_vr_p38_gun_vertex(11,6) && mohu_vr_p38_gun_vertex(11,32));
    assert(!mohu_vr_p38_gun_vertex(11,5) && !mohu_vr_p38_gun_vertex(11,33));
    assert(mohu_vr_p38_gun_vertex(13,68) && !mohu_vr_p38_gun_vertex(13,69));
    assert(!mohu_vr_p38_gun_vertex(9,0));
    double grip_to_muzzle=0;
    for (unsigned i=0; i<3; ++i)
        grip_to_muzzle += (cal->muzzle[i]-cal->grip_pivot[i])*cal->forward[i];
    assert(fabs((muzzle[2]-grip[2])-1000*grip_to_muzzle/cal->model_units_per_metre)<.05);
    uint32_t moved[8];memcpy(moved,c,sizeof c);
    const double translated[3]={200,70,300};
    assert(mohu_vr_weapon_calibrated_control(moved,identity,translated,1000,cal));
    assert((int32_t)moved[5]-(int32_t)c[5]==100);
    const double turn[9]={0,0,1,0,1,0,-1,0,0};
    uint32_t rotated[8]={0};
    assert(mohu_vr_weapon_calibrated_control(rotated,turn,hand,1000,cal));
    point(rotated,cal->grip_pivot,grip);
    point(rotated,cal->muzzle,muzzle);
    for (unsigned i=0; i<3; ++i) assert(fabs(grip[i]-hand[i])<=.5);
    assert(muzzle[0]>grip[0]+200);
    const double inv[9]={.5,0,0,0,.25,0,0,0,.5};
    const double tr[3]={-20,16,3042};
    int32_t position[3],angles[3];
    assert(mohu_vr_weapon_muzzle_shot(rotated,cal,inv,tr,position,angles));
    for (unsigned i=0; i<3; ++i)
        assert(fabs(position[i]/65536.0 - inv[i*3+i]*(muzzle[i]-tr[i]))<1.0/65536);
    assert(abs(angles[0])<65536);
    assert(abs(angles[1]-1024*65536)<65536);
    assert(angles[2]==0);
    uint32_t original[8];memcpy(original,c,sizeof c);
    double bad[9]={NAN,0,0,0,1,0,0,0,1};
    assert(!mohu_vr_weapon_calibrated_control(c,bad,hand,1000,cal));
    assert(!memcmp(c,original,sizeof c));
    assert(!mohu_vr_weapon_calibrated_control(c,identity,hand,NAN,cal));
    assert(!memcmp(c,original,sizeof c));
    int32_t saved[3];memcpy(saved,position,sizeof saved);
    assert(!mohu_vr_weapon_muzzle_shot(c,cal,bad,tr,position,angles));
    assert(!memcmp(saved,position,sizeof saved));
    puts("calibrated grip/muzzle, rotation, translation, scaled native camera: PASS");
    return 0;
}
