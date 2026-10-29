#include "../underground/world_decode.h"

#include <assert.h>
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

#define NODE_SPINE  0x80000100u
#define NODE_LEAF_A 0x80000140u
#define NODE_LEAF_B 0x80000180u
#define STRIP_A     0x80002000u
#define STRIP_B     0x80002100u
#define VERTICES    0x80001000u

static void build_level(void) {
    memset(g_ram, 0, sizeof g_ram);
    put_vertex(VERTICES, 0, -10, -10, 100);
    put_vertex(VERTICES, 1, 10, -10, 100);
    put_vertex(VERTICES, 2, -10, 10, 100);
    put_vertex(VERTICES, 3, 10, 10, 100);

    const int16_t spine[6] = {-100, -100, 0, 100, 100, 1000};
    const int16_t leaf_a[6] = {-20, -20, 100, 20, 20, 120};
    const int16_t leaf_b[6] = {-5, -5, 100, 5, 5, 120};
    put_box(NODE_SPINE, spine);
    put_box(NODE_LEAF_A, leaf_a);
    put_box(NODE_LEAF_B, leaf_b);
    put_word(NODE_SPINE + 12u, 0u);
    put_word(NODE_SPINE + 24u, NODE_LEAF_A);
    put_word(NODE_SPINE + 32u, NODE_LEAF_B);
    put_word(NODE_LEAF_A + 12u, 3u);
    put_word(NODE_LEAF_A + 24u, STRIP_A);
    put_word(NODE_LEAF_B + 12u, 1u);
    put_word(NODE_LEAF_B + 24u, STRIP_B);

    put_word(STRIP_A, (1u << 16) | 0u);
    put_word(STRIP_A + 4u, (0x00CFu << 16) | 2u);
    put_word(STRIP_A + 8u, (1u << 13) | 3u);
    put_word(STRIP_A + 12u, 0x8000u);
    put_word(STRIP_A + 16u, 0x1fffu);

    put_word(STRIP_B, (2u << 16) | 0u);
    put_word(STRIP_B + 4u, 3u);
    put_word(STRIP_B + 8u, 0x1fffu);
}

static MohuWorldRequest request(void) {
    MohuWorldRequest r;
    memset(&r, 0, sizeof r);
    r.root = NODE_SPINE;
    r.vertex_table = VERTICES;
    r.vertex_count = 4u;
    r.generation = 7u;
    r.bypass_masks = 1;
    return r;
}

static void check_bounds(const MohuWorldMesh *mesh) {
    assert(mesh->bounds_min[0] == -10 && mesh->bounds_min[1] == -10 &&
           mesh->bounds_min[2] == 100);
    assert(mesh->bounds_max[0] == 10 && mesh->bounds_max[1] == 10 &&
           mesh->bounds_max[2] == 100);
    assert(mesh->leaf_bounds_min[0] == -20 && mesh->leaf_bounds_min[1] == -20 &&
           mesh->leaf_bounds_min[2] == 100);
    assert(mesh->leaf_bounds_max[0] == 20 && mesh->leaf_bounds_max[1] == 20 &&
           mesh->leaf_bounds_max[2] == 120);
}

static void test_full_decode(void) {
    build_level();
    MohuWorldRequest r = request();
    MohuWorldMesh mesh;
    MohuWorldReport report;
    assert(mohu_world_decode(&r, &mesh, &report) == MOHU_WORLD_OK);
    assert(report.nodes_visited == 3u && report.leaves_visited == 2u);
    assert(mesh.generation == 7u);
    assert(mesh.vertex_count == 4u && mesh.leaf_count == 2u);
    assert(mesh.triangle_count == 4u && report.triangles_decoded == 4u);
    assert(mesh.triangle_capacity >= mesh.triangle_count);
    assert(mesh.materials_decoded == 0u && mesh.material_tokens == 4u);
    check_bounds(&mesh);

    const uint32_t expected[4][3] = {{0, 1, 2}, {1, 2, 3}, {3, 2, 0},
                                     {0, 2, 3}};
    for (unsigned i = 0; i < 4; ++i)
        for (unsigned k = 0; k < 3; ++k)
            assert(mesh.triangles[i].vertex[k] == expected[i][k]);

    assert(!mesh.triangles[0].is_extension && mesh.triangles[0].extension_word == 0u);
    assert(mesh.triangles[0].source_address == STRIP_A);
    assert(mesh.triangles[0].base_word[0] == ((1u << 16) | 0u));
    assert(mesh.triangles[0].record_index == 0x00CFu);
    assert(mesh.triangles[1].record_index == 0x00CFu);
    assert(mesh.triangles[3].record_index == 0u);
    assert(mesh.triangles[1].is_extension);
    assert(mesh.triangles[1].extension_word == ((1u << 13) | 3u));
    assert(mesh.triangles[1].render_flags == 1u);
    assert(!mesh.triangles[1].winding_swapped);
    assert(mesh.triangles[2].winding_swapped);
    assert(mesh.triangles[2].render_flags == 0u);
    assert(mesh.triangles[3].source_address == STRIP_B);

    /* Deterministic traversal: a second decode is byte-identical. */
    MohuWorldMesh again;
    assert(mohu_world_decode(&r, &again, &report) == MOHU_WORLD_OK);
    assert(again.triangle_count == mesh.triangle_count);
    assert(!memcmp(again.triangles, mesh.triangles,
                   mesh.triangle_count * sizeof *mesh.triangles));
    mohu_world_mesh_free(&again);
    mohu_world_mesh_free(&mesh);
    assert(!mesh.vertices && !mesh.triangles && !mesh.triangle_count);
}

static void test_masks(void) {
    build_level();
    put_word(NODE_SPINE + 16u, 1u);
    put_word(NODE_SPINE + 20u, 1u);
    put_word(NODE_LEAF_A + 16u, 1u);
    put_word(NODE_LEAF_A + 20u, 1u);
    put_word(NODE_LEAF_B + 16u, 2u);
    put_word(NODE_LEAF_B + 20u, 1u);

    MohuWorldRequest r = request();
    MohuWorldMesh mesh;
    MohuWorldReport report;
    r.bypass_masks = 0;
    r.masks[0] = 1u;
    r.masks[1] = 1u;
    assert(mohu_world_decode(&r, &mesh, &report) == MOHU_WORLD_OK);
    assert(mesh.triangle_count == 3u && mesh.leaf_count == 1u);
    check_bounds(&mesh);
    mohu_world_mesh_free(&mesh);

    r.bypass_masks = 1;
    assert(mohu_world_decode(&r, &mesh, &report) == MOHU_WORLD_OK);
    assert(mesh.triangle_count == 4u && mesh.leaf_count == 2u);
    mohu_world_mesh_free(&mesh);
}

static void test_rejections(void) {
    MohuWorldRequest r = request();
    MohuWorldMesh mesh;
    MohuWorldReport report;

    assert(mohu_world_decode(NULL, &mesh, &report) ==
           MOHU_WORLD_REJECT_ARGUMENT);

    build_level();
    r.root = 0x80000002u;
    assert(mohu_world_decode(&r, &mesh, &report) == MOHU_WORLD_REJECT_TREE_ROOT);
    r.root = 0u;
    assert(mohu_world_decode(&r, &mesh, &report) == MOHU_WORLD_REJECT_TREE_ROOT);
    assert(!mesh.vertices && !mesh.triangle_count);

    r = request();
    r.vertex_table = 0x801ff000u;
    r.vertex_count = MOHU_WORLD_MAX_VERTICES;
    assert(mohu_world_decode(&r, &mesh, &report) ==
           MOHU_WORLD_REJECT_VERTEX_TABLE);

    r = request();
    build_level();
    put_word(NODE_LEAF_A + 12u, 5000u);
    assert(mohu_world_decode(&r, &mesh, &report) ==
           MOHU_WORLD_REJECT_LEAF_COUNT);
    assert(report.node == NODE_LEAF_A && !mesh.triangles);

    r = request();
    build_level();
    const int16_t malformed[6] = {10, 0, 0, -10, 0, 0};
    put_box(NODE_LEAF_A, malformed);
    assert(mohu_world_decode(&r, &mesh, &report) ==
           MOHU_WORLD_REJECT_NODE_BOUNDS);

    r = request();
    build_level();
    put_word(STRIP_A + 8u, (1u << 13) | 7u);
    assert(mohu_world_decode(&r, &mesh, &report) ==
           MOHU_WORLD_REJECT_VERTEX_INDEX);
    assert(report.detail == 7u && !mesh.vertices);

    r = request();
    build_level();
    put_word(STRIP_A + 16u, 0u);
    assert(mohu_world_decode(&r, &mesh, &report) ==
           MOHU_WORLD_REJECT_STRIP_TERMINATOR);

    r = request();
    build_level();
    put_word(NODE_LEAF_A + 24u, 0x801ffffcu);
    assert(mohu_world_decode(&r, &mesh, &report) ==
           MOHU_WORLD_REJECT_STRIP_SPAN);

    build_level();
    r = request();
    r.max_triangles = 1u;
    assert(mohu_world_decode(&r, &mesh, &report) ==
           MOHU_WORLD_REJECT_TRIANGLE_BUDGET);
    assert(report.triangles_decoded == 1u && !mesh.triangles);

    build_level();
    r = request();
    r.max_leaves = 1u;
    assert(mohu_world_decode(&r, &mesh, &report) ==
           MOHU_WORLD_REJECT_LEAF_BUDGET);

    build_level();
    put_word(NODE_SPINE + 24u, NODE_SPINE);
    put_word(NODE_SPINE + 32u, 0u);
    r = request();
    assert(mohu_world_decode(&r, &mesh, &report) ==
           MOHU_WORLD_REJECT_TREE_BUDGET);
    assert(report.nodes_visited > 1u && !mesh.triangles);

    for (unsigned i = 0; i <= MOHU_WORLD_REJECT_ALLOCATION; ++i)
        assert(strcmp(mohu_world_status_name((MohuWorldStatus)i), "unknown"));
    assert(!strcmp(mohu_world_status_name(MOHU_WORLD_OK), "ok"));
    assert(!strcmp(mohu_world_status_name(MOHU_WORLD_REJECT_VERTEX_INDEX),
                   "vertex_index"));
}

static void test_cache(void) {
    build_level();
    MohuWorldRequest r = request();
    MohuWorldCache cache;
    memset(&cache, 0, sizeof cache);
    const MohuWorldMesh *mesh = NULL;
    int reused = -1;

    assert(mohu_world_cache_acquire(&cache, &r, 1u, &mesh, &reused) ==
           MOHU_WORLD_OK);
    assert(!reused && cache.misses == 1u && mesh && mesh->triangle_count == 4u);
    const MohuWorldMesh *first = mesh;
    assert(mesh->source_fingerprint != 0u);
    assert(mohu_world_source_unchanged(mesh));

    assert(mohu_world_cache_acquire(&cache, &r, 1u, &mesh, &reused) ==
           MOHU_WORLD_OK);
    assert(reused && mesh == first && cache.hits == 1u && cache.misses == 1u);

    assert(mohu_world_cache_acquire(&cache, &r, 2u, &mesh, &reused) ==
           MOHU_WORLD_OK);
    assert(reused && mesh == first && cache.validations == 1u &&
           cache.hits == 2u);

    put_word(0x80003000u, 0xdeadbeefu);
    assert(mohu_world_cache_acquire(&cache, &r, 3u, &mesh, &reused) ==
           MOHU_WORLD_OK);
    assert(reused && mesh == first && cache.validations == 2u);

    put_word(STRIP_B + 4u, 2u);
    assert(mohu_world_cache_acquire(&cache, &r, 4u, &mesh, &reused) ==
           MOHU_WORLD_OK);
    assert(!reused && mesh && cache.stale == 1u && cache.misses == 2u);
    assert(mesh->triangles[3].vertex[2] == 2u);
    assert(mesh->source_fingerprint != 0u);

    r.generation = 8u;
    assert(mohu_world_cache_acquire(&cache, &r, 5u, &mesh, &reused) ==
           MOHU_WORLD_OK);
    assert(!reused && cache.misses == 3u);

    mohu_world_cache_free(&cache);
    assert(!cache.entries[0].mesh.triangles);
    r.generation = 7u;
    assert(mohu_world_cache_acquire(&cache, &r, 6u, &mesh, &reused) ==
           MOHU_WORLD_OK);
    assert(!reused && cache.misses == 1u);
    mohu_world_cache_free(&cache);
}

int main(void) {
    test_full_decode();
    test_masks();
    test_rejections();
    test_cache();
    puts("PASS: static-world leaf/strip decode, winding, masks, bounds, "
         "named rejections and snapshot cache");
    return 0;
}
