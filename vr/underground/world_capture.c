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
#include "gpu.h"
#include "world_decode.h"

#define CAPTURE_MASK0 0x800B7490u
#define CAPTURE_MASK1 0x800B7494u
#define CAPTURE_MASK_BYPASS 0x800B7498u

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
/* Material records are read in place by the decoder; the dump above keeps only
 * the first 16 for evidence. 1024 covers every observed index (max 219). */
#define CAPTURE_MATERIAL_RECORDS 1024u
#define CAPTURE_PACKET_SIZE 0x60u
#define CAPTURE_NATIVE_FACES 4096u
#define CAPTURE_NATIVE_REGS 512u
#define CAPTURE_MAX_ENTRIES 64u
#define CAPTURE_ENTRY_FACES 512u
#define CAPTURE_VISIBLE_MAX 512u
#define CAPTURE_VISIBLE_COUNT 0x800B74B4u
#define CAPTURE_VISIBLE_LIST 0x800B74B8u
#define CAPTURE_GP0_MAX 128u
#define CAPTURE_GP0_FRAME_ENTRIES 4096u

typedef struct {
    uint32_t src, opcode, n_words, words[GPU_GP0_RING_MAX_WORDS];
} Gp0Capture;

typedef struct {
    uint32_t ra, begin, limit, a2, a3, sp, gp, level, sub, root, count, table;
    uint32_t entry_index;
    uint32_t scratch_hash, range_len, range_hash;
    uint32_t record_base, record_entries;
    uint32_t native_faces[CAPTURE_NATIVE_FACES];
    uint32_t native_regs[CAPTURE_NATIVE_REGS][32];
    uint32_t native_count, native_overflow;
    int compare_valid;
    uint32_t compare_status;
    uint32_t cmp_native, cmp_unique, cmp_matched, cmp_missing;
    uint32_t cmp_decoded_only, cmp_dup, cmp_multi, cmp_multi_count;
    uint32_t cmp_triangles, cmp_first_missing, cmp_first_dup;
    uint32_t cmp_first_multi;
    uint32_t cmp_missing_addrs[16];
    uint32_t cmp_missing_words[16][4];
    uint32_t cmp_missing_regs[16][32];
    uint32_t cmp_missing_owner[16];
    uint8_t cmp_missing_consulted[16];
    uint32_t cmp_missing_list_count, cmp_missing_in_range;
    int vis_valid;
    uint32_t vis_status, vis_native, vis_matched, vis_missing;
    uint32_t vis_decoded_only, vis_triangles, vis_first_missing;
    int gp0_valid;
    uint32_t gp0_count, gp0_overflow;
    Gp0Capture gp0[CAPTURE_GP0_MAX];
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
    uint32_t packet_ptr;                  /* gpr[4] at face entry */
    uint8_t packet[CAPTURE_PACKET_SIZE];  /* packet bytes after this face */
    uint32_t packet_hash;
    int packet_dumped;
} FaceCapture;

/* One 80010CF0 invocation, recorded regardless of return address. Faces are
 * attributed to the most recent entry so a non-draw caller cannot leak faces
 * into the preceding draw. */
typedef struct {
    uint32_t index, ra, pc, level, sub, root, table, count;
    uint32_t gpr[32];
    uint32_t faces, overflow, selected;
    uint32_t visible_count, visible_overflow;
    uint32_t visible_entry[CAPTURE_VISIBLE_MAX];
    uint32_t visible_faces[CAPTURE_VISIBLE_MAX];
    uint32_t visible_list[CAPTURE_VISIBLE_MAX];
    uint32_t addrs[CAPTURE_ENTRY_FACES];
    int compare_valid;
    uint32_t compare_status, cmp_native, cmp_matched, cmp_missing;
    uint32_t cmp_decoded_only, cmp_triangles, cmp_first_missing;
} EntryCapture;

static DrawCapture g_draws[CAPTURE_MAX_DRAWS];
static FaceCapture g_faces[CAPTURE_MAX_FACES];
static EntryCapture g_entries[CAPTURE_MAX_ENTRIES];
static unsigned g_draw_count, g_face_count, g_entry_count, g_entry_overflow;
static unsigned g_draw_limit, g_face_limit;
static int g_enabled, g_written;
static const char* g_path;
static int g_has_previous;
static int g_census_done;

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

/* Dump the face's packet destination (gpr[4] at its entry). The wrapper calls
 * this immediately after 80011424 returns; the fallback call at the next face
 * entry only runs if the wrapper was not used. */
static void capture_previous_face_packet(void) {
    if (g_face_count == 0) return;
    FaceCapture* face = &g_faces[g_face_count - 1u];
    if (face->packet_dumped) return;
    if (!face->packet_ptr || !span(face->packet_ptr, CAPTURE_PACKET_SIZE))
        return;
    copy_span(face->packet, face->packet_ptr, CAPTURE_PACKET_SIZE);
    face->packet_hash = fnv1a(face->packet, CAPTURE_PACKET_SIZE);
    face->packet_dumped = 1;
}

/* The per-draw record-table pointer is scratch+0x3E8 at packet entry; the
 * DrawCapture copy is filled later in the entry path, so read it live here. */
static uint32_t live_record_table(const DrawCapture* draw) {
    if (draw->record_base) return draw->record_base;
    /* The scratch copy is filled at the NEXT entry and can still describe the
     * previous draw (slot 5). A face from this draw carries the correct base. */
    for (unsigned i = g_face_count; i > 0; --i) {
        if (g_faces[i - 1u].table_base) return g_faces[i - 1u].table_base;
    }
    return psx_mod_read_word(CAPTURE_SCRATCH + 0x3E8u);
}

/* Decode the real arena once, from the captured root/table/count, so the
 * decoder is exercised against actual guest data rather than a synthetic
 * fixture. Diagnostic only; no mesh escapes this function. */
static void capture_census(const DrawCapture* draw) {
    if (g_census_done || !draw->root || !draw->table || !draw->count) return;
    g_census_done = 1;
    MohuWorldRequest request;
    memset(&request, 0, sizeof request);
    request.root = draw->root;
    request.vertex_table = draw->table;
    request.vertex_count = draw->count;
    request.masks[0] = psx_mod_read_word(CAPTURE_MASK0);
    request.masks[1] = psx_mod_read_word(CAPTURE_MASK1);
    /* Census intent: every resident leaf, before view-dependent culling. */
    request.bypass_masks = 1;
    request.generation = 1;
    request.record_table = live_record_table(draw);
    request.record_count = CAPTURE_MATERIAL_RECORDS;
    request.require_materials = request.record_table != 0;
    MohuWorldMesh mesh;
    MohuWorldReport report;
    const MohuWorldStatus status = mohu_world_decode(&request, &mesh, &report);
    fprintf(stdout,
            "mohu-vr-world-census: status=%s root=0x%08X table=0x%08X "
            "count=%u masks=0x%08X,0x%08X nodes=%u leaves=%u triangles=%u "
            "tokens=%u materials=%u records=0x%08X/%u "
            "bounds=%d,%d,%d..%d,%d,%d "
            "reject=0x%08X/0x%08X/%u\n",
            mohu_world_status_name(status), request.root, request.vertex_table,
            request.vertex_count, request.masks[0], request.masks[1],
            report.nodes_visited, report.leaves_visited,
            report.triangles_decoded, mesh.material_tokens,
            mesh.materials_decoded, request.record_table, request.record_count,
            mesh.bounds_min[0], mesh.bounds_min[1], mesh.bounds_min[2],
            mesh.bounds_max[0], mesh.bounds_max[1], mesh.bounds_max[2],
            report.node, report.leaf, report.detail);
    fflush(stdout);
    mohu_world_mesh_free(&mesh);
}

/* Decode the exact visible-entry set the native builder submitted and compare
 * it with the native face addresses. This is the view-specific parity check,
 * separate from the full-tree census. */
static void visible_compare(DrawCapture* draw) {
    if (draw->entry_index >= g_entry_count) return;
    const EntryCapture* entry = &g_entries[draw->entry_index];
    const uint32_t count = entry->visible_count < CAPTURE_VISIBLE_MAX
                               ? entry->visible_count
                               : CAPTURE_VISIBLE_MAX;
    uint32_t entries[CAPTURE_VISIBLE_MAX];
    memcpy(entries, entry->visible_entry, count * sizeof *entries);

    MohuWorldVisibleRequest request;
    memset(&request, 0, sizeof request);
    request.entries = entries;
    request.entry_count = count;
    request.vertex_table = draw->table;
    request.vertex_count = draw->count;
    request.generation = 1;
    request.record_table = live_record_table(draw);
    request.record_count = CAPTURE_MATERIAL_RECORDS;
    request.require_materials = request.record_table != 0;
    MohuWorldMesh mesh;
    MohuWorldReport report;
    const MohuWorldStatus status =
        mohu_world_decode_visible(&request, &mesh, &report);

    draw->vis_valid = 1;
    draw->vis_status = status;
    draw->vis_native = draw->native_count;
    if (status == MOHU_WORLD_OK) {
        draw->vis_triangles = mesh.triangle_count;
        for (uint32_t i = 0; i < draw->native_count; ++i) {
            const uint32_t address = draw->native_faces[i];
            int seen = 0;
            for (uint32_t j = 0; j < i; ++j) {
                if (draw->native_faces[j] == address) {
                    seen = 1;
                    break;
                }
            }
            if (seen) continue;
            int found = 0;
            for (uint32_t t = 0; t < mesh.triangle_count; ++t) {
                if (mesh.triangles[t].face_tag == address) {
                    found = 1;
                    break;
                }
            }
            if (found) {
                ++draw->vis_matched;
            } else {
                ++draw->vis_missing;
                if (!draw->vis_first_missing)
                    draw->vis_first_missing = address;
            }
        }
        for (uint32_t t = 0; t < mesh.triangle_count; ++t) {
            const uint32_t source = mesh.triangles[t].face_tag;
            int seen = 0;
            for (uint32_t k = 0; k < t; ++k) {
                if (mesh.triangles[k].face_tag == source) {
                    seen = 1;
                    break;
                }
            }
            if (seen) continue;
            int found = 0;
            for (uint32_t i = 0; i < draw->native_count; ++i) {
                if (draw->native_faces[i] == source) {
                    found = 1;
                    break;
                }
            }
            if (!found) ++draw->vis_decoded_only;
        }
    }
    fprintf(stdout,
            "mohu-vr-visible-faces: draw=%u status=%s native=%u matched=%u "
            "missing=%u decoded_only=%u triangles=%u materials=%u "
            "first_missing=0x%08X\n",
            (unsigned)(draw - g_draws), mohu_world_status_name(status),
            draw->vis_native, draw->vis_matched, draw->vis_missing,
            draw->vis_decoded_only, draw->vis_triangles,
            mesh.materials_decoded, draw->vis_first_missing);
    if (status == MOHU_WORLD_OK) {
        fprintf(stdout, "mohu-vr-visible-sources: draw=%u sources=",
                (unsigned)(draw - g_draws));
        for (uint32_t t = 0; t < mesh.triangle_count; ++t) {
            const uint32_t source = mesh.triangles[t].face_tag;
            int seen = 0;
            for (uint32_t k = 0; k < t; ++k)
                if (mesh.triangles[k].face_tag == source) seen = 1;
            if (!seen) fprintf(stdout, "%s0x%08X", t ? "," : "", source);
        }
        fprintf(stdout, " native=");
        for (uint32_t i = 0; i < draw->native_count; ++i)
            fprintf(stdout, "%s0x%08X", i ? "," : "",
                    draw->native_faces[i]);
        fputc('\n', stdout);
    }
    fflush(stdout);
    mohu_world_mesh_free(&mesh);
}

/* Record the final GP0 polygon/env commands the draw emitted. The debug ring
 * is filtered to the draw's packet range (physical form). Word offsets are
 * evidence only: per-face texpage/CLUT attribution is not established. */
static void gp0_dump(DrawCapture* draw) {
    draw->gp0_valid = 1;
    static GpuGp0RingEntry entries[CAPTURE_GP0_FRAME_ENTRIES];
    extern uint32_t s_frame_count;
    if (!gpu_gp0_ring_capacity()) return;
    const uint32_t begin = draw->begin & 0x1FFFFFu;
    const uint32_t limit = draw->limit & 0x1FFFFFu;
    for (uint32_t delta = 0; delta < 2; ++delta) {
        const uint32_t frame = s_frame_count - delta;
        const int dumped = gpu_gp0_ring_dump_frame(
            frame, entries, (int)CAPTURE_GP0_FRAME_ENTRIES);
        for (int i = 0; i < dumped; ++i) {
            const GpuGp0RingEntry* entry = &entries[i];
            const uint8_t opcode = entry->opcode;
            const int wanted = (opcode >= 0x20 && opcode <= 0x3F) ||
                               (opcode >= 0xE1 && opcode <= 0xE6);
            if (!wanted) continue;
            const uint32_t source = entry->src_addr & 0x1FFFFFu;
            if (source < begin || source >= limit) continue;
            if (draw->gp0_count >= CAPTURE_GP0_MAX) {
                ++draw->gp0_overflow;
                continue;
            }
            Gp0Capture* gp0 = &draw->gp0[draw->gp0_count++];
            gp0->src = entry->src_addr;
            gp0->opcode = opcode;
            gp0->n_words = entry->n_words;
            for (unsigned w = 0; w < GPU_GP0_RING_MAX_WORDS; ++w)
                gp0->words[w] = entry->cmd[w];
        }
    }
}

/* Compare the face addresses the native loop actually processed with the
 * source addresses the decoder produced for the same root. Decoded-only
 * addresses are expected because the census bypasses camera culling. A native
 * address absent from the decoded mesh is a decoder failure, not a cull. */
static void capture_compare(DrawCapture* draw) {
    if (draw->compare_valid) return;
    draw->compare_valid = 1;
    gp0_dump(draw);
    if (!draw->native_count) return;
    draw->cmp_native = draw->native_count;
    if (!draw->root || !draw->table || !draw->count) {
        draw->compare_status = MOHU_WORLD_REJECT_ARGUMENT;
        return;
    }
    MohuWorldRequest request;
    memset(&request, 0, sizeof request);
    request.root = draw->root;
    request.vertex_table = draw->table;
    request.vertex_count = draw->count;
    request.masks[0] = psx_mod_read_word(CAPTURE_MASK0);
    request.masks[1] = psx_mod_read_word(CAPTURE_MASK1);
    request.bypass_masks = 1;
    request.generation = 1;
    MohuWorldMesh mesh;
    MohuWorldReport report;
    const MohuWorldStatus status = mohu_world_decode(&request, &mesh, &report);
    draw->compare_status = status;
    if (status == MOHU_WORLD_OK) {
        draw->cmp_triangles = mesh.triangle_count;
        for (uint32_t i = 0; i < draw->native_count; ++i) {
            const uint32_t address = draw->native_faces[i];
            int seen = 0;
            for (uint32_t j = 0; j < i; ++j) {
                if (draw->native_faces[j] == address) {
                    seen = 1;
                    break;
                }
            }
            if (seen) {
                ++draw->cmp_dup;
                if (!draw->cmp_first_dup) draw->cmp_first_dup = address;
                continue;
            }
            ++draw->cmp_unique;
            uint32_t decoded = 0;
            for (uint32_t t = 0; t < mesh.triangle_count; ++t) {
                if (mesh.triangles[t].face_tag == address) ++decoded;
            }
            if (!decoded) {
                ++draw->cmp_missing;
                if (!draw->cmp_first_missing)
                    draw->cmp_first_missing = address;
                if (draw->cmp_missing_list_count < 16) {
                    const uint32_t k = draw->cmp_missing_list_count++;
                    const int consulted = address >= mesh.source_start &&
                                          address < mesh.source_end;
                    draw->cmp_missing_addrs[k] = address;
                    draw->cmp_missing_words[k][0] =
                        span(address, 8u) ? psx_mod_read_word(address)
                                          : 0xFFFFFFFFu;
                    draw->cmp_missing_words[k][1] =
                        span(address, 8u) ? psx_mod_read_word(address + 4u)
                                          : 0xFFFFFFFFu;
                    draw->cmp_missing_words[k][2] =
                        (address >= 8u && span(address - 8u, 8u))
                            ? psx_mod_read_word(address - 8u) : 0xFFFFFFFFu;
                    draw->cmp_missing_words[k][3] =
                        (address >= 4u && span(address - 4u, 8u))
                            ? psx_mod_read_word(address - 4u) : 0xFFFFFFFFu;
                    for (uint32_t j = 0; j < draw->native_count; ++j) {
                        if (draw->native_faces[j] == address) {
                            if (j < CAPTURE_NATIVE_REGS)
                                memcpy(draw->cmp_missing_regs[k],
                                       draw->native_regs[j],
                                       sizeof draw->cmp_missing_regs[k]);
                            break;
                        }
                    }
                    for (uint32_t p = draw->root;
                         draw->table > draw->root && p + 4u <= draw->table;
                         p += 4u) {
                        if (psx_mod_read_word(p) == address) {
                            draw->cmp_missing_owner[k] = p;
                            break;
                        }
                    }
                    if (!draw->cmp_missing_owner[k]) {
                        for (uint32_t p = 0x800A0000u;
                             p + 4u <= 0x80100000u; p += 4u) {
                            if (p >= draw->root && p < draw->table) continue;
                            if (psx_mod_read_word(p) == address) {
                                draw->cmp_missing_owner[k] = p;
                                break;
                            }
                        }
                    }
                    draw->cmp_missing_consulted[k] = (uint8_t)consulted;
                    draw->cmp_missing_in_range += (uint32_t)consulted;
                }
            } else {
                ++draw->cmp_matched;
                if (decoded > 1) {
                    ++draw->cmp_multi;
                    draw->cmp_multi_count += decoded;
                    if (!draw->cmp_first_multi)
                        draw->cmp_first_multi = address;
                }
            }
        }
        for (uint32_t t = 0; t < mesh.triangle_count; ++t) {
            const uint32_t source = mesh.triangles[t].face_tag;
            int seen = 0;
            for (uint32_t k = 0; k < t; ++k) {
                if (mesh.triangles[k].face_tag == source) {
                    seen = 1;
                    break;
                }
            }
            if (seen) continue;
            int found = 0;
            for (uint32_t i = 0; i < draw->native_count; ++i) {
                if (draw->native_faces[i] == source) {
                    found = 1;
                    break;
                }
            }
            if (!found) ++draw->cmp_decoded_only;
        }
    }
    fprintf(stdout,
            "mohu-vr-native-faces: draw=%u status=%s native=%u overflow=%u "
            "unique=%u matched=%u missing=%u decoded_only=%u dup=%u "
            "multi=%u multi_count=%u triangles=%u first_missing=0x%08X "
            "first_dup=0x%08X first_multi=0x%08X missing_in_range=%u "
            "missing_addrs=",
            (unsigned)(draw - g_draws), mohu_world_status_name(status),
            draw->cmp_native, draw->native_overflow, draw->cmp_unique,
            draw->cmp_matched, draw->cmp_missing, draw->cmp_decoded_only,
            draw->cmp_dup, draw->cmp_multi, draw->cmp_multi_count,
            draw->cmp_triangles, draw->cmp_first_missing,
            draw->cmp_first_dup, draw->cmp_first_multi,
            draw->cmp_missing_in_range);
    for (uint32_t k = 0; k < draw->cmp_missing_list_count; ++k)
        fprintf(stdout, "%s0x%08X", k ? "," : "",
                draw->cmp_missing_addrs[k]);
    fprintf(stdout, " missing_words=");
    for (uint32_t k = 0; k < draw->cmp_missing_list_count; ++k)
        fprintf(stdout, "%s%08X,%08X,%08X,%08X", k ? ";" : "",
                draw->cmp_missing_words[k][0], draw->cmp_missing_words[k][1],
                draw->cmp_missing_words[k][2], draw->cmp_missing_words[k][3]);
    fprintf(stdout, " missing_regs=");
    for (uint32_t k = 0; k < draw->cmp_missing_list_count; ++k) {
        fprintf(stdout, "%s", k ? ";" : "");
        for (unsigned r = 0; r < 32; ++r)
            fprintf(stdout, "%s%08X", r ? "," : "",
                    draw->cmp_missing_regs[k][r]);
    }
    fprintf(stdout, " missing_owners=");
    for (uint32_t k = 0; k < draw->cmp_missing_list_count; ++k)
        fprintf(stdout, "%s0x%08X", k ? "," : "",
                draw->cmp_missing_owner[k]);
    fputc('\n', stdout);
    fflush(stdout);
    if (draw->entry_index < g_entry_count) {
        const EntryCapture* entry = &g_entries[draw->entry_index];
        const uint32_t visible = entry->visible_count < CAPTURE_VISIBLE_MAX
                                     ? entry->visible_count
                                     : CAPTURE_VISIBLE_MAX;
        for (uint32_t i = 0; i < visible && i < 32u; ++i) {
            MohuWorldRequest node_request;
            memset(&node_request, 0, sizeof node_request);
            node_request.root = entry->visible_entry[i];
            node_request.vertex_table = draw->table;
            node_request.vertex_count = draw->count;
            node_request.masks[0] = psx_mod_read_word(CAPTURE_MASK0);
            node_request.masks[1] = psx_mod_read_word(CAPTURE_MASK1);
            node_request.bypass_masks = 1;
            node_request.generation = 1;
            MohuWorldMesh node_mesh;
            MohuWorldReport node_report;
            const MohuWorldStatus node_status =
                mohu_world_decode(&node_request, &node_mesh, &node_report);
            const uint32_t node_address = entry->visible_entry[i];
            uint32_t owner = 0;
            for (uint32_t p = draw->root;
                 draw->table > draw->root && p + 4u <= draw->table; p += 4u) {
                if (psx_mod_read_word(p) == node_address) {
                    owner = p;
                    break;
                }
            }
            if (!owner) {
                for (uint32_t p = 0x800A0000u; p + 4u <= 0x80100000u;
                     p += 4u) {
                    if (p >= draw->root && p < draw->table) continue;
                    if (psx_mod_read_word(p) == node_address) {
                        owner = p;
                        break;
                    }
                }
            }
            fprintf(stdout,
                    "mohu-vr-visible-node: draw=%u i=%u node=0x%08X "
                    "faces=%u list=0x%08X status=%s triangles=%u "
                    "first_source=0x%08X last_source=0x%08X owner=0x%08X\n",
                    (unsigned)(draw - g_draws), i, node_address,
                    entry->visible_faces[i], entry->visible_list[i],
                    mohu_world_status_name(node_status),
                    node_mesh.triangle_count,
                    node_mesh.triangle_count
                        ? node_mesh.triangles[0].source_address : 0u,
                    node_mesh.triangle_count
                        ? node_mesh.triangles[node_mesh.triangle_count - 1u]
                              .source_address : 0u,
                    owner);
            if (owner >= 0x80000020u) {
                uint8_t parent_bytes[0x30];
                copy_span(parent_bytes, owner - 0x20u, sizeof parent_bytes);
                fprintf(stdout, "  parent_base=0x%08X parent_bytes=",
                        owner - 0x20u);
                for (unsigned b = 0; b < sizeof parent_bytes; ++b)
                    fprintf(stdout, "%02X", parent_bytes[b]);
                for (unsigned k = 0; k < 3; ++k) {
                    const uint32_t base = owner - (k == 0 ? 0x18u
                                                  : k == 1 ? 0x1Cu : 0x20u);
                    fprintf(stdout,
                            " base=0x%08X:faces=%u:c18=0x%08X:c1c=0x%08X:"
                            "c20=0x%08X",
                            base, psx_mod_read_word(base + 0x0Cu),
                            psx_mod_read_word(base + 0x18u),
                            psx_mod_read_word(base + 0x1Cu),
                            psx_mod_read_word(base + 0x20u));
                }
                fputc('\n', stdout);
            }
            fflush(stdout);
            mohu_world_mesh_free(&node_mesh);
        }
    }
    mohu_world_mesh_free(&mesh);
    visible_compare(draw);
}

static void write_hex(FILE* file, const uint8_t* data, unsigned size) {
    static const char hex[] = "0123456789abcdef";
    for (unsigned i = 0; i < size; ++i) {
        fputc(hex[data[i] >> 4], file);
        fputc(hex[data[i] & 0xFu], file);
    }
}

/* Compare a non-draw entry's own face list with its own root. Selected draws
 * are compared by capture_compare instead. */
static void entry_compare(EntryCapture* entry) {
    if (entry->compare_valid || !entry->faces || entry->selected) return;
    entry->compare_valid = 1;
    entry->cmp_native = entry->faces;
    if (!entry->root || !entry->table || !entry->count) {
        entry->compare_status = MOHU_WORLD_REJECT_ARGUMENT;
        return;
    }
    MohuWorldRequest request;
    memset(&request, 0, sizeof request);
    request.root = entry->root;
    request.vertex_table = entry->table;
    request.vertex_count = entry->count;
    request.masks[0] = psx_mod_read_word(CAPTURE_MASK0);
    request.masks[1] = psx_mod_read_word(CAPTURE_MASK1);
    request.bypass_masks = 1;
    request.generation = 1;
    MohuWorldMesh mesh;
    MohuWorldReport report;
    const MohuWorldStatus status = mohu_world_decode(&request, &mesh, &report);
    entry->compare_status = status;
    if (status == MOHU_WORLD_OK) {
        const uint32_t stored = entry->faces < CAPTURE_ENTRY_FACES
                                    ? entry->faces : CAPTURE_ENTRY_FACES;
        entry->cmp_triangles = mesh.triangle_count;
        for (uint32_t i = 0; i < stored; ++i) {
            const uint32_t address = entry->addrs[i];
            int seen = 0;
            for (uint32_t j = 0; j < i; ++j) {
                if (entry->addrs[j] == address) {
                    seen = 1;
                    break;
                }
            }
            if (seen) continue;
            uint32_t decoded = 0;
            for (uint32_t t = 0; t < mesh.triangle_count; ++t) {
                if (mesh.triangles[t].face_tag == address) ++decoded;
            }
            if (decoded) {
                ++entry->cmp_matched;
            } else {
                ++entry->cmp_missing;
                if (!entry->cmp_first_missing)
                    entry->cmp_first_missing = address;
            }
        }
        for (uint32_t t = 0; t < mesh.triangle_count; ++t) {
            const uint32_t source = mesh.triangles[t].face_tag;
            int seen = 0;
            for (uint32_t k = 0; k < t; ++k) {
                if (mesh.triangles[k].face_tag == source) {
                    seen = 1;
                    break;
                }
            }
            if (seen) continue;
            int found = 0;
            for (uint32_t i = 0; i < stored; ++i) {
                if (entry->addrs[i] == source) {
                    found = 1;
                    break;
                }
            }
            if (!found) ++entry->cmp_decoded_only;
        }
    }
    fprintf(stdout,
            "mohu-vr-entry-faces: entry=%u ra=0x%08X root=0x%08X faces=%u "
            "overflow=%u matched=%u missing=%u decoded_only=%u triangles=%u "
            "status=%s first_missing=0x%08X\n",
            entry->index, entry->ra, entry->root, entry->faces,
            entry->overflow, entry->cmp_matched, entry->cmp_missing,
            entry->cmp_decoded_only, entry->cmp_triangles,
            mohu_world_status_name(status), entry->cmp_first_missing);
    fflush(stdout);
    mohu_world_mesh_free(&mesh);
}

static void flush_capture(void) {
    if (!g_enabled || g_written) return;
    FILE* file = fopen(g_path, "wb");
    if (!file) {
        fprintf(stdout, "mohu-vr-world-capture: cannot open %s\n", g_path);
        fflush(stdout);
        return;
    }
    for (unsigned i = 0; i < g_entry_count; ++i)
        entry_compare(&g_entries[i]);
    fprintf(file, "MOHU-SP-WORLD-CAPTURE 1\n");
    fprintf(file, "draws=%u faces=%u draw_limit=%u face_limit=%u\n",
            g_draw_count, g_face_count, g_draw_limit, g_face_limit);
    uint8_t caller_code[0x100];
    copy_span(caller_code, 0x8009A480u, sizeof caller_code);
    fprintf(file, "caller_base=0x8009A480 caller_code=");
    write_hex(file, caller_code, sizeof caller_code);
    fputc('\n', file);
    uint8_t builder_code[0x730];
    copy_span(builder_code, 0x80010CF0u, sizeof builder_code);
    fprintf(file, "builder_base=0x80010CF0 builder_code=");
    write_hex(file, builder_code, sizeof builder_code);
    fputc('\n', file);
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
        if (d->compare_valid) {
            fprintf(file,
                    "draw=%u native_compare=1 native=%u overflow=%u "
                    "unique=%u matched=%u missing=%u decoded_only=%u dup=%u "
                    "multi=%u multi_count=%u triangles=%u status=%u "
                    "first_missing=0x%08X first_dup=0x%08X "
                    "first_multi=0x%08X missing_in_range=%u missing_addrs=",
                    i, d->cmp_native, d->native_overflow, d->cmp_unique,
                    d->cmp_matched, d->cmp_missing, d->cmp_decoded_only,
                    d->cmp_dup, d->cmp_multi, d->cmp_multi_count,
                    d->cmp_triangles, d->compare_status, d->cmp_first_missing,
                    d->cmp_first_dup, d->cmp_first_multi,
                    d->cmp_missing_in_range);
            for (uint32_t k = 0; k < d->cmp_missing_list_count; ++k)
                fprintf(file, "%s0x%08X", k ? "," : "",
                        d->cmp_missing_addrs[k]);
            fprintf(file, " missing_words=");
            for (uint32_t k = 0; k < d->cmp_missing_list_count; ++k)
                fprintf(file, "%s%08X,%08X,%08X,%08X", k ? ";" : "",
                        d->cmp_missing_words[k][0],
                        d->cmp_missing_words[k][1],
                        d->cmp_missing_words[k][2],
                        d->cmp_missing_words[k][3]);
            fprintf(file, " missing_regs=");
            for (uint32_t k = 0; k < d->cmp_missing_list_count; ++k) {
                fprintf(file, "%s", k ? ";" : "");
                for (unsigned r = 0; r < 32; ++r)
                    fprintf(file, "%s%08X", r ? "," : "",
                            d->cmp_missing_regs[k][r]);
            }
            fprintf(file, " missing_owners=");
            for (uint32_t k = 0; k < d->cmp_missing_list_count; ++k)
                fprintf(file, "%s0x%08X", k ? "," : "",
                        d->cmp_missing_owner[k]);
            fputc('\n', file);
        }
        if (d->vis_valid)
            fprintf(file,
                    "visible_faces=1 draw=%u status=%u native=%u matched=%u "
                    "missing=%u decoded_only=%u triangles=%u "
                    "first_missing=0x%08X\n",
                    (unsigned)(d - g_draws), d->vis_status, d->vis_native,
                    d->vis_matched,
                    d->vis_missing, d->vis_decoded_only, d->vis_triangles,
                    d->vis_first_missing);
        if (d->gp0_valid) {
            for (uint32_t g = 0; g < d->gp0_count; ++g) {
                fprintf(file, "gp0=%u src=0x%08X op=0x%02X n=%u words=",
                        (unsigned)(d - g_draws), d->gp0[g].src,
                        d->gp0[g].opcode, d->gp0[g].n_words);
                for (unsigned w = 0; w < GPU_GP0_RING_MAX_WORDS; ++w)
                    fprintf(file, "%08X", d->gp0[g].words[w]);
                fputc('\n', file);
            }
            if (d->gp0_overflow)
                fprintf(file, "gp0_overflow=%u draw=%u\n", d->gp0_overflow,
                        (unsigned)(d - g_draws));
        }
    }
    for (unsigned i = 0; i < g_entry_count; ++i) {
        const EntryCapture* e = &g_entries[i];
        fprintf(file,
                "entry=%u ra=0x%08X pc=0x%08X level=0x%08X sub=0x%08X "
                "root=0x%08X table=0x%08X count=%u faces=%u selected=%u "
                "overflow=%u compare=%d status=%u matched=%u missing=%u "
                "decoded_only=%u triangles=%u first_missing=0x%08X "
                "visible=%u visible_overflow=%u visible_entries=",
                e->index, e->ra, e->pc, e->level, e->sub, e->root, e->table,
                e->count, e->faces, e->selected, e->overflow,
                e->compare_valid, e->compare_status, e->cmp_matched,
                e->cmp_missing, e->cmp_decoded_only, e->cmp_triangles,
                e->cmp_first_missing, e->visible_count,
                e->visible_overflow);
        const uint32_t stored_visible = e->visible_count < CAPTURE_VISIBLE_MAX
                                            ? e->visible_count
                                            : CAPTURE_VISIBLE_MAX;
        for (uint32_t v = 0; v < stored_visible; ++v)
            fprintf(file, "%s%08X:%u:%08X", v ? "," : "",
                    e->visible_entry[v], e->visible_faces[v],
                    e->visible_list[v]);
        fprintf(file, " gpr=");
        for (unsigned r = 0; r < 32; ++r)
            fprintf(file, "%08X", e->gpr[r]);
        fputc('\n', file);
    }
    for (unsigned i = 0; i < g_face_count; ++i) {
        const FaceCapture* f = &g_faces[i];
        fprintf(file,
                "face=%u draw=%u ra=0x%08X s7=0x%08X face=0x%08X "
                "index=%u table_base=0x%08X record_base=0x%08X ok=%u "
                "flags=0x%08X gpr27=0x%08X d8=0x%08X dc=0x%08X "
                "packet_ptr=0x%08X\n",
                i, f->draw, f->ra, f->s7, f->face, f->index, f->table_base,
                f->record_base, f->record_ok, f->flags, f->gpr27, f->table_d8,
                f->table_dc, f->packet_ptr);
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
        fprintf(file, "face=%u packet_captured=%d packet_hash=0x%08X packet=",
                i, f->packet_dumped, f->packet_hash);
        write_hex(file, f->packet,
                  f->packet_dumped ? CAPTURE_PACKET_SIZE : 0u);
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

static void capture_entry(CPUState* cpu) {
    /* The dispatcher re-enters the same segment body at 0x80011008 after each
     * 80011424 return. Those are continuations, not new invocations. */
    if (cpu->pc && cpu->pc != 0x80010CF0u) return;
    if (g_entry_count >= CAPTURE_MAX_ENTRIES) {
        ++g_entry_overflow;
        return;
    }
    EntryCapture* entry = &g_entries[g_entry_count];
    memset(entry, 0, sizeof *entry);
    entry->index = g_entry_count++;
    entry->ra = cpu->gpr[31];
    entry->pc = cpu->pc;
    memcpy(entry->gpr, cpu->gpr, sizeof entry->gpr);
    entry->level = cpu->gpr[18];
    if (mohu_vr_ray_span(entry->level, 0x40u)) {
        entry->sub = psx_mod_read_word(entry->level + 8u);
        entry->count = psx_mod_read_word(entry->level + 0x3Cu);
        entry->table = psx_mod_read_word(entry->level + 0x2Cu);
        if (mohu_vr_ray_span(entry->sub, 0x18u))
            entry->root = psx_mod_read_word(entry->sub + 0x14u);
    }
    entry->visible_count = psx_mod_read_word(CAPTURE_VISIBLE_COUNT);
    uint32_t visible = entry->visible_count;
    if (visible > CAPTURE_VISIBLE_MAX) {
        entry->visible_overflow = visible - CAPTURE_VISIBLE_MAX;
        visible = CAPTURE_VISIBLE_MAX;
    }
    for (uint32_t i = 0; i < visible; ++i) {
        const uint32_t pointer =
            psx_mod_read_word(CAPTURE_VISIBLE_LIST + i * 4u);
        entry->visible_entry[i] = pointer;
        if (!span(pointer, 0x1Cu)) continue;
        entry->visible_faces[i] = psx_mod_read_word(pointer + 0x0Cu);
        entry->visible_list[i] = psx_mod_read_word(pointer + 0x18u);
    }
}

static void capture_packet(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!g_enabled || !cpu) return;
    capture_entry(cpu);
    if (cpu->gpr[31] != 0x8009A51Cu) return;

    capture_previous_range();
    capture_previous_scratch();
    if (g_draw_count) capture_compare(&g_draws[g_draw_count - 1u]);
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
    if (g_entry_count) {
        g_entries[g_entry_count - 1u].selected = 1;
        draw->entry_index = g_entry_count - 1u;
    }
    capture_census(draw);
    g_has_previous = 1;
    ++g_draw_count;
}

static void capture_face(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!g_enabled || !cpu) return;
    if (cpu->gpr[31] != 0x80011008u || cpu->gpr[19] != 0x1F800000u) return;
    if (g_entry_count) {
        EntryCapture* entry = &g_entries[g_entry_count - 1u];
        const uint32_t face_address = cpu->gpr[23] - 8u;
        if (entry->faces < CAPTURE_ENTRY_FACES)
            entry->addrs[entry->faces] = face_address;
        else
            ++entry->overflow;
        ++entry->faces;
        if (entry->selected && g_draw_count) {
            DrawCapture* draw = &g_draws[g_draw_count - 1u];
            const uint32_t slot = draw->native_count;
            if (slot < CAPTURE_NATIVE_FACES) {
                draw->native_faces[slot] = face_address;
                if (slot < CAPTURE_NATIVE_REGS)
                    memcpy(draw->native_regs[slot], cpu->gpr,
                           sizeof draw->native_regs[slot]);
                ++draw->native_count;
            } else {
                ++draw->native_overflow;
            }
        }
    }
    capture_previous_face_packet();
    if (g_face_count >= g_face_limit) return;

    FaceCapture* face = &g_faces[g_face_count];
    memset(face, 0, sizeof *face);
    /* Faces can run before the first captured packet entry; label those
     * 0xFFFFFFFF instead of pretending they belong to draw 0. */
    face->draw = g_draw_count ? g_draw_count - 1u : 0xFFFFFFFFu;
    face->ra = cpu->gpr[31];
    face->s7 = cpu->gpr[23];
    face->face = face->s7 - 8u;
    face->flags = cpu->gpr[22];
    face->gpr27 = cpu->gpr[27];
    face->packet_ptr = cpu->gpr[4];
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
    g_census_done = 0;

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

void mohu_world_capture_face_done(void) {
    if (!g_enabled) return;
    capture_previous_face_packet();
}

void mohu_world_capture_register(void) {
    (void)psx_mod_register_command("mohu.vr.world-capture", capture_command);
}
