#ifndef MOHU_VR_SCOPE_H
#define MOHU_VR_SCOPE_H

#include "mod_plugins.h"

#include <stdint.h>

#define MOHU_VR_SCOPE_ZOOM 2.5

/* Narrow both focal lengths around the existing asymmetric projection centre.
 * Pose, IPD and translation are intentionally unchanged. */
int mohu_vr_scope_apply_zoom(PSXModRenderView* view, double zoom);
#endif
