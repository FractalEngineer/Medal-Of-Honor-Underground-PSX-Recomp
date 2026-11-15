#include "vr_settings.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char* trim(char* text) {
    while (*text && isspace((unsigned char)*text)) ++text;
    char* end = text + strlen(text);
    while (end > text && isspace((unsigned char)end[-1])) *--end = '\0';
    return text;
}

static void unquote(char* value) {
    const size_t size = strlen(value);
    if (size >= 2 && value[0] == '"' && value[size - 1] == '"') {
        memmove(value, value + 1, size - 2);
        value[size - 2] = '\0';
    }
}

void mohu_vr_settings_read(MohuVrSettings* settings, const char* path) {
    if (!settings) return;
    memset(settings, 0, sizeof(*settings));
    snprintf(settings->runtime, sizeof(settings->runtime), "current");
    if (!path || !path[0]) return;
    FILE* file = fopen(path, "rb");
    if (!file) return;

    int in_vr = 0;
    char line[512];
    while (fgets(line, sizeof(line), file)) {
        char* text = trim(line);
        if (!*text || *text == '#') continue;
        if (*text == '[') {
            char* close = strchr(text, ']');
            if (!close) continue;
            *close = '\0';
            in_vr = strcmp(trim(text + 1), "vr") == 0;
            continue;
        }
        if (!in_vr) continue;
        char* equal = strchr(text, '=');
        if (!equal) continue;
        *equal = '\0';
        char* key = trim(text);
        char* value = trim(equal + 1);
        value[strcspn(value, "#")] = '\0';
        value = trim(value);
        unquote(value);
        if (strcmp(key, "enabled") == 0) {
            settings->has_enabled = 1;
            settings->enabled = strcmp(value, "true") == 0 ||
                                strcmp(value, "1") == 0 ||
                                strcmp(value, "on") == 0;
        } else if (strcmp(key, "runtime") == 0) {
            snprintf(settings->runtime, sizeof(settings->runtime), "%s", value);
        }
    }
    fclose(file);
}

static int file_exists(const char* path) {
    FILE* file = fopen(path, "rb");
    if (!file) return 0;
    fclose(file);
    return 1;
}

static int try_manifest(char* out, size_t capacity, const char* root,
                        const char* relative) {
    if (!root || !*root) return 0;
    snprintf(out, capacity, "%s\\%s", root, relative);
    return file_exists(out);
}

const char* mohu_vr_runtime_manifest(const char* runtime) {
    static char manifest[1024];
    if (!runtime || !*runtime || strcmp(runtime, "current") == 0) return 0;
#ifdef _WIN32
    const char* program_files = getenv("ProgramFiles");
    const char* program_files_x86 = getenv("ProgramFiles(x86)");
    const char* local_app_data = getenv("LOCALAPPDATA");
    if (strcmp(runtime, "vdxr") == 0) {
        if (try_manifest(manifest, sizeof(manifest), program_files,
                "Virtual Desktop Streamer\\OpenXR\\virtualdesktop-openxr.json") ||
            try_manifest(manifest, sizeof(manifest), program_files_x86,
                "Virtual Desktop Streamer\\OpenXR\\virtualdesktop-openxr.json") ||
            try_manifest(manifest, sizeof(manifest), local_app_data,
                "Programs\\VirtualDesktopStreamer\\OpenXR\\virtualdesktop-openxr.json"))
            return manifest;
    } else if (strcmp(runtime, "oculus") == 0) {
        if (try_manifest(manifest, sizeof(manifest), program_files,
                "Meta Horizon\\Support\\oculus-runtime\\oculus_openxr_64.json") ||
            try_manifest(manifest, sizeof(manifest), program_files,
                "Oculus\\Support\\oculus-runtime\\oculus_openxr_64.json"))
            return manifest;
    } else if (strcmp(runtime, "steamvr") == 0) {
        if (try_manifest(manifest, sizeof(manifest), program_files_x86,
                "Steam\\steamapps\\common\\SteamVR\\steamxr_win64.json") ||
            try_manifest(manifest, sizeof(manifest), program_files,
                "Steam\\steamapps\\common\\SteamVR\\steamxr_win64.json"))
            return manifest;
    }
#else
    (void)try_manifest;
    (void)file_exists;
#endif
    return 0;
}
