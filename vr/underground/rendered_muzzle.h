#pragma once

#include "weapon_markers.h"
#include "mod_plugins.h"
#include <math.h>

typedef struct {
    double base[3][3]; /* grip, animated tip, axis base, in base-camera units */
    double eye[3][3];  /* the same points after the actual scoped render view */
    double base_axis[3], eye_axis[3];
} MohuVrRenderedPoints;

typedef struct {
    MohuVrMarkerSample animated, canonical;
    MohuVrRenderedPoints points, aim;
    PSXModRenderView view;
    uint32_t attempt, eye, control[8], native_control[8], camera[8];
    uint64_t camera_cycle;
    int32_t position[3], angles[3]; /* W5 helper on this draw's copied data */
    int valid, restored, canonical_equal;
} MohuVrRenderedMuzzle;

static inline int mohu_vr_rendered_pair_ready(
    const MohuVrRenderedMuzzle pair[2], int rendered) {
    return pair && rendered && pair[0].valid && pair[1].valid &&
        pair[0].restored && pair[1].restored &&
        pair[0].eye==0u && pair[1].eye==1u &&
        pair[0].attempt==pair[1].attempt &&
        !memcmp(&pair[0].animated.key,&pair[1].animated.key,
                sizeof(MohuVrMarkerKey));
}

/* Same composition as the reference laser capture: view * applied model
 * affine. The title adapter supplies animated markers and quantized RT/TR;
 * eye translation is applied once, after model placement. No static muzzle. */
static inline int mohu_vr_rendered_points(const uint32_t control[8],
    const PSXModRenderView* view, const double points[3][3],
    MohuVrRenderedPoints* out) {
    if (!control || !view || !points || !out ||
        view->struct_size != sizeof *view || view->precise > 1u) return 0;
    MohuVrRenderedPoints result = {0};
    for (unsigned p=0; p<3; ++p) {
        for (unsigned row=0; row<3; ++row) {
            result.base[p][row]=(int32_t)control[5u+row];
            for (unsigned col=0; col<3; ++col) {
                const unsigned i=row*3u+col;
                if (!isfinite(points[p][col])) return 0;
                result.base[p][row]+=(int16_t)(control[i/2u]>>((i&1u)*16u)) /
                    4096.0 * points[p][col];
            }
        }
        for (unsigned row=0; row<3; ++row) {
            result.eye[p][row]=view->precise ?
                view->translation_precise[row] : view->translation[row];
            for (unsigned col=0; col<3; ++col) {
                const unsigned i=row*3u+col;
                const double r=view->precise ? view->rotation[i] :
                    view->rotation_q12[i]/4096.0;
                result.eye[p][row]+=r*result.base[p][col];
            }
            if (!isfinite(result.eye[p][row])) return 0;
        }
    }
    double lengths[2]={0};
    for (unsigned axis=0; axis<3; ++axis) {
        result.base_axis[axis]=result.base[1][axis]-result.base[2][axis];
        result.eye_axis[axis]=result.eye[1][axis]-result.eye[2][axis];
        lengths[0]+=result.base_axis[axis]*result.base_axis[axis];
        lengths[1]+=result.eye_axis[axis]*result.eye_axis[axis];
    }
    for (unsigned i=0; i<2; ++i)
        if (!isfinite(lengths[i]) || lengths[i]<0.0001) return 0;
    for (unsigned axis=0; axis<3; ++axis) {
        result.base_axis[axis]/=sqrt(lengths[0]);
        result.eye_axis[axis]/=sqrt(lengths[1]);
    }
    *out=result;
    return 1;
}
