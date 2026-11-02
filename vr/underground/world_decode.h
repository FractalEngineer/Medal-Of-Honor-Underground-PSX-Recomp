#ifndef MOHU_WORLD_DECODE_H
#define MOHU_WORLD_DECODE_H

#include <stdint.h>

/*
 * Title-owned static-world geometry decoder for M1.
 *
 * It decodes the measured SP arena layout only: the visibility tree
 * (int16 AABB at +0..+10, leaf count at +12, masks at +16/+20, children at
 * +24/+32/+28) and each leaf's strip list (8-byte base triangles, 4-byte
 * extensions, 0x1fff terminator). Vertex table and count are the level's
 * +0x2c and +0x3c fields. This is the same layout the raycast reader uses;
 * decoding never projects, culls or writes GPU state.
 *
 * MATERIALS. The upper half of the second base word is `record_index`, an
 * index into the native 12-byte per-face parameter table at
 * `word[0x1F8003E8]`. Its words are UV0|CLUT, UV1|texpage and UV2, exactly the
 * fields the packet builder writes into the 0x34 command. When the caller
 * supplies `record_table`/`record_count`, each triangle gets those material
 * fields and `materials_decoded` is incremented. Without a table the geometry
 * still decodes but `materials_decoded` stays 0 and textured output must
 * refuse the mesh. `require_materials` turns a missing/out-of-range record
 * into a named rejection instead of a silent unmaterialed face.
 * Unsupported or malformed input rejects the whole decode with a named status;
 * faces are never silently dropped.
 */

#define MOHU_WORLD_MAX_VERTICES   8192u
#define MOHU_WORLD_MAX_NODES      8192u
#define MOHU_WORLD_MAX_LEAVES     16384u
#define MOHU_WORLD_MAX_TRIANGLES  65536u
#define MOHU_WORLD_MAX_LEAF_FACES 4096u
#define MOHU_WORLD_MAX_ENTRIES    16384u
#define MOHU_WORLD_MAX_RECORDS    65536u
#define MOHU_WORLD_STACK_DEPTH    256u
#define MOHU_WORLD_CACHE_SLOTS    4u

typedef enum {
    MOHU_WORLD_OK = 0,
    MOHU_WORLD_REJECT_ARGUMENT,
    MOHU_WORLD_REJECT_VERTEX_TABLE,
    MOHU_WORLD_REJECT_TREE_ROOT,
    MOHU_WORLD_REJECT_NODE_BOUNDS,
    MOHU_WORLD_REJECT_LEAF_COUNT,
    MOHU_WORLD_REJECT_LEAF_BUDGET,
    MOHU_WORLD_REJECT_STRIP_SPAN,
    MOHU_WORLD_REJECT_STRIP_TERMINATOR,
    MOHU_WORLD_REJECT_STRIP_BUDGET,
    MOHU_WORLD_REJECT_VERTEX_INDEX,
    MOHU_WORLD_REJECT_TREE_BUDGET,
    MOHU_WORLD_REJECT_TRIANGLE_BUDGET,
    MOHU_WORLD_REJECT_ALLOCATION,
    MOHU_WORLD_REJECT_ENTRY,
    MOHU_WORLD_REJECT_MATERIAL
} MohuWorldStatus;

/* One source vertex: three signed 16-bit camera-relative coordinates and two
 * unused bytes, matching the native 8-byte stride. */
typedef struct {
    int16_t x, y, z, pad;
} MohuWorldVertex;

/* Per-face material fields from the native 12-byte record. The low half of
 * record word 0 is UV0 and its high half is the CLUT; word 1 is UV1|texpage;
 * word 2 is UV2. The UV association is the native packet order, not an
 * independently verified vertex mapping. */
typedef struct {
    uint16_t clut;
    uint16_t texpage;
    uint16_t uv[3];
    uint8_t valid;
} MohuWorldMaterial;

typedef struct {
    uint32_t vertex[3];       /* indices into MohuWorldMesh.vertices */
    uint32_t source_address;  /* guest word that introduced this triangle */
    uint32_t face_tag;        /* native face address: base start, or the word
                               * before an extension code (extension - 4) */
    uint32_t base_word[2];    /* raw base words; upper half of [1] is below */
    uint16_t record_index;    /* upper half of base_word[1]: record table index */
    uint32_t extension_word;  /* 0 for a base triangle */
    uint16_t render_flags;    /* extension bits 13..14; 0 when not decoded */
    uint8_t winding_swapped;  /* extension bit 15 */
    uint8_t is_extension;
    MohuWorldMaterial material;
} MohuWorldTriangle;

typedef struct {
    uint32_t root;
    uint32_t vertex_table;
    uint32_t vertex_count;
    uint32_t masks[2];
    int bypass_masks;
    uint32_t max_triangles;   /* 0 = MOHU_WORLD_MAX_TRIANGLES */
    uint32_t max_leaves;      /* 0 = MOHU_WORLD_MAX_LEAVES */
    uint32_t generation;      /* resource version, echoed into the mesh */
    uint32_t record_table;    /* native 12-byte record table; 0 = no materials */
    uint32_t record_count;    /* bounded entries; 0 = no materials */
    int require_materials;    /* reject a face without a valid record */
    int32_t far_plane;        /* caller policy, echoed; decode never applies it */
} MohuWorldRequest;

/* The native builder submits a view-specific set of leaf entries, not a root
 * walk: entry pointers from 0x800B74B8, each with a face count at +12 and a
 * strip-list pointer at +24. This request decodes exactly that set. It is not
 * a replacement for the full-tree census. */
typedef struct {
    const uint32_t *entries;
    uint32_t entry_count;
    uint32_t vertex_table;
    uint32_t vertex_count;
    uint32_t max_triangles;   /* 0 = MOHU_WORLD_MAX_TRIANGLES */
    uint32_t generation;
    uint32_t record_table;    /* native 12-byte record table; 0 = no materials */
    uint32_t record_count;    /* bounded entries; 0 = no materials */
    int require_materials;    /* reject a face without a valid record */
    int32_t far_plane;        /* caller policy, echoed; decode never applies it */
} MohuWorldVisibleRequest;

typedef struct {
    uint32_t generation;
    uint32_t vertex_count;
    uint32_t leaf_count;
    uint32_t triangle_count;
    uint32_t triangle_capacity;
    MohuWorldVertex *vertices;      /* owned copy of the source table */
    MohuWorldTriangle *triangles;   /* owned, deterministic traversal order */
    int32_t bounds_min[3];          /* referenced-vertex bounds */
    int32_t bounds_max[3];
    int16_t leaf_bounds_min[3];     /* union of accepted leaf boxes */
    int16_t leaf_bounds_max[3];
    uint32_t material_tokens;       /* faces whose raw words were retained */
    uint32_t materials_decoded;     /* triangles with a valid record material */
    int32_t far_plane;              /* echoed caller policy, not applied here */
    uint32_t source_start;          /* first source byte consulted */
    uint32_t source_end;            /* one past the last source byte consulted */
    uint32_t source_fingerprint;    /* FNV-1a over [source_start, source_end) */
} MohuWorldMesh;

typedef struct {
    MohuWorldStatus status;
    uint32_t node;              /* guest address of the rejecting node/word */
    uint32_t leaf;              /* owning leaf when a strip rejected */
    uint32_t detail;            /* count, index or budget value involved */
    uint32_t leaves_visited;
    uint32_t nodes_visited;
    uint32_t triangles_decoded;
} MohuWorldReport;

const char *mohu_world_status_name(MohuWorldStatus status);

/* Decodes into `mesh`, which is zeroed first. On success the caller owns the
 * allocations and must call mohu_world_mesh_free(). On any rejection the mesh
 * is left empty (atomic) and the report names the first failing case. */
MohuWorldStatus mohu_world_decode(const MohuWorldRequest *request,
                                  MohuWorldMesh *mesh,
                                  MohuWorldReport *report);

/* Decodes the exact visible-entry set the native builder submits. Entries are
 * decoded in array order; duplicates are decoded as many times as they occur.
 * On success the caller owns the mesh and must free it. */
MohuWorldStatus mohu_world_decode_visible(const MohuWorldVisibleRequest *request,
                                          MohuWorldMesh *mesh,
                                          MohuWorldReport *report);

void mohu_world_mesh_free(MohuWorldMesh *mesh);

/* Re-hashes the source range a decoded mesh consulted. The cache calls this at
 * most once per native snapshot, never per eye. */
uint32_t mohu_world_source_fingerprint(const MohuWorldMesh *mesh);
int mohu_world_source_unchanged(const MohuWorldMesh *mesh);

typedef struct {
    int valid;
    uint32_t snapshot_serial;   /* native snapshot this entry was validated for */
    MohuWorldRequest request;   /* identity; pose and screen coords are absent */
    MohuWorldMesh mesh;
} MohuWorldCacheEntry;

typedef struct {
    MohuWorldCacheEntry entries[MOHU_WORLD_CACHE_SLOTS];
    uint32_t next_slot;
    uint32_t hits;          /* reused without revalidation (same snapshot) */
    uint32_t validations;   /* reused after the source fingerprint matched */
    uint32_t misses;        /* decoded fresh */
    uint32_t stale;         /* identity matched but source content changed */
} MohuWorldCache;

/* Cache key: the request fields plus generation. A hit is only possible when
 * the source fingerprint still matches or the entry already belongs to
 * `snapshot_serial`. `*mesh` is borrowed until the next acquire/reset/free. */
MohuWorldStatus mohu_world_cache_acquire(MohuWorldCache *cache,
                                         const MohuWorldRequest *request,
                                         uint32_t snapshot_serial,
                                         const MohuWorldMesh **mesh,
                                         int *reused);
void mohu_world_cache_free(MohuWorldCache *cache);

#endif
