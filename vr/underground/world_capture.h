#ifndef MOHU_WORLD_CAPTURE_H
#define MOHU_WORLD_CAPTURE_H

struct CPUState;

/* Diagnostic-only, environment-gated capture of the real 80010CF0 packet
 * inputs and the 80011424 face record. The generated CPS bodies do not call
 * psx_mod_function_entry for these addresses, so the MOHU_VR_WORLD_CAPTURE
 * build links wrappers instead; registration only adds the flush command.
 * Nothing runs unless MOHU_SP_WORLD_CAPTURE names an output file. */
void mohu_world_capture_register(void);
void mohu_world_capture_activate(void);
void mohu_world_capture_packet(struct CPUState* cpu);
void mohu_world_capture_face(struct CPUState* cpu);

#endif
