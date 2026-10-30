#include "world_decode.h"

#include "mod_plugins.h"

#include <limits.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

static const char *const s_status_names[] = {
    "ok", "argument", "vertex_table", "tree_root", "node_bounds",
    "leaf_count", "leaf_budget", "strip_span", "strip_terminator",
    "strip_budget", "vertex_index", "tree_budget", "triangle_budget",
    "allocation", "entry", "material"
};

const char *mohu_world_status_name(MohuWorldStatus status) {
    const size_t count = sizeof s_status_names / sizeof s_status_names[0];
    return (unsigned)status < count ? s_status_names[status] : "unknown";
}

static int span_ok(uint32_t address, uint32_t size) {
    return !(address & 3u) && address >= 0x80000000u && address < 0x80200000u &&
           size <= 0x80200000u - address;
}

static void record_read(MohuWorldMesh *mesh, uint32_t address, uint32_t size) {
    if (address < mesh->source_start) mesh->source_start = address;
    if (address + size > mesh->source_end) mesh->source_end = address + size;
}

static MohuWorldStatus reject(MohuWorldReport *report, MohuWorldStatus status,
                              uint32_t node, uint32_t leaf, uint32_t detail) {
    if (report) {
        report->status = status;
        report->node = node;
        report->leaf = leaf;
        report->detail = detail;
    }
    return status;
}

static int reserve_triangles(MohuWorldMesh *mesh, uint32_t needed,
                             uint32_t limit, MohuWorldStatus *status) {
    if (needed > limit) {
        *status = MOHU_WORLD_REJECT_TRIANGLE_BUDGET;
        return 0;
    }
    if (needed <= mesh->triangle_capacity) return 1;
    uint32_t capacity = mesh->triangle_capacity;
    if (!capacity) capacity = 64;
    while (capacity < needed) {
        if (capacity > limit / 2u) { capacity = limit; break; }
        capacity *= 2u;
    }
    if (capacity < needed) {
        *status = MOHU_WORLD_REJECT_TRIANGLE_BUDGET;
        return 0;
    }
    MohuWorldTriangle *grown = realloc(mesh->triangles,
                                       (size_t)capacity * sizeof *grown);
    if (!grown) {
        *status = MOHU_WORLD_REJECT_ALLOCATION;
        return 0;
    }
    mesh->triangles = grown;
    mesh->triangle_capacity = capacity;
    return 1;
}

static void include_bounds(MohuWorldMesh *mesh, const MohuWorldVertex *v) {
    const int32_t xyz[3] = {v->x, v->y, v->z};
    for (unsigned i = 0; i < 3; ++i) {
        if (xyz[i] < mesh->bounds_min[i]) mesh->bounds_min[i] = xyz[i];
        if (xyz[i] > mesh->bounds_max[i]) mesh->bounds_max[i] = xyz[i];
    }
}

/* Native record table: 12 bytes per face, indexed by `record_index`.
 *   word0 = UV0 | CLUT<<16
 *   word1 = UV1 | texpage<<16
 *   word2 = UV2
 * These are the exact words the packet builder writes into its 0x34 packet
 * (80011238..80011338). A caller that requires materials gets a named rejection
 * for a missing or out-of-range record rather than an unmaterialed face. */
typedef struct {
    uint32_t table;
    uint32_t count;
    int required;
} MaterialSource;

static MohuWorldStatus read_material(const MaterialSource *source,
                                     uint32_t index,
                                     MohuWorldMaterial *material,
                                     MohuWorldMesh *mesh,
                                     MohuWorldReport *report) {
    memset(material, 0, sizeof *material);
    if (!source->table || !source->count) {
        if (source->required)
            return reject(report, MOHU_WORLD_REJECT_MATERIAL, 0u, report->leaf,
                          index);
        return MOHU_WORLD_OK;
    }
    if (index >= source->count)
        return reject(report, MOHU_WORLD_REJECT_MATERIAL, source->table,
                      report->leaf, index);
    const uint32_t address = source->table + index * 12u;
    if (!span_ok(address, 12u))
        return reject(report, MOHU_WORLD_REJECT_MATERIAL, address, report->leaf,
                      index);
    record_read(mesh, address, 12u);
    const uint32_t word0 = psx_mod_read_word(address);
    const uint32_t word1 = psx_mod_read_word(address + 4u);
    const uint32_t word2 = psx_mod_read_word(address + 8u);
    material->clut = (uint16_t)(word0 >> 16);
    material->texpage = (uint16_t)(word1 >> 16);
    material->uv[0] = (uint16_t)word0;
    material->uv[1] = (uint16_t)word1;
    material->uv[2] = (uint16_t)word2;
    material->valid = 1;
    return MOHU_WORLD_OK;
}

static MohuWorldStatus append_triangle(MohuWorldMesh *mesh, uint32_t limit,
                                       const uint32_t idx[3],
                                       uint32_t source_address,
                                       uint32_t face_tag,
                                       const uint32_t base_word[2],
                                       uint32_t extension_word,
                                       uint16_t render_flags,
                                       int winding_swapped, int is_extension,
                                       const MaterialSource *materials,
                                       MohuWorldReport *report) {
    MohuWorldMaterial material;
    const uint32_t record_index = base_word[1] >> 16;
    const MohuWorldStatus material_status =
        read_material(materials, record_index, &material, mesh, report);
    if (material_status != MOHU_WORLD_OK) return material_status;
    if (!reserve_triangles(mesh, mesh->triangle_count + 1u, limit,
                           &report->status))
        return reject(report, report->status, source_address, report->leaf,
                      mesh->triangle_count + 1u);
    MohuWorldTriangle *t = &mesh->triangles[mesh->triangle_count++];
    memset(t, 0, sizeof *t);
    for (unsigned i = 0; i < 3; ++i) {
        t->vertex[i] = idx[i];
        include_bounds(mesh, &mesh->vertices[idx[i]]);
    }
    t->source_address = source_address;
    t->face_tag = face_tag;
    t->base_word[0] = base_word[0];
    t->base_word[1] = base_word[1];
    t->record_index = (uint16_t)record_index;
    t->extension_word = extension_word;
    t->render_flags = render_flags;
    t->winding_swapped = (uint8_t)(winding_swapped ? 1 : 0);
    t->is_extension = (uint8_t)(is_extension ? 1 : 0);
    t->material = material;
    mesh->material_tokens++;
    if (material.valid) mesh->materials_decoded++;
    report->triangles_decoded = mesh->triangle_count;
    return MOHU_WORLD_OK;
}

static MohuWorldStatus decode_strip(uint32_t list, uint32_t faces,
                                    MohuWorldMesh *mesh, uint32_t limit,
                                    uint32_t leaf,
                                    const MaterialSource *materials,
                                    MohuWorldReport *report) {
    uint32_t cursor = list, idx[3] = {0}, emitted = 0, bytes = 0;
    uint32_t base_word[2] = {0, 0};
    int base = 1;

    while (emitted < faces) {
        uint32_t source = cursor, extension_word = 0;
        uint16_t render_flags = 0;
        int winding_swapped = 0, is_extension = 0;

        if (base) {
            if (!span_ok(cursor, 8u))
                return reject(report, MOHU_WORLD_REJECT_STRIP_SPAN, cursor,
                              leaf, 8u);
            record_read(mesh, cursor, 8u);
            const uint32_t a = psx_mod_read_word(cursor);
            const uint32_t b = psx_mod_read_word(cursor + 4u);
            base_word[0] = a;
            base_word[1] = b;
            idx[0] = a & 0x1fffu;
            idx[1] = (a >> 16) & 0x1fffu;
            idx[2] = b & 0x1fffu;
            cursor += 8u;
            bytes += 8u;
            base = 0;
        } else {
            if (!span_ok(cursor, 4u))
                return reject(report, MOHU_WORLD_REJECT_STRIP_SPAN, cursor,
                              leaf, 4u);
            record_read(mesh, cursor, 4u);
            const uint32_t code = psx_mod_read_word(cursor) & 0xffffu;
            cursor += 4u;
            bytes += 4u;
            if (code == 0x1fffu) {
                base = 1;
                continue;
            }
            const uint32_t old1 = idx[1], old2 = idx[2];
            const int swap = (code & 0x8000u) != 0;
            idx[0] = swap ? old2 : old1;
            idx[1] = swap ? old1 : old2;
            idx[2] = code & 0x1fffu;
            extension_word = code;
            render_flags = (uint16_t)((code >> 13) & 3u);
            winding_swapped = swap;
            is_extension = 1;
        }

        if (bytes > faces * 20u)
            return reject(report, MOHU_WORLD_REJECT_STRIP_BUDGET, list, leaf,
                          bytes);
        for (unsigned i = 0; i < 3; ++i) {
            if (idx[i] >= mesh->vertex_count)
                return reject(report, MOHU_WORLD_REJECT_VERTEX_INDEX, source,
                              leaf, idx[i]);
        }
        const uint32_t tag = is_extension ? source - 4u : source;
        const MohuWorldStatus status =
            append_triangle(mesh, limit, idx, source, tag, base_word,
                            extension_word, render_flags, winding_swapped,
                            is_extension, materials, report);
        if (status != MOHU_WORLD_OK) {
            report->node = source;
            report->leaf = leaf;
            return status;
        }
        ++emitted;
    }

    if (!span_ok(cursor, 4u) || psx_mod_read_half(cursor) != 0x1fffu)
        return reject(report, MOHU_WORLD_REJECT_STRIP_TERMINATOR, cursor,
                      leaf, 0u);
    return MOHU_WORLD_OK;
}

static MohuWorldStatus load_vertices(uint32_t table, uint32_t count,
                                     uint32_t generation, MohuWorldMesh *mesh,
                                     MohuWorldReport *report) {
    if (!count || count > MOHU_WORLD_MAX_VERTICES ||
        !span_ok(table, count * 8u))
        return reject(report, MOHU_WORLD_REJECT_VERTEX_TABLE, table, 0u, count);

    mesh->vertices = calloc(count, sizeof *mesh->vertices);
    if (!mesh->vertices)
        return reject(report, MOHU_WORLD_REJECT_ALLOCATION, 0u, 0u, count);
    mesh->vertex_count = count;
    mesh->generation = generation;
    mesh->source_start = 0xFFFFFFFFu;
    mesh->source_end = 0u;
    for (unsigned i = 0; i < 3; ++i) {
        mesh->bounds_min[i] = INT32_MAX;
        mesh->bounds_max[i] = INT32_MIN;
        mesh->leaf_bounds_min[i] = INT16_MAX;
        mesh->leaf_bounds_max[i] = INT16_MIN;
    }
    record_read(mesh, table, count * 8u);
    for (uint32_t i = 0; i < count; ++i) {
        const uint32_t address = table + i * 8u;
        mesh->vertices[i].x = (int16_t)psx_mod_read_half(address);
        mesh->vertices[i].y = (int16_t)psx_mod_read_half(address + 2u);
        mesh->vertices[i].z = (int16_t)psx_mod_read_half(address + 4u);
        mesh->vertices[i].pad = 0;
    }
    return MOHU_WORLD_OK;
}

static void finish_mesh(MohuWorldMesh *mesh, MohuWorldReport *report) {
    if (!mesh->triangle_count) {
        for (unsigned i = 0; i < 3; ++i) {
            mesh->bounds_min[i] = 0;
            mesh->bounds_max[i] = 0;
        }
    }
    if (!mesh->leaf_count) {
        for (unsigned i = 0; i < 3; ++i) {
            mesh->leaf_bounds_min[i] = 0;
            mesh->leaf_bounds_max[i] = 0;
        }
    }
    mesh->source_fingerprint = mohu_world_source_fingerprint(mesh);
    report->status = MOHU_WORLD_OK;
}

static MohuWorldStatus decode_tree(const MohuWorldRequest *request,
                                   MohuWorldMesh *mesh, uint32_t limit,
                                   const MaterialSource *materials,
                                   MohuWorldReport *report) {
    uint32_t stack[MOHU_WORLD_STACK_DEPTH];
    unsigned top = 1;
    stack[0] = request->root;

    while (top) {
        const uint32_t node = stack[--top];
        if (!span_ok(node, 36u) || (node & 3u))
            return reject(report, MOHU_WORLD_REJECT_TREE_ROOT, node, 0u, 0u);
        if (++report->nodes_visited > MOHU_WORLD_MAX_NODES)
            return reject(report, MOHU_WORLD_REJECT_TREE_BUDGET, node, 0u,
                          report->nodes_visited);
        record_read(mesh, node, 36u);

        if (!request->bypass_masks &&
            (!(psx_mod_read_word(node + 16u) & request->masks[0]) ||
             !(psx_mod_read_word(node + 20u) & request->masks[1])))
            continue;

        int16_t bounds[6];
        for (unsigned i = 0; i < 6; ++i)
            bounds[i] = (int16_t)psx_mod_read_half(node + i * 2u);
        for (unsigned i = 0; i < 3; ++i) {
            if (bounds[i] > bounds[i + 3])
                return reject(report, MOHU_WORLD_REJECT_NODE_BOUNDS, node, 0u,
                              (uint32_t)i);
        }

        const int32_t faces = (int32_t)psx_mod_read_word(node + 12u);
        if (faces < 0 || faces > (int32_t)MOHU_WORLD_MAX_LEAF_FACES)
            return reject(report, MOHU_WORLD_REJECT_LEAF_COUNT, node, 0u,
                          (uint32_t)faces);

        if (!faces) {
            static const unsigned offsets[3] = {28u, 32u, 24u};
            for (unsigned i = 0; i < 3; ++i) {
                const uint32_t child =
                    psx_mod_read_word(node + offsets[i]);
                if (!child) continue;
                if (top == MOHU_WORLD_STACK_DEPTH)
                    return reject(report, MOHU_WORLD_REJECT_TREE_BUDGET, node,
                                  0u, top);
                stack[top++] = child;
            }
            continue;
        }

        if (++report->leaves_visited > request->max_leaves)
            return reject(report, MOHU_WORLD_REJECT_LEAF_BUDGET, node, 0u,
                          report->leaves_visited);
        for (unsigned i = 0; i < 3; ++i) {
            if (bounds[i] < mesh->leaf_bounds_min[i])
                mesh->leaf_bounds_min[i] = bounds[i];
            if (bounds[i + 3] > mesh->leaf_bounds_max[i])
                mesh->leaf_bounds_max[i] = bounds[i + 3];
        }
        report->leaf = node;
        const uint32_t list = psx_mod_read_word(node + 24u);
        const MohuWorldStatus status =
            decode_strip(list, (uint32_t)faces, mesh, limit, node, materials,
                         report);
        report->leaf = 0;
        if (status != MOHU_WORLD_OK) return status;
    }
    return MOHU_WORLD_OK;
}

MohuWorldStatus mohu_world_decode(const MohuWorldRequest *request,
                                  MohuWorldMesh *mesh,
                                  MohuWorldReport *report) {
    if (report) memset(report, 0, sizeof *report);
    if (mesh) memset(mesh, 0, sizeof *mesh);
    if (!request || !mesh || !report)
        return reject(report, MOHU_WORLD_REJECT_ARGUMENT, 0u, 0u, 0u);
    uint32_t limit = request->max_triangles ? request->max_triangles
                                            : MOHU_WORLD_MAX_TRIANGLES;
    if (limit > MOHU_WORLD_MAX_TRIANGLES) limit = MOHU_WORLD_MAX_TRIANGLES;
    uint32_t max_leaves = request->max_leaves ? request->max_leaves
                                              : MOHU_WORLD_MAX_LEAVES;
    if (max_leaves > MOHU_WORLD_MAX_LEAVES) max_leaves = MOHU_WORLD_MAX_LEAVES;
    if (request->record_count > MOHU_WORLD_MAX_RECORDS)
        return reject(report, MOHU_WORLD_REJECT_MATERIAL, request->record_table,
                      0u, request->record_count);
    if (request->require_materials &&
        (!request->record_table || !request->record_count))
        return reject(report, MOHU_WORLD_REJECT_MATERIAL, 0u, 0u, 0u);

    const MohuWorldStatus prepared =
        load_vertices(request->vertex_table, request->vertex_count,
                      request->generation, mesh, report);
    if (prepared != MOHU_WORLD_OK) return prepared;
    mesh->far_plane = request->far_plane;

    const MaterialSource materials = {
        request->record_table, request->record_count, request->require_materials
    };
    MohuWorldRequest bounded = *request;
    bounded.max_leaves = max_leaves;
    const MohuWorldStatus status =
        decode_tree(&bounded, mesh, limit, &materials, report);
    if (status != MOHU_WORLD_OK) {
        mohu_world_mesh_free(mesh);
        report->status = status;
        return status;
    }

    mesh->leaf_count = report->leaves_visited;
    finish_mesh(mesh, report);
    return MOHU_WORLD_OK;
}

MohuWorldStatus mohu_world_decode_visible(
    const MohuWorldVisibleRequest *request, MohuWorldMesh *mesh,
    MohuWorldReport *report) {
    if (report) memset(report, 0, sizeof *report);
    if (mesh) memset(mesh, 0, sizeof *mesh);
    if (!request || !mesh || !report || (request->entry_count &&
                                         !request->entries))
        return reject(report, MOHU_WORLD_REJECT_ARGUMENT, 0u, 0u, 0u);
    if (request->entry_count > MOHU_WORLD_MAX_ENTRIES)
        return reject(report, MOHU_WORLD_REJECT_LEAF_BUDGET, 0u, 0u,
                      request->entry_count);

    uint32_t limit = request->max_triangles ? request->max_triangles
                                            : MOHU_WORLD_MAX_TRIANGLES;
    if (limit > MOHU_WORLD_MAX_TRIANGLES) limit = MOHU_WORLD_MAX_TRIANGLES;
    if (request->record_count > MOHU_WORLD_MAX_RECORDS)
        return reject(report, MOHU_WORLD_REJECT_MATERIAL, request->record_table,
                      0u, request->record_count);
    if (request->require_materials &&
        (!request->record_table || !request->record_count))
        return reject(report, MOHU_WORLD_REJECT_MATERIAL, 0u, 0u, 0u);

    const MohuWorldStatus prepared =
        load_vertices(request->vertex_table, request->vertex_count,
                      request->generation, mesh, report);
    if (prepared != MOHU_WORLD_OK) return prepared;
    mesh->far_plane = request->far_plane;
    const MaterialSource materials = {
        request->record_table, request->record_count, request->require_materials
    };

    for (uint32_t i = 0; i < request->entry_count; ++i) {
        const uint32_t entry = request->entries[i];
        if (!span_ok(entry, 36u) || (entry & 3u)) {
            mohu_world_mesh_free(mesh);
            return reject(report, MOHU_WORLD_REJECT_ENTRY, entry, 0u, i);
        }
        record_read(mesh, entry, 36u);

        int16_t bounds[6];
        for (unsigned b = 0; b < 6; ++b)
            bounds[b] = (int16_t)psx_mod_read_half(entry + b * 2u);
        for (unsigned b = 0; b < 3; ++b) {
            if (bounds[b] > bounds[b + 3]) {
                mohu_world_mesh_free(mesh);
                return reject(report, MOHU_WORLD_REJECT_NODE_BOUNDS, entry,
                              0u, b);
            }
        }

        const uint32_t faces = psx_mod_read_word(entry + 12u);
        if (faces > MOHU_WORLD_MAX_LEAF_FACES) {
            mohu_world_mesh_free(mesh);
            return reject(report, MOHU_WORLD_REJECT_LEAF_COUNT, entry, 0u,
                          faces);
        }
        if (!faces) continue;

        if (++report->leaves_visited > MOHU_WORLD_MAX_LEAVES) {
            mohu_world_mesh_free(mesh);
            return reject(report, MOHU_WORLD_REJECT_LEAF_BUDGET, entry, 0u,
                          report->leaves_visited);
        }
        for (unsigned b = 0; b < 3; ++b) {
            if (bounds[b] < mesh->leaf_bounds_min[b])
                mesh->leaf_bounds_min[b] = bounds[b];
            if (bounds[b + 3] > mesh->leaf_bounds_max[b])
                mesh->leaf_bounds_max[b] = bounds[b + 3];
        }
        report->leaf = entry;
        const uint32_t list = psx_mod_read_word(entry + 24u);
        const MohuWorldStatus status =
            decode_strip(list, faces, mesh, limit, entry, &materials, report);
        report->leaf = 0;
        if (status != MOHU_WORLD_OK) {
            mohu_world_mesh_free(mesh);
            report->status = status;
            return status;
        }
    }

    mesh->leaf_count = report->leaves_visited;
    finish_mesh(mesh, report);
    return MOHU_WORLD_OK;
}

void mohu_world_mesh_free(MohuWorldMesh *mesh) {
    if (!mesh) return;
    free(mesh->vertices);
    free(mesh->triangles);
    memset(mesh, 0, sizeof *mesh);
}

uint32_t mohu_world_source_fingerprint(const MohuWorldMesh *mesh) {
    if (!mesh || mesh->source_end <= mesh->source_start) return 0;
    const uint32_t start = mesh->source_start & ~3u;
    const uint32_t end = (mesh->source_end + 3u) & ~3u;
    uint32_t hash = 2166136261u;
    for (uint32_t address = start; address < end; address += 4u) {
        const uint32_t word = psx_mod_read_word(address);
        for (unsigned shift = 0; shift < 32; shift += 8) {
            hash ^= (word >> shift) & 0xFFu;
            hash *= 16777619u;
        }
    }
    return hash;
}

int mohu_world_source_unchanged(const MohuWorldMesh *mesh) {
    return mesh && mesh->source_end > mesh->source_start &&
           mesh->source_fingerprint == mohu_world_source_fingerprint(mesh);
}

static int same_request(const MohuWorldRequest *a, const MohuWorldRequest *b) {
    return a->root == b->root && a->vertex_table == b->vertex_table &&
           a->vertex_count == b->vertex_count &&
           a->generation == b->generation &&
           a->masks[0] == b->masks[0] && a->masks[1] == b->masks[1] &&
           a->bypass_masks == b->bypass_masks &&
           a->max_triangles == b->max_triangles &&
           a->max_leaves == b->max_leaves &&
           a->record_table == b->record_table &&
           a->record_count == b->record_count &&
           a->require_materials == b->require_materials &&
           a->far_plane == b->far_plane;
}

MohuWorldStatus mohu_world_cache_acquire(MohuWorldCache *cache,
                                         const MohuWorldRequest *request,
                                         uint32_t snapshot_serial,
                                         const MohuWorldMesh **mesh,
                                         int *reused) {
    if (reused) *reused = 0;
    if (mesh) *mesh = NULL;
    if (!cache || !request || !mesh || !reused)
        return MOHU_WORLD_REJECT_ARGUMENT;

    MohuWorldCacheEntry *slot = NULL;
    for (unsigned i = 0; i < MOHU_WORLD_CACHE_SLOTS; ++i) {
        MohuWorldCacheEntry *entry = &cache->entries[i];
        if (!entry->valid || !same_request(&entry->request, request)) continue;
        if (entry->snapshot_serial == snapshot_serial) {
            cache->hits++;
            *mesh = &entry->mesh;
            *reused = 1;
            return MOHU_WORLD_OK;
        }
        if (mohu_world_source_unchanged(&entry->mesh)) {
            entry->snapshot_serial = snapshot_serial;
            cache->validations++;
            cache->hits++;
            *mesh = &entry->mesh;
            *reused = 1;
            return MOHU_WORLD_OK;
        }
        cache->stale++;
        mohu_world_mesh_free(&entry->mesh);
        entry->valid = 0;
        break;
    }

    for (unsigned i = 0; i < MOHU_WORLD_CACHE_SLOTS; ++i) {
        if (!cache->entries[i].valid) {
            slot = &cache->entries[i];
            break;
        }
    }
    if (!slot) {
        slot = &cache->entries[cache->next_slot % MOHU_WORLD_CACHE_SLOTS];
        cache->next_slot = (cache->next_slot + 1u) % MOHU_WORLD_CACHE_SLOTS;
        mohu_world_mesh_free(&slot->mesh);
        slot->valid = 0;
    }

    MohuWorldReport report;
    const MohuWorldStatus status =
        mohu_world_decode(request, &slot->mesh, &report);
    if (status != MOHU_WORLD_OK) {
        cache->misses++;
        slot->valid = 0;
        return status;
    }
    slot->request = *request;
    slot->snapshot_serial = snapshot_serial;
    slot->valid = 1;
    cache->misses++;
    *mesh = &slot->mesh;
    return MOHU_WORLD_OK;
}

void mohu_world_cache_free(MohuWorldCache *cache) {
    if (!cache) return;
    for (unsigned i = 0; i < MOHU_WORLD_CACHE_SLOTS; ++i)
        mohu_world_mesh_free(&cache->entries[i].mesh);
    memset(cache, 0, sizeof *cache);
}
