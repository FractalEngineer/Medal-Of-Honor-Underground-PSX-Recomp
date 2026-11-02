#include "cpu_state.h"
#include "psx_cycle_freeze.h"
#include "interrupts.h"
extern void mohu_packet(CPUState*);
extern void mohu_lle_packet(CPUState*);
extern int mohu_vr_world_packet_cache(CPUState*);

/* Exact original CPS register/packet interface, including its resume entries.
 * Only render transactions select batched timing. Canonical simulation and
 * unsupported contexts retain the original executable reference body. */
void func_80010CF0(CPUState *cpu) {
    if(!g_psx_render_pass_active ||
       (cpu->pc && (cpu->pc<0x80010CF0u || cpu->pc>=0x80011420u))) {
        mohu_lle_packet(cpu);return;
    }
    psx_cyc_batch_flush();
    psx_gte_stall(cpu);
    if(mohu_vr_world_packet_cache(cpu))return;
    mohu_packet(cpu);
    psx_check_interrupts_at(cpu,cpu->pc);
}
