#include "vr_settings.h"

#include <stdio.h>
#include <string.h>

static int expect(int condition, const char* what) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", what);
        return 1;
    }
    return 0;
}

int main(void) {
    int failures = 0;
    const char* path = "mohu_vr_settings_test.toml";
    FILE* file = fopen(path, "wb");
    if (!file) return 1;
    fputs(
        "[video]\n"
        "fullscreen = 1\n"
        "\n"
        "[vr]\n"
        "enabled = true\n"
        "runtime = \"vdxr\"\n"
        "\n"
        "[mkb]\n"
        "look_sensitivity = 7\n",
        file);
    fclose(file);

    MohuVrSettings settings;
    mohu_vr_settings_read(&settings, path);
    remove(path);

    failures += expect(settings.has_enabled && settings.enabled, "vr enabled");
    failures += expect(strcmp(settings.runtime, "vdxr") == 0, "vr runtime");
    failures += expect(mohu_vr_runtime_manifest("current") == 0,
                       "current runtime has no manifest override");

    if (!failures) printf("mohu_vr_settings_test: ok\n");
    return failures ? 1 : 0;
}
