#pragma once

#include <stddef.h>

/* Optional RecompLauncher overrides for the mouse/keyboard mod.
 *
 * RecompLauncher writes settings.toml before starting the game. When the game
 * was started by the launcher (RECOMPLAUNCHER is set), the mod reads
 * [mkb] and [mkb_bindings] from that file and applies them over mods/state.toml.
 * The parser is deliberately a small TOML subset: the launcher writes plain
 * `key = value` lines in those two tables, and a full TOML dependency is not
 * warranted for six keys and twenty bindings.
 *
 * Binding values may be either the mod's native tokens ("key:26,mouse:3") or
 * friendly names from the launcher UI ("W", "Left Mouse", "Wheel Up"). */

typedef struct MohuMkbBindingOverride {
    char id[48];
    char value[192];
} MohuMkbBindingOverride;

typedef struct MohuMkbSettings {
    int has_look_sensitivity;
    int look_sensitivity;
    int has_aim_sensitivity;
    int aim_sensitivity;
    int has_aimed_zoom;
    int aimed_zoom;
    int binding_count;
    MohuMkbBindingOverride bindings[32];
} MohuMkbSettings;

void mohu_mkb_settings_read(MohuMkbSettings* settings, const char* path);

/* 0 when the key is absent or has no integer value. */
int mohu_mkb_settings_integer(const MohuMkbSettings* settings, const char* key,
                              int* found);

/* Convert one override binding to the mod's token format. Returns 1 when the
 * table had an entry for this id (even when it is empty). */
int mohu_mkb_settings_binding_tokens(const MohuMkbSettings* settings,
                                     const char* id, char* out, size_t capacity);
