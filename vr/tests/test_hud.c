/* Reference test_native_hud.c adapted to Underground regions and RGB5 mattes. */
#include "hud.h"
#include "mod_plugins.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
static PSXModOpenXRHands hands;
static PSXModOpenXRSurface surfaces[2];
static unsigned accepted=3,calls;
int psx_mod_openxr_hands(PSXModOpenXRHands *out){*out=hands;return 1;}
int psx_mod_openxr_surface(const PSXModOpenXRSurface *s){surfaces[s->id]=*s;calls++;return !!(accepted&(1u<<s->id));}
void psx_mod_counter_add(const char *name,uint32_t delta){(void)name;(void)delta;}
static uint8_t black[512*240*4],white[512*240*4];
static void content(int level) {
    memset(black,0,sizeof black);memset(white,level,sizeof white);
    for(int y=20;y<30;y++)for(int x=20;x<30;x++)memset(white+(y*512+x)*4,0,3);
    for(int y=15;y<18;y++)for(int x=380;x<385;x++) {
        unsigned i=(y*512+x)*4;
        black[i]=white[i]=120;black[i+1]=white[i+1]=200;black[i+2]=white[i+2]=80;
    }
}
int main(void) {
    assert(mohu_vr_native_surface_allowed(0,1,9,0,1,0));
    assert(mohu_vr_native_surface_allowed(1,0,9,0,1,0));
    assert(mohu_vr_native_surface_allowed(1,1,0,0,1,0));
    assert(!mohu_vr_native_surface_allowed(1,1,1,0,1,0));
    assert(mohu_vr_native_surface_allowed(1,1,1,1,1,0));
    assert(mohu_vr_native_surface_allowed(1,1,1,0,0,0));
    assert(mohu_vr_native_surface_allowed(1,1,1,0,1,1));
    mohu_vr_hud_track_health(80,100);
    mohu_vr_hud_track_health(70,200);
    mohu_vr_hud_frame(1);
    assert(!mohu_vr_hud_native_damage_visible());
    mohu_vr_hud_note_native_damage();
    mohu_vr_hud_frame(1);
    assert(mohu_vr_hud_native_damage_visible());
    mohu_vr_hud_frame(1);
    assert(!mohu_vr_hud_native_damage_visible());
    hands.focused=hands.origin_valid=1;
    for(int side=0;side<2;side++){hands.pose[side][0].active=1;hands.pose[side][0].flags=15;hands.pose[side][0].orientation_xyzw[3]=1;}
    for(int level=248;level<=255;level+=7) {
        content(level);mohu_vr_hud_frame(1.2f);assert(mohu_vr_hud_set_native(black,white));
        mohu_vr_hud_prepare();assert(mohu_vr_hud_ready_mask()==3 && mohu_vr_hud_replacement_mask()==3);
        const uint8_t *p=surfaces[0].rgba;
        assert(p[3]==0); /* Native 248-white background is fully transparent. */
        assert(p[((112-1-12)*112+12)*4+3]==255); /* Opaque black is artwork. */
        assert(p[((112-1-12)*112+12)*4]==0);
        assert(surfaces[0].flags==PSX_MOD_OPENXR_SURFACE_FACE_HEAD);
        assert(fabsf(surfaces[0].size_m[1]-.144f)<.0001f);
    }
    mohu_vr_hud_frame(1);calls=0;mohu_vr_hud_prepare();assert(!calls && !mohu_vr_hud_replacement_mask());
    assert(mohu_vr_hud_set_native(black,white));hands.pose[0][0].active=0;
    mohu_vr_hud_prepare();assert(mohu_vr_hud_replacement_mask()==2);
    hands.pose[0][0].active=1;hands.focused=0;mohu_vr_hud_prepare();assert(!mohu_vr_hud_replacement_mask());
    hands.focused=1;hands.age_ms=101;mohu_vr_hud_prepare();assert(!mohu_vr_hud_replacement_mask());
    hands.age_ms=0;accepted=1;mohu_vr_hud_prepare();assert(mohu_vr_hud_replacement_mask()==1);
    accepted=3;hands.pose[0][0].position_m[0]=NAN;mohu_vr_hud_prepare();assert(mohu_vr_hud_replacement_mask()==2);
    hands.pose[0][0].position_m[0]=0;
    white[(20*512+20)*4]=255; /* One invalid matte keeps the other hand usable. */
    mohu_vr_hud_frame(1);assert(mohu_vr_hud_set_native(black,white));
    mohu_vr_hud_prepare();assert(mohu_vr_hud_replacement_mask()==2);
    mohu_vr_hud_disable_left();assert(mohu_vr_hud_ready_mask()==2);

    /* A marker-only matte capture must compose below an opaque HUD pixel. */
    content(248);mohu_vr_hud_frame(1);assert(mohu_vr_hud_set_native(black,white));
    unsigned ring_art=(32*512+43)*4;
    black[ring_art]=white[ring_art]=0;
    black[ring_art+1]=white[ring_art+1]=0;
    black[ring_art+2]=white[ring_art+2]=0;
    mohu_vr_hud_frame(1);assert(mohu_vr_hud_set_native(black,white));
    memset(black,0,sizeof black);memset(white,248,sizeof white);
    for(int y=30;y<41;y++)for(int x=33;x<44;x++) {
        unsigned i=(y*512+x)*4;
        black[i]=white[i]=64;
        black[i+1]=white[i+1]=0;
        black[i+2]=white[i+2]=0;
    }
    for(int y=39;y<50;y++)for(int x=47;x<58;x++) {
        unsigned i=(y*512+x)*4;
        black[i]=white[i]=64;
        black[i+1]=white[i+1]=0;
        black[i+2]=white[i+2]=0;
    }
    assert(mohu_vr_hud_set_damage_native(black,white));
    const uint8_t *left=surfaces[0].rgba;
    const unsigned hud_pixel=((112-1-(32-8))*112+(43-8))*4;
    const unsigned marker_pixel=((112-1-(44-8))*112+(52-8))*4;
    assert(left[hud_pixel]==0 && left[hud_pixel+1]==0 && left[hud_pixel+2]==0);
    assert(left[marker_pixel]==64 && left[marker_pixel+1]==0 &&
           left[marker_pixel+2]==0 && left[marker_pixel+3]==255);
    mohu_vr_hud_disable_left();assert(mohu_vr_hud_ready_mask()==2);
    mohu_vr_hud_frame(1);assert(!mohu_vr_hud_set_native(NULL,NULL));
    mohu_vr_hud_prepare();assert(!mohu_vr_hud_replacement_mask());
    return 0;
}
