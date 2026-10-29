# Render kernel contract and qualification

2026-10-30. SLUS-01270; framework remains `555e1eab`. These are experimental
build-selected render implementations. Normal `build-release` still uses the
original functions. First target is 60 fresh application frames/s; 90 is deferred.

## Preflight caller

Native `80011424`, 668 bytes, FNV-1a `C38CDCC1`, is called at `80011000` and
returns to `80011008`. `$s3` is `1F800000`, `$s6` carries winding/face flags,
`$s7` points at the face, and GTE SXY/SZ/FLAG are inputs. This is a custom
register/scratchpad interface, not an `a0..a3 -> v0` C function.

`preflight.c` retains the original integer operations, branch decisions and
PGXP operand sequence, using `psx_hle_gte_execute` for the original GTE math.
It reads the native face/vertex data through CPU callbacks and retains native
scratchpad writes. Its supported scratchpad is the full 1 KB at `1F800000`.
All 131 numeric CPU words through the end of GTE control, all scratchpad bytes,
and 322 register/memory precision entries are compared, including projection
provenance. No pointer-bearing CPU service fields are serialized.

`preflight_entry.c` includes the original generated shard with only its symbol
renamed. The host core is selected only during a frozen render transaction,
with exact return address, scratch base and leaf entry PC. Canonical simulation,
unknown callers and interior resumes execute the original body. The wrapper
flushes pending CPU/GTE work, executes the operation and checks completion at
the caller boundary. It never changes native simulation/audio/VBlank rates.

The standalone oracle is extracted from the unchanged generated body into an
ignored output directory. Its deterministic 100,000 full-state comparisons
include every winding flag and result masks 0, 1, 2, 4, 6, 8, 10, 12 and 14.
These service doubles check operation/operand sequencing; they do not substitute
for live GTE/precision coverage.

The explicitly armed diagnostic link wrapper executes the candidate with a
private CPU/scratchpad, rolls back its precision checkpoint, then executes the
original once. Canonical scope avoids nested precision checkpoints. Real slot-2
128-call and slot-5 1,024-call captures have zero numeric/precision differences
or refusals. Input homogeneous projections in these canonical captures are
invalid; eye projective rendering is covered separately by integration controls,
not claimed from the canonical capture.

## Packet caller

Native `80010CF0`, 1,840 bytes, is called at `8009A514`, return `8009A51C`.
The original CPS body has entry plus interior continuations, including
`80011008`. `build_packet_kernel.py` derives an exact copy of that body with
batched render timing and the shared GTE service. Every arithmetic/PGXP
operation, callee, packet writer and continuation remains present. This is an
intermediate optimization, not a decoded mesh renderer.

`packet_entry.c` selects the derived body only in frozen render passes and its
supported PC range; canonical calls remain original. The diagnostic harness
uses private 2 MB RAM and scratchpad, compares all numeric CPU/GTE results,
written bytes and precision metadata, then restores before the original runs.
The final 512-call run covers one entry, 511 resumes and 8,091 writes with zero
differences/refusals. An earlier run refused its entry because `$s3` is established
by the prologue; that failed receipt is retained. The corrected entry guard
allows the original prologue to establish it. Heavy frozen slot-2 packet and
complete XR/hand workload qualification remain open.

## Build and fixture ownership

`MOHU_VR_HOST_PREFLIGHT` and `MOHU_VR_HOST_PACKET` default OFF. When selected,
the implementation family is `mohu-vr-render-kernels`, contract
`slus01270-render-kernels-v1`. `PSX_EXECUTION_PROFILE=REFERENCE` selects the
original shard; REFERENCE and ENHANCED both build successfully. Diagnostic
`MOHU_VR_PREFLIGHT_HARNESS` / `MOHU_VR_PACKET_HARNESS` are separate builds and
cannot run alongside the corresponding selected implementation.

Source/header/recipe hashes participate in the execution identity. The current
enhanced identity is `1b2f45c2ed83546d119ac31c37dcc6746d5a954ccbf763b8634f8815b7910ccb`.
Its valid mission-start fixture is `analysis/fixtures/sp-cache-view-key`.
It was saved through normal native boot/input using copied cards. It is not the
operator's heavier frozen slot-2 scene despite sharing file slot number 2.
No header/cookie conversion or inventory mutation was used. The probes now
accept `--build-dir` and `--fixtures` for complete isolated runtime directories.

## Decision

Retain the kernels as experimental source; do not promote them to normal play.
Preflight-only three alternating mission-start comparisons reduce pair work
about 9%. Kernel plus fresh-view scheduling gives about 48.2–48.8 pairs/s in the
latest limited desktop control. Full XR/HUD/hands and second-scene promotion
gates remain open. See [renderer checkpoint](RENDER_KERNEL_CHECKPOINT.md) and
[compact receipt](../../vr/proof/render-kernel-checkpoint-receipt.json).
