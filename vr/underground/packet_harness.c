/* Bounded canonical-call oracle for the packet CPS segments. Candidate state
 * is private and its precision journal is rolled back before the native call.
 * Never supplies a gameplay result. No code or inventory changes.
 */
#include "cpu_state.h"
#include "pgxp.h"
#include "mod_plugins.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <windows.h>
extern void mohu_packet(CPUState*);
extern void __real_func_80010CF0(CPUState*);
extern unsigned mohu_vr_native_profile_scope(void);
extern void gte_precision_checkpoint_begin(void);
extern void gte_precision_checkpoint_rollback(void);
static unsigned char ram[0x200000],scratch[1024];
static CPUState *source;
typedef struct Write {uint32_t addr,value,width;PGXPWordShadow shadow;} Write;
static Write writes[512];
static unsigned write_count,left,stride,sequence,checks,failed,refused,reg_failed,mem_failed,shadow_failed;
static unsigned resumes,entries,total_writes,first_reg=~0u;
static uint64_t host_ticks,native_ticks;
static unsigned char *address(uint32_t a,unsigned width) {
    uint32_t p=a&0x1FFFFFFFu;
    if(p<0x200000u && p+width<=0x200000u)return ram+p;
    if(p>=0x1F800000u && p+width<=0x1F800400u)return scratch+p-0x1F800000u;
    abort(); /* A device access is outside this caller capsule. */
}
static uint32_t read_word(uint32_t a) {uint32_t v;memcpy(&v,address(a,4),4);return v;}
static uint16_t read_half(uint32_t a) {uint16_t v;memcpy(&v,address(a,2),2);return v;}
static uint8_t read_byte(uint32_t a) {return *address(a,1);}
static void store(uint32_t a,uint32_t v,unsigned width) {
    if(write_count>=512)abort();
    writes[write_count++]=(Write){.addr=a,.value=v,.width=width};
    memcpy(address(a,width),&v,width);
}
static void write_word(uint32_t a,uint32_t v) {store(a,v,4);}
static void write_half(uint32_t a,uint16_t v) {store(a,v,2);}
static void write_byte(uint32_t a,uint8_t v) {store(a,v,1);}
void __wrap_func_80010CF0(CPUState *cpu) {
    if(!left || mohu_vr_native_profile_scope() || ++sequence%stride) {__real_func_80010CF0(cpu);return;}
    const int initial=!cpu->pc || cpu->pc==0x80010CF0u;
    /* The entry prologue establishes S3. It is an INPUT only on resumes. */
    if(!initial && cpu->gpr[19]!=0x1F800000u) {++refused;__real_func_80010CF0(cpu);return;}
    source=cpu;
    for(uint32_t i=0;i<0x200000u;i+=4) {uint32_t v=cpu->read_word(0x80000000u+i);memcpy(ram+i,&v,4);}
    for(uint32_t i=0;i<1024;i+=4) {uint32_t v=cpu->read_word(0x1F800000u+i);memcpy(scratch+i,&v,4);}
    CPUState local=*cpu;local.read_word=read_word;local.read_half=read_half;local.read_byte=read_byte;
    local.write_word=write_word;local.write_half=write_half;local.write_byte=write_byte;
    if(initial)++entries;else ++resumes;
    write_count=0;
    LARGE_INTEGER a,b;gte_precision_checkpoint_begin();
    QueryPerformanceCounter(&a);mohu_packet(&local);QueryPerformanceCounter(&b);
    host_ticks+=(uint64_t)(b.QuadPart-a.QuadPart);
    /* Capture the FINAL word after overlapping writes, including precision. */
    for(unsigned i=0;i<write_count;++i) {
        Write *w=&writes[i];uint32_t aligned=w->addr&~3u;
        w->value=read_word(aligned);
        pgxp_capture_word_shadow(aligned,w->value,&w->shadow);
    }
    gte_precision_checkpoint_rollback();
    QueryPerformanceCounter(&a);__real_func_80010CF0(cpu);QueryPerformanceCounter(&b);
    native_ticks+=(uint64_t)(b.QuadPart-a.QuadPart);
    unsigned bad_reg=memcmp(local.gpr,cpu->gpr,sizeof cpu->gpr)!=0 || local.pc!=cpu->pc ||
        local.hi!=cpu->hi || local.lo!=cpu->lo || memcmp(local.gte_data,cpu->gte_data,sizeof cpu->gte_data)!=0 ||
        memcmp(local.gte_ctrl,cpu->gte_ctrl,sizeof cpu->gte_ctrl)!=0;
    if(bad_reg && first_reg==~0u)for(unsigned i=0;i<32;++i)if(local.gpr[i]!=cpu->gpr[i]) {first_reg=i;break;}
    unsigned bad_mem=0,bad_shadow=0;
    for(unsigned i=0;i<write_count;++i) {
        Write *w=&writes[i];uint32_t aligned=w->addr&~3u,value=source->read_word(aligned);
        if(value!=w->value)bad_mem=1;
        PGXPWordShadow s={0};pgxp_capture_word_shadow(aligned,value,&s);
        if(memcmp(&s,&w->shadow,sizeof s))bad_shadow=1;
    }
    reg_failed+=bad_reg;mem_failed+=bad_mem;shadow_failed+=bad_shadow;
    total_writes+=write_count;
    failed+=(bad_reg||bad_mem||bad_shadow);++checks;--left;
}
int mohu_packet_harness_command(const char *args,char *reply,int cap) {
    if(!strncmp(args,"arm ",4)) {
        unsigned n,s;
        if(sscanf(args+4,"%u %u",&n,&s)!=2 || !n || n>4096 || !s || s>4096 || left)return -1;
        left=n;stride=s;sequence=checks=failed=refused=reg_failed=mem_failed=shadow_failed=entries=resumes=total_writes=0;
        host_ticks=native_ticks=0;first_reg=~0u;
    }
    LARGE_INTEGER f;QueryPerformanceFrequency(&f);
    int n=snprintf(reply,cap,"{\"checks\":%u,\"remaining\":%u,\"failed\":%u,\"refused\":%u,\"reg_failed\":%u,\"mem_failed\":%u,\"shadow_failed\":%u,\"first_reg\":%u,\"entries\":%u,\"resumes\":%u,\"writes\":%u,\"candidate_us\":%.3f,\"reference_us\":%.3f}",
        checks,left,failed,refused,reg_failed,mem_failed,shadow_failed,first_reg,entries,resumes,total_writes,
        host_ticks*1e6/(double)f.QuadPart,native_ticks*1e6/(double)f.QuadPart);
    return n>0 && n<cap?0:-1;
}
