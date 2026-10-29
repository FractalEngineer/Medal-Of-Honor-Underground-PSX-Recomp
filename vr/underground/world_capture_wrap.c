/* Link-wrap entry points for the default-OFF SP world capture. Compiled only
 * with MOHU_VR_WORLD_CAPTURE, because the generated CPS bodies call
 * psx_mod_function_entry only for the fixed list in game.toml. The capture
 * functions are inert unless MOHU_SP_WORLD_CAPTURE is set. */
#include "cpu_state.h"
#include "world_capture.h"

extern void __real_func_80010CF0(CPUState* cpu);
extern void __real_func_80011424(CPUState* cpu);

void __wrap_func_80010CF0(CPUState* cpu) {
    mohu_world_capture_packet(cpu);
    __real_func_80010CF0(cpu);
}

void __wrap_func_80011424(CPUState* cpu) {
    mohu_world_capture_face(cpu);
    __real_func_80011424(cpu);
}
