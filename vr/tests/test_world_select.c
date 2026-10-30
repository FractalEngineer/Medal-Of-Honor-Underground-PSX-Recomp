#include "../underground/world_select.h"

#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static unsigned char g_ram[0x200000];

uint32_t psx_mod_read_word(uint32_t address) {
    uint32_t value;
    memcpy(&value, g_ram + (address & 0x1fffffffu), sizeof value);
    return value;
}

uint16_t psx_mod_read_half(uint32_t address) {
    uint16_t value;
    memcpy(&value, g_ram + (address & 0x1fffffffu), sizeof value);
    return value;
}

static void put_word(uint32_t address, uint32_t value) {
    memcpy(g_ram + (address & 0x1fffffffu), &value, sizeof value);
}

static void put_box(uint32_t address, const int16_t bounds[6]) {
    memcpy(g_ram + (address & 0x1fffffffu), bounds, 12u);
}

static void put_vertex(uint32_t table, unsigned index, int16_t x, int16_t y,
                       int16_t z) {
    const int16_t value[4] = {x, y, z, 0};
    memcpy(g_ram + (table & 0x1fffffffu) + index * 8u, value, sizeof value);
}

static void build_level(void) {
    memset(g_ram, 0, sizeof g_ram);
    const uint32_t table = 0x80001000u, spine = 0x80000100u;
    const uint32_t leaf_a = 0x80000140u, leaf_b = 0x80000180u;
    const uint32_t strip_a = 0x80002000u, strip_b = 0x80002100u;

    put_vertex(table, 0, -10, -10, 100);
    put_vertex(table, 1, 10, -10, 100);
    put_vertex(table, 2, -10, 10, 100);
    put_vertex(table, 3, 10, 10, 100);

    const int16_t spine_box[6] = {-20, -20, 80, 20, 20, 140};
    const int16_t leaf_box[6] = {-15, -15, 95, 15, 15, 125};
    put_box(spine, spine_box);
    put_box(leaf_a, leaf_box);
    put_box(leaf_b, leaf_box);
    put_word(spine + 24u, leaf_a);
    put_word(spine + 32u, leaf_b);
    put_word(leaf_a + 12u, 3u);
    put_word(leaf_a + 24u, strip_a);
    put_word(leaf_b + 12u, 1u);
    put_word(leaf_b + 24u, strip_b);
    put_word(strip_a, (1u << 16) | 0u);
    put_word(strip_a + 4u, 2u);
    put_word(strip_a + 8u, 3u);
    put_word(strip_a + 12u, 0x8000u);
    put_word(strip_a + 16u, 0x1fffu);
    put_word(strip_b, (2u << 16) | 0u);
    put_word(strip_b + 4u, 3u);
    put_word(strip_b + 8u, 0x1fffu);
}

static MohuWorldEyeView identity_view(void) {
    MohuWorldEyeView view;
    memset(&view, 0, sizeof view);
    view.rotation[0] = view.rotation[4] = view.rotation[8] = 1.0;
    view.fx = view.fy = 100.0;
    view.cx = 160.0;
    view.cy = 120.0;
    view.width = 320;
    view.height = 240;
    return view;
}

int main(void) {
    build_level();
    MohuWorldRequest request;
    memset(&request, 0, sizeof request);
    request.root = 0x80000100u;
    request.vertex_table = 0x80001000u;
    request.vertex_count = 4u;
    request.bypass_masks = 1;

    MohuWorldMesh mesh;
    MohuWorldReport report;
    assert(mohu_world_decode(&request, &mesh, &report) == MOHU_WORLD_OK);
    assert(mesh.triangle_count == 4u);

    uint32_t indices[8];
    MohuWorldSelection selection;
    MohuWorldEyeView view = identity_view();
    assert(mohu_world_select_eye(&mesh, &view, indices, 8u, &selection) ==
           MOHU_WORLD_OK);
    assert(selection.count == 4u && selection.tested == 4u &&
           selection.outside == 0u && selection.unknown == 0u);
    for (unsigned i = 0; i < 4; ++i) assert(indices[i] == i);

    /* Caller far-plane policy is separate from decode and conservative. */
    view.far_plane = 90.0;
    assert(mohu_world_select_eye(&mesh, &view, indices, 8u, &selection) ==
           MOHU_WORLD_OK);
    assert(selection.count == 0u && selection.outside == 4u);
    view.far_plane = 110.0;
    assert(mohu_world_select_eye(&mesh, &view, indices, 8u, &selection) ==
           MOHU_WORLD_OK);
    assert(selection.count == 4u && selection.outside == 0u);
    view.far_plane = -1.0;
    assert(mohu_world_select_eye(&mesh, &view, indices, 8u, &selection) ==
           MOHU_WORLD_REJECT_ARGUMENT);
    view = identity_view();

    view.rotation[0] = -1.0;
    view.rotation[8] = -1.0;
    assert(mohu_world_select_eye(&mesh, &view, indices, 8u, &selection) ==
           MOHU_WORLD_OK);
    assert(selection.count == 0u && selection.outside == 4u);

    view = identity_view();
    view.translation[2] = -1000.0;
    assert(mohu_world_select_eye(&mesh, &view, indices, 8u, &selection) ==
           MOHU_WORLD_OK);
    assert(selection.count == 0u && selection.outside == 4u);

    view.translation[2] = 70000.0;
    assert(mohu_world_select_eye(&mesh, &view, indices, 8u, &selection) ==
           MOHU_WORLD_OK);
    assert(selection.count == 4u && selection.unknown == 4u);

    view = identity_view();
    assert(mohu_world_select_eye(&mesh, &view, indices, 2u, &selection) ==
           MOHU_WORLD_REJECT_TRIANGLE_BUDGET);
    assert(selection.count == 2u && selection.tested == 3u);

    view.fx = 0.0;
    assert(mohu_world_select_eye(&mesh, &view, indices, 8u, &selection) ==
           MOHU_WORLD_REJECT_ARGUMENT);
    assert(mohu_world_select_eye(&mesh, NULL, indices, 8u, &selection) ==
           MOHU_WORLD_REJECT_ARGUMENT);
    view = identity_view();
    assert(mohu_world_select_eye(&mesh, &view, NULL, 4u, &selection) ==
           MOHU_WORLD_REJECT_ARGUMENT);
    assert(mohu_world_select_eye(NULL, &view, indices, 8u, &selection) ==
           MOHU_WORLD_REJECT_ARGUMENT);

    mohu_world_mesh_free(&mesh);
    assert(mohu_world_select_eye(&mesh, &view, indices, 8u, &selection) ==
           MOHU_WORLD_OK);
    assert(selection.count == 0u && selection.tested == 0u);

    puts("PASS: conservative per-eye world selection, far-plane policy, "
         "saturation, budget and argument guards");
    return 0;
}
