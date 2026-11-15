#pragma once

#include <stddef.h>

/* VR launch selection from the launcher's settings.toml.
 *
 * The VR launchers pass MOHU_VR_OPENXR/PSX_OPENXR_ENABLE and XR_RUNTIME_JSON
 * in the environment. RecompLauncher cannot set environment variables per
 * setting, so it writes [vr] into settings.toml instead. The VR plugin reads
 * this only when RECOMPLAUNCHER is set and no explicit VR environment is
 * present, then applies the same launch profile the Windows launcher uses. */

typedef struct MohuVrSettings {
    int has_enabled;
    int enabled;
    char runtime[24]; /* current | vdxr | steamvr | oculus */
} MohuVrSettings;

void mohu_vr_settings_read(MohuVrSettings* settings, const char* path);

/* Resolve the OpenXR runtime manifest for a named runtime. Returns NULL for
 * "current" (use the system's active runtime) or when no install is found.
 * On non-Windows platforms only the active runtime is supported. */
const char* mohu_vr_runtime_manifest(const char* runtime);
