#pragma once

#include "mod_plugins.h"
#include "vr_geometry_math.h"

#include <math.h>
#include <stdint.h>

/*
 * Underground level visibility tree layout measured by the frustum probe:
 * int16 AABB at +0..+10, leaf count at +12, masks at +16/+20, and children at
 * +24/+32/+28. Bounds are in camera-relative world space.
 */
static inline int mohu_vr_ray_box(const double origin[3],
                                  const double direction[3],
                                  const int16_t bounds[6],
                                  double tmin, double tmax,
                                  double* t_enter) {
    return psx_vr_ray_box(origin, direction, bounds, tmin, tmax, t_enter);
}
static inline int mohu_vr_ray_tree(uint32_t root,
                                   const double origin[3],
                                   const double direction[3],
                                   const uint32_t masks[2],
                                   int bypass_masks,
                                   double tmax,
                                   double* t_hit,
                                   uint32_t* leaf) {
    if (!root || (root & 3u) || !origin || !direction || !isfinite(tmax) ||
        tmax <= 0.0) {
        return 0;
    }
    uint32_t stack[256];
    unsigned top = 1;
    unsigned visited = 0;
    double best = tmax;
    uint32_t best_leaf = 0;
    stack[0] = root;

    while (top) {
        const uint32_t node = stack[--top];
        const uint32_t offset = node & 0x1fffffffu;
        if (!node || (node & 3u) || offset > 0x200000u - 36u ||
            ++visited > 8192u) {
            return 0;
        }
        if (!bypass_masks && masks &&
            (!(psx_mod_read_word(node + 16u) & masks[0]) ||
             !(psx_mod_read_word(node + 20u) & masks[1]))) {
            continue;
        }

        int16_t bounds[6];
        for (int i = 0; i < 6; ++i) {
            bounds[i] = (int16_t)psx_mod_read_half(node + (uint32_t)i * 2u);
        }
        for (int axis = 0; axis < 3; ++axis) {
            if (bounds[axis] > bounds[axis + 3]) {
                return 0;
            }
        }

        double t_enter = 0.0;
        if (!mohu_vr_ray_box(origin, direction, bounds, 0.0, best, &t_enter)) {
            continue;
        }
        if ((int32_t)psx_mod_read_word(node + 12u) > 0) {
            if (t_enter > 1e-3) {
                best = t_enter;
                best_leaf = node;
            }
            continue;
        }
        static const unsigned child_offsets[3] = {24u, 32u, 28u};
        for (int i = 0; i < 3; ++i) {
            const uint32_t child = psx_mod_read_word(node + child_offsets[i]);
            if (child) {
                if (top == 256u) {
                    return 0;
                }
                stack[top++] = child;
            }
        }
    }

    if (!best_leaf) {
        return 0;
    }
    if (t_hit) {
        *t_hit = best;
    }
    if (leaf) {
        *leaf = best_leaf;
    }
    return 1;
}

/* Ported from the first game; see ALPHA_WEAPON_REPAIRS.md for provenance. */
/* Ray vs triangle (Moeller-Trumbore, no back-face cull). */
static inline int mohu_vr_ray_tri(const double o[3],const double d[3],
                                 const double v0[3],const double v1[3],const double v2[3],
                                 double tmax,double *t_out) {
    if (!o || !d || !v0 || !v1 || !v2 || !t_out || !isfinite(tmax) || tmax<=0) return 0;
    for (unsigned i=0;i<3;i++)
        if (!isfinite(o[i]) || !isfinite(d[i]) || !isfinite(v0[i]) ||
            !isfinite(v1[i]) || !isfinite(v2[i])) return 0;
    const double e1[3]={v1[0]-v0[0],v1[1]-v0[1],v1[2]-v0[2]};
    const double e2[3]={v2[0]-v0[0],v2[1]-v0[1],v2[2]-v0[2]};
    const double p[3]={d[1]*e2[2]-d[2]*e2[1],d[2]*e2[0]-d[0]*e2[2],d[0]*e2[1]-d[1]*e2[0]};
    double det=e1[0]*p[0]+e1[1]*p[1]+e1[2]*p[2];
    if(!isfinite(det) || (det>-1e-9&&det<1e-9))return 0;
    double inv=1.0/det;
    const double t[3]={o[0]-v0[0],o[1]-v0[1],o[2]-v0[2]};
    double u=(t[0]*p[0]+t[1]*p[1]+t[2]*p[2])*inv;
    if(!isfinite(u)||u<0||u>1)return 0;
    const double q[3]={t[1]*e1[2]-t[2]*e1[1],t[2]*e1[0]-t[0]*e1[2],t[0]*e1[1]-t[1]*e1[0]};
    double v=(d[0]*q[0]+d[1]*q[1]+d[2]*q[2])*inv;
    if(!isfinite(v)||v<0||u+v>1)return 0;
    double tt=(e2[0]*q[0]+e2[1]*q[1]+e2[2]*q[2])*inv;
    if(!isfinite(tt)||tt<=1e-3||tt>tmax)return 0;
    *t_out=tt;return 1;
}

static inline int mohu_vr_ray_span(uint32_t p, uint32_t size) {
    return !(p & 3u) && p >= 0x80000000u && p < 0x80200000u &&
           size <= 0x80200000u - p;
}

/* SP 80010CF0 and MP arena 80012A90 consume 8-byte base triangles;
 * MP props 80015608 use 16 bytes.
 * Both use 4-byte strip extensions and a 0x1fff terminator. This differs from the
 * reference's fixed-record reader. count includes the extension triangles.
 * Bit 15 chooses old vertex 2/1 versus 1/2; bits 13/14 are render flags. */
static inline int mohu_vr_ray_strip_tris(uint32_t list, uint32_t count,
    uint32_t table, uint32_t vertex_count, unsigned base_bytes,
    const double o[3], const double d[3],
    double tmax, double* t_hit) {
    if (!o || !d || !t_hit || !isfinite(tmax) || tmax<=0 || !count ||
        count>4096u || (base_bytes!=8u && base_bytes!=16u) || !vertex_count || vertex_count>8192u ||
        !mohu_vr_ray_span(table,vertex_count*8u)) return -1;
    for (unsigned k=0;k<3;k++) if (!isfinite(o[k]) || !isfinite(d[k])) return -1;
    uint32_t cursor=list,idx[3]={0}, emitted=0,bytes=0;
    int base=1,found=0; double best=tmax;
    while (emitted<count) {
        if (base) {
            if (!mohu_vr_ray_span(cursor,base_bytes)) return -1;
            uint32_t a=psx_mod_read_word(cursor),b=psx_mod_read_word(cursor+4u);
            idx[0]=a&0x1fffu;idx[1]=(a>>16)&0x1fffu;idx[2]=b&0x1fffu;
            cursor+=base_bytes; bytes+=base_bytes; base=0;
        } else {
            if (!mohu_vr_ray_span(cursor,4u)) return -1;
            uint32_t code=psx_mod_read_word(cursor)&0xffffu;
            cursor+=4u; bytes+=4u;
            if (code==0x1fffu) {base=1;continue;}
            uint32_t b=idx[1],c=idx[2];
            idx[0]=(code&0x8000u)?c:b;
            idx[1]=(code&0x8000u)?b:c;idx[2]=code&0x1fffu;
        }
        if (bytes>count*20u) return -1;
        double v[9];
        for (unsigned k=0;k<3;k++) {
            if (idx[k]>=vertex_count) return -1;
            for (unsigned c=0;c<3;c++)
                v[k*3+c]=(int16_t)psx_mod_read_half(table+idx[k]*8u+c*2u);
        }
        double t;
        if (mohu_vr_ray_tri(o,d,v,v+3,v+6,best,&t)) {best=t;found=1;}
        ++emitted;
    }
    if (!mohu_vr_ray_span(cursor,4u) || psx_mod_read_half(cursor)!=0x1fffu) return -1;
    if (found) *t_hit=best;
    return found;
}

/* Underground SP 80010CF0 reads 8-byte base records, masks each vertex
 * index with 0x1fff and indexes level+2c's 8-byte vertices. +3c is the vertex
 * count. Origin-inside boxes MUST still test their triangles. Return -1 on
 * malformed data/budget exhaustion, 0 for a valid miss, 1 for an exact hit.
 * No visibility masks: a hand can aim beyond the head's current PVS. */
static inline int mohu_vr_ray_tree_tris(uint32_t root, uint32_t table,
    uint32_t vertex_count, const double o[3], const double d[3],
    double tmax, double* t_hit) {
    if (!o || !d || !t_hit || !isfinite(tmax) || tmax <= 0 ||
        !vertex_count || vertex_count > 8192u ||
        !mohu_vr_ray_span(table, vertex_count * 8u)) return -1;
    double length=0;
    for (unsigned i=0;i<3;i++) {
        if (!isfinite(o[i]) || !isfinite(d[i])) return -1;
        length+=d[i]*d[i];
    }
    if (length<1e-12) return -1;
    uint32_t stack[256]; unsigned top=1,visited=0,triangles=0;
    stack[0]=root;
    double best=tmax; int found=0;
    while (top) {
        uint32_t node=stack[--top];
        if (!mohu_vr_ray_span(node,36u) || ++visited>8192u) return -1;
        int16_t bounds[6];
        for (unsigned i=0;i<6;i++) bounds[i]=(int16_t)psx_mod_read_half(node+2*i);
        for (unsigned i=0;i<3;i++) if (bounds[i]>bounds[i+3]) return -1;
        double enter;
        if (!mohu_vr_ray_box(o,d,bounds,0,best,&enter)) continue;
        int32_t count=(int32_t)psx_mod_read_word(node+12u);
        if (count<0 || count>4096) return -1;
        if (count) {
            uint32_t list=psx_mod_read_word(node+24u);
            if ((triangles+=(unsigned)count)>65536u) return -1;
            double t;
            int hit=mohu_vr_ray_strip_tris(list,(uint32_t)count,table,
                vertex_count,8u,o,d,best,&t);
            if (hit<0) return -1;
            if (hit) {best=t;found=1;}
        } else {
            static const unsigned offsets[3]={24u,32u,28u};
            for (unsigned i=0;i<3;i++) {
                uint32_t child=psx_mod_read_word(node+offsets[i]);
                if (child) {if (top==256u) return -1; stack[top++]=child;}
            }
        }
    }
    if (found) *t_hit=best;
    return found;
}
