#pragma once

#include <stdint.h>

typedef struct MohuMkbMouse {
    double pending_x, pending_y;
} MohuMkbMouse;

void mohu_mkb_mouse_reset(MohuMkbMouse* mouse);
void mohu_mkb_mouse_motion(MohuMkbMouse* mouse, double dx, double dy);
/* Consume displacement once at the owned simulation update, in Q16 native
 * angle units. Positive mouse Y looks down (negative native pitch). */
void mohu_mkb_mouse_take(MohuMkbMouse* mouse, int64_t* yaw, int64_t* pitch);
void mohu_mkb_mouse_take_scaled(MohuMkbMouse* mouse, double gain,
                                int64_t* yaw, int64_t* pitch);
/* Native camera rows use scales 2, 5/4, 2. Preserve fractional Q16 pose. */
void mohu_mkb_view_matrix(int32_t pitch, int32_t yaw, const int32_t eye[3],
                          int16_t rotation[9], int32_t translation[3]);
int mohu_mkb_shot_matrix(const int32_t origin[3], const int32_t target[3],
                         int16_t rotation[9]);
void mohu_mkb_angles(int32_t pitch, int32_t yaw, int64_t dp, int64_t dy,
                     int32_t* next_pitch, int32_t* next_yaw);

void mohu_mkb_stick_pair(int left, int right, int up, int down,
                         uint8_t* lx, uint8_t* ly);

uint16_t mohu_mkb_action_aliases(uint16_t buttons, int enter, int backspace,
                                 int alternate_square);
int mohu_mkb_weapon_slot(const int16_t* reserve, unsigned count, unsigned current,
                         int direction, int requested);
uint16_t mohu_mkb_menu_buttons(uint16_t buttons, int left, int right, int up,
                               int down, int confirm, int back);
