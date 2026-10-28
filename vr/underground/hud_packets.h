#pragma once

#include "mod_plugins.h"

/* Ownership from the guarded native 8008F9F4 producer: input+C0, two
 * 40-byte FT4 banks. UV/palette may change with the selected weapon. */
static inline int mohu_vr_owned_ammo_packet(uint32_t node,uint32_t tag,
                                          uint32_t buffer,uint32_t input) {
    return buffer<=1u && input>=0x800B0000u && input<=0x801FC000u &&
        !(input&3u) && node==input+0xC0u+buffer*40u &&
        (tag>>24)==9u &&
        ((psx_mod_read_word(node+4u)>>24)&0xFCu)==0x2Cu;
}

/* Captured alternating FT4 ammo artwork in this guarded overlay generation.
 * Both packets have the same payload; only their OT link differs. */
static inline int mohu_vr_ammo_icon_packet(uint32_t node, uint32_t tag,
                                           uint32_t buffer) {
    if (buffer > 1u || node != 0x800F109Cu + buffer * 40u ||
        (tag >> 24) != 9u) {
        return 0;
    }
    static const uint32_t payload[9] = {
        0x2C808080u, 0x000F019Fu, 0x3DFEA080u,
        0x000F01BFu, 0x000FA0A0u, 0x0023019Fu,
        0x0000B480u, 0x002301BFu, 0x0000B4A0u,
    };
    for (unsigned i = 0; i < 9u; ++i) {
        if (psx_mod_read_word(node + 4u + i * 4u) != payload[i]) {
            return 0;
        }
    }
    return 1;
}
