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
 * MATERIALS ARE NOT DECODED. Every triangle retains the source words, but
 * `materials_decoded` stays 0 until the packet/preflight/subdivision bodies'
 * material fields are captured and mapped. The upper half of the second base
 * word is captured as `record_index`; a real slot-2 capture resolved that
 * index to a 12-byte table of three 16-bit UV pairs, so it is not a material
 * descriptor. Textured rendering must refuse this mesh rather than guess.
 * Unsupported or malformed input rejects the whole decode with a named status;
 * faces are never silently dropped.
 */

#define MOHU_WORLD_MAX_VERTICES   8192u
#define MOHU_WORLD_MAX_NODES      8192u
#define MOHU_WORLD_MAX_LEAVES     16384u
#define MOHU_WORLD_MAX_TRIANGLES  65536u
#define MOHU_WORLD_MAX_LEAF_FACES 4096u
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
    MOHU_WORLD_REJECT_ALLOCATION
} MohuWorldStatus;

/* One source vertex: three signed 16-bit camera-relative coordinates and two
 * unused bytes, matching the native 8-byte stride. */
typedef struct {
    int16_t x, y, z, pad;
} MohuWorldVertex;

typedef struct {
    uint32_t vertex[3];       /* indices into MohuWorldMesh.vertices */
    uint32_t source_address;  /* guest word that introduced this triangle */
    uint32_t base_word[2];    /* raw base words; upper half of [1] is below */
    uint16_t record_index;    /* upper half of base_word[1]: per-face UV record */
    uint32_t extension_word;  /* 0 for a base triangle */
    uint16_t render_flags;    /* extension bits 13..14; 0 when not decoded */
    uint8_t winding_swapped;  /* extension bit 15 */
    uint8_t is_extension;
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
} MohuWorldRequest;

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
    uint32_t materials_decoded;     /* always 0 until the M1 material map lands */
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
