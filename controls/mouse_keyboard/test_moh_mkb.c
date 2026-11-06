#include "moh_mkb.h"

#include <stdint.h>
#include <stdio.h>
#include <math.h>

#define CHECK(value) do { \
    if (!(value)) { \
        fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #value); \
        return 1; \
    } \
} while (0)

int main(void) {
    uint8_t lx = 0, ly = 0;
    mohu_mkb_stick_pair(0, 0, 0, 0, &lx, &ly);
    CHECK(lx == 128 && ly == 128);
    mohu_mkb_stick_pair(0, 0, 1, 0, &lx, &ly);
    CHECK(lx == 128 && ly == 0);
    mohu_mkb_stick_pair(0, 1, 1, 0, &lx, &ly);
    CHECK(lx == 255 && ly == 0);
    mohu_mkb_stick_pair(1, 1, 0, 0, &lx, &ly);
    CHECK(lx == 128 && ly == 128);
    mohu_mkb_stick_pair(0, 0, 1, 1, &lx, &ly);
    CHECK(lx == 128 && ly == 128);

    CHECK(mohu_mkb_action_aliases(0xFFFFu, 1, 1, 1) == 0x2FFFu);
    CHECK(mohu_mkb_action_aliases(0xFFFFu, 0, 0, 0) == 0xFFFFu);
    CHECK(mohu_mkb_menu_buttons(0xFFFFu, 1, 0, 0, 0, 0, 0) == 0xFF7Fu);
    CHECK(mohu_mkb_menu_buttons(0xFFFFu, 0, 0, 0, 1, 0, 0) == 0xFFBFu);
    CHECK(mohu_mkb_menu_buttons(0xFFFFu, 1, 1, 1, 1, 0, 0) == 0xFFFFu);
    CHECK(mohu_mkb_menu_buttons(0xFFFFu, 0, 0, 0, 0, 1, 1) == 0xAFFFu);
    const int16_t inventory[] = {24, -1, 0, 8};
    CHECK(mohu_mkb_weapon_slot(inventory, 4, 0, 1, -1) == 2);
    CHECK(mohu_mkb_weapon_slot(inventory, 4, 0, -1, -1) == 3);
    CHECK(mohu_mkb_weapon_slot(inventory, 4, 3, 1, -1) == 0);
    CHECK(mohu_mkb_weapon_slot(inventory, 4, 0, 0, 1) == -1);
    CHECK(mohu_mkb_weapon_slot(inventory, 4, 0, 0, 3) == 3);

    MohuMkbMouse mouse = {0};
    mohu_mkb_mouse_reset(&mouse);
    mohu_mkb_mouse_motion(&mouse, 200, -300);
    int64_t dyaw = 0, dpitch = 0;
    mohu_mkb_mouse_take(&mouse, &dyaw, &dpitch);
    CHECK(dyaw == 200 * 65536 && dpitch == 300 * 65536);
    mohu_mkb_mouse_take(&mouse, &dyaw, &dpitch);
    CHECK(dyaw == 0 && dpitch == 0);
    int32_t pitch, yaw;
    mohu_mkb_angles(0, 4090 * 65536, -32 * 65536, 32 * 65536, &pitch, &yaw);
    CHECK(pitch == -32 * 65536 && yaw == 26 * 65536);
    mohu_mkb_angles(0, 0, INT64_C(10000000000), -32 * 65536, &pitch, &yaw);
    CHECK(pitch == 0x02AA0000 && yaw == 4064 * 65536);

    mohu_mkb_mouse_reset(&mouse);
    int64_t total_yaw = 0, total_pitch = 0;
    for (int i = 0; i < 3; ++i) {
        mohu_mkb_mouse_motion(&mouse, .4, -.4);
        mohu_mkb_mouse_take(&mouse, &dyaw, &dpitch);
        total_yaw += dyaw;
        total_pitch += dpitch;
    }
    CHECK(total_yaw == (int64_t)(1.2 * 65536));
    CHECK(total_pitch == (int64_t)(1.2 * 65536));
    mohu_mkb_mouse_motion(&mouse, NAN, 2);
    mohu_mkb_mouse_take(&mouse, &dyaw, &dpitch);
    CHECK(dyaw == 0 && dpitch == 0);

    printf("mouse keyboard reducer: PASS\n");
    return 0;
}
