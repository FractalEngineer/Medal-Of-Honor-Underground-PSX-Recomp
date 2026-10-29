/* Host triangle preflight. Keep the original generated body as the oracle.
 * Collapse instruction dispatch/timing into one operation, retaining the real
 * GTE and precision transports. No projection/culling/PGXP approximation.
 * All numeric GPR results are retained, including early-return temporaries.
 */
#include "preflight.h"
#include "pgxp_hooks.h"
#include "hle_gte.h"

#define A(i,d,a,b,x) do { \
    uint32_t sa_=(a), sb_=(b); r[d]=(x); \
    PGXP_ALU(i,r[d],sa_,sb_); (void)sa_; (void)sb_; \
} while (0)
#define L(i,d,a,half) do { \
    uint32_t addr_=(a); r[d]=(half)?cpu->read_half(addr_):cpu->read_word(addr_); \
    PGXP_LOAD(i,addr_,r[d]); \
} while (0)
#define S(i,s,off,half) do { \
    uint32_t addr_=r[19]+(off); \
    if(half) cpu->write_half(addr_,(uint16_t)r[s]); else cpu->write_word(addr_,r[s]); \
    PGXP_STORE(i,addr_,r[s]); \
} while (0)
#define R(i,d,g) do { r[d]=gte_read_data(cpu,g); PGXP_COP2(i,r[d],0); } while (0)
#define W(i,s,g) do { gte_write_data(cpu,g,r[s]); PGXP_COP2(i,r[s],0); } while (0)

void mohu_preflight(CPUState *cpu) {
    uint32_t *r=cpu->gpr;
    A(0x32C82000u,8,r[22],0x2000u,sa_&sb_);
    A(0x32C98000u,9,r[22],0x8000u,sa_&sb_);
    A(0x32CA4000u,10,r[22],0x4000u,sa_&sb_);
    L(0x8EF60000u,22,r[23],0);
    A(0x3C0E7FF9u,14,0u,0u,0x7FF90000u);
    A(0x35CE8000u,14,r[14],0x8000u,sa_|sb_);
    r[25]=gte_read_ctrl(cpu,31); PGXP_COP2(0x4859F800u,r[25],0);
    const uint32_t swap=r[9];
    A(0x3C0F8000u,15,0u,0u,0x80000000u);
    if(swap) {
        R(0x480B6000u,11,12); R(0x480C6800u,12,13);
        W(0x488B6800u,11,13); W(0x488C6000u,12,12);
        R(0x480B8800u,11,17); R(0x480C9000u,12,18);
        W(0x488B9000u,11,18); W(0x488C8800u,12,17);
    }
    A(0x32CC1FFFu,12,r[22],0x1FFFu,sa_&sb_);
    A(0x34091FFFu,9,0u,0x1FFFu,sb_);
    const int sentinel=r[12]==r[9];
    L(0x8E6903F0u,9,r[19]+1008u,0);
    if(sentinel) A(0x00006021u,12,0u,0u,0u);
    A(0x000C60C0u,12,r[12],3u,sa_<<sb_);
    A(0x340B0001u,11,0u,1u,sb_);
    if(!r[8]) psx_hle_gte_execute(cpu,0x1400006u);
    A(0x01896021u,12,r[12],r[9],sa_+sb_);
    L(0x95890004u,9,r[12]+4u,1);
    A(0x01D97024u,14,r[14],r[25],sa_&sb_);
    A(0x01F97824u,15,r[15],r[25],sa_&sb_);
    const uint32_t two_sided=r[8];
    L(0x8D880000u,8,r[12],0);
    if(!two_sided) {
        R(0x480BC000u,11,24);
        A(0x000B582Au,11,0u,r[11],(uint32_t)((int32_t)sa_<(int32_t)sb_));
        if(r[10]) A(0x396B0001u,11,r[11],1u,sa_^sb_);
    }
    A(0x00001021u,2,0u,0u,0u);
    W(0x48890800u,9,1);
    /* Original MTC2 VXY0 is a direct backing write (no canonicalization). */
    cpu->gte_data[0]=r[8]; PGXP_COP2(0x48880000u,r[8],0);
    if(r[15] && r[14]) goto done;
    const uint32_t front=r[11];
    R(0x480C9000u,12,18);
    if(!front) goto done;

    R(0x48096800u,9,13);
    S(0xA66C0022u,12,34u,1); S(0xAE690030u,9,48u,0);
    R(0x480B8800u,11,17); R(0x48086000u,8,12);
    S(0xA66B001Au,11,26u,1); S(0xAE68002Cu,8,44u,0);
    R(0x480D9800u,13,19); R(0x480A7000u,10,14);
    A(0x0180C021u,24,r[12],0u,sa_);
    A(0x016C782Bu,15,r[11],r[12],(uint32_t)(sa_<sb_));
    const uint32_t first_min=r[15];
    A(0x01607021u,14,r[11],0u,sa_);
    if(!first_min) {
        A(0x01807021u,14,r[12],0u,sa_);
        A(0x0160C021u,24,r[11],0u,sa_);
    }
    A(0x01CD782Bu,15,r[14],r[13],(uint32_t)(sa_<sb_));
    const uint32_t min_done=r[15];
    A(0x030D782Bu,15,r[24],r[13],(uint32_t)(sa_<sb_));
    if(!min_done) A(0x01A07021u,14,r[13],0u,sa_);
    const uint32_t max_third=r[15];
    L(0x8E63039Cu,3,r[19]+924u,0);
    if(max_third) A(0x01A0C021u,24,r[13],0u,sa_);
    A(0x00187840u,15,r[24],1u,sa_<<sb_);
    A(0x01F87821u,15,r[15],r[24],sa_+sb_);
    A(0x01EE7821u,15,r[15],r[14],sa_+sb_);
    A(0x000F7902u,15,r[15],4u,sa_>>sb_);
    S(0xA66D002Au,13,42u,1); S(0xAE6A0034u,10,52u,0);
    S(0xA66F0042u,15,66u,1);
    if(r[3]) {
        A(0x00031880u,3,r[3],2u,sa_<<sb_);
        A(0x0163C82Bu,25,r[11],r[3],(uint32_t)(sa_<sb_));
        const uint32_t near0=r[25];
        A(0x0183C82Bu,25,r[12],r[3],(uint32_t)(sa_<sb_));
        if(near0) A(0x34420001u,2,r[2],1u,sa_|sb_);
        const uint32_t near1=r[25];
        A(0x01A3C82Bu,25,r[13],r[3],(uint32_t)(sa_<sb_));
        if(near1) A(0x34420002u,2,r[2],2u,sa_|sb_);
        if(r[25]) A(0x34420004u,2,r[2],4u,sa_|sb_);
    }
    A(0x2F19000Au,25,r[24],10u,(uint32_t)(sa_<sb_));
    const uint32_t tiny=r[25];
    A(0x2DF80010u,24,r[15],16u,(uint32_t)(sa_<sb_));
    if(tiny && r[24]) { A(0x00001021u,2,0u,0u,0u); goto done; }
    A(0x000FC082u,24,r[15],2u,sa_>>sb_);
    A(0x2F1801FDu,24,r[24],509u,(uint32_t)(sa_<sb_));
    const uint32_t depth_ok=r[24];
    L(0x966E03B4u,14,r[19]+948u,1);
    if(!depth_ok) {
        A(0x340F01FDu,15,0u,509u,sb_);
        A(0x000F7880u,15,r[15],2u,sa_<<sb_);
        S(0xA66F0042u,15,66u,1);
    }
    A(0x00085C03u,11,r[8],16u,(uint32_t)((int32_t)sa_>>sb_));
    L(0x967903B6u,25,r[19]+950u,1);
    A(0x00084400u,8,r[8],16u,sa_<<sb_);
    A(0x00084403u,8,r[8],16u,(uint32_t)((int32_t)sa_>>sb_));
    A(0x34180001u,24,0u,1u,sb_);
    A(0x00096403u,12,r[9],16u,(uint32_t)((int32_t)sa_>>sb_));
    if((int32_t)r[8]>=0) {
        A(0x010EC02Bu,24,r[8],r[14],(uint32_t)(sa_<sb_));
        const uint32_t inside=r[24]; A(0x0000C021u,24,0u,0u,0u);
        if(!inside) A(0x37180002u,24,r[24],2u,sa_|sb_);
    }
    A(0x00094C00u,9,r[9],16u,sa_<<sb_);
    A(0x00094C03u,9,r[9],16u,(uint32_t)((int32_t)sa_>>sb_));
    A(0x34080004u,8,0u,4u,sb_);
    A(0x000A6C03u,13,r[10],16u,(uint32_t)((int32_t)sa_>>sb_));
    if((int32_t)r[11]>=0) {
        A(0x0179402Bu,8,r[11],r[25],(uint32_t)(sa_<sb_));
        const uint32_t inside=r[8]; A(0x00004021u,8,0u,0u,0u);
        if(!inside) A(0x35080008u,8,r[8],8u,sa_|sb_);
    }
    A(0x01184021u,8,r[8],r[24],sa_+sb_);
    const uint32_t clip0=r[8];
    A(0x000A5400u,10,r[10],16u,sa_<<sb_);
    if(!clip0) goto accepted;
    A(0x000A5403u,10,r[10],16u,(uint32_t)((int32_t)sa_>>sb_));
    A(0x34180001u,24,0u,1u,sb_);
    if((int32_t)r[9]>=0) {
        A(0x012EC02Bu,24,r[9],r[14],(uint32_t)(sa_<sb_));
        const uint32_t inside=r[24]; A(0x0000C021u,24,0u,0u,0u);
        if(!inside) A(0x37180002u,24,r[24],2u,sa_|sb_);
    }
    A(0x34090004u,9,0u,4u,sb_);
    if((int32_t)r[12]>=0) {
        A(0x0199482Bu,9,r[12],r[25],(uint32_t)(sa_<sb_));
        const uint32_t inside=r[9]; A(0x00004821u,9,0u,0u,0u);
        if(!inside) A(0x35290008u,9,r[9],8u,sa_|sb_);
    }
    A(0x01384821u,9,r[9],r[24],sa_+sb_);
    const uint32_t clip1=r[9];
    A(0x34180001u,24,0u,1u,sb_);
    if(!clip1) goto accepted;
    if((int32_t)r[10]>=0) {
        A(0x014EC02Bu,24,r[10],r[14],(uint32_t)(sa_<sb_));
        const uint32_t inside=r[24]; A(0x0000C021u,24,0u,0u,0u);
        if(!inside) A(0x37180002u,24,r[24],2u,sa_|sb_);
    }
    A(0x340A0004u,10,0u,4u,sb_);
    if((int32_t)r[13]>=0) {
        A(0x01B9502Bu,10,r[13],r[25],(uint32_t)(sa_<sb_));
        const uint32_t inside=r[10]; A(0x00005021u,10,0u,0u,0u);
        if(!inside) A(0x354A0008u,10,r[10],8u,sa_|sb_);
    }
    A(0x01585021u,10,r[10],r[24],sa_+sb_);
    const uint32_t clip2=r[10];
    A(0x01094024u,8,r[8],r[9],sa_&sb_);
    if(!clip2) goto accepted;
    A(0x010A4024u,8,r[8],r[10],sa_&sb_);
    if(r[8]) { A(0x00001021u,2,0u,0u,0u); goto done; }
accepted:
    A(0x0040C821u,25,r[2],0u,sa_);
    A(0x34020001u,2,0u,1u,sb_);
    if(r[25]) A(0x00191040u,2,r[25],1u,sa_<<sb_);
done:
    cpu->pc=r[31];
}
