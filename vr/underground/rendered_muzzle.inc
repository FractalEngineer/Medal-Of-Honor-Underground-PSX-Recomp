/* W6.1 host-only snapshots. Included after the existing canonical sampler and
 * shot helpers. No second native producer, guest writes, or laser submission. */
static bool g_muzzle_enabled, g_muzzle_requested, g_muzzle_valid;
static uint32_t g_muzzle_sequence, g_muzzle_rejected;
static MohuVrRenderedMuzzle g_muzzle_pending[2], g_muzzle_pair[2];

static void vr_muzzle_invalidate(void) {
    g_muzzle_valid=false;
    memset(g_muzzle_pending,0,sizeof g_muzzle_pending);
}

static void vr_muzzle_begin(void) {
    if (g_muzzle_enabled) memset(g_muzzle_pending,0,sizeof g_muzzle_pending);
}

static void vr_muzzle_finish(int rendered) {
    if (!g_muzzle_enabled) return;
    if (!mohu_vr_rendered_pair_ready(g_muzzle_pending,rendered)) {
        g_muzzle_valid=false;
        ++g_muzzle_rejected;
        return;
    }
    if (g_muzzle_requested) {
        memcpy(g_muzzle_pair,g_muzzle_pending,sizeof g_muzzle_pair);
        ++g_muzzle_sequence;
        g_muzzle_valid=true;
        g_muzzle_requested=false;
    }
}

static void vr_muzzle_draw(CPUState* cpu) {
    if (!g_muzzle_enabled || !cpu || !g_stereo_active || !g_stereo_mp ||
        g_stereo_current_eye>1u || !g_weapon_capture_frame_valid ||
        !g_weapon_capture_eye_view_valid || !g_weapon_capture_tracked_valid ||
        !g_weapon_delta_valid || !g_weapon_absolute ||
        !vr_weapon_calibrated_active()) return;
    MohuVrMarkerKey key;
    if (!vr_marker_model_key(&key) || key.object!=g_weapon_profile_last_object ||
        key.id!=g_weapon_profile_last_id || !g_shot_camera_valid ||
        g_shot_camera_owner!=key.owner || g_shot_camera_cycle>psx_cycle_count ||
        psx_cycle_count-g_shot_camera_cycle>MOHU_VR_SHOT_MAX_CAMERA_AGE) return;
    MohuVrRenderedMuzzle result={0};
    const MohuVrMarkerGroup* group=mohu_vr_marker_group(key.id);
    result.animated.key=key;
    result.animated.cycle=psx_cycle_count;
    result.animated.sequence=g_weapon_capture_sequence;
    result.animated.vertex_count=group->counts[0]+group->counts[1]+group->counts[2];
    for (unsigned i=0; i<result.animated.vertex_count; ++i) {
        unsigned j=0;
        for (; j<g_weapon_capture_frame_vertex_count; ++j)
            if (g_weapon_capture_frame_nodes[j]==group->vertices[i][0] &&
                g_weapon_capture_frame_indices[j]==group->vertices[i][1]) break;
        if (j==g_weapon_capture_frame_vertex_count) return;
        memcpy(result.animated.vertices[i],g_weapon_capture_frame_animated[j],
               sizeof result.animated.vertices[i]);
    }
    if (!mohu_vr_marker_points(group,result.animated.vertices,
            result.animated.vertex_count,result.animated.points)) return;
    result.animated.valid=1;
    result.attempt=g_stereo_attempts;
    result.eye=g_stereo_current_eye;
    result.view=g_weapon_capture_eye_view;
    memcpy(result.control,cpu->gte_ctrl,sizeof result.control);
    memcpy(result.native_control,g_weapon_capture_native_control,sizeof result.native_control);
    memcpy(result.camera,g_shot_camera,sizeof result.camera);
    result.camera_cycle=g_shot_camera_cycle;
    result.canonical=g_marker_cache;
    result.canonical_equal=mohu_vr_marker_usable(&result.canonical,&key,psx_cycle_count) &&
        result.canonical.vertex_count==result.animated.vertex_count &&
        !memcmp(result.canonical.vertices,result.animated.vertices,
                result.animated.vertex_count*sizeof result.animated.vertices[0]);
    if (!mohu_vr_rendered_points(result.control,&result.view,
            result.animated.points,&result.points)) return;
    const MohuVrWeaponCalibration* calibration=mohu_vr_weapon_calibration_find(key.id);
    if (!calibration) return;
    double fixed[3][3];
    for (unsigned i=0; i<3; ++i) {
        fixed[0][i]=calibration->grip_pivot[i];
        fixed[1][i]=calibration->muzzle[i];
        fixed[2][i]=calibration->muzzle[i]-calibration->forward[i];
    }
    if (!mohu_vr_rendered_points(result.control,&result.view,fixed,&result.aim)) return;
    double camera[9], inverse[9], translation[3];
    for (unsigned i=0; i<9; ++i)
        camera[i]=(int16_t)(result.camera[i/2]>>((i&1u)*16u))/4096.0;
    for (unsigned i=0; i<3; ++i) {
        translation[i]=(int32_t)result.camera[5+i];
    }
    if (!mohu_vr_laser_inverse(camera,inverse) ||
        !mohu_vr_weapon_muzzle_shot(result.control,calibration,
            inverse,translation,result.position,result.angles)) return;
    result.valid=1;
    g_muzzle_pending[result.eye]=result;
}

static int vr_muzzle_usable(void) {
    MohuVrMarkerKey key;
    PSXModOpenXRHands hands={0}; hands.struct_size=sizeof hands;
    double rotation[9], translation[3];
    return g_muzzle_enabled && g_muzzle_valid && !g_weapon_force_tracking_loss &&
        vr_marker_model_key(&key) &&
        !memcmp(&key,&g_muzzle_pair[0].animated.key,sizeof key) &&
        psx_mod_openxr_hands(&hands) && mohu_vr_weapon_track_delta(
            &hands,g_openxr_units_per_meter,rotation,translation);
}

/* Append bounded numeric arrays; diagnostics never returns a partial JSON. */
static int vr_muzzle_command(const char* args, char* reply, int cap) {
    if (!args || !reply || cap<2) return -1;
    unsigned eye=0, start=0; int end=0;
    if (!strcmp(args,"capture")) {
        g_muzzle_enabled=g_muzzle_requested=true;
        vr_muzzle_invalidate();
    } else if (!strcmp(args,"stop")) {
        g_muzzle_enabled=g_muzzle_requested=false;
        vr_muzzle_invalidate();
    } else if (sscanf(args,"read=%u%n",&eye,&end)==1 && !args[end] && eye<2u) {
        const MohuVrRenderedMuzzle* s=&g_muzzle_pair[eye];
        if (!g_muzzle_valid) return -1;
        int n=snprintf(reply,(size_t)cap,
            "{\"valid\":%d,\"sequence\":%u,\"attempt\":%u,\"eye\":%u,\"restored\":%d,"
            "\"owner\":%u,\"input\":%u,\"object\":%u,\"id\":%u,\"hash\":%u,\"generation\":%u,"
            "\"cycle\":%llu,\"camera_cycle\":%llu,\"vertex_count\":%u,"
            "\"canonical_equal\":%d,\"canonical_sequence\":%u,\"canonical_cycle\":%llu,"
            "\"projection\":%u,\"href\":%u,\"precise\":%u,\"hand_fixed\":1}",
            vr_muzzle_usable(),g_muzzle_sequence,s->attempt,s->eye,s->restored,
            s->animated.key.owner,s->animated.key.input,s->animated.key.object,
            s->animated.key.id,s->animated.key.geometry_fnv32,s->animated.key.generation,
            (unsigned long long)s->animated.cycle,(unsigned long long)s->camera_cycle,
            s->animated.vertex_count,s->canonical_equal,s->canonical.sequence,
            (unsigned long long)s->canonical.cycle,s->view.projection,
            s->view.projection_h_ref,s->view.precise);
        return n>0 && n<cap ? 1 : -1;
    } else if (sscanf(args,"data=%u:%u%n",&eye,&start,&end)==2 &&
               !args[end] && eye<2u && start<4u && g_muzzle_valid) {
        const MohuVrRenderedMuzzle* s=&g_muzzle_pair[eye];
        int n=snprintf(reply,(size_t)cap,"{\"sequence\":%u,\"eye\":%u",g_muzzle_sequence,eye);
        if (n<1 || n>=cap) return -1;
#define MUZZLE_ARRAY(name, count, fmt, expression) do { \
    int added=snprintf(reply+n,(size_t)(cap-n),",\"" name "\":["); \
    if (added<0 || added>=cap-n) return -1; n+=added; \
    for (unsigned i=0; i<(count); ++i) { \
        added=snprintf(reply+n,(size_t)(cap-n),i ? "," fmt : fmt,(expression)); \
        if (added<0 || added>=cap-n) return -1; n+=added; \
    } \
    if (n+2>=cap) return -1; reply[n++]=']'; reply[n]=0; \
} while (0)
        if (start==0u) {
        MUZZLE_ARRAY("control",8,"%u",s->control[i]);
        MUZZLE_ARRAY("native_control",8,"%u",s->native_control[i]);
        MUZZLE_ARRAY("camera",8,"%u",s->camera[i]);
        } else if (start==1u) {
        MUZZLE_ARRAY("model_points",9,"%.12f",s->animated.points[i/3][i%3]);
        MUZZLE_ARRAY("base_points",9,"%.12f",s->points.base[i/3][i%3]);
        MUZZLE_ARRAY("eye_points",9,"%.12f",s->points.eye[i/3][i%3]);
        } else if (start==2u) {
        MUZZLE_ARRAY("base_axis",3,"%.12f",s->points.base_axis[i]);
        MUZZLE_ARRAY("eye_axis",3,"%.12f",s->points.eye_axis[i]);
        MUZZLE_ARRAY("view_rotation",9,"%.12f",s->view.precise ? s->view.rotation[i] : s->view.rotation_q12[i]/4096.0);
        MUZZLE_ARRAY("view_translation",3,"%.12f",s->view.precise ? s->view.translation_precise[i] : (double)s->view.translation[i]);
        MUZZLE_ARRAY("projection_q16",4,"%d",i==0 ? s->view.fx_q16 : i==1 ? s->view.fy_q16 : i==2 ? s->view.cx_delta_q16 : s->view.cy_delta_q16);
        } else {
        MUZZLE_ARRAY("w5_position",3,"%d",s->position[i]);
        MUZZLE_ARRAY("w5_angles",3,"%d",s->angles[i]);
        MUZZLE_ARRAY("aim_base",3,"%.12f",s->aim.base[1][i]);
        MUZZLE_ARRAY("aim_axis",3,"%.12f",s->aim.base_axis[i]);
        MUZZLE_ARRAY("aim_eye",3,"%.12f",s->aim.eye[1][i]);
        MUZZLE_ARRAY("aim_eye_axis",3,"%.12f",s->aim.eye_axis[i]);
        }
#undef MUZZLE_ARRAY
        if (n+2>=cap) return -1;
        reply[n++]='}'; reply[n]=0;
        return 1;
    } else if (sscanf(args,"vertices=%u:%u%n",&eye,&start,&end)==2 &&
               !args[end] && eye<2u && g_muzzle_valid &&
               start<g_muzzle_pair[eye].animated.vertex_count) {
        const MohuVrRenderedMuzzle* s=&g_muzzle_pair[eye];
        const MohuVrMarkerGroup* group=mohu_vr_marker_group(s->animated.key.id);
        int n=snprintf(reply,(size_t)cap,"{\"sequence\":%u,\"start\":%u,\"vertices\":[",g_muzzle_sequence,start);
        for (unsigned i=start; i<s->animated.vertex_count && i<start+4; ++i) {
            if (n<0 || n>=cap) return -1;
            const int added=snprintf(reply+n,(size_t)(cap-n),
                "%s[%u,%u,%d,%d,%d,%d,%d,%d]",i==start ? "" : ",",group->vertices[i][0],
                group->vertices[i][1],s->animated.vertices[i][0],
                s->animated.vertices[i][1],s->animated.vertices[i][2],
                s->canonical.vertices[i][0],s->canonical.vertices[i][1],
                s->canonical.vertices[i][2]);
            if (added<0 || added>=cap-n) return -1;
            n+=added;
        }
        if (n+3>=cap) return -1;
        memcpy(reply+n,"]}",3);
        return 1;
    } else if (strcmp(args,"status")) return -1;
    const int n=snprintf(reply,(size_t)cap,
        "{\"enabled\":%d,\"requested\":%d,\"valid\":%d,\"stored_valid\":%d,"
        "\"sequence\":%u,\"rejected\":%u,\"generation\":%u}",
        g_muzzle_enabled,g_muzzle_requested,vr_muzzle_usable(),g_muzzle_valid,
        g_muzzle_sequence,g_muzzle_rejected,g_marker_generation);
    return n>0 && n<cap ? 1 : -1;
}
