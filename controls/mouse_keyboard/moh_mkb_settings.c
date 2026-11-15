#include "moh_mkb_settings.h"

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

static int same(const char* a, const char* b) {
    while (*a && *b) {
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) return 0;
        ++a;
        ++b;
    }
    return *a == '\0' && *b == '\0';
}

static const struct {
    const char* name;
    const char* token;
} kNames[] = {
    {"return", "key:40"}, {"enter", "key:40"},
    {"escape", "key:41"}, {"esc", "key:41"},
    {"backspace", "key:42"}, {"tab", "key:43"},
    {"space", "key:44"}, {"spacebar", "key:44"},
    {"minus", "key:45"}, {"equals", "key:46"},
    {"leftbracket", "key:47"}, {"rightbracket", "key:48"},
    {"backslash", "key:49"}, {"semicolon", "key:51"},
    {"apostrophe", "key:52"}, {"grave", "key:53"},
    {"comma", "key:54"}, {"period", "key:55"}, {"slash", "key:56"},
    {"capslock", "key:57"},
    {"printscreen", "key:70"}, {"scrolllock", "key:71"}, {"pause", "key:72"},
    {"insert", "key:73"}, {"home", "key:74"}, {"pageup", "key:75"},
    {"delete", "key:76"}, {"del", "key:76"}, {"end", "key:77"},
    {"pagedown", "key:78"},
    {"right", "key:79"}, {"arrowright", "key:79"},
    {"left", "key:80"}, {"arrowleft", "key:80"},
    {"down", "key:81"}, {"arrowdown", "key:81"},
    {"up", "key:82"}, {"arrowup", "key:82"},
    {"leftctrl", "key:224"}, {"lctrl", "key:224"}, {"ctrl", "key:224"},
    {"leftshift", "key:225"}, {"lshift", "key:225"}, {"shift", "key:225"},
    {"leftalt", "key:226"}, {"lalt", "key:226"}, {"alt", "key:226"},
    {"leftgui", "key:227"}, {"lgui", "key:227"}, {"super", "key:227"},
    {"rightctrl", "key:228"}, {"rctrl", "key:228"},
    {"rightshift", "key:229"}, {"rshift", "key:229"},
    {"rightalt", "key:230"}, {"ralt", "key:230"},
    {"rightgui", "key:231"}, {"rgui", "key:231"},
    {"lmb", "mouse:1"}, {"mouse1", "mouse:1"},
    {"leftmouse", "mouse:1"}, {"mouseleft", "mouse:1"},
    {"leftclick", "mouse:1"},
    {"mmb", "mouse:2"}, {"mouse2", "mouse:2"},
    {"middlemouse", "mouse:2"}, {"middleclick", "mouse:2"},
    {"rmb", "mouse:3"}, {"mouse3", "mouse:3"},
    {"rightmouse", "mouse:3"}, {"mouseright", "mouse:3"},
    {"rightclick", "mouse:3"},
    {"mouse4", "mouse:4"}, {"mouse5", "mouse:5"},
    {"wheelup", "wheel:up"}, {"mousewheelup", "wheel:up"},
    {"wheeldown", "wheel:down"}, {"mousewheeldown", "wheel:down"},
};

static int name_to_token(const char* name, char* out, size_t capacity) {
    if (!name || !*name) return 0;
    if (!strncmp(name, "key:", 4) || !strncmp(name, "mouse:", 6) ||
        !strncmp(name, "wheel:", 6)) {
        if (strlen(name) + 1 > capacity) return 0;
        strcpy(out, name);
        return 1;
    }
    /* The launcher's chips read "Left Mouse", "Wheel Up", "Page Down"; the
     * table is written without spaces so one normalization covers both. */
    char compact[96];
    size_t compact_length = 0;
    for (const char* p = name; *p && compact_length + 1 < sizeof(compact); ++p)
        if (*p != ' ' && *p != '_' && *p != '-')
            compact[compact_length++] = (char)tolower((unsigned char)*p);
    compact[compact_length] = '\0';
    if (strlen(compact) == 1) {
        const char c = (char)toupper((unsigned char)compact[0]);
        if (c >= 'A' && c <= 'Z') {
            snprintf(out, capacity, "key:%d", 4 + (c - 'A'));
            return 1;
        }
        if (c == '0') {
            snprintf(out, capacity, "key:39");
            return 1;
        }
        if (c >= '1' && c <= '9') {
            snprintf(out, capacity, "key:%d", 30 + (c - '1'));
            return 1;
        }
    }
    if (compact[0] == 'f') {
        const int n = atoi(compact + 1);
        if (n >= 1 && n <= 12) {
            snprintf(out, capacity, "key:%d", 57 + n);
            return 1;
        }
    }
    for (size_t i = 0; i < sizeof(kNames) / sizeof(kNames[0]); ++i)
        if (same(compact, kNames[i].name)) {
            snprintf(out, capacity, "%s", kNames[i].token);
            return 1;
        }
    return 0;
}

void mohu_mkb_settings_read(MohuMkbSettings* settings, const char* path) {
    if (!settings) return;
    memset(settings, 0, sizeof(*settings));
    if (!path || !path[0]) return;
    FILE* file = fopen(path, "rb");
    if (!file) return;

    enum { SECTION_NONE, SECTION_MKB, SECTION_BINDINGS } section = SECTION_NONE;
    char line[512];
    while (fgets(line, sizeof(line), file)) {
        char* text = trim(line);
        if (!*text || *text == '#') continue;
        if (*text == '[') {
            char* close = strchr(text, ']');
            if (!close) continue;
            *close = '\0';
            char* name = trim(text + 1);
            section = same(name, "mkb") ? SECTION_MKB :
                      same(name, "mkb_bindings") ? SECTION_BINDINGS :
                      SECTION_NONE;
            continue;
        }
        if (section == SECTION_NONE) continue;
        char* equal = strchr(text, '=');
        if (!equal) continue;
        *equal = '\0';
        char* key = trim(text);
        char* value = trim(equal + 1);
        const size_t comment = strcspn(value, "#");
        value[comment] = '\0';
        value = trim(value);
        unquote(value);
        if (section == SECTION_MKB) {
            const int number = atoi(value);
            if (same(key, "look_sensitivity")) {
                settings->has_look_sensitivity = 1;
                settings->look_sensitivity = number;
            } else if (same(key, "aim_sensitivity")) {
                settings->has_aim_sensitivity = 1;
                settings->aim_sensitivity = number;
            } else if (same(key, "aimed_zoom")) {
                settings->has_aimed_zoom = 1;
                settings->aimed_zoom = number;
            }
        } else if (!strncmp(key, "bind_", 5) &&
                   settings->binding_count <
                       (int)(sizeof(settings->bindings) / sizeof(settings->bindings[0]))) {
            MohuMkbBindingOverride* binding =
                &settings->bindings[settings->binding_count++];
            snprintf(binding->id, sizeof(binding->id), "%s", key);
            snprintf(binding->value, sizeof(binding->value), "%s", value);
        }
    }
    fclose(file);
}

int mohu_mkb_settings_integer(const MohuMkbSettings* settings, const char* key,
                              int* found) {
    if (found) *found = 0;
    if (!settings || !key) return 0;
    const struct {
        const char* key;
        int has;
        int value;
    } values[] = {
        {"look_sensitivity", settings->has_look_sensitivity,
         settings->look_sensitivity},
        {"aim_sensitivity", settings->has_aim_sensitivity,
         settings->aim_sensitivity},
        {"aimed_zoom", settings->has_aimed_zoom, settings->aimed_zoom},
    };
    for (size_t i = 0; i < sizeof(values) / sizeof(values[0]); ++i)
        if (same(key, values[i].key)) {
            if (found) *found = values[i].has;
            return values[i].value;
        }
    return 0;
}

int mohu_mkb_settings_binding_tokens(const MohuMkbSettings* settings,
                                     const char* id, char* out, size_t capacity) {
    if (!settings || !id || !out || capacity == 0) return 0;
    const char* value = 0;
    for (int i = 0; i < settings->binding_count; ++i)
        if (same(settings->bindings[i].id, id)) {
            value = settings->bindings[i].value;
            break;
        }
    if (!value) return 0;
    out[0] = '\0';
    size_t used = 0;
    const char* cursor = value;
    while (*cursor) {
        const char* end = cursor;
        while (*end && *end != ',' && *end != '|') ++end;
        char item[96];
        size_t length = (size_t)(end - cursor);
        if (length >= sizeof(item)) length = sizeof(item) - 1;
        memcpy(item, cursor, length);
        item[length] = '\0';
        char* name = trim(item);
        char token[96];
        if (name_to_token(name, token, sizeof(token))) {
            const size_t token_length = strlen(token);
            if (used && used + 1 < capacity) out[used++] = ',';
            if (used + token_length >= capacity) return 0;
            memcpy(out + used, token, token_length);
            used += token_length;
            out[used] = '\0';
        }
        cursor = *end ? end + 1 : end;
    }
    return 1;
}
