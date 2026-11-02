#include "../underground/world_project.h"

#include "mod_plugins.h"

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

static MohuWorldMesh decode_four_triangles(void) {
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

    MohuWorldRequest request;
    memset(&request, 0, sizeof request);
    request.root = spine;
    request.vertex_table = table;
    request.vertex_count = 4u;
    request.bypass_masks = 1;
    MohuWorldMesh mesh;
    MohuWorldReport report;
    assert(mohu_world_decode(&request, &mesh, &report) == MOHU_WORLD_OK);
    assert(mesh.triangle_count == 4u);
    return mesh;
}

static MohuWorldMesh decode_clipped_triangle(void) {
    memset(g_ram, 0, sizeof g_ram);
    const uint32_t table = 0x80001000u, root = 0x80000100u;
    const uint32_t strip = 0x80002000u;
    put_vertex(table, 0, -10, -10, 10);
    put_vertex(table, 1, 10, -10, -10);
    put_vertex(table, 2, 10, 10, 10);
    const int16_t box[6] = {-10, -10, -10, 10, 10, 10};
    put_box(root, box);
    put_word(root + 12u, 1u);
    put_word(root + 24u, strip);
    put_word(strip, (1u << 16) | 0u);
    put_word(strip + 4u, 2u);
    put_word(strip + 8u, 0x1fffu);

    MohuWorldRequest request;
    memset(&request, 0, sizeof request);
    request.root = root;
    request.vertex_table = table;
    request.vertex_count = 3u;
    request.bypass_masks = 1;
    MohuWorldMesh mesh;
    MohuWorldReport report;
    assert(mohu_world_decode(&request, &mesh, &report) == MOHU_WORLD_OK);
    assert(mesh.triangle_count == 1u);
    return mesh;
}

static void test_adapter(void) {
    PSXModRenderView raw;
    memset(&raw, 0, sizeof raw);
    raw.projection = 1;
    raw.fx_q16 = 100 << 16;
    raw.fy_q16 = 100 << 16;
    raw.precise = 1;
    raw.rotation[0] = raw.rotation[4] = raw.rotation[8] = 1.0;
    raw.translation_precise[2] = 3.0;

    MohuWorldEyeView view;
    assert(mohu_world_eye_from_view(&raw, 160.0, 120.0, 320, 240, &view));
    assert(view.fx == 100.0 && view.fy == 100.0);
    assert(view.cx == 160.0 && view.cy == 120.0);
    assert(view.rotation[0] == 1.0 && view.translation[2] == 3.0);
    assert(view.width == 320 && view.height == 240);

    raw.precise = 0;
    raw.projection = 0;
    raw.rotation_q12[0] = raw.rotation_q12[4] = raw.rotation_q12[8] = 4096;
    raw.translation[0] = 5;
    assert(mohu_world_eye_from_view(&raw, 160.0, 120.0, 320, 240, &view));
    assert(view.fx == 400.0 && view.translation[0] == 5.0);
    assert(view.rotation[0] == 1.0);

    raw.projection = 1;
    raw.fx_q16 = 0;
    assert(!mohu_world_eye_from_view(&raw, 160.0, 120.0, 320, 240, &view));
    assert(!mohu_world_eye_from_view(NULL, 160.0, 120.0, 320, 240, &view));
    assert(!mohu_world_eye_from_view(&raw, 160.0, 120.0, 0, 240, &view));
}

static void test_projection(void) {
    MohuWorldMesh mesh = decode_four_triangles();
    MohuWorldEyeView view = identity_view();
    MohuWorldProjectedTriangle out[8];
    MohuWorldProjection stats;

    assert(mohu_world_project_eye(&mesh, &view, 1.0, out, 8u, &stats) ==
           MOHU_WORLD_OK);
    assert(stats.tested == 4u && stats.emitted == 4u && stats.dropped == 0u &&
           stats.clipped == 0u);
    for (unsigned i = 0; i < 4; ++i) {
        assert(out[i].count == 3u && out[i].triangle == i);
    }
    assert(fabs(out[0].vertex[0].screen[0] - 150.0) < 1e-9);
    assert(fabs(out[0].vertex[0].screen[1] - 110.0) < 1e-9);
    assert(fabs(out[0].vertex[1].screen[0] - 170.0) < 1e-9);
    assert(fabs(out[0].vertex[2].screen[1] - 130.0) < 1e-9);

    view.rotation[0] = -1.0;
    view.rotation[8] = -1.0;
    assert(mohu_world_project_eye(&mesh, &view, 1.0, out, 8u, &stats) ==
           MOHU_WORLD_OK);
    assert(stats.dropped == 4u && stats.emitted == 0u);

    view = identity_view();
    assert(mohu_world_project_eye(&mesh, &view, 1.0, out, 2u, &stats) ==
           MOHU_WORLD_REJECT_TRIANGLE_BUDGET);
    assert(stats.emitted == 2u && stats.tested == 3u);

    assert(mohu_world_project_eye(&mesh, &view, 0.0, out, 8u, &stats) ==
           MOHU_WORLD_REJECT_ARGUMENT);
    view.fx = 0.0;
    assert(mohu_world_project_eye(&mesh, &view, 1.0, out, 8u, &stats) ==
           MOHU_WORLD_REJECT_ARGUMENT);
    mohu_world_mesh_free(&mesh);
}

static void test_near_clip(void) {
    MohuWorldMesh mesh = decode_clipped_triangle();
    MohuWorldEyeView view = identity_view();
    MohuWorldProjectedTriangle out[2];
    MohuWorldProjection stats;
    assert(mohu_world_project_eye(&mesh, &view, 1.0, out, 2u, &stats) ==
           MOHU_WORLD_OK);
    assert(stats.tested == 1u && stats.emitted == 1u && stats.clipped == 1u &&
           stats.dropped == 0u);
    assert(out[0].count == 4u);
    for (unsigned i = 0; i < 4; ++i) {
        assert(out[0].vertex[i].eye[2] > 0.0);
        assert(isfinite(out[0].vertex[i].screen[0]));
        assert(isfinite(out[0].vertex[i].screen[1]));
    }
    mohu_world_mesh_free(&mesh);
}

static void test_drawlist(void) {
    MohuWorldMesh mesh = decode_four_triangles();
    MohuWorldEyeView view = identity_view();
    MohuWorldProjectedTriangle projected[8];
    MohuWorldProjection projection;
    assert(mohu_world_project_eye(&mesh, &view, 1.0, projected, 8u,
                                  &projection) == MOHU_WORLD_OK);
    assert(projection.emitted == 4u);

    MohuWorldScreenTriangle triangles[8];
    MohuWorldDrawList list;
    assert(mohu_world_drawlist(projected, projection.emitted, triangles, 8u,
                               &list) == MOHU_WORLD_OK);
    assert(list.polygons == 4u && list.triangles == 4u && list.degenerate == 0u);
    assert(triangles[0].source_triangle == 0u);
    assert(fabs(triangles[0].screen[0][0] - 150.0) < 1e-9);
    assert(fabs(triangles[0].screen[0][1] - 110.0) < 1e-9);
    assert(fabs(triangles[0].screen[1][0] - 170.0) < 1e-9);
    assert(fabs(triangles[0].screen[2][1] - 130.0) < 1e-9);

    assert(mohu_world_drawlist(projected, projection.emitted, triangles, 1u,
                               &list) == MOHU_WORLD_REJECT_TRIANGLE_BUDGET);
    assert(list.triangles == 1u && list.polygons == 2u);

    MohuWorldProjectedTriangle bad[1];
    memset(bad, 0, sizeof bad);
    bad[0].count = 2u;
    assert(mohu_world_drawlist(bad, 1u, triangles, 8u, &list) == MOHU_WORLD_OK);
    assert(list.triangles == 0u && list.degenerate == 1u);

    bad[0].count = 3u;
    bad[0].vertex[0].screen[0] = NAN;
    assert(mohu_world_drawlist(bad, 1u, triangles, 8u, &list) == MOHU_WORLD_OK);
    assert(list.triangles == 0u && list.polygons == 1u && list.degenerate == 1u);

    assert(mohu_world_drawlist(NULL, 1u, triangles, 8u, &list) ==
           MOHU_WORLD_REJECT_ARGUMENT);
    mohu_world_mesh_free(&mesh);

    mesh = decode_clipped_triangle();
    view = identity_view();
    assert(mohu_world_project_eye(&mesh, &view, 1.0, projected, 8u,
                                  &projection) == MOHU_WORLD_OK);
    assert(projection.emitted == 1u && projected[0].count == 4u);
    assert(mohu_world_drawlist(projected, projection.emitted, triangles, 8u,
                               &list) == MOHU_WORLD_OK);
    assert(list.polygons == 1u && list.triangles == 2u && list.degenerate == 0u);
    for (unsigned i = 0; i < 2u; ++i)
        for (unsigned v = 0; v < 3u; ++v)
            assert(isfinite(triangles[i].screen[v][0]) &&
                   isfinite(triangles[i].screen[v][1]));
    mohu_world_mesh_free(&mesh);
}

int main(void) {
    test_adapter();
    test_projection();
    test_near_clip();
    test_drawlist();
    puts("PASS: per-eye view adapter, host transform/projection, near clip, "
         "draw-list triangulation, budget and argument guards");
    return 0;
}
