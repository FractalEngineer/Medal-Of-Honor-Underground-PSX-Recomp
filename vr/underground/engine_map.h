#ifndef MOHU_VR_ENGINE_MAP_H
#define MOHU_VR_ENGINE_MAP_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum {
    MOHU_VR_ROLE_ENTITY_TRANSFORM = 0,
    MOHU_VR_ROLE_ENTITY_NODE_TRANSFORM,
    MOHU_VR_ROLE_RT_TR_LOADER,
    MOHU_VR_ROLE_LEVEL_VERTEX_TRANSFORMER,
    MOHU_VR_ROLE_GAMEPLAY_RENDER_WAIT,
    MOHU_VR_ROLE_SCENE_DRAW_BRIDGE,
    MOHU_VR_ROLE_SCENE_DRAW_DISPATCHER,
    MOHU_VR_ROLE_ENTITY_RENDER_ENTRY,
    MOHU_VR_ROLE_RENDER_LIST_WRAPPER,
    MOHU_VR_ROLE_ACTOR_RENDER_ENTRY,
    MOHU_VR_ROLE_PLAYER_RENDER_ENTRY,
    MOHU_VR_ROLE_ACTOR_UPDATE_DISPATCHER,
    MOHU_VR_ROLE_FRAME_RENDER,
    MOHU_VR_ROLE_FRAME_DRIVER,
    MOHU_VR_ROLE_DRAW_OTAG,
    MOHU_VR_ROLE_POST_RENDER_UPDATE,
    MOHU_VR_ROLE_COUNT
} MohuVrEngineRole;

typedef enum {
    MOHU_VR_CONTAINER_MAIN_EXE = 0,
    MOHU_VR_CONTAINER_OVERLAY
} MohuVrContainerKind;

typedef enum {
    MOHU_VR_STATUS_DISABLED = 0,
    MOHU_VR_STATUS_CANDIDATE,
    MOHU_VR_STATUS_STATIC_CONFIRMED,
    MOHU_VR_STATUS_LIVE_CONFIRMED
} MohuVrEvidenceStatus;

typedef enum {
    MOHU_VR_CONFIDENCE_NONE = 0,
    MOHU_VR_CONFIDENCE_LOW,
    MOHU_VR_CONFIDENCE_MEDIUM,
    MOHU_VR_CONFIDENCE_HIGH
} MohuVrConfidence;

/*
 * Main-EXE container hashes identify exact executables. Whole window-capture
 * hashes are advisory because the capture index changes between runs; function
 * byte hashes identify overlay bindings and are the runtime guard.
 */
typedef struct {
    MohuVrEngineRole role;
    MohuVrContainerKind container_kind;
    const char* name;
    uint32_t reference_address;
    uint32_t target_address;
    uint32_t target_load_base;
    uint32_t function_size;
    uint16_t gte_rtps_count;
    const char* reference_container_sha256;
    const char* target_container_sha256;
    const char* reference_function_sha256;
    const char* target_function_sha256;
    uint32_t target_function_fnv1a;
    bool observed_executing;
    MohuVrEvidenceStatus status;
    MohuVrConfidence confidence;
} MohuVrEngineBinding;

size_t mohu_vr_engine_map_count(void);
const MohuVrEngineBinding* mohu_vr_engine_map_at(size_t index);
const MohuVrEngineBinding* mohu_vr_engine_map_find(MohuVrEngineRole role);

#endif
