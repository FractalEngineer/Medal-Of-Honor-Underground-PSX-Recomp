#include "hud_packets.h"

#include <assert.h>

/* Two consecutive native packet captures, including distinct OT links. */
static uint32_t packets[20] = {
    0x090BA488u, 0x2C808080u, 0x000F019Fu, 0x3DFEA080u, 0x000F01BFu,
    0x000FA0A0u, 0x0023019Fu, 0x0000B480u, 0x002301BFu, 0x0000B4A0u,
    0x090BA4B0u, 0x2C808080u, 0x000F019Fu, 0x3DFEA080u, 0x000F01BFu,
    0x000FA0A0u, 0x0023019Fu, 0x0000B480u, 0x002301BFu, 0x0000B4A0u,
};

uint32_t psx_mod_read_word(uint32_t address) {
    assert(address >= 0x800F109Cu && address < 0x800F10ECu);
    return packets[(address - 0x800F109Cu) / 4u];
}

int main(void) {
    assert(mohu_vr_owned_ammo_packet(0x800F109Cu,packets[0],0,0x800F0FDCu));
    assert(mohu_vr_owned_ammo_packet(0x800F10C4u,packets[10],1,0x800F0FDCu));
    assert(!mohu_vr_owned_ammo_packet(0x800F109Cu,packets[0],1,0x800F0FDCu));
    assert(!mohu_vr_owned_ammo_packet(0x800F109Cu,packets[0],0,0));
    packets[3]^=0xFFFFu; /* Different native UV/CLUT is still the owned icon. */
    assert(mohu_vr_owned_ammo_packet(0x800F109Cu,packets[0],0,0x800F0FDCu));
    packets[3]^=0xFFFFu;
    assert(mohu_vr_ammo_icon_packet(0x800F109Cu, packets[0], 0));
    assert(mohu_vr_ammo_icon_packet(0x800F10C4u, packets[10], 1));
    assert(!mohu_vr_ammo_icon_packet(0x800F109Cu, packets[0], 1));
    assert(!mohu_vr_ammo_icon_packet(0x800F10C4u, packets[10], 0));
    assert(!mohu_vr_ammo_icon_packet(0x800F10C4u, packets[10], 2));
    assert(!mohu_vr_ammo_icon_packet(0x800F10C8u, packets[10], 1));
    assert(!mohu_vr_ammo_icon_packet(0x800F10C4u, 0x080BA4B0u, 1));
    for (unsigned i = 11; i < 20; ++i) {
        packets[i] ^= 1u;
        assert(!mohu_vr_ammo_icon_packet(0x800F10C4u, packets[10], 1));
        packets[i] ^= 1u;
    }
    return 0;
}
