#include "menu_surface.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    for (unsigned mode = 0; mode < 2u; ++mode) {
        const MohuVrPauseBinding* b = mohu_vr_pause_binding(mode != 0u);
        uint32_t read[4], enter[3];
        memcpy(read, b->read_words, sizeof read);
        memcpy(enter, b->enter_words, sizeof enter);
        assert(mohu_vr_pause_state(b, read, enter, 0u) == 0);
        assert(mohu_vr_pause_state(b, read, enter, 1u) == 1);
        assert(mohu_vr_pause_state(b, read, enter, 2u) == -1);
        assert(mohu_vr_pause_state(b, read, enter, UINT32_MAX) == -1);
        assert(mohu_vr_pause_state(NULL, read, enter, 1u) == -1);
        assert(mohu_vr_pause_state(b, NULL, enter, 1u) == -1);
        for (unsigned i = 0; i < 4u; ++i) {
            read[i] ^= 1u;
            assert(mohu_vr_pause_state(b, read, enter, 1u) == -1);
            read[i] ^= 1u;
        }
        for (unsigned i = 0; i < 3u; ++i) {
            enter[i] ^= 1u;
            assert(mohu_vr_pause_state(b, read, enter, 1u) == -1);
            enter[i] ^= 1u;
        }
        assert(mohu_vr_pause_state(mohu_vr_pause_binding(mode == 0u),
                                   read, enter, 1u) == -1);
    }
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
