#ifndef MOHU_VR_SCOPE_H
#define MOHU_VR_SCOPE_H

#include "mod_plugins.h"

#include <stdint.h>

#define MOHU_VR_SCOPE_ZOOM 2.5

/* Narrow both focal lengths around the existing asymmetric projection centre.
 * Pose, IPD and translation are intentionally unchanged. */
int mohu_vr_scope_apply_zoom(PSXModRenderView* view, double zoom);
/* Final H reached by 8008A090's integer ramp from idle H=400.
 * H also controls native depth cue; it is independent of the eye focal zoom. */
uint32_t mohu_vr_scope_final_depth_h(uint32_t target);
uint16_t mohu_vr_scope_fog_start(uint16_t original, uint32_t target,
                                uint32_t current_h, uint32_t cutoff);
#endif
