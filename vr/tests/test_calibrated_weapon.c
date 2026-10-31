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
    assert(fabs(cal->mount_offset_m[0])<1e-12);
    assert(fabs(cal->mount_offset_m[1])<1e-12);
    assert(fabs(cal->mount_offset_m[2])<1e-12);
    double expected_x=0,expected_y=0;
    for (unsigned i=0;i<3;++i) {
        expected_x+=(cal->muzzle[i]-cal->grip_pivot[i])*cal->right[i]*1000/cal->model_units_per_metre;
        expected_y-=(cal->muzzle[i]-cal->grip_pivot[i])*cal->up[i]*1000/cal->model_units_per_metre;
    }
    assert(fabs(muzzle[0]-grip[0]-expected_x)<.05);
    assert(fabs(muzzle[1]-grip[1]-expected_y)<.05);
    const MohuVrWeaponProfile *p38=mohu_vr_weapon_profile_find(0);
    assert(mohu_vr_weapon_gun_vertex(p38,11,6));
    assert(mohu_vr_weapon_gun_vertex(p38,11,32));
    assert(!mohu_vr_weapon_gun_vertex(p38,11,5));
    assert(!mohu_vr_weapon_gun_vertex(p38,11,33));
    assert(mohu_vr_weapon_gun_vertex(p38,13,68));
    assert(!mohu_vr_weapon_gun_vertex(p38,13,69));
    assert(!mohu_vr_weapon_gun_vertex(p38,9,0));
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
    assert(fabs((muzzle[0]-grip[0])-
        1000*(cal->muzzle[2]-cal->grip_pivot[2])/850.0)<.05);
    const double inv[9]={.5,0,0,0,.25,0,0,0,.5};
    const double tr[3]={-20,16,3042};
    int32_t position[3],angles[3];
    assert(mohu_vr_weapon_muzzle_shot(rotated,cal,inv,tr,position,angles));
    for (unsigned i=0; i<3; ++i)
        assert(fabs(position[i]/65536.0 - inv[i*3+i]*(muzzle[i]-tr[i]))<1.0/65536);
    assert(abs(angles[0])<65536);
    assert(abs(angles[1]-1024*65536)<65536);
    assert(angles[2]==0);
    int32_t marker_position[3],marker_angles[3];
    assert(mohu_vr_weapon_animated_shot(rotated,cal->muzzle,cal->forward,
        inv,tr,marker_position,marker_angles));
    assert(!memcmp(position,&marker_position,sizeof position));
    assert(!memcmp(angles,&marker_angles,sizeof angles));
    const double animated_tip[3]={cal->muzzle[0],cal->muzzle[1],cal->muzzle[2]+32};
    const double animated_axis[3]={cal->forward[0],cal->forward[1],
                                   cal->forward[2]};
    assert(mohu_vr_weapon_animated_shot(rotated,animated_tip,animated_axis,
        inv,tr,marker_position,marker_angles));
    assert(marker_position[0]>position[0]);
    int32_t marker_saved[3];
    memcpy(marker_saved,marker_position,sizeof marker_saved);
    const double zero_axis[3]={0,0,0};
    assert(!mohu_vr_weapon_animated_shot(rotated,animated_tip,zero_axis,
        inv,tr,marker_position,marker_angles));
    assert(!memcmp(marker_saved,marker_position,sizeof marker_saved));
    const double bad_tip[3]={NAN,0,0};
    assert(!mohu_vr_weapon_animated_shot(rotated,bad_tip,animated_axis,
        inv,tr,marker_position,marker_angles));
    assert(!memcmp(marker_saved,marker_position,sizeof marker_saved));
    uint32_t original[8];memcpy(original,c,sizeof c);
    double bad[9]={NAN,0,0,0,1,0,0,0,1};
    assert(!mohu_vr_weapon_calibrated_control(c,bad,hand,1000,cal));
    assert(!memcmp(c,original,sizeof c));
    assert(!mohu_vr_weapon_calibrated_control(c,identity,hand,NAN,cal));
    assert(!memcmp(c,original,sizeof c));
    const MohuVrWeaponCalibration *mp40=mohu_vr_weapon_calibration_find(1);
    assert(mp40 && mp40->provisional);
    uint32_t mp40_control[8]={0,0,0,0,0,0,0,0};
    assert(mohu_vr_weapon_calibrated_control(
        mp40_control,identity,hand,1000,mp40));
    point(mp40_control,mp40->grip_pivot,grip);
    point(mp40_control,mp40->muzzle,muzzle);
    for (unsigned i=0; i<3; ++i) assert(fabs(grip[i]-hand[i])<=.5);
    double mp40_forward=0;
    for (unsigned i=0;i<3;++i)
        mp40_forward+=(mp40->muzzle[i]-mp40->grip_pivot[i])*mp40->forward[i];
    assert(mp40_forward>0);
    int32_t saved[3];memcpy(saved,position,sizeof saved);
    assert(!mohu_vr_weapon_muzzle_shot(c,cal,bad,tr,position,angles));
    assert(!memcmp(saved,position,sizeof saved));
    /* Every authored firearm bore remains +Z rather than a whole-model PCA
     * axis. Held props stay upright while their launch axis stays forward. */
    for (size_t i=0; i<mohu_vr_weapon_profile_count(); ++i) {
        const MohuVrWeaponProfile* p=mohu_vr_weapon_profile_at(i);
        const MohuVrWeaponCalibration* a=p->calibration;
        uint32_t affine[8]={0};
        assert(mohu_vr_weapon_calibrated_control(affine,identity,hand,1000,a));
        double p0[3],p1[3];
        point(affine,a->grip_pivot,p0);
        const double up[3]={a->grip_pivot[0],a->grip_pivot[1]-100,a->grip_pivot[2]};
        point(affine,up,p1);
        assert(p1[1]<p0[1] && fabs(p1[2]-p0[2])<.001);
        assert(mohu_vr_weapon_muzzle_shot(affine,a,identity,(double[3]){0},position,angles));
        assert(angles[0]==0 && angles[1]==0 && angles[2]==0);
        if (p->id!=10 && p->id!=15) assert(a->model_units_per_metre==850);
        if (p->id==10 || p->id==15) {
            point(affine,a->muzzle,p1);
            assert(p1[1]<p0[1]-150); /* cap/neck above grip, not aimed ahead */
        }
    }
    const MohuVrWeaponProfile* stg=mohu_vr_weapon_profile_find(17);
    assert(!mohu_vr_weapon_gun_vertex(stg,27,0));
    assert(!mohu_vr_weapon_gun_vertex(stg,27,110));
    assert(mohu_vr_weapon_gun_vertex(stg,27,5)); /* shared stock edge */
    assert(mohu_vr_weapon_gun_vertex(stg,27,10));
    assert(mohu_vr_weapon_gun_vertex(stg,27,108)); /* muzzle */
    assert(mohu_vr_weapon_gun_vertex(stg,29,15)); /* magazine */
    assert(mohu_vr_weapon_gun_vertex(stg,31,12)); /* sight */
    const MohuVrWeaponCalibration* panzerfaust=
        mohu_vr_weapon_calibration_find(13);
    assert(panzerfaust && fabs(panzerfaust->mount_offset_m[1]+.20)<1e-12);
    uint32_t panzer_control[8]={0};
    assert(mohu_vr_weapon_calibrated_control(
        panzer_control,identity,hand,1000,panzerfaust));
    point(panzer_control,panzerfaust->grip_pivot,grip);
    assert(fabs(grip[1]-(hand[1]-200))<=.5);
    puts("calibrated grip/muzzle, authored bore, upright prop, StG semantic mask: PASS");
    return 0;
}
