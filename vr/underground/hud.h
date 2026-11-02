#pragma once
#include <stdint.h>

/* Port of the reference native dual-matte HUD. Frame-local success owns
 * suppression; a missing capture/tracked hand/upload retains native artwork. */
void mohu_vr_hud_frame(float aspect);
int mohu_vr_hud_wants_native(void);
int mohu_vr_native_surface_allowed(int requested, int stereo_proof,
                                   unsigned completed_pairs,
                                   int pause_active, int gameplay_active,
                                   int scene_idle);
void mohu_vr_hud_track_health(int16_t health, uint64_t cycle);
void mohu_vr_hud_note_native_damage(void);
int mohu_vr_hud_native_damage_visible(void);
int mohu_vr_hud_set_native(const uint8_t *black, const uint8_t *white);
int mohu_vr_hud_set_damage_native(const uint8_t *black, const uint8_t *white);
void mohu_vr_hud_disable_left(void);
void mohu_vr_hud_prepare(void);
unsigned mohu_vr_hud_replacement_mask(void);
unsigned mohu_vr_hud_ready_mask(void);
int mohu_vr_hud_dump(const char *directory);
