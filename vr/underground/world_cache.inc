/* Bounded architecture prototype: reuse WORLD packet geometry only within the
 * same native draw and exact camera pose. Entities, weapons, hands and laser
 * still execute each view. Any pose/input/OT change takes the native renderer.
 * This deliberately does not claim head-motion cache coverage: camera-culled
 * packets cannot safely provide unseen geometry. No stale image is presented.
 */
#include "pgxp.h"
#include "world_cache_key.h"
typedef struct MohuWorldPoint {
    int32_t x,y;
    uint16_t z;
    int precise,projective;
    PGXPProjection projection;
} MohuWorldPoint;
typedef struct MohuWorldCache {
    uint32_t epoch,generation,args[4],ctrl[31],ot,heads[512],out_heads[512];
    PSXModRenderView view;
    uint32_t end,words,capacity,*data;
    MohuWorldPoint *points;
    uint32_t scratch[256],gte_data[32],gte_ctrl[32];
    struct {int valid;int32_t x,y;uint16_t z;PGXPProjection projection;int projective;} sxy[3];
    bool valid;
} MohuWorldCache;
static MohuWorldCache g_world_caches[16];
static bool g_world_cache_enabled,g_world_cache_nested;
static uint32_t g_world_cache_epoch;

static void vr_world_cache_reset(void) {
    ++g_world_cache_epoch;
    g_world_cache_nested=false;
    for(unsigned i=0;i<16;++i)g_world_caches[i].valid=false;
}

int mohu_vr_world_packet_cache(CPUState *cpu) {
    if(!g_world_cache_enabled || g_world_cache_nested || !g_active ||
       !g_stereo_active || g_stereo_mp || !g_stereo_eye_view_valid ||
       !cpu || (cpu->pc && cpu->pc!=0x80010CF0u) || cpu->gpr[31]!=0x8009A51Cu) return 0;
    const uint32_t begin=cpu->gpr[4],limit=cpu->gpr[5],ot=stereo_ot_base();
    if(!mohu_vr_ray_span(begin,4u) || !mohu_vr_ray_span(ot,512u*4u) ||
       limit<begin || limit>0x80200000u) return 0;
    uint32_t heads[512];
    for(unsigned i=0;i<512;++i)heads[i]=psx_mod_read_word(ot+4u*i);
    MohuWorldCache *slot=NULL,*available=NULL;
    for(unsigned i=0;i<16;++i) {
        MohuWorldCache *s=&g_world_caches[i];
        if(!s->valid || s->epoch!=g_world_cache_epoch || s->generation!=g_marker_generation) {
            if(!available)available=s;
            continue;
        }
        if(s->ot==ot && !memcmp(s->args,cpu->gpr+4,sizeof s->args) &&
           !memcmp(s->ctrl,cpu->gte_ctrl,sizeof s->ctrl) &&
           mohu_vr_same_view(&s->view,&g_stereo_eye_view) &&
           !memcmp(s->heads,heads,sizeof heads)) {slot=s;break;}
    }
    if(slot) {
        /* A new draw creates precision in its CURRENT render timeline. Do not
         * transplant old generation receipts: a projective scope may enable
         * precision after its checkpoint, and the shared restore guard must
         * correctly refuse that operation. These are owned native coordinates
         * with an exact view/epoch key, transported through the public GTE API. */
        for(unsigned i=0;i<slot->words;++i) {
            uint32_t a=begin+4u*i;
            psx_mod_write_word(a,slot->data[i]);
            const MohuWorldPoint *p=&slot->points[i];
            if(p->precise) {
                pgxp_gte_push_sxy(p->x,p->y,p->z,slot->data[i]);
                if(p->projective)pgxp_gte_set_projection(&p->projection);
                pgxp_store_gte_reg(a,14);
            }
        }
        for(unsigned i=0;i<512;++i)psx_mod_write_word(ot+4u*i,slot->out_heads[i]);
        for(unsigned i=0;i<256;++i)psx_mod_write_word(0x1F800000u+4u*i,slot->scratch[i]);
        memcpy(cpu->gte_data,slot->gte_data,sizeof slot->gte_data);
        memcpy(cpu->gte_ctrl,slot->gte_ctrl,sizeof slot->gte_ctrl);
        for(unsigned i=0;i<3;++i) {
            /* Legitimate projection transport; the render checkpoint owns
             * these host shadows and restores them with the eye. */
            if(slot->sxy[i].valid) {
                pgxp_gte_push_sxy(slot->sxy[i].x,slot->sxy[i].y,slot->sxy[i].z,slot->gte_data[12+i]);
                if(slot->sxy[i].projective)pgxp_gte_set_projection(&slot->sxy[i].projection);
            } else {
                pgxp_gte_push_sxy((int32_t)(int16_t)slot->gte_data[12+i]*65536,
                    (int32_t)(int16_t)(slot->gte_data[12+i]>>16)*65536,0,slot->gte_data[12+i]);
                pgxp_gte_reg_written(14,slot->gte_data[12+i]);
            }
        }
        cpu->gpr[2]=slot->end;cpu->pc=cpu->gpr[31];
        psx_mod_counter_add("mohu.vr.world_cache.hit",1);
        return 1;
    }
    if(!available) {
        psx_mod_counter_add("mohu.vr.world_cache.capacity_refused",1);
        return 0;
    }
    slot=available;slot->valid=false;
    slot->epoch=g_world_cache_epoch;slot->generation=g_marker_generation;
    memcpy(slot->args,cpu->gpr+4,sizeof slot->args);
    memcpy(slot->ctrl,cpu->gte_ctrl,sizeof slot->ctrl);
    slot->view=g_stereo_eye_view;slot->ot=ot;memcpy(slot->heads,heads,sizeof heads);
    const uint32_t ra=cpu->gpr[31];
    g_world_cache_nested=true;
    uint32_t end=psx_mod_call_guest(cpu,0x80010CF0u,ra,cpu->gpr[4],cpu->gpr[5],cpu->gpr[6],cpu->gpr[7]);
    g_world_cache_nested=false;
    cpu->gpr[2]=end;cpu->pc=ra;
    psx_mod_counter_add("mohu.vr.world_cache.miss",1);
    if(end<begin || end>limit || (end&3u) || end-begin>0x20000u) return 1;
    const unsigned words=(end-begin)/4u;
    if(!words)return 1;
    if(words>slot->capacity) {
        uint32_t *data=malloc(words*sizeof *data);
        MohuWorldPoint *points=calloc(words,sizeof *points);
        if(!data || !points) {free(data);free(points);return 1;}
        free(slot->data);free(slot->points);slot->data=data;slot->points=points;slot->capacity=words;
    }
    slot->words=words;slot->end=end;
    for(unsigned i=0;i<words;++i) {
        uint32_t a=begin+4u*i;slot->data[i]=psx_mod_read_word(a);
        MohuWorldPoint *p=slot->points+i;memset(p,0,sizeof *p);
        PGXPWordShadow receipt={0};
        if(pgxp_capture_word_shadow(a,slot->data[i],&receipt) && receipt.valid) {
            p->projective=pgxp_load_projection(a,slot->data[i],&p->projection);
            if(p->projective) {
                /* Signed homogeneous geometry can have SZ=0 at the camera
                 * plane. Retain that projection for the shared near clipper. */
                p->x=receipt.x16;p->y=receipt.y16;p->z=receipt.z;p->precise=1;
            } else if(receipt.z) {
                p->precise=pgxp_load_precise_word(a,slot->data[i],&p->x,&p->y,&p->z);
            }
        }
    }
    for(unsigned i=0;i<512;++i)slot->out_heads[i]=psx_mod_read_word(ot+4u*i);
    for(unsigned i=0;i<256;++i)slot->scratch[i]=psx_mod_read_word(0x1F800000u+4u*i);
    memcpy(slot->gte_data,cpu->gte_data,sizeof slot->gte_data);
    memcpy(slot->gte_ctrl,cpu->gte_ctrl,sizeof slot->gte_ctrl);
    for(unsigned i=0;i<3;++i) {
        slot->sxy[i].valid=pgxp_get_gte_sxy_checked(i,cpu->gte_data[12+i],1,&slot->sxy[i].x,&slot->sxy[i].y);
        int live=0;uint32_t value=0,flags=0;int32_t x=0,y=0;uint16_t z=0;
        pgxp_debug_shadow(2,12+i,&live,&value,&flags,&x,&y,&z);slot->sxy[i].z=z;
        slot->sxy[i].projective=pgxp_get_gte_projection(i,cpu->gte_data[12+i],&slot->sxy[i].projection);
    }
    slot->valid=true;
    return 1;
}
