/* Default-OFF capture of the real SP world packet/material inputs.
 *
 * 80010CF0 entry: caller return address (0x8009A51C), a0/a1 packet range,
 * the level pointer in s2, the resolved tree root/vertex table, the record
 * table base at scratch+0x3E8, and the scratch/range contents left by the
 * previous draw.
 *
 * 80011424 entry (the per-face preflight body): s7 = face+8, index =
 * half[face+6], record = word[scratch+0x3E8] + index*12, the 12 record bytes,
 * the face's raw 16 bytes, the record table, and the gpr[27]+0xD8/+0xDC
 * table words. This is evidence for a material mapping, not a decoder.
 *
 * No hook runs unless MOHU_SP_WORLD_CAPTURE names a file. Limits default to
 * 3 draws and 32 faces. The file is written once, then capture disables.
 */
#include "world_capture.h"
#include "cpu_state.h"
#include "mod_plugins.h"
#include "raycast.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CAPTURE_MAX_DRAWS 8u
#define CAPTURE_MAX_FACES 128u
#define CAPTURE_SCRATCH 0x1F800000u
#define CAPTURE_SCRATCH_SIZE 0x400u
#define CAPTURE_RANGE_MAX 0x1000u
#define CAPTURE_RECORD_SIZE 12u
#define CAPTURE_FACE_WINDOW 16u
#define CAPTURE_TABLE_ENTRIES 16u
#define CAPTURE_TABLE_SIZE (CAPTURE_TABLE_ENTRIES * CAPTURE_RECORD_SIZE)

typedef struct {
    uint32_t ra, begin, limit, a2, a3, sp, gp, level, sub, root, count, table;
    uint32_t scratch_hash, range_len, range_hash;
    uint32_t record_base, record_entries;
    uint8_t scratch[CAPTURE_SCRATCH_SIZE];
    uint8_t range[CAPTURE_RANGE_MAX];
    uint8_t records[CAPTURE_TABLE_SIZE];
} DrawCapture;

typedef struct {
    uint32_t draw, ra, s7, face, index, table_base, record_base, record_ok;
    uint32_t flags, gpr27, table_d8, table_dc, table_ok;
    uint32_t gpr[32];
    uint8_t face_bytes[CAPTURE_FACE_WINDOW];
    uint8_t record[CAPTURE_RECORD_SIZE];
    uint8_t table[CAPTURE_TABLE_SIZE];
} FaceCapture;

static DrawCapture g_draws[CAPTURE_MAX_DRAWS];
static FaceCapture g_faces[CAPTURE_MAX_FACES];
static unsigned g_draw_count, g_face_count;
static unsigned g_draw_limit, g_face_limit;
static int g_enabled, g_written;
static const char* g_path;
static int g_has_previous;

static int span(uint32_t p, uint32_t size) {
    if (p & 3u) return 0;
    if (p >= 0x80000000u && p < 0x80200000u && size <= 0x80200000u - p)
        return 1;
    if (p >= CAPTURE_SCRATCH && p < CAPTURE_SCRATCH + CAPTURE_SCRATCH_SIZE &&
        size <= CAPTURE_SCRATCH + CAPTURE_SCRATCH_SIZE - p)
        return 1;
    return 0;
}

static uint32_t fnv1a(const uint8_t* data, unsigned size) {
    uint32_t hash = 2166136261u;
    for (unsigned i = 0; i < size; ++i) {
        hash ^= data[i];
        hash *= 16777619u;
    }
    return hash;
}

static int valid_table(uint32_t base) {
    return base && (base & 3u) == 0 && mohu_vr_ray_span(base, CAPTURE_TABLE_SIZE);
}

static void copy_span(uint8_t* out, uint32_t address, unsigned size) {
    for (unsigned i = 0; i < size; ++i)
        out[i] = psx_mod_read_byte(address + i);
}

static void capture_previous_range(void) {
    if (!g_has_previous || g_draw_count == 0) return;
    DrawCapture* draw = &g_draws[g_draw_count - 1u];
    if (draw->limit < draw->begin) return;
    uint32_t length = draw->limit - draw->begin;
    if (length > 0x20000u || !span(draw->begin, length)) return;
    draw->range_len = length < CAPTURE_RANGE_MAX ? length : CAPTURE_RANGE_MAX;
    copy_span(draw->range, draw->begin, draw->range_len);
    draw->range_hash = fnv1a(draw->range, draw->range_len);
}

static void capture_previous_scratch(void) {
    if (g_draw_count == 0) return;
    DrawCapture* draw = &g_draws[g_draw_count - 1u];
    copy_span(draw->scratch, CAPTURE_SCRATCH, CAPTURE_SCRATCH_SIZE);
    draw->scratch_hash = fnv1a(draw->scratch, CAPTURE_SCRATCH_SIZE);
    draw->record_base = psx_mod_read_word(CAPTURE_SCRATCH + 0x3E8u);
    if (valid_table(draw->record_base)) {
        copy_span(draw->records, draw->record_base, CAPTURE_TABLE_SIZE);
        draw->record_entries = CAPTURE_TABLE_ENTRIES;
    }
}

static void write_hex(FILE* file, const uint8_t* data, unsigned size) {
    static const char hex[] = "0123456789abcdef";
    for (unsigned i = 0; i < size; ++i) {
        fputc(hex[data[i] >> 4], file);
        fputc(hex[data[i] & 0xFu], file);
    }
}

static void flush_capture(void) {
    if (!g_enabled || g_written) return;
    FILE* file = fopen(g_path, "wb");
    if (!file) {
        fprintf(stdout, "mohu-vr-world-capture: cannot open %s\n", g_path);
        fflush(stdout);
        return;
    }
    fprintf(file, "MOHU-SP-WORLD-CAPTURE 1\n");
    fprintf(file, "draws=%u faces=%u draw_limit=%u face_limit=%u\n",
            g_draw_count, g_face_count, g_draw_limit, g_face_limit);
    for (unsigned i = 0; i < g_draw_count; ++i) {
        const DrawCapture* d = &g_draws[i];
        fprintf(file,
                "draw=%u ra=0x%08X begin=0x%08X limit=0x%08X a2=0x%08X "
                "a3=0x%08X sp=0x%08X gp=0x%08X level=0x%08X sub=0x%08X "
                "root=0x%08X count=%u table=0x%08X\n",
                i, d->ra, d->begin, d->limit, d->a2, d->a3, d->sp, d->gp,
                d->level, d->sub, d->root, d->count, d->table);
        fprintf(file, "draw=%u scratch_len=%u scratch_hash=0x%08X scratch=",
                i, CAPTURE_SCRATCH_SIZE, d->scratch_hash);
        write_hex(file, d->scratch, CAPTURE_SCRATCH_SIZE);
        fputc('\n', file);
        fprintf(file, "draw=%u range_len=%u range_hash=0x%08X range=", i,
                d->range_len, d->range_hash);
        write_hex(file, d->range, d->range_len);
        fputc('\n', file);
        fprintf(file, "draw=%u record_base=0x%08X record_entries=%u records=",
                i, d->record_base, d->record_entries);
        write_hex(file, d->records,
                  d->record_entries * CAPTURE_RECORD_SIZE);
        fputc('\n', file);
    }
    for (unsigned i = 0; i < g_face_count; ++i) {
        const FaceCapture* f = &g_faces[i];
        fprintf(file,
                "face=%u draw=%u ra=0x%08X s7=0x%08X face=0x%08X "
                "index=%u table_base=0x%08X record_base=0x%08X ok=%u "
                "flags=0x%08X gpr27=0x%08X d8=0x%08X dc=0x%08X\n",
                i, f->draw, f->ra, f->s7, f->face, f->index, f->table_base,
                f->record_base, f->record_ok, f->flags, f->gpr27, f->table_d8,
                f->table_dc);
        fprintf(file, "face=%u gpr=", i);
        for (unsigned r = 0; r < 32; ++r)
            fprintf(file, "%08X", f->gpr[r]);
        fputc('\n', file);
        fprintf(file, "face=%u face_bytes=", i);
        write_hex(file, f->face_bytes, CAPTURE_FACE_WINDOW);
        fprintf(file, " record=");
        write_hex(file, f->record, CAPTURE_RECORD_SIZE);
        fprintf(file, " table=");
        write_hex(file, f->table, f->table_ok * CAPTURE_TABLE_SIZE);
        fputc('\n', file);
    }
    fclose(file);
    g_written = 1;
    g_enabled = 0;
    fprintf(stdout,
            "mohu-vr-world-capture: wrote %s draws=%u faces=%u\n",
            g_path, g_draw_count, g_face_count);
    fflush(stdout);
}

static void capture_packet(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!g_enabled || !cpu || cpu->gpr[31] != 0x8009A51Cu) return;

    capture_previous_range();
    capture_previous_scratch();
    g_has_previous = 0;

    if (g_draw_count == g_draw_limit) {
        flush_capture();
        return;
    }

    DrawCapture* draw = &g_draws[g_draw_count];
    memset(draw, 0, sizeof *draw);
    draw->ra = cpu->gpr[31];
    draw->begin = cpu->gpr[4];
    draw->limit = cpu->gpr[5];
    draw->a2 = cpu->gpr[6];
    draw->a3 = cpu->gpr[7];
    draw->sp = cpu->gpr[29];
    draw->gp = cpu->gpr[28];
    draw->level = cpu->gpr[18];
    if (mohu_vr_ray_span(draw->level, 0x40u)) {
        draw->sub = psx_mod_read_word(draw->level + 8u);
        draw->count = psx_mod_read_word(draw->level + 0x3Cu);
        draw->table = psx_mod_read_word(draw->level + 0x2Cu);
        if (mohu_vr_ray_span(draw->sub, 0x18u))
            draw->root = psx_mod_read_word(draw->sub + 0x14u);
    }
    g_has_previous = 1;
    ++g_draw_count;
}

static void capture_face(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!g_enabled || !cpu || g_face_count >= g_face_limit) return;
    if (cpu->gpr[31] != 0x80011008u || cpu->gpr[19] != 0x1F800000u) return;

    FaceCapture* face = &g_faces[g_face_count];
    memset(face, 0, sizeof *face);
    face->draw = g_draw_count ? g_draw_count - 1u : 0u;
    face->ra = cpu->gpr[31];
    face->s7 = cpu->gpr[23];
    face->face = face->s7 - 8u;
    face->flags = cpu->gpr[22];
    face->gpr27 = cpu->gpr[27];
    memcpy(face->gpr, cpu->gpr, sizeof face->gpr);

    int window_ok = 0;
    if (span(face->face, CAPTURE_FACE_WINDOW)) {
        copy_span(face->face_bytes, face->face, CAPTURE_FACE_WINDOW);
        face->index = psx_mod_read_half(face->s7 - 2u);
        window_ok = 1;
    }
    face->table_base = psx_mod_read_word(CAPTURE_SCRATCH + 0x3E8u);
    if (window_ok && face->table_base && (face->table_base & 3u) == 0u) {
        const uint64_t record = (uint64_t)face->table_base +
                                (uint64_t)face->index * CAPTURE_RECORD_SIZE;
        if (record <= 0xFFFFFFFFu &&
            mohu_vr_ray_span((uint32_t)record, CAPTURE_RECORD_SIZE)) {
            face->record_base = (uint32_t)record;
            face->record_ok = 1;
            copy_span(face->record, face->record_base, CAPTURE_RECORD_SIZE);
        }
    }
    if (valid_table(face->table_base)) {
        copy_span(face->table, face->table_base, CAPTURE_TABLE_SIZE);
        face->table_ok = 1;
    }
    if (face->gpr27 && (face->gpr27 & 3u) == 0u &&
        mohu_vr_ray_span(face->gpr27, 0xE0u)) {
        face->table_d8 = psx_mod_read_word(face->gpr27 + 0xD8u);
        face->table_dc = psx_mod_read_word(face->gpr27 + 0xDCu);
    }
    ++g_face_count;
}

void mohu_world_capture_activate(void) {
    memset(g_draws, 0, sizeof g_draws);
    memset(g_faces, 0, sizeof g_faces);
    g_draw_count = g_face_count = 0;
    g_written = 0;
    g_has_previous = 0;

    g_path = getenv("MOHU_SP_WORLD_CAPTURE");
    g_enabled = g_path && *g_path;
    g_draw_limit = 3;
    g_face_limit = 32;
    const char* draws = getenv("MOHU_SP_WORLD_CAPTURE_DRAWS");
    const char* faces = getenv("MOHU_SP_WORLD_CAPTURE_FACES");
    if (draws) {
        unsigned value = (unsigned)strtoul(draws, NULL, 10);
        if (value >= 1u && value <= CAPTURE_MAX_DRAWS) g_draw_limit = value;
    }
    if (faces) {
        unsigned value = (unsigned)strtoul(faces, NULL, 10);
        if (value >= 1u && value <= CAPTURE_MAX_FACES) g_face_limit = value;
    }
    if (g_enabled) {
        fprintf(stdout,
                "mohu-vr-world-capture: armed path=%s draws=%u faces=%u\n",
                g_path, g_draw_limit, g_face_limit);
        fflush(stdout);
    }
}

static int capture_command(const char* args, char* reply, int cap) {
    if (args && strncmp(args, "write", 5) == 0) flush_capture();
    const int used = snprintf(reply, (size_t)cap,
                              "{\"enabled\":%d,\"written\":%d,\"draws\":%u,"
                              "\"faces\":%u,\"draw_limit\":%u,"
                              "\"face_limit\":%u}",
                              g_enabled, g_written, g_draw_count, g_face_count,
                              g_draw_limit, g_face_limit);
    return used > 0 && used < cap ? 0 : -1;
}

void mohu_world_capture_packet(CPUState* cpu) {
    capture_packet(cpu, 0x80010CF0u);
}

void mohu_world_capture_face(CPUState* cpu) {
    capture_face(cpu, 0x80011424u);
}

void mohu_world_capture_register(void) {
    (void)psx_mod_register_command("mohu.vr.world-capture", capture_command);
}
