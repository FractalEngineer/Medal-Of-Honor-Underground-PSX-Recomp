/* Build-selected render-only implementation. The normal simulation and every
 * interior resume entry retain the original CPS body and completion timing.
 * Eye replay freezes guest time; one host leaf supplies the same caller result
 * without thousands of per-instruction timing/dispatch helper calls.
 */
#define func_80011424 mohu_lle_preflight
#ifdef MOHU_VR_HOST_PACKET_BUILD
#define func_80010CF0 mohu_lle_packet
#endif
#include "../../generated/SLUS_012.70_full_00.c"
#undef func_80011424
#ifdef MOHU_VR_HOST_PACKET_BUILD
#undef func_80010CF0
#endif
#include "preflight.h"
#include "psx_cycle_freeze.h"

void func_80011424(CPUState *cpu) {
    if(!g_psx_render_pass_active || cpu->gpr[31]!=0x80011008u ||
       cpu->gpr[19]!=0x1F800000u || (cpu->pc && cpu->pc!=0x80011424u)) {
        mohu_lle_preflight(cpu);
        return;
    }
    /* The operation cannot reach device MMIO under this caller ABI. Native
     * static-text validity is checked by the existing dispatcher. No runtime
     * implementation switch and no change to simulation/audio/VBlank rates. */
    psx_cyc_batch_flush();
    psx_gte_stall(cpu);
    mohu_preflight(cpu);
    psx_check_interrupts_at(cpu,0x80011008u);
}
