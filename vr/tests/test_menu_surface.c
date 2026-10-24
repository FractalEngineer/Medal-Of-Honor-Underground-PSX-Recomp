#include "menu_surface.h"

#include <assert.h>
#include <stdio.h>

int main(void) {
    uint32_t seen = 0u;
    uint32_t idle = MOHU_VR_NATIVE_SURFACE_IDLE_VBLANKS;
    assert(!mohu_vr_native_surface_due(0u, &seen, &idle, 1));

    assert(!mohu_vr_native_surface_due(1u, &seen, &idle, 0));
    assert(seen == 1u && idle == 0u);
    assert(!mohu_vr_native_surface_due(1u, &seen, &idle, 0));
    assert(!mohu_vr_native_surface_due(1u, &seen, &idle, 0));
    assert(!mohu_vr_native_surface_due(1u, &seen, &idle, 0));
    assert(mohu_vr_native_surface_due(1u, &seen, &idle, 0));
    assert(!mohu_vr_native_surface_due(1u, &seen, &idle, 1));

    assert(!mohu_vr_native_surface_due(2u, &seen, &idle, 0));
    assert(seen == 2u && idle == 0u);
    puts("PASS: native menu surface resumes after four scene-idle vblanks");
    return 0;
}
