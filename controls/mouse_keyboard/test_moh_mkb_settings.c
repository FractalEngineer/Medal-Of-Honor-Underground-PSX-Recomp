#include "moh_mkb_settings.h"

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
    const char* path = "mohu_mkb_settings_test.toml";
    FILE* file = fopen(path, "wb");
    if (!file) return 1;
    fputs(
        "[video]\n"
        "fullscreen = 1\n"
        "\n"
        "[mkb]\n"
        "look_sensitivity = 7\n"
        "aim_sensitivity = 6\n"
        "aimed_zoom = 150\n"
        "\n"
        "[mkb_bindings]\n"
        "bind_forward = \"W\"\n"
        "bind_fire = \"Left Mouse, Enter\"\n"
        "bind_aim = \"mouse:3\"\n"
        "bind_jump = \"Space|Wheel Up\"\n"
        "\n"
        "[vr]\n"
        "enabled = true\n",
        file);
    fclose(file);

    MohuMkbSettings settings;
    mohu_mkb_settings_read(&settings, path);
    remove(path);

    int found = 0;
    failures += expect(mohu_mkb_settings_integer(&settings, "look_sensitivity", &found) == 7 &&
                       found, "look_sensitivity override");
    failures += expect(mohu_mkb_settings_integer(&settings, "aim_sensitivity", &found) == 6 &&
                       found, "aim_sensitivity override");
    failures += expect(mohu_mkb_settings_integer(&settings, "aimed_zoom", &found) == 150 &&
                       found, "aimed_zoom override");
    failures += expect(mohu_mkb_settings_integer(&settings, "missing", &found) == 0 &&
                       !found, "missing key");

    char tokens[256];
    failures += expect(mohu_mkb_settings_binding_tokens(&settings, "bind_forward",
                                                        tokens, sizeof(tokens)) &&
                       strcmp(tokens, "key:26") == 0, "friendly W");
    failures += expect(mohu_mkb_settings_binding_tokens(&settings, "bind_fire",
                                                        tokens, sizeof(tokens)) &&
                       strcmp(tokens, "mouse:1,key:40") == 0,
                       "friendly mouse + Enter");
    failures += expect(mohu_mkb_settings_binding_tokens(&settings, "bind_aim",
                                                        tokens, sizeof(tokens)) &&
                       strcmp(tokens, "mouse:3") == 0, "native token preserved");
    failures += expect(mohu_mkb_settings_binding_tokens(&settings, "bind_jump",
                                                        tokens, sizeof(tokens)) &&
                       strcmp(tokens, "key:44,wheel:up") == 0,
                       "pipe separator + wheel");
    failures += expect(!mohu_mkb_settings_binding_tokens(&settings, "bind_missing",
                                                         tokens, sizeof(tokens)),
                       "absent binding");

    if (!failures) printf("mohu_mkb_settings_test: ok\n");
    return failures ? 1 : 0;
}
