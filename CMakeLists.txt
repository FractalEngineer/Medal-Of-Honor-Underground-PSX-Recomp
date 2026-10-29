cmake_minimum_required(VERSION 3.20)
set(PSXRECOMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/psxrecomp" CACHE PATH
    "Path to psxrecomp")
if(NOT EXISTS "${PSXRECOMP_ROOT}/runtime/runtime.cmake")
    message(FATAL_ERROR
        "PSXRecomp runtime is missing: ${PSXRECOMP_ROOT}/runtime/runtime.cmake\n"
        "This project expects the psxrecomp framework checkout at ${PSXRECOMP_ROOT}.\n"
        "Run: git submodule update --init --recursive\n"
        "If psxrecomp/ is not a submodule, set -DPSXRECOMP_ROOT=<path-to-psxrecomp>.")
endif()

project(Medal_of_Honor_Underground_Recomp LANGUAGES C CXX)

# --- Opt-in product surfaces (OFF by default in the framework) -------------
# Scaffold prompts / flags fill these. Without recomp-ui, PSX_RECOMP_UI is OFF.
# The wizard (WIZARD_CMAKE_BLOCK / ENABLE_SETUP_WIZARD) is the first-run disc
# picker; releases are compiled from the committed generated/ C, so it never
# needs to generate or rebuild anything on a player's machine.
# recomp-ui submodule present (PSX_RECOMP_UI defaults ON).
# Full netplay UI -- enable after adding recomp-ui + testing:
# if(EXISTS "${PSXRECOMP_ROOT}/lib/recomp-net/CMakeLists.txt")
#     set(PSX_NETPLAY ON CACHE BOOL "..." FORCE)
# endif()
set(PSX_SETUP_WIZARD ON CACHE BOOL
    "Advertise first-run setup wizard + Generate & rebuild in recomp-ui" FORCE)
option(MOHU_VR_DIAGNOSTICS "Build the guarded Underground VR diagnostic plugin" OFF)
option(MOHU_VR_NATIVE_PROFILE "Time native CPS function segments (diagnostic only)" OFF)
option(MOHU_VR_PREFLIGHT_HARNESS "Isolated native/host preflight caller comparisons (diagnostic only)" OFF)
option(MOHU_VR_HOST_PREFLIGHT "Build-selected host preflight for render-only eye passes (experimental)" OFF)
option(MOHU_VR_PACKET_HARNESS "Isolated native/host packet comparisons (diagnostic only)" OFF)
option(MOHU_VR_HOST_PACKET "Batch native packet CPS segments in render-only passes (experimental)" OFF)
include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")

# This project's own mod catalog. The FRAMEWORK stages it -- together with its
# builtin psx.* packages -- into <exe-dir>/mods/bundled, and refuses to
# configure if a catalog exists here but is not declared. Never copy it by
# hand: five titles did, and framework 4cc04be3's rename of the staged
# directory broke all five silently (bead beads-eio.3.101).
if(MOHU_VR_DIAGNOSTICS)
    set(PSX_PRELOADED_MODS "${CMAKE_CURRENT_SOURCE_DIR}/vr/preloaded")
    # Full render-view tests need PGXP packet provenance. The default target
    # below remains the base flavor.
    set(_MOHU_RUNTIME_OPTIONS PGXP)
else()
    set(PSX_PRELOADED_MODS "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded")
    set(_MOHU_RUNTIME_OPTIONS)
endif()
if(NOT IS_DIRECTORY "${PSX_PRELOADED_MODS}")
    set(PSX_PRELOADED_MODS "NONE")
endif()

psxrecomp_add_game_runtime(psx-runtime
    ${_MOHU_RUNTIME_OPTIONS}
    PRELOADED_MODS_DIR "${PSX_PRELOADED_MODS}"
    # ENABLE_NETPLAY_IF_PRESENT
    # NETPLAY_LOBBY_URL "ws://netplay.retcomm.net:8765"
    ENABLE_SETUP_WIZARD
    WINDOW_TITLE "Medal of Honor Underground Recompiled"
    DEFAULT_GAME_CONFIG_PATH "game.toml"
    MAX_PLAYERS 2
    LAUNCHER_BOXART "${CMAKE_CURRENT_SOURCE_DIR}/launcher_assets/img/boxart.tga"
    APP_ICON "${CMAKE_CURRENT_SOURCE_DIR}/assets/psxrecomp.ico"
    # Committed game C (psxrecomp_cli.py generate; git add generated). Release
    # CI configures with -DPSXRECOMP_REQUIRE_GAME_C=ON so a checkout without
    # it fails instead of building a setup host.
    GEN_MARKER "generated/SLUS_012.70_dispatch.c"
    GEN_FULL_GLOB "generated/SLUS_012.70_full_*.c"
    CODEGEN_SETUP_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/codegen_setup.c"
)

get_target_property(_mohu_execution_profile psx-runtime PSX_EXECUTION_PROFILE)
set(_mohu_packet_core "${CMAKE_CURRENT_BINARY_DIR}/mohu_packet_core.c")
if(MOHU_VR_PACKET_HARNESS OR
   (MOHU_VR_HOST_PACKET AND _mohu_execution_profile STREQUAL "ENHANCED"))
    find_package(Python3 COMPONENTS Interpreter REQUIRED)
    execute_process(COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/vr/tools/build_packet_kernel.py"
        --source "${CMAKE_CURRENT_SOURCE_DIR}/generated/SLUS_012.70_full_00.c"
        --out "${_mohu_packet_core}" COMMAND_ERROR_IS_FATAL ANY)
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
        vr/tools/build_packet_kernel.py generated/SLUS_012.70_full_00.c)
    target_include_directories(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/generated")
endif()
if(MOHU_VR_HOST_PACKET AND NOT MOHU_VR_HOST_PREFLIGHT)
    message(FATAL_ERROR "Host packet currently requires the qualified preflight kernel")
endif()
if(MOHU_VR_HOST_PREFLIGHT)
    if(NOT MOHU_VR_DIAGNOSTICS OR MOHU_VR_PREFLIGHT_HARNESS OR MOHU_VR_NATIVE_PROFILE)
        message(FATAL_ERROR "Host preflight requires VR and cannot be combined with diagnostic wrappers")
    endif()
    set(_mohu_preflight_shard "${CMAKE_CURRENT_SOURCE_DIR}/generated/SLUS_012.70_full_00.c")
    foreach(_mohu_target psx-runtime psx-runtime-pgxp)
        if(TARGET ${_mohu_target})
            get_target_property(_mohu_sources ${_mohu_target} SOURCES)
            list(REMOVE_ITEM _mohu_sources "${_mohu_preflight_shard}")
            set_property(TARGET ${_mohu_target} PROPERTY SOURCES "${_mohu_sources}")
        endif()
    endforeach()
    set(_mohu_hle_sources vr/underground/preflight_entry.c vr/underground/preflight.c)
    set(_mohu_hle_contract mohu-vr-preflight)
    set(_mohu_hle_files vr/underground/preflight.h)
    if(MOHU_VR_HOST_PACKET)
        list(APPEND _mohu_hle_sources vr/underground/packet_entry.c "${_mohu_packet_core}")
        list(APPEND _mohu_hle_files vr/tools/build_packet_kernel.py vr/underground/world_cache.inc
            vr/underground/world_cache_key.h)
        set(_mohu_hle_contract mohu-vr-render-kernels)
        set_property(SOURCE vr/underground/preflight_entry.c APPEND PROPERTY
            COMPILE_DEFINITIONS MOHU_VR_HOST_PACKET_BUILD=1)
        if(_mohu_execution_profile STREQUAL "ENHANCED")
            set_property(SOURCE vr/underground/vr_diagnostic.c APPEND PROPERTY
                COMPILE_DEFINITIONS MOHU_VR_HOST_PACKET_BUILD=1)
        endif()
    endif()
    if(_mohu_execution_profile STREQUAL "REFERENCE")
        # A reference build must not require private HLE headers or recipes.
        set(_mohu_hle_files)
    endif()
    psxrecomp_add_implementation(psx-runtime
        NAME ${_mohu_hle_contract} CONTRACT slus01270-render-kernels-v1
        HLE_SOURCES ${_mohu_hle_sources}
        LLE_SOURCES "${_mohu_preflight_shard}"
        CONTRACT_FILES ${_mohu_hle_files} "${_mohu_preflight_shard}"
            generated/SLUS_012.70_decls.h)
endif()

if(MOHU_VR_DIAGNOSTICS)
    target_sources(psx-runtime PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/vr/underground/engine_map.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/vr/underground/input.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/vr/underground/world_decode.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/vr/underground/world_select.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/vr/underground/world_project.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/vr/underground/weapon.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/vr/underground/hud.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/vr/underground/vr_diagnostic.c")
    if(MOHU_VR_PACKET_HARNESS)
        if(NOT WIN32 OR MSVC OR NOT PSX_DEBUG_TOOLS OR MOHU_VR_NATIVE_PROFILE)
            message(FATAL_ERROR "Packet harness requires Windows GNU ABI, debug tools, native timers OFF")
        endif()
        set_property(SOURCE vr/underground/vr_diagnostic.c APPEND PROPERTY
            COMPILE_DEFINITIONS MOHU_VR_PACKET_HARNESS=1)
        if(MOHU_VR_HOST_PACKET)
            message(FATAL_ERROR "Packet harness and live packet implementation must be separate builds")
        endif()
        target_sources(psx-runtime PRIVATE "${_mohu_packet_core}" vr/underground/packet_harness.c)
        target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_80010CF0")
    endif()
    if(MOHU_VR_PREFLIGHT_HARNESS)
        if(NOT WIN32 OR MSVC OR NOT PSX_DEBUG_TOOLS OR MOHU_VR_NATIVE_PROFILE)
            message(FATAL_ERROR "Preflight harness requires Windows GNU ABI, debug tools, native timers OFF")
        endif()
        set_property(SOURCE vr/underground/vr_diagnostic.c APPEND PROPERTY
            COMPILE_DEFINITIONS MOHU_VR_PREFLIGHT_HARNESS=1)
        target_sources(psx-runtime PRIVATE vr/underground/preflight.c vr/underground/preflight_harness.c)
        target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_80011424")
    endif()
    if(MOHU_VR_NATIVE_PROFILE)
        if(NOT WIN32 OR MSVC OR NOT PSX_DEBUG_TOOLS)
            message(FATAL_ERROR "Native segment profiling requires Windows GNU ABI and debug tools")
        endif()
        set_property(SOURCE vr/underground/vr_diagnostic.c APPEND PROPERTY
            COMPILE_DEFINITIONS MOHU_VR_NATIVE_PROFILE=1)
        target_sources(psx-runtime PRIVATE vr/underground/native_profile.c)
        foreach(_profile_address 80010000 80010508 80010CF0 80011424 80013B40 80013EB4 80017628 8001A004)
            target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_${_profile_address}")
        endforeach()
    endif()
endif()

# Current psxrecomp embeds its UTF-8 manifest as an object library. recomp-ui
# cannot detect that when adding its older fallback manifest, so keep the
# framework manifest and drop the duplicate resource source.
if(WIN32 AND NOT MSVC)
    set(_recomp_ui_manifest
        "${CMAKE_CURRENT_BINARY_DIR}/psx-runtime_recomp_utf8_manifest.rc")
    get_target_property(_psx_runtime_sources psx-runtime SOURCES)
    if(_recomp_ui_manifest IN_LIST _psx_runtime_sources)
        list(REMOVE_ITEM _psx_runtime_sources "${_recomp_ui_manifest}")
        set_target_properties(psx-runtime PROPERTIES
            SOURCES "${_psx_runtime_sources}")
    endif()
endif()

# Stage runtime configs next to the exe for direct build/ launches. Only copy
# files that exist — never fail POST_BUILD when game_options.toml is absent.
foreach(_PSX_RUNTIME_CONFIG game.toml game_options.toml)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${_PSX_RUNTIME_CONFIG}")
        add_custom_command(TARGET psx-runtime POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${CMAKE_CURRENT_SOURCE_DIR}/${_PSX_RUNTIME_CONFIG}"
                "$<TARGET_FILE_DIR:psx-runtime>/${_PSX_RUNTIME_CONFIG}"
            COMMENT "Staging ${_PSX_RUNTIME_CONFIG}"
            VERBATIM)
    endif()
endforeach()
