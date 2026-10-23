#ifndef MOHU_VR_CAMERA_MAP_H
#define MOHU_VR_CAMERA_MAP_H

/*
 * Single-player scene roots measured in the slot-0 Underground scene.
 *
 * These are globals that hold pointers, not object addresses. The source-game
 * equivalents are 0x8009D64C (scene) and 0x8009D654 (player). The level
 * transformer's address-only diff independently maps 0x8009D638 to
 * 0x800AA160, placing all three roots in the same relocated data table.
 */
#define MOHU_VR_SP_SCENE_POINTER_ADDR 0x800AA174u
#define MOHU_VR_SP_PLAYER_POINTER_ADDR 0x800AA17Cu

/*
 * Underground's actor layout is shifted by 0x14 from the reference game's
 * measured 0x388 input pointer. The level transformer reads +0x39C in the
 * same position that the reference reads +0x388.
 */
#define MOHU_VR_PLAYER_INPUT_OFFSET 0x39Cu

#endif
