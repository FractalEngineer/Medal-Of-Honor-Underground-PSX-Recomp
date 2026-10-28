#pragma once
#include <stdint.h>

/* Port of the reference native dual-matte HUD. Frame-local success owns
 * suppression; a missing capture/tracked hand/upload retains native artwork. */
void mohu_vr_hud_frame(float aspect);
int mohu_vr_hud_wants_native(void);
int mohu_vr_hud_set_native(const uint8_t *black, const uint8_t *white);
void mohu_vr_hud_prepare(void);
unsigned mohu_vr_hud_replacement_mask(void);
unsigned mohu_vr_hud_ready_mask(void);
int mohu_vr_hud_dump(const char *directory);
