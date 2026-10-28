#include "../underground/raycast.h"

#include <assert.h>
#include <math.h>
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

static void set_word(uint32_t address, uint32_t value) {
    memcpy(g_ram + address, &value, sizeof value);
}

static void set_bounds(uint32_t address, const int16_t bounds[6]) {
    memcpy(g_ram + address, bounds, 12u);
}

static void set_leaf(uint32_t address, int16_t z0, int16_t z1) {
    const int16_t bounds[6] = {-10, -10, z0, 10, 10, z1};
    set_bounds(address, bounds);
    set_word(address + 12u, 1u);
}

static void set_spine(uint32_t address) {
    const int16_t bounds[6] = {-100, -100, 0, 100, 100, 1000};
    set_bounds(address, bounds);
    set_word(address + 12u, 0u);
}

int main(void) {
    const int16_t box[6] = {-10, -10, 100, 10, 10, 120};
    const double forward[3] = {0.0, 0.0, 1.0};
    const double sideways[3] = {1.0, 0.0, 0.0};
    const double origin[3] = {0.0, 0.0, 0.0};
    const double inside[3] = {0.0, 0.0, 110.0};
    const double behind[3] = {0.0, 0.0, 300.0};
    const double outside[3] = {0.0, 20.0, 110.0};
    const double side[3] = {100.0, 0.0, 0.0};
    double t = 0.0;

    assert(mohu_vr_ray_box(origin, forward, box, 0.0, 1000.0, &t) &&
           t > 99.0 && t < 101.0);
    assert(!mohu_vr_ray_box(behind, forward, box, 0.0, 1000.0, &t));
    assert(mohu_vr_ray_box(inside, forward, box, 0.0, 1000.0, &t) &&
           t == 0.0);
    assert(mohu_vr_ray_box(inside, sideways, box, 0.0, 1000.0, &t));
    assert(!mohu_vr_ray_box(outside, sideways, box, 0.0, 1000.0, &t));
    assert(!mohu_vr_ray_box(side, forward, box, 0.0, 1000.0, &t));
    assert(!mohu_vr_ray_box(origin, forward, box, 0.0, 50.0, &t));

    memset(g_ram, 0, sizeof g_ram);
    set_spine(0x100u);
    set_leaf(0x140u, 100, 120);
    set_leaf(0x180u, 200, 220);
    set_leaf(0x1c0u, 300, 320);
    set_word(0x100u + 24u, 0x140u);
    set_word(0x100u + 32u, 0x180u);
    set_word(0x100u + 28u, 0x1c0u);

    uint32_t leaf = 0u;
    assert(mohu_vr_ray_tree(0x100u, origin, forward, NULL, 1, 1000.0,
                            &t, &leaf) &&
           leaf == 0x140u && t > 99.0 && t < 101.0);
    assert(!mohu_vr_ray_tree(0x100u, origin, forward, NULL, 1, 50.0,
                             &t, &leaf));
    assert(mohu_vr_ray_tree(0x140u, origin, forward, NULL, 1, 1000.0,
                            &t, &leaf) &&
           leaf == 0x140u);

    set_word(0x100u + 16u, 15u);
    set_word(0x100u + 20u, 15u);
    set_word(0x140u + 16u, 1u);
    set_word(0x140u + 20u, 2u);
    set_word(0x180u + 16u, 4u);
    set_word(0x180u + 20u, 2u);
    const uint32_t hit_masks[2] = {1u, 2u};
    const uint32_t miss_masks[2] = {4u, 2u};
    assert(mohu_vr_ray_tree(0x100u, origin, forward, hit_masks, 0, 1000.0,
                            &t, &leaf) &&
           leaf == 0x140u);
    assert(mohu_vr_ray_tree(0x100u, origin, forward, miss_masks, 0, 1000.0,
                            &t, &leaf) &&
           leaf == 0x180u);

    const double in_leaf[3] = {0.0, 0.0, 110.0};
    assert(mohu_vr_ray_tree(0x100u, in_leaf, forward, NULL, 1, 1000.0,
                            &t, &leaf) &&
           leaf == 0x180u);

    const int16_t malformed[6] = {10, 0, 0, -10, 0, 0};
    set_word(0x140u + 12u, 0u);
    set_bounds(0x140u, malformed);
    assert(!mohu_vr_ray_tree(0x100u, origin, forward, NULL, 1, 1000.0,
                             &t, &leaf));

    /* Exact surfaces differ from the broad-phase boxes. Exercise both native
     * strip schemas, winding, the origin-inside case and atomic invalid data. */
    memset(g_ram,0,sizeof g_ram);
    const int16_t vertices[4][4]={{-10,-10,110,0},{10,-10,110,0},
                                 {-10,10,110,0},{10,10,110,0}};
    memcpy(g_ram+0x1000,vertices,sizeof vertices);
    set_leaf(0x100,100,120);
    set_word(0x118,0x80002000u);
    set_word(0x2000,(1u<<16)|0x2000u); /* render flag masked from vertex 0 */
    set_word(0x2004,2u);
    set_word(0x2008,0x1fff1fffu);
    const double left[3]={-5,-5,0}, in_surface_box[3]={-5,-5,105};
    assert(mohu_vr_ray_tree_tris(0x80000100u,0x80001000u,4,left,forward,1000,&t)==1 && t==110);
    assert(mohu_vr_ray_tree_tris(0x80000100u,0x80001000u,4,in_surface_box,forward,1000,&t)==1 && t==5);
    assert(mohu_vr_ray_tree_tris(0x80000100u,0x80001000u,4,left,forward,100,&t)==0);
    const double upper_right[3]={5,5,0};
    assert(mohu_vr_ray_tree_tris(0x80000100u,0x80001000u,4,upper_right,forward,1000,&t)==0);
    set_word(0x100+12,2u);
    set_word(0x2008,3u);set_word(0x200c,0x1fffu);
    assert(mohu_vr_ray_tree_tris(0x80000100u,0x80001000u,4,upper_right,forward,1000,&t)==1 && t==110);
    set_word(0x2008,0x8003u); /* reversed strip winding, still two-sided */
    assert(mohu_vr_ray_tree_tris(0x80000100u,0x80001000u,4,upper_right,forward,1000,&t)==1 && t==110);
    /* MP's same indices have eight extra bytes in the base record. */
    set_word(0x2010,3u);set_word(0x2014,0x1fffu);
    assert(mohu_vr_ray_strip_tris(0x80002000u,2u,0x80001000u,4u,16u,upper_right,forward,1000,&t)==1 && t==110);
    t=17;
    set_word(0x2014,0u);
    assert(mohu_vr_ray_strip_tris(0x80002000u,2u,0x80001000u,4u,16u,upper_right,forward,1000,&t)==-1 && t==17);
    set_word(0x2008,4u); /* out-of-range extension vertex */
    assert(mohu_vr_ray_tree_tris(0x80000100u,0x80001000u,4,left,forward,1000,&t)==-1 && t==17);
    assert(mohu_vr_ray_tree_tris(0x80000100u,0x801ffffcu,4,left,forward,1000,&t)==-1);
    assert(mohu_vr_ray_tree_tris(0x80000100u,0x80001000u,4,left,forward,NAN,&t)==-1);
    assert(mohu_vr_ray_tree_tris(0x80000100u,0x80001000u,4,left,(double[3]){0},1000,&t)==-1);
    set_spine(0x100);set_word(0x118,0x80000100u); /* cycle consumes bounded traversal budget */
    assert(mohu_vr_ray_tree_tris(0x80000100u,0x80001000u,4,left,forward,1000,&t)==-1);

    puts("PASS: raycast broad phase, exact SP/MP strips, inside, malformed and budget guards");
    return 0;
}
