/* Standalone custom-ABI differential test. The runner extracts the ORIGINAL
 * generated body into ignored output; it never changes the game source.
 * These deterministic GTE/precision service doubles compare operation order
 * and all operands. Real GTE/PGXP results have a separate live caller harness.
 */
#include "preflight.h"
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

void oracle_preflight(CPUState*);
uint32_t g_debug_last_store_pc;
volatile uint32_t g_psx_last_fn_entry;
static unsigned char ram[0x10000],scratch[1024],before[1024];
static uint64_t transport;
static uint32_t random_state=0x91270u;
static uint32_t random_word(void) {
    random_state^=random_state<<13;random_state^=random_state>>17;
    random_state^=random_state<<5;return random_state;
}
static unsigned char *address(uint32_t a,unsigned size) {
    a&=0x1FFFFFFFu;
    if(a>=0x1F800000u && a+size<=0x1F800400u) return scratch+a-0x1F800000u;
    assert(a+size<=sizeof ram);return ram+a;
}
uint32_t psx_read_word(uint32_t a) {uint32_t v;memcpy(&v,address(a,4),4);return v;}
uint16_t psx_read_half(uint32_t a) {uint16_t v;memcpy(&v,address(a,2),2);return v;}
static void write_word(uint32_t a,uint32_t v) {memcpy(address(a,4),&v,4);}
static void write_half(uint32_t a,uint16_t v) {memcpy(address(a,2),&v,2);}
static void note(uint32_t i,uint32_t a,uint32_t b,uint32_t c) {
    transport=(transport^i)*1099511628211ull;
    transport=(transport^a)*1099511628211ull;
    transport=(transport^b)*1099511628211ull;
    transport=(transport^c)*1099511628211ull;
}
void psx_pgxp_alu(CPUState *c,uint32_t i,uint32_t r,uint32_t a,uint32_t b) {(void)c;note(i,r,a,b);}
void psx_pgxp_load(CPUState *c,uint32_t i,uint32_t a,uint32_t v) {(void)c;note(i,a,v,0);}
void psx_pgxp_store(CPUState *c,uint32_t i,uint32_t a,uint32_t v) {(void)c;note(i,a,v,0);}
void psx_pgxp_cop2(CPUState *c,uint32_t i,uint32_t v,uint32_t a) {(void)c;note(i,v,a,0);}
void psx_check_interrupts_at(CPUState *c,uint32_t a) {(void)c;(void)a;}
static void canonicalize(CPUState *c) {
    const unsigned u[]={7,16,17,18,19},s[]={1,3,5,8,9,10,11},t[]={4,12,20,26,27,29,30};
    for(unsigned i=0;i<sizeof u/sizeof *u;++i)c->gte_data[u[i]]&=0xFFFFu;
    for(unsigned i=0;i<sizeof s/sizeof *s;++i)c->gte_data[s[i]]=(uint32_t)(int32_t)(int16_t)c->gte_data[s[i]];
    for(unsigned i=0;i<sizeof t/sizeof *t;++i)c->gte_ctrl[t[i]]=(uint32_t)(int32_t)(int16_t)c->gte_ctrl[t[i]];
    c->gte_data[15]=c->gte_data[14];
}
uint32_t gte_read_ctrl(CPUState *c,uint8_t r) {return c->gte_ctrl[r];}
uint32_t gte_read_data(CPUState *c,uint8_t r) {
    if(r==17 || r==18 || r==19)return c->gte_data[r]&0xFFFFu;
    return c->gte_data[r];
}
void gte_write_data(CPUState *c,uint8_t r,uint32_t v) {
    canonicalize(c);
    c->gte_data[r]=r==1?(uint32_t)(int32_t)(int16_t)v:(r==17 || r==18)?v&0xFFFFu:v;
}
void gte_execute(CPUState *c,uint32_t cmd) {
    assert((cmd&63u)==6u);canonicalize(c);
    int64_t x[3],y[3];
    for(unsigned i=0;i<3;++i) {x[i]=(int16_t)c->gte_data[12+i];y[i]=(int16_t)(c->gte_data[12+i]>>16);}
    int64_t a=x[0]*(y[1]-y[2])+x[1]*(y[2]-y[0])+x[2]*(y[0]-y[1]);
    c->gte_data[24]=(uint32_t)a;
    c->gte_ctrl[31]=a>INT32_MAX?0x80010000u:a<INT32_MIN?0x80008000u:0;
}
void psx_hle_gte_execute(CPUState *c,uint32_t cmd) {gte_execute(c,cmd);}
int main(void) {
    unsigned counts[16]={0},flags[8]={0};
    for(unsigned trial=0;trial<100000;++trial) {
        CPUState entry={0};
        for(unsigned i=0;i<32;++i) {entry.gpr[i]=random_word();entry.gte_data[i]=random_word();entry.gte_ctrl[i]=random_word();}
        entry.gpr[0]=0;entry.gpr[19]=0x1F800000u;entry.gpr[23]=0x80001000u;
        entry.gpr[31]=0x80011008u;entry.gpr[22]=(trial&7u)<<13;
        entry.read_word=psx_read_word;entry.read_half=psx_read_half;
        entry.write_word=write_word;entry.write_half=write_half;
        canonicalize(&entry);
        for(unsigned i=0;i<1024;i+=4) {uint32_t v=random_word();memcpy(scratch+i,&v,4);}
        write_word(0x80001000u,trial%17u==0?0x1FFFu:trial&3u);
        write_word(0x1F8003F0u,0x80002000u);
        for(unsigned i=0;i<32;i+=4)write_word(0x80002000u+i,random_word());
        write_word(0x1F80039Cu,trial%3u==0?0:random_word()&0x3FFFu);
        write_half(0x1F8003B4u,320);write_half(0x1F8003B6u,240);
        /* Include tiny-depth and mixed screen-edge cases, not just wide RNG. */
        if(trial%5u==0)for(unsigned i=17;i<=19;++i)entry.gte_data[i]=trial%31u;
        if(trial%7u==0)for(unsigned i=12;i<=14;++i)entry.gte_data[i]=(random_word()&0x1FFu)|((random_word()&0xFFu)<<16);
        memcpy(before,scratch,1024);CPUState native=entry,host=entry;
        transport=14695981039346656037ull;oracle_preflight(&native);
        unsigned char expected[1024];memcpy(expected,scratch,1024);
        uint64_t native_transport=transport;
        memcpy(scratch,before,1024);transport=14695981039346656037ull;mohu_preflight(&host);
        if(memcmp(&host,&native,131u*4u) || memcmp(scratch,expected,1024) || transport!=native_transport) {
            fprintf(stderr,"preflight mismatch trial=%u transport=%d\n",trial,transport!=native_transport);
            for(unsigned i=0;i<32;++i)if(host.gpr[i]!=native.gpr[i])fprintf(stderr,"r%u host=%08X reference=%08X\n",i,host.gpr[i],native.gpr[i]);
            return 1;
        }
        ++counts[native.gpr[2]&15u];++flags[(entry.gpr[22]>>13)&7u];
    }
    assert(counts[0] && counts[1] && counts[2] && counts[4] && counts[6] && counts[8] && counts[10] && counts[12] && counts[14]);
    for(unsigned i=0;i<8;++i)assert(flags[i]);
    puts("100000 preflight caller comparisons passed; all winding flags and subdivision masks covered");return 0;
}
