# Disc image comparison — 2026-10-29

**Operator follow-up:** the personal headset smoke passed: no more missing
level or stuck music; pause and Sten are also reported OK. Performance remains
unsatisfactory and is the next task. [Report](../../vr/proof/clean-disc-headset-smoke-receipt.json).
Image comparison/activation is closed; do not repeat it as a performance task.

**Activation completed later the same day:** the operator deleted the old dump
and one duplicate. The remaining folder holds `Medal of Honor - Underground
(USA).cue/.bin`, with the same verified SHA-256 below. Existing RunVR batch
files now use it through source/staged `game.toml` and the refreshed launcher
selection/cache. The old-image repair is default-OFF and explicitly disabled.
No new batch file was created. A copied slot-5 production smoke passes without
disc/recovery overrides. The original comparison and temporary-test history
below remains evidence; its earlier statement that configuration was unchanged
applies to that comparison turn, before this requested activation.

Both newly supplied BINs are **byte-for-byte identical** and pass the complete
MODE2/2352 sector checks. Either is a suitable replacement for the damaged
original. This turn only compared/read the images and temporarily mounted one
for a copied-save smoke; the configured disc, source images and original saves
remain unchanged.

| Image folder | BIN bytes | Wholly zero raw sectors | Sector checks |
|---|---:|---:|---|
| `Medal Of Honor Underground (USA)` — old | 748,001,856 | 64 | Fails |
| `Medal of Honor - Underground` — new A | 748,001,856 | 0 | Passes |
| `MOH_Underground` — new B | 748,001,856 | 0 | Same bytes as A |

Both new CUEs correctly name their BIN, declare one `MODE2/2352` track and
`INDEX 01 00:00:00`. Filename differences do not change their disc layout.

## Exact identities

Both new BINs:

```text
SHA-256 2aed19d588f69274f8be70001eaa9b6400240b62088da72bace815ab902d56ed
SHA-1   3d4ed9b1c7fb99acd96dd9c6ce2749a40cb8a1c2
MD5     9b5f6e9ed0ced26fda1bfb7cdd2b7a01
CRC32   19a9614b
```

The old BIN is SHA-256
`0951683ffd1bc2db1094ef3b0e142df6741efe2a5f95ad13bb5f2813a6c252d9`,
MD5 `8a2e3361e8272ce09e9a4ea7bd0403ad`. The hashes currently listed in
`game.toml` identify that old image; they were not an independent integrity
oracle and must not be used to reject these internally valid replacements.

## Checks and differences

All **318,028 sectors** of the new image were checked: sync/MSF/mode headers,
duplicated subheaders, Mode-2 Form-1/Form-2 EDC and Form-1 ECC P/Q. There are
286,542 Form-1 and 31,486 Form-2 sectors, zero absent Form-2 EDCs, and **zero
failures**. A complete raw-sector comparison proves B has the same bytes, so
the result applies to both. The checker also detects intentionally corrupted
payload/header controls; it is not simply returning success for every input.

The old image has 64 invalid headers, 63 invalid duplicated subheaders, 994 EDC
failures, 4 ECC-P failures and 442 ECC-Q failures. Counts overlap; do not sum
them as distinct damaged sectors. Against the new image, 1,498 raw sectors
differ, with these overlapping regions:

- Header: 64 sectors; subheader: 127.
- Payload: 1,058 sectors; EDC/ECC region: 536.
- All 64 old entirely-zero sectors contain nonzero data in the new image.

The ISO directory/file layout is identical: **835 files**, unchanged paths,
lengths and LBAs, with no added/removed files. Logical file data differs in
24 files: `DATA/MSN2/LVL2/M2_2_1.VB;1` and 23 `.STR` videos under `MOVIE`.
Form-2 full-payload changes are additionally included in the raw-sector report;
logical ISO file hashes cover the 2048-byte user-data view.

The music sector **LBA 9469 now has its actual payload, valid header and valid
EDC/ECC**. This replaces the need to synthesize its header and play silence.
No bytes were copied into or written over the original image.

`SLUS_012.70`, `LEVEL.BIN`, `LEVEL2P.BIN`, `SHELL.BIN` and `SYSTEM.CNF` payloads
are identical between old and new. This is the same game/code layout: these
images do not require rediscovering VR addresses, regenerating the executable,
or discarding native overlay caches solely because of this comparison.

## Copied-save runtime check

An initial clean-image launch was correctly refused because the enabled
`mohu.repair.music-sector` package targets only the damaged image's SHA-256.
That is a working guard, not a fault in the new dump. Do NOT add the clean
image to that patch's target or weaken the expected-zero-byte guard.

The second launch temporarily disabled only that recovery feature, loaded a
copy of SP slot 5 and completed the production 180-pair export threshold with
120 valid stereo records, no failed records, normal exit and no remaining
game process. The original mod-state bytes were backed up before the change
and restored in `finally`; their SHA-256 matches. Original save/preferences
hashes also match. Release/debug-OFF stayed in place; no headset or XR-runtime
settings were used. This is a boot/copied-save smoke, not a physical visual,
music-listening or 60/90-FPS acceptance test.

## Permanent activation

The remaining selected CUE is
`Medal of Honor - Underground/Medal of Honor - Underground (USA).cue`.
Activation is complete:

1. Source/staged game configuration, prepare names/digests, catalog identity,
   probe metadata, current launcher disc selection and `disc.cfg` are updated.
2. The recovery feature is default-OFF in the source/staged catalog and disabled
   in current mod state. Exact original-image/zero-byte guards are unchanged.
3. The framework probe recomputed content identities and the TOC fingerprint.
   `5abe13ac...` is unchanged because the TOC is unchanged; MD5/SHA-1/CRC32 now
   identify the clean data. Executable/VR hooks/native caches are preserved.
4. The default-config copied slot-5 smoke passes and closes normally. The
   operator has now run the existing batch file personally and confirms the
   world/music fix, pause and Sten. The CPU replay performance milestone remains open;
   a clean image alone does not establish 60/90 FPS.

Activation evidence: [receipt](../../vr/proof/clean-disc-activation-receipt.json).

Read-only tools: `audit_sp_disc.py`, `compare_sp_discs.py`,
`check_cd_sectors.c`. Bulk metadata, checker controls and runtime receipt are
under `analysis/vr-baseline/disc-comparison-20261029/`. The compact
[receipt](../../vr/proof/disc-image-comparison-receipt.json) records exact
hashes, counts, changed files, boot-code equality and the smoke's provenance.
Source-image folders are ignored as local PlayStation assets.
