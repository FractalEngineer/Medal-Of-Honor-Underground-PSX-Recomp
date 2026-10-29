/* Explicitly armed diagnostic caller harness, absent from normal builds.
 * Candidate writes ONLY private CPU/scratchpad. The shared precision journal
 * is rolled back BEFORE the runnable native reference executes exactly once.
 * No save-header edits, guest patches, live implementation switch or candidate
 * gameplay results. This is a bounded contract test, never a timing/FPS run.
 */
#include "preflight.h"
#include "pgxp.h"
#include "mod_plugins.h"
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

extern void __real_func_80011424(CPUState *cpu);
extern unsigned mohu_vr_native_profile_scope(void);
extern void gte_precision_checkpoint_begin(void);
extern void gte_precision_checkpoint_rollback(void);

typedef struct Shadow {
    uint32_t present,live,value,flags;
    int32_t x,y;
    uint32_t z,projection_valid;
    PGXPProjection projection;
} Shadow;
typedef struct Result {
    uint32_t regs[131]; /* pointer-free CPU prefix, ending after GTE control */
    unsigned char scratch[1024];
    Shadow shadow[34+32+256];
} Result;
_Static_assert(offsetof(CPUState,gte_ctrl)+sizeof(((CPUState*)0)->gte_ctrl)==131u*4u,"CPU prefix changed");
typedef struct Record {
    uint32_t scope,flags,header,vertex;
    Result input,candidate,reference;
} Record;
static Record record;
static unsigned char sandbox[1024];
static CPUState *source;
static FILE *capture;
static unsigned left,stride,sequence,checks,failed,refused;
static unsigned numeric_failed,precision_failed,results[16],windings[8];
static uint64_t candidate_ticks,reference_ticks;
static unsigned first_reg=~0u,first_shadow=~0u;

static uint32_t read_word(uint32_t a) {
    uint32_t v;
    if(a>=0x1F800000u && a<=0x1F8003FCu) {memcpy(&v,sandbox+(a-0x1F800000u),4);return v;}
    return source->read_word(a);
}
static uint16_t read_half(uint32_t a) {
    uint16_t v;
    if(a>=0x1F800000u && a<=0x1F8003FEu) {memcpy(&v,sandbox+(a-0x1F800000u),2);return v;}
    return source->read_half(a);
}
static void write_word(uint32_t a,uint32_t v) {
    if(a<0x1F800000u || a>0x1F8003FCu) abort();
    memcpy(sandbox+(a-0x1F800000u),&v,4);
}
static void write_half(uint32_t a,uint16_t v) {
    if(a<0x1F800000u || a>0x1F8003FEu) abort();
    memcpy(sandbox+(a-0x1F800000u),&v,2);
}
static void snapshot(Result *out,CPUState *cpu,int private_scratch) {
    memset(out,0,sizeof *out);
    memcpy(out->regs,cpu,sizeof out->regs);
    for(unsigned i=0;i<256;++i) {
        uint32_t a=0x1F800000u+4u*i;
        uint32_t v=private_scratch?read_word(a):cpu->read_word(a);
        memcpy(out->scratch+4u*i,&v,4);
    }
    for(unsigned i=0;i<34+32+256;++i) {
        Shadow *s=&out->shadow[i]; uint16_t z=0; int live=0;
        int space=i<34?1:i<66?2:0;
        uint32_t key=i<34?i:i<66?i-34:0x1F800000u+4u*(i-66);
        s->present=(uint32_t)pgxp_debug_shadow(space,key,&live,&s->value,
            &s->flags,&s->x,&s->y,&z);
        s->live=(uint32_t)live;s->z=z;
        if(i>=46 && i<50) s->projection_valid=(uint32_t)pgxp_get_gte_projection(
            i-46,cpu->gte_data[i-34],&s->projection);
        if(i>=66) s->projection_valid=(uint32_t)pgxp_load_projection(key,
            private_scratch?read_word(key):cpu->read_word(key),&s->projection);
    }
}
static int valid(CPUState *cpu) {
    if(cpu->gpr[19]!=0x1F800000u || cpu->gpr[31]!=0x80011008u ||
       (cpu->pc && cpu->pc!=0x80011424u)) return 0;
    uint32_t face=cpu->gpr[23]&0x1FFFFFFFu;
    if((face&3u) || face>=0x200000u-4u) return 0;
    uint32_t table=cpu->read_word(0x1F8003F0u)&0x1FFFFFFFu;
    uint32_t index=cpu->read_word(cpu->gpr[23])&0x1FFFu;
    if(index==0x1FFFu) index=0;
    if((table&3u) || table>=0x200000u-8u || index>(0x200000u-8u-table)/8u) return 0;
    uint32_t hash=2166136261u;
    for(uint32_t p=0x80011424u;p<0x800116C0u;++p) hash=(hash^cpu->read_byte(p))*16777619u;
    return hash==0xC38CDCC1u;
}
void __wrap_func_80011424(CPUState *cpu) {
    const unsigned scope=mohu_vr_native_profile_scope();
    if(!left || scope || ++sequence%stride) {__real_func_80011424(cpu);return;}
    if(!valid(cpu)) {++refused;__real_func_80011424(cpu);return;}
    source=cpu;
    memset(&record,0,sizeof record);
    record.scope=scope;record.flags=cpu->gpr[22];
    record.header=cpu->read_word(cpu->gpr[23]);
    record.vertex=cpu->read_word(0x1F8003F0u);
    snapshot(&record.input,cpu,0);
    memcpy(sandbox,record.input.scratch,sizeof sandbox);
    CPUState local=*cpu;
    local.read_word=read_word;local.read_half=read_half;
    local.write_word=write_word;local.write_half=write_half;
    LARGE_INTEGER a,b;
    gte_precision_checkpoint_begin();
    QueryPerformanceCounter(&a);mohu_preflight(&local);QueryPerformanceCounter(&b);
    candidate_ticks+=(uint64_t)(b.QuadPart-a.QuadPart);
    snapshot(&record.candidate,&local,1);
    gte_precision_checkpoint_rollback();
    QueryPerformanceCounter(&a);__real_func_80011424(cpu);QueryPerformanceCounter(&b);
    reference_ticks+=(uint64_t)(b.QuadPart-a.QuadPart);
    snapshot(&record.reference,cpu,0);
    /* A sliced/interrupted reference is not a completed caller comparison. */
    if(cpu->pc!=0x80011008u) {++refused;return;}
    int bad_numeric=memcmp(record.candidate.regs,record.reference.regs,sizeof record.reference.regs)!=0 ||
        memcmp(record.candidate.scratch,record.reference.scratch,sizeof sandbox)!=0;
    int bad_precision=memcmp(record.candidate.shadow,record.reference.shadow,sizeof record.reference.shadow)!=0;
    if(bad_numeric && first_reg==~0u) for(unsigned i=0;i<131;++i)
        if(record.candidate.regs[i]!=record.reference.regs[i]) {first_reg=i;break;}
    if(bad_precision && first_shadow==~0u) for(unsigned i=0;i<322;++i)
        if(memcmp(&record.candidate.shadow[i],&record.reference.shadow[i],sizeof(Shadow))) {first_shadow=i;break;}
    numeric_failed+=(unsigned)bad_numeric;precision_failed+=(unsigned)bad_precision;
    failed+=(unsigned)(bad_numeric||bad_precision);++checks;--left;
    ++results[cpu->gpr[2]&15u];++windings[(record.flags>>13)&7u];
    if(capture) {fwrite(&record,sizeof record,1,capture);if(!left) {fclose(capture);capture=NULL;}}
}
int mohu_preflight_harness_command(const char *args,char *reply,int cap) {
    if(!strncmp(args,"arm ",4)) {
        unsigned n=0,s=0;
        if(sscanf(args+4,"%u %u",&n,&s)!=2 || !n || n>4096 || !s || s>4096 || left) return -1;
        const char *path=getenv("MOHU_VR_PREFLIGHT_CAPTURE_FILE");
        if(!path || !(capture=fopen(path,"wb"))) return -1;
        uint32_t header[4]={0x50464831u,sizeof(Record),sizeof(Shadow),n};
        if(fwrite(header,sizeof header,1,capture)!=1) {fclose(capture);capture=NULL;return -1;}
        left=n;stride=s;sequence=checks=failed=refused=numeric_failed=precision_failed=0;
        candidate_ticks=reference_ticks=0;first_reg=first_shadow=~0u;
        memset(results,0,sizeof results);memset(windings,0,sizeof windings);
    }
    LARGE_INTEGER f;QueryPerformanceFrequency(&f);
    int used=snprintf(reply,cap,"{\"checks\":%u,\"remaining\":%u,\"failed\":%u,\"numeric_failed\":%u,\"precision_failed\":%u,\"refused\":%u,\"first_reg\":%u,\"first_shadow\":%u,\"candidate_us\":%.3f,\"reference_us\":%.3f,\"result_counts\":[",
        checks,left,failed,numeric_failed,precision_failed,refused,first_reg,first_shadow,
        candidate_ticks*1e6/(double)f.QuadPart,reference_ticks*1e6/(double)f.QuadPart);
    for(unsigned i=0;i<16 && used>0 && used<cap;++i) used+=snprintf(reply+used,cap-used,"%s%u",i?",":"",results[i]);
    if(used<=0 || used>=cap) return -1;
    used+=snprintf(reply+used,cap-used,"],\"winding_counts\":[");
    for(unsigned i=0;i<8 && used>0 && used<cap;++i) used+=snprintf(reply+used,cap-used,"%s%u",i?",":"",windings[i]);
    if(used<=0 || used>=cap) return -1;
    return snprintf(reply+used,cap-used,"]}")<cap-used?0:-1;
}
