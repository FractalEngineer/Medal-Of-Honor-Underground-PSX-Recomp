#ifndef MOHU_PREFLIGHT_H
#define MOHU_PREFLIGHT_H
#include "cpu_state.h"

/* SLUS-01270 80011424, 668 bytes, FNV-1a C38CDCC1. Leaf entry only;
 * caller 80011000, continuation 80011008. Not a normal C argument ABI.
 * This core owns no clock: its caller must publish completion before dispatch.
 * Diagnostic harnesses use private CPU/scratchpad and precision checkpoints. */
void mohu_preflight(CPUState *cpu);
#endif
