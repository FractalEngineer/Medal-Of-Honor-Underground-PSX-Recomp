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
static const uint8_t *mattes[2];
static unsigned ready, replacement;
static float pixel_aspect=1;

int mohu_vr_hud_wants_native(void) {
    const char *v=getenv("PSX_VR_WRIST_HUD");
    return !v || atoi(v)!=0;
}
void mohu_vr_hud_frame(float aspect) {
    ready=replacement=0;
    mattes[0]=mattes[1]=NULL;
    pixel_aspect=isfinite(aspect)&&aspect>.1f&&aspect<8?aspect:1;
}
unsigned mohu_vr_hud_replacement_mask(void) {return replacement;}
unsigned mohu_vr_hud_ready_mask(void) {return ready;}
int mohu_vr_hud_set_native(const uint8_t *black,const uint8_t *white) {
    ready=0;
    if(!black || !white)return 0;
    mattes[0]=black;mattes[1]=white;
    /* GP0 fills are quantized to native RGB5 in this renderer: white reads
     * 248, not 255. Use the isolated empty corner's measured matte level so
     * its transparent background does not become a visible alpha-7 card. */
    const int white_level=white[0];
    if(white_level<240 || white[1]!=white_level || white[2]!=white_level ||
       black[0] || black[1] || black[2])return 0;
    for(int side=0;side<2;side++) {
        const int *r=regions[side];int coverage=0,valid=1;
        for(int row=0;row<r[3];row++)for(int col=0;col<r[2];col++) {
            unsigned source=((row+r[1])*W+col+r[0])*4;
            unsigned dest=((r[3]-1-row)*r[2]+col)*4;
            int delta[3],sum=0;
            for(int c=0;c<3;c++){delta[c]=(int)white[source+c]-black[source+c];sum+=delta[c];}
            if(delta[0]<-2 || delta[1]<-2 || delta[2]<-2 ||
               abs(delta[0]-delta[1])>3 || abs(delta[1]-delta[2])>3)valid=0;
            int alpha=(255*(3*white_level-sum)+3*white_level/2)/(3*white_level);
            if(alpha<0)alpha=0;if(alpha>255)alpha=255;
            pixels[side][dest+3]=(uint8_t)alpha;
            for(int c=0;c<3;c++) {
                int value=alpha?(black[source+c]*255+alpha/2)/alpha:0;
                pixels[side][dest+c]=(uint8_t)(value>255?255:value);
            }
            if(alpha>128)coverage++;
        }
        if(valid && coverage>=(side?5:50))ready|=1u<<side;
    }
    return ready!=0;
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
