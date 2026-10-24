#include "frustum.h"

#include <assert.h>
#include <string.h>

static unsigned char ram[0x200000];

uint32_t psx_mod_read_word(uint32_t address) {
    uint32_t value;
    memcpy(&value, ram + (address & 0x1fffffffu), sizeof(value));
    return value;
}

uint16_t psx_mod_read_half(uint32_t address) {
    uint16_t value;
    memcpy(&value, ram + (address & 0x1fffffffu), sizeof(value));
    return value;
}

static void write_word(uint32_t address, uint32_t value) {
    memcpy(ram + address, &value, sizeof(value));
}

static void node(uint32_t address, int leaf) {
    static const int16_t bounds[6] = {-10, -10, 90, 10, 10, 110};
    memcpy(ram + address, bounds, sizeof(bounds));
    write_word(address + 12u, (uint32_t)leaf);
    write_word(address + 16u, 1u);
    write_word(address + 20u, 2u);
}

int main(void) {
    double matrix[9] = {1, 0, 0, 0, 1, 0, 0, 0, 1};
    double tr[3] = {0};
    PSXModRenderView view = {0};
    view.struct_size = sizeof(view);
    view.rotation_q12[0] = view.rotation_q12[4] = view.rotation_q12[8] = 4096;
    view.projection = 1;
    view.fx_q16 = view.fy_q16 = 256 * 65536;

    const int16_t forward[6] = {-10, -10, 90, 10, 10, 110};
    const int16_t behind[6] = {-10, -10, -110, 10, 10, -90};
    const int16_t side[6] = {390, -10, 90, 410, 10, 110};
    const int16_t crossing[6] = {-1000, -1000, -10, 1000, 1000, 1000};
    assert(mohu_vr_box_visible(forward, matrix, tr, &view, 256, 120, 512, 240));
    assert(!mohu_vr_box_visible(behind, matrix, tr, &view, 256, 120, 512, 240));
    assert(!mohu_vr_box_visible(side, matrix, tr, &view, 256, 120, 512, 240));
    assert(mohu_vr_box_visible(crossing, matrix, tr, &view, 256, 120, 512, 240));

    view.rotation_q12[0] = view.rotation_q12[8] = -4096;
    assert(mohu_vr_box_visible(behind, matrix, tr, &view, 256, 120, 512, 240));
    assert(!mohu_vr_box_visible(forward, matrix, tr, &view, 256, 120, 512, 240));
    view.rotation_q12[0] = view.rotation_q12[8] = 4096;
    view.translation[0] = -400;
    assert(mohu_vr_box_visible(side, matrix, tr, &view, 256, 120, 512, 240));

    tr[0] = 40000;
    assert(mohu_vr_box_visible(forward, matrix, tr, &view, 256, 120, 512, 240));
    tr[0] = view.translation[0] = 0;

    uint32_t queue[1000];
    const uint32_t masks[2] = {1u, 2u};
    unsigned count = 0;
    node(0x100, 0);
    node(0x140, 1);
    node(0x180, 1);
    node(0x1c0, 1);
    write_word(0x118, 0x80000140u);
    write_word(0x120, 0x80000180u);
    write_word(0x11c, 0x800001c0u);
    assert(mohu_vr_collect_tree(
        0x80000100u, queue, &count, matrix, tr, &view, 256, 120,
        masks, 0, 0));
    assert(count == 3u);
    assert(queue[0] == 0x800001c0u);
    assert(queue[1] == 0x80000180u);
    assert(queue[2] == 0x80000140u);

    write_word(0x1d0, 0u);
    assert(mohu_vr_collect_tree(
        0x80000100u, queue, &count, matrix, tr, &view, 256, 120,
        masks, 0, 0));
    assert(count == 2u);
    assert(mohu_vr_collect_tree(
        0x80000100u, queue, &count, matrix, tr, &view, 256, 120,
        masks, 1, 0));
    assert(count == 3u);

    write_word(0x118, 0x801ffffcu);
    assert(!mohu_vr_collect_tree(
        0x80000100u, queue, &count, matrix, tr, &view, 256, 120,
        masks, 1, 0));
    write_word(0x118, 0x80000100u);
    write_word(0x11c, 0u);
    write_word(0x120, 0u);
    assert(!mohu_vr_collect_tree(
        0x80000100u, queue, &count, matrix, tr, &view, 256, 120,
        masks, 1, 0));

    memset(ram, 0, sizeof(ram));
    for (unsigned i = 0; i < 1001u; ++i) {
        const uint32_t address = 0x100u + i * 80u;
        node(address, 0);
        node(address + 40u, 1);
        write_word(address + 28u, 0x80000000u + address + 40u);
        if (i < 1000u) {
            write_word(address + 24u, 0x80000000u + address + 80u);
        }
    }
    assert(!mohu_vr_collect_tree(
        0x80000100u, queue, &count, matrix, tr, &view, 256, 120,
        masks, 1, 0));
    return 0;
}
