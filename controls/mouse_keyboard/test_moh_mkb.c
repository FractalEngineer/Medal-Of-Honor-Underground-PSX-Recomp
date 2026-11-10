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
    const unsigned weapons[] = {0, 1, 4, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17};
    for (unsigned i = 0; i < sizeof(weapons) / sizeof(weapons[0]); ++i)
        CHECK(mohu_mkb_zoom_supported(weapons[i]));
    CHECK(!mohu_mkb_zoom_supported(5)); /* Keep native sniper scope. */
    CHECK(!mohu_mkb_zoom_supported(7)); /* Camera uses native aim. */
    double zoom = 0;
    zoom = mohu_mkb_zoom_step(zoom, 1);
    CHECK(fabs(mohu_mkb_zoom_ease(zoom) - 7.0 / 27.0) < 1e-9);
    zoom = mohu_mkb_zoom_step(zoom, 1);
    CHECK(fabs(mohu_mkb_zoom_ease(zoom) - 20.0 / 27.0) < 1e-9);
    zoom = mohu_mkb_zoom_step(zoom, 1);
    CHECK(zoom == 1);
    for (int i = 0; i < 3; ++i) zoom = mohu_mkb_zoom_step(zoom, 0);
    CHECK(zoom == 0);
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
    const int16_t inventory[] = {24, -1, 0, 8, 0, 0, 0};
    const int16_t clips[] = {0, 10, 0, 0, 3, 0, 0};
    const uint16_t weapon_flags[] = {0, 9, 0, 0, 0, 1, 8};
    CHECK(mohu_mkb_weapon_slot(inventory, clips, weapon_flags, 7, 3, -1, -1) == 0);
    CHECK(mohu_mkb_weapon_slot(inventory, clips, weapon_flags, 7, 0, 1, -1) == 3);
    CHECK(mohu_mkb_weapon_slot(inventory, clips, weapon_flags, 7, 3, 1, -1) == 4);
    CHECK(mohu_mkb_weapon_slot(inventory, clips, weapon_flags, 7, 4, 1, -1) == 5);
    CHECK(mohu_mkb_weapon_slot(inventory, clips, weapon_flags, 7, 5, 1, -1) == 6);
    CHECK(mohu_mkb_weapon_slot(inventory, clips, weapon_flags, 7, 6, 1, -1) == 0);
    CHECK(mohu_mkb_weapon_slot(inventory, clips, weapon_flags, 7, 0, 0, 1) == -1);
    CHECK(mohu_mkb_weapon_slot(inventory, clips, weapon_flags, 7, 0, 0, 2) == -1);
    CHECK(mohu_mkb_weapon_slot(inventory, clips, weapon_flags, 7, 0, 0, 4) == 4);

    MohuMkbMouse mouse = {0};
    mohu_mkb_mouse_reset(&mouse);
    mohu_mkb_mouse_motion(&mouse, 200, -300);
    int64_t dyaw = 0, dpitch = 0;
    mohu_mkb_mouse_take(&mouse, &dyaw, &dpitch);
    CHECK(dyaw == 200 * 65536 && dpitch == 300 * 65536);
    mohu_mkb_mouse_take(&mouse, &dyaw, &dpitch);
    CHECK(dyaw == 0 && dpitch == 0);

    /* Tiny motions survive consumption; batching cannot change turn rate. */
    mohu_mkb_mouse_reset(&mouse);
    for (int i = 0; i < 8; ++i) {
        mohu_mkb_mouse_motion(&mouse, 1, -1);
        mohu_mkb_mouse_take_scaled(&mouse, 0.125, &dyaw, &dpitch);
        CHECK(dyaw == 8192 && dpitch == 8192);
    }
    int16_t rotation[9], previous[9];
    int32_t translation[3];
    const int32_t eye[3] = {100 * 65536 + 16384, 20 * 65536, -30 * 65536};
    mohu_mkb_view_matrix(0, 0, eye, previous, translation);
    CHECK(translation[0] == -201 && translation[1] == -25 && translation[2] == 60);
    for (int i = 1; i <= 8; ++i) {
        mohu_mkb_view_matrix(0, i * 8192, eye, rotation, translation);
        CHECK(rotation[2] < previous[2] && rotation[6] > previous[6]);
        for (unsigned j = 0; j < 9; ++j) previous[j] = rotation[j];
    }
    /* The forward column follows a nearby target with vertical parallax. */
    const int32_t origin[3] = {10 * 65536, 40 * 65536, 20 * 65536};
    const int32_t target[3] = {110 * 65536, 5 * 65536, 120 * 65536};
    CHECK(mohu_mkb_shot_matrix(origin, target, rotation));
    const double norm = sqrt(100 * 100 + 35 * 35 + 100 * 100);
    CHECK(fabs(rotation[2] / 4096.0 - 100 / norm) < 1.0 / 4096);
    CHECK(fabs(rotation[5] / 4096.0 + 35 / norm) < 1.0 / 4096);
    CHECK(!mohu_mkb_shot_matrix(origin, origin, rotation));
    CHECK(mohu_mkb_mounted_yaw(0x01000000, 0x01000000, 0x10000, 660) == 0x01010000);
    CHECK(mohu_mkb_mounted_yaw(0x01000000, 0x01000000, 0x08000000, 660) == 0x03940000);
    CHECK(mohu_mkb_mounted_yaw(0x01000000, 0x01000000, -0x08000000, 330) == (int32_t)0xffb60000u);
    CHECK(mohu_mkb_mounted_yaw(0x07ff0000, 0, 0x20000, 0) == (int32_t)0xf8010000u);
    int32_t pitch_target, applied;
    CHECK(mohu_mkb_mounted_pitch(-272, 0, 200, 0,
                                 50 * 65536, &pitch_target, &applied));
    CHECK(pitch_target < -272 * 65536 && applied == 50 * 65536);
    CHECK(mohu_mkb_mounted_pitch(-272, 0, 200, 0,
                                 1000 * 65536, &pitch_target, &applied));
    CHECK(pitch_target == (-272 - 60) * 65536 && applied < 1000 * 65536);
    CHECK(mohu_mkb_mounted_pitch(-272, 0, 200, 1,
                                 -1000 * 65536, &pitch_target, &applied));
    CHECK(pitch_target == (-272 + 27) * 65536 && applied > -1000 * 65536);
    CHECK(!mohu_mkb_mounted_pitch(0, 0, 0, 0, 1, &pitch_target, &applied));
    CHECK(mohu_mkb_mounted_pitch(-272, 0, 200, 0,
                                 -33 * 65536, &pitch_target, &applied));
    CHECK(pitch_target > -272 * 65536 && applied == -33 * 65536);
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
