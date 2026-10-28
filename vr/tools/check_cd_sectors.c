/* Read-only MODE2/2352 header, EDC and Form-1 P/Q audit. No image writes.
 * ECMA-130 CD-ROM GF(2^8) P/Q and reflected EDC polynomial 0xD8018001.
 * Form-2's optional all-zero EDC is reported separately, not treated as valid.
 * Usage: check_cd_sectors image.bin > metadata.json
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static uint32_t edc_table[256];
static uint8_t forward[256], backward[256];
static void tables(void) {
    for (unsigned i=0;i<256;++i) {
        unsigned j=i<<1;
        if (j&256) j^=0x11d;
        forward[i]=(uint8_t)j;
        backward[i^j]=(uint8_t)i;
        uint32_t e=i;
        for (unsigned k=0;k<8;++k) e=(e>>1)^((e&1)?0xd8018001u:0u);
        edc_table[i]=e;
    }
}
static uint32_t edc(const uint8_t *p,unsigned size) {
    uint32_t e=0;
    for (unsigned i=0;i<size;++i) e=(e>>8)^edc_table[(e^p[i])&255];
    return e;
}
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static unsigned bcd(unsigned x) {return (x/10)*16+x%10;}
static void ecc(const uint8_t *src,unsigned major_count,unsigned minor_count,
                unsigned major_mult,unsigned minor_inc,uint8_t *dest) {
    unsigned size=major_count*minor_count;
    for (unsigned major=0;major<major_count;++major) {
        unsigned index=(major>>1)*major_mult+(major&1);
        uint8_t a=0,b=0;
        for (unsigned minor=0;minor<minor_count;++minor) {
            uint8_t value=src[index];
            index+=minor_inc;
            if (index>=size) index-=size;
            a^=value;b^=value;a=forward[a];
        }
        a=backward[forward[a]^b];
        dest[major]=a;dest[major+major_count]=a^b;
    }
}
typedef struct {unsigned count,first[32];} Failures;
static void fail(Failures *f,unsigned lba) {
    if (f->count<32) f->first[f->count]=lba;
    ++f->count;
}
static void emit(const char *name,const Failures *f) {
    printf(",\"%s\":{\"count\":%u,\"first_lbas\":[",name,f->count);
    for (unsigned i=0;i<f->count && i<32;++i) printf("%s%u",i?",":"",f->first[i]);
    printf("]}");
}
int main(int argc,char **argv) {
    if (argc!=2) {fprintf(stderr,"Expected raw BIN path\n");return 2;}
    FILE *file=fopen(argv[1],"rb");
    if (!file) {perror("open image");return 2;}
    tables();
    uint8_t sector[2352],copy[2352],p[172],q[104];
    const uint8_t sync[12]={0,255,255,255,255,255,255,255,255,255,255,0};
    unsigned lba=0,form1=0,form2=0,edc_optional_zero=0;
    Failures headers={0},subheaders={0},checksums={0},parity_p={0},parity_q={0};
    size_t bytes;
    while ((bytes=fread(sector,1,sizeof sector,file))==sizeof sector) {
        unsigned position=lba+150;
        if (memcmp(sector,sync,12) || sector[12]!=bcd(position/4500) ||
            sector[13]!=bcd(position/75%60) || sector[14]!=bcd(position%75) || sector[15]!=2)
            fail(&headers,lba);
        if (sector[15]==2) {
            if (memcmp(sector+16,sector+20,4)) fail(&subheaders,lba);
            if (sector[18]&0x20) {
                ++form2;
                uint32_t stored=le32(sector+2348);
                if (!stored) ++edc_optional_zero;
                else if (stored!=edc(sector+16,2332)) fail(&checksums,lba);
            } else {
                ++form1;
                if (le32(sector+2072)!=edc(sector+16,2056)) fail(&checksums,lba);
                memcpy(copy,sector,sizeof copy);memset(copy+12,0,4);
                ecc(copy+12,86,24,2,86,p);
                if (memcmp(p,sector+2076,sizeof p)) fail(&parity_p,lba);
                ecc(copy+12,52,43,86,88,q);
                if (memcmp(q,sector+2248,sizeof q)) fail(&parity_q,lba);
            }
        }
        ++lba;
    }
    int error=ferror(file)!=0;
    fclose(file);
    if (bytes || error) {fprintf(stderr,"Incomplete image read\n");return 2;}
    printf("{\"sectors\":%u,\"form1\":%u,\"form2\":%u,\"form2_edc_absent\":%u",lba,form1,form2,edc_optional_zero);
    emit("invalid_header",&headers);emit("invalid_subheader",&subheaders);
    emit("invalid_edc",&checksums);emit("invalid_ecc_p",&parity_p);emit("invalid_ecc_q",&parity_q);
    puts("}");return 0;
}
