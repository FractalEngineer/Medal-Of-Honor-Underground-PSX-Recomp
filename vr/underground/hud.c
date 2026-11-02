/* Adapted from Medal-Of-Honor-PSX-Recomp/vr/moh_vr_hud.c.
 * Native art/straight-alpha dual mattes, per-hand fallback and FACE_HEAD
 * attachment use the existing framework; no authored replacement HUD. */
#include "hud.h"
#include "mod_plugins.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { W=512, H=240, PANEL_W=160, PANEL_H=112 };
static const int regions[2][4]={{8,8,112,112},{368,8,136,40}};
static uint8_t pixels[2][PANEL_W*PANEL_H*4];
static uint8_t damage_pixels[PANEL_W*PANEL_H*4];
static const uint8_t *mattes[2];
static unsigned ready, replacement;
static float pixel_aspect=1;
static int white_level;
static int16_t last_health;
static int health_valid;
static int native_damage_pending;
static int native_damage_visible;

int mohu_vr_hud_wants_native(void) {
    const char *v=getenv("PSX_VR_WRIST_HUD");
    return !v || atoi(v)!=0;
}
int mohu_vr_native_surface_allowed(int requested, int stereo_proof,
                                   unsigned completed_pairs,
                                   int pause_active, int gameplay_active,
                                   int scene_idle) {
    if (!requested) return 1;
    /* Boot, movies and menus may use the native presentation plane. Once a
     * gameplay pair exists, only a verified menu/frontend state may restore
     * that plane. A stale player pointer can survive the mission-complete
     * transition, so a confirmed scene-idle interval also proves frontend
     * ownership. Immediate gameplay failures have not gone idle. */
    return !stereo_proof || completed_pairs == 0u || pause_active ||
           !gameplay_active || scene_idle;
}
void mohu_vr_hud_track_health(int16_t health, uint64_t cycle) {
    (void)cycle;
    if (health < 0) {
        health_valid = 0;
        return;
    }
    if (health_valid && health < last_health) {
        psx_mod_counter_add("mohu.vr.hud.damage", 1);
    }
    last_health = health;
    health_valid = 1;
}
void mohu_vr_hud_note_native_damage(void) {
    native_damage_pending = 1;
}
int mohu_vr_hud_native_damage_visible(void) {
    return native_damage_visible;
}
void mohu_vr_hud_frame(float aspect) {
    ready=replacement=0;
    mattes[0]=mattes[1]=NULL;
    pixel_aspect=isfinite(aspect)&&aspect>.1f&&aspect<8?aspect:1;
    native_damage_visible=native_damage_pending;
    native_damage_pending=0;
}
unsigned mohu_vr_hud_replacement_mask(void) {return replacement;}
unsigned mohu_vr_hud_ready_mask(void) {return ready;}
static int decode_panel(const uint8_t *black,const uint8_t *white,int side,
                        uint8_t *output) {
    const int *r=regions[side];int coverage=0,valid=1;
    for(int row=0;row<r[3];row++)for(int col=0;col<r[2];col++) {
        unsigned source=((row+r[1])*W+col+r[0])*4;
        unsigned dest=((r[3]-1-row)*r[2]+col)*4;
        int delta[3],sum=0;
        for(int c=0;c<3;c++){delta[c]=(int)white[source+c]-black[source+c];sum+=delta[c];}
        if(delta[0]<-2 || delta[1]<-2 || delta[2]<-2 ||
           abs(delta[0]-delta[1])>3 || abs(delta[1]-delta[2])>3)valid=0;
        int alpha=(255*(3*white_level-sum)+3*white_level/2)/(3*white_level);
        if(alpha<0)alpha=0;
        if(alpha>255)alpha=255;
        output[dest+3]=(uint8_t)alpha;
        for(int c=0;c<3;c++) {
            int value=alpha?(black[source+c]*255+alpha/2)/alpha:0;
            output[dest+c]=(uint8_t)(value>255?255:value);
        }
        if(alpha>128)coverage++;
    }
    return valid && coverage>=(side?5:50);
}
int mohu_vr_hud_set_native(const uint8_t *black,const uint8_t *white) {
    ready=0;
    if(!black || !white)return 0;
    mattes[0]=black;mattes[1]=white;
    /* GP0 fills are quantized to native RGB5 in this renderer: white reads
     * 248, not 255. Use the isolated empty corner's measured matte level so
     * its transparent background does not become a visible alpha-7 card. */
    white_level=white[0];
    if(white_level<240 || white[1]!=white_level || white[2]!=white_level ||
       black[0] || black[1] || black[2])return 0;
    for(int side=0;side<2;side++) {
        if(decode_panel(black,white,side,pixels[side]))ready|=1u<<side;
    }
    return ready!=0;
}
int mohu_vr_hud_set_damage_native(const uint8_t *black,const uint8_t *white) {
    if(!(ready&1u) || !black || !white ||
       !decode_panel(black,white,0,damage_pixels))return 0;
    const int *r=regions[0];
    for(int row=0;row<r[3];row++)for(int col=0;col<r[2];col++) {
        unsigned source=((row+r[1])*W+col+r[0])*4;
        unsigned dest=((r[3]-1-row)*r[2]+col)*4;
        unsigned char ring[4];
        memcpy(ring,&pixels[0][dest],sizeof ring);
        unsigned char *output=&pixels[0][dest],*over=&damage_pixels[dest];
        /* Keep the compass underneath, place the native marker above it,
         * then restore the solid dark/green health ring over the marker. */
        const int dx=col-52,dy=(r[3]-1-row)-74;
        const int outer=dx*dx*20*20+dy*dy*40*40<=40*40*20*20;
        const int ring_pixel=outer && ring[3]>128 &&
            (ring[2]<32 || ring[1]>ring[0] ||
             ring[0]+ring[1]+ring[2]<220);
        if(ring_pixel)continue;
        const unsigned ua=ring[3],oa=over[3],inverse=255u-oa;
        const unsigned out_alpha=oa+(ua*inverse+127u)/255u;
        if(!out_alpha)continue;
        for(int c=0;c<3;c++) {
            const unsigned value=(
                (unsigned)over[c]*oa+
                (unsigned)ring[c]*ua*inverse/255u+out_alpha/2u)/out_alpha;
            output[c]=(uint8_t)(value>255u?255u:value);
        }
        output[3]=(uint8_t)out_alpha;
        const unsigned black_alpha=(unsigned)output[3];
        for(int c=0;c<3;c++) {
            const unsigned premultiplied=
                ((unsigned)output[c]*black_alpha+127u)/255u;
            ((uint8_t *)mattes[0])[source+c]=(uint8_t)premultiplied;
            ((uint8_t *)mattes[1])[source+c]=(uint8_t)(
                premultiplied+
                ((unsigned)white_level*(255u-black_alpha)+127u)/255u);
        }
    }
    return 1;
}
void mohu_vr_hud_disable_left(void) {
    ready&=~1u;
}
void mohu_vr_hud_prepare(void) {
    replacement=0;
    if(!mohu_vr_hud_wants_native() || !ready)return;
    PSXModOpenXRHands hands={0};hands.struct_size=sizeof hands;
    if(!psx_mod_openxr_hands(&hands) || !hands.focused || !hands.origin_valid || hands.age_ms>100)return;
    for(unsigned side=0;side<2;side++) {
        if(!(ready&(1u<<side)))continue;
        const PSXModTrackedPose *grip=&hands.pose[side][PSX_MOD_XR_GRIP_POSE];
        if(!grip->active || (grip->flags&15)!=15)continue;
        int finite=1;for(int i=0;i<3;i++)if(!isfinite(grip->position_m[i]))finite=0;
        if(!finite)continue;
        PSXModOpenXRSurface surface={0};surface.struct_size=sizeof surface;
        surface.id=side;surface.width_px=(unsigned)regions[side][2];
        surface.height_px=(unsigned)regions[side][3];surface.rgba=pixels[side];
        surface.size_m[0]=.12f;
        surface.size_m[1]=.12f*regions[side][3]/regions[side][2]*pixel_aspect;
        for(int i=0;i<3;i++)surface.position_m[i]=grip->position_m[i];
        surface.position_m[1]+=.06f;surface.orientation_xyzw[3]=1;
        surface.flags=PSX_MOD_OPENXR_SURFACE_FACE_HEAD;
        if(psx_mod_openxr_surface(&surface))replacement|=1u<<side;
    }
}
int mohu_vr_hud_dump(const char *directory) {
    if(!directory || !*directory || !mattes[0] || !mattes[1])return 0;
    const uint8_t *data[4]={mattes[0],mattes[1],pixels[0],pixels[1]};
    const char *names[4]={"hud-black.rgba","hud-white.rgba","hud-left.rgba","hud-right.rgba"};
    for(int i=0;i<4;i++) {
        char path[2048];int n=snprintf(path,sizeof path,"%s/%s",directory,names[i]);
        if(n<0 || (size_t)n>=sizeof path)return 0;
        size_t size=i<2?W*H*4:(size_t)regions[i-2][2]*regions[i-2][3]*4;
        FILE *file=fopen(path,"wb");if(!file)return 0;
        size_t written=fwrite(data[i],1,size,file);int closed=fclose(file);
        if(written!=size || closed)return 0;
    }
    return 1;
}
