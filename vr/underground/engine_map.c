#include "engine_map.h"

static const MohuVrEngineBinding k_bindings[MOHU_VR_ROLE_COUNT] = {
    {
        .role = MOHU_VR_ROLE_ENTITY_TRANSFORM,
        .container_kind = MOHU_VR_CONTAINER_OVERLAY,
        .name = "entity transform",
        .reference_address = 0x80084718u,
        .target_address = 0x80093830u,
        .target_load_base = 0x8008C000u,
        .function_size = 164u,
        .gte_rtps_count = 0u,
        .reference_container_sha256 =
            "c9fcfbe4e776d1dfc53fedeb38ac71bc3e00d577bfbbf0f1362f37057b95a1c6",
        .target_container_sha256 =
            "91ef751213453585d65ae4dc862fc1783ac6149fb9ad09a8f511dfcf0e1d87cf",
        .reference_function_sha256 =
            "f4455bbb4310ddc5d8995de3f4b0fb1a08541c5238ecaa5db617d347e738625b",
        .target_function_sha256 =
            "020c5da5c4e2b5985c9c3c569059426b683b83eca26aefb84065c94104cd2522",
        .observed_executing = true,
        .status = MOHU_VR_STATUS_LIVE_CONFIRMED,
        .confidence = MOHU_VR_CONFIDENCE_HIGH,
    },
    {
        .role = MOHU_VR_ROLE_ENTITY_NODE_TRANSFORM,
        .container_kind = MOHU_VR_CONTAINER_MAIN_EXE,
        .name = "entity node transformer",
        .reference_address = 0x80013AE4u,
        .target_address = 0x80013B40u,
        .target_load_base = 0x80010000u,
        .function_size = 884u,
        .gte_rtps_count = 0u,
        .reference_container_sha256 =
            "19215344b0031358a6f628cbee0bd124f23275d4621aa16ada8f959cfa0792e3",
        .target_container_sha256 =
            "5c4566b7264a29554abb9d868f23cc40e99ebf3b58b9776dfe2f4ae465bbd641",
        .reference_function_sha256 =
            "ab109f983a7b61c183213d557eeaf7b070d572c7e37e245e358262e304e1c803",
        .target_function_sha256 =
            "62db0b0ab33441337bd0efa98e92e0dc45399eddf79e9d3af0247a1c30f0b1ff",
        .observed_executing = true,
        .status = MOHU_VR_STATUS_LIVE_CONFIRMED,
        .confidence = MOHU_VR_CONFIDENCE_HIGH,
    },
    {
        .role = MOHU_VR_ROLE_RT_TR_LOADER,
        .container_kind = MOHU_VR_CONTAINER_MAIN_EXE,
        .name = "GTE RT/TR loader",
        .reference_address = 0x80013E58u,
        .target_address = 0x80013EB4u,
        .target_load_base = 0x80010000u,
        .function_size = 316u,
        .gte_rtps_count = 0u,
        .reference_container_sha256 =
            "19215344b0031358a6f628cbee0bd124f23275d4621aa16ada8f959cfa0792e3",
        .target_container_sha256 =
            "5c4566b7264a29554abb9d868f23cc40e99ebf3b58b9776dfe2f4ae465bbd641",
        .reference_function_sha256 =
            "e849993249db8f68b82466398c2c587e47f29fb94dfa134f8878d82a0c7a7eb4",
        .target_function_sha256 =
            "e849993249db8f68b82466398c2c587e47f29fb94dfa134f8878d82a0c7a7eb4",
        .observed_executing = true,
        .status = MOHU_VR_STATUS_LIVE_CONFIRMED,
        .confidence = MOHU_VR_CONFIDENCE_HIGH,
    },
    {
        .role = MOHU_VR_ROLE_LEVEL_VERTEX_TRANSFORMER,
        .container_kind = MOHU_VR_CONTAINER_OVERLAY,
        .name = "level vertex transformer",
        .reference_address = 0x8008B3E8u,
        .target_address = 0x80099960u,
        .target_load_base = 0x80097000u,
        .function_size = 2840u,
        .gte_rtps_count = 12u,
        .reference_container_sha256 =
            "81b86e73f295a2486242bb3153951597dca557de25b8432677d65c12a8b8bc01",
        .target_container_sha256 =
            "16fc9e35958bc478b13f544bbf8c4706331a195ac634e9879c69cf96ea827246",
        .reference_function_sha256 =
            "5974d2586e25c4dfd6ad9ea050907e0e142f8db7c267690a3165bb3f6a429f3f",
        .target_function_sha256 =
            "8bbc2a5573c17eb65d242c127b4f6f778304a82ad6c0aa775a744afe9b0a5e47",
        .observed_executing = true,
        .status = MOHU_VR_STATUS_LIVE_CONFIRMED,
        .confidence = MOHU_VR_CONFIDENCE_HIGH,
    },
    {
        .role = MOHU_VR_ROLE_GAMEPLAY_RENDER_WAIT,
        .container_kind = MOHU_VR_CONTAINER_OVERLAY,
        .name = "gameplay render wait",
        .reference_address = 0x80090B80u,
        .target_address = 0x8009D828u,
        .target_load_base = 0x80097000u,
        .function_size = 440u,
        .gte_rtps_count = 0u,
        .reference_container_sha256 =
            "25b984768f6201f783ae425adabbaee0db1200d337012fbc0e9e1624db51dc65",
        .target_container_sha256 =
            "16fc9e35958bc478b13f544bbf8c4706331a195ac634e9879c69cf96ea827246",
        .reference_function_sha256 =
            "597e6ec6270f8488b6c4525d32f54418ecebdebc0eca62ad9104bdb652f83d2f",
        .target_function_sha256 =
            "f19ff4ea5806bcad08e2834f89b6f3f79d0d96c482bed1043dc5be0c41b1f29a",
        .observed_executing = true,
        .status = MOHU_VR_STATUS_LIVE_CONFIRMED,
        .confidence = MOHU_VR_CONFIDENCE_HIGH,
    },
};

size_t mohu_vr_engine_map_count(void) {
    return MOHU_VR_ROLE_COUNT;
}

const MohuVrEngineBinding* mohu_vr_engine_map_at(size_t index) {
    if (index >= MOHU_VR_ROLE_COUNT) {
        return NULL;
    }
    return &k_bindings[index];
}

const MohuVrEngineBinding* mohu_vr_engine_map_find(MohuVrEngineRole role) {
    if ((unsigned)role >= (unsigned)MOHU_VR_ROLE_COUNT) {
        return NULL;
    }
    return &k_bindings[(size_t)role];
}
