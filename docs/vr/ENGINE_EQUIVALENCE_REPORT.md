# Engine Equivalence Candidates

Generated 2026-10-23T12:03:28+00:00.

> Discovery aid only. Similarity does not prove function equivalence.
> Every mapping still requires disassembly review, overlay identity,
> a calling-contract check, and a live gameplay trace before registration.

## Inputs

| Side | Main executable | SHA-256 | Entry | Load | Text size |
| --- | --- | --- | --- | --- | --- |
| Source | `C:\Users\titan\Desktop\Github_Projects\Mine\Medal-Of-Honor-PSX-Recomp\disc\SLUS_009.74` | `19215344b0031358a6f628cbee0bd124f23275d4621aa16ada8f959cfa0792e3` | `0x8001DFD4` | `0x80010000` | `0x2A000` |
| Target | `disc/SLUS_012.70` | `5c4566b7264a29554abb9d868f23cc40e99ebf3b58b9776dfe2f4ae465bbd641` | `0x8001F844` | `0x80010000` | `0x2B800` |

Source overlay captures: `C:\Users\titan\Desktop\Github_Projects\Mine\Medal-Of-Honor-PSX-Recomp\analysis\vr-proof\overlay_captures.mods.json`  
Target overlay captures: `build-release/overlay_captures.json`  

Overlay captures are separate code generations. A target address is
meaningful only together with the capture identity shown below.

## Landmarks

### `0x80084718` - entity transform

Source: `source overlay 14 @0x80074000 c9fcfbe4`; 41 instructions; GTE -; calls 1; branches 0.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x8006E100` | target overlay 9 @0x80069000 a8abcd09 | 0.436 | 28 | - | 2 | low similarity |
| 2 | `0x8001F844` | target main EXE | 0.401 | 42 | - | 2 | low similarity |
| 3 | `0x800241EC` | target main EXE | 0.389 | 38 | - | 5 | low similarity |
| 4 | `0x8002497C` | target main EXE | 0.384 | 34 | - | 2 | low similarity |
| 5 | `0x800965F0` | target overlay 12 @0x8007F000 7edd35ed | 0.383 | 40 | - | 3 | low similarity |

### `0x800814C4` - geometry entry

Source: `source overlay 14 @0x80074000 c9fcfbe4`; 518 instructions; GTE RTPS:3; calls 3; branches 34.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x8008DE88` | target overlay 12 @0x8007F000 7edd35ed | 0.328 | 461 | RTPS:1 | 8 | low similarity |
| 2 | `0x800147C8` | target overlay 3 @0x80014000 fde15eae | 0.315 | 280 | RTPS:1 | 0 | low similarity |
| 3 | `0x80010000` | target main EXE | 0.298 | 322 | RTPS:2 | 9 | low similarity |
| 4 | `0x80011DA0` | target main EXE | 0.298 | 322 | RTPS:2 | 9 | low similarity |
| 5 | `0x8001D688` | target overlay 5 @0x8001D000 f72b1501 | 0.278 | 544 | - | 3 | low similarity |

### `0x80080DD4` - geometry filter

Source: `source overlay 14 @0x80074000 c9fcfbe4`; 444 instructions; GTE RTPS:3; calls 3; branches 33.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x8008DE88` | target overlay 12 @0x8007F000 7edd35ed | 0.342 | 461 | RTPS:1 | 8 | low similarity |
| 2 | `0x800147C8` | target overlay 3 @0x80014000 fde15eae | 0.330 | 280 | RTPS:1 | 0 | low similarity |
| 3 | `0x80010000` | target main EXE | 0.318 | 322 | RTPS:2 | 9 | low similarity |
| 4 | `0x80011DA0` | target main EXE | 0.318 | 322 | RTPS:2 | 9 | low similarity |
| 5 | `0x8001D688` | target overlay 5 @0x8001D000 f72b1501 | 0.272 | 544 | - | 3 | low similarity |

### `0x800824D0` - per-model render entry

Source: `source overlay 14 @0x80074000 c9fcfbe4`; 286 instructions; GTE -; calls 9; branches 37.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x800914EC` | target overlay 12 @0x8007F000 7edd35ed | 0.660 | 218 | - | 6 | weak candidate |
| 2 | `0x8008B380` | target overlay 12 @0x8007F000 7edd35ed | 0.425 | 319 | - | 15 | low similarity |
| 3 | `0x80028CC4` | target main EXE | 0.390 | 259 | - | 12 | low similarity |
| 4 | `0x800295E4` | target main EXE | 0.382 | 223 | - | 0 | low similarity |
| 5 | `0x800789B0` | target overlay 11 @0x80072000 840620ce | 0.378 | 278 | - | 10 | low similarity |

### `0x8008B3E8` - level vertex transformer

Source: `source overlay 15 @0x8008A000 81b86e73`; 710 instructions; GTE RTPS:12; calls 0; branches 67.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x8008DE88` | target overlay 12 @0x8007F000 7edd35ed | 0.287 | 461 | RTPS:1 | 8 | low similarity |
| 2 | `0x80010000` | target main EXE | 0.274 | 322 | RTPS:2 | 9 | low similarity |
| 3 | `0x80011DA0` | target main EXE | 0.274 | 322 | RTPS:2 | 9 | low similarity |
| 4 | `0x800147C8` | target overlay 3 @0x80014000 fde15eae | 0.270 | 280 | RTPS:1 | 0 | low similarity |
| 5 | `0x8001D688` | target overlay 5 @0x8001D000 f72b1501 | 0.242 | 544 | - | 3 | low similarity |

### `0x80016E38` - VSync wrapper

Source: `source main EXE`; 26 instructions; GTE -; calls 2; branches 1.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x800186A8` | target main EXE | 0.948 | 26 | - | 2 | near-identical candidate |
| 2 | `0x8002414C` | target main EXE | 0.620 | 21 | - | 2 | weak candidate |
| 3 | `0x800188BC` | target main EXE | 0.619 | 24 | - | 2 | weak candidate |
| 4 | `0x80016FCC` | target main EXE | 0.603 | 23 | - | 1 | weak candidate |
| 5 | `0x80023AE0` | target main EXE | 0.601 | 21 | - | 2 | weak candidate |

### `0x80090B80` - gameplay render wait

Source: `source overlay 16 @0x80090000 25b98476`; 110 instructions; GTE -; calls 10; branches 8.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x8006E170` | target overlay 9 @0x80069000 a8abcd09 | 0.413 | 121 | - | 24 | low similarity |
| 2 | `0x800183D0` | target main EXE | 0.410 | 93 | - | 9 | low similarity |
| 3 | `0x8001E50C` | target main EXE | 0.408 | 116 | - | 5 | low similarity |
| 4 | `0x80022F70` | target main EXE | 0.405 | 101 | - | 5 | low similarity |
| 5 | `0x8001B690` | target main EXE | 0.398 | 81 | - | 9 | low similarity |

### `0x8007E414` - multiplayer weapon geometry

Source: `source overlay 14 @0x80074000 c9fcfbe4`; 160 instructions; GTE -; calls 4; branches 9.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x8009702C` | target overlay 12 @0x8007F000 7edd35ed | 0.353 | 161 | - | 10 | low similarity |
| 2 | `0x8002DE04` | target main EXE | 0.340 | 145 | - | 3 | low similarity |
| 3 | `0x8002877C` | target main EXE | 0.340 | 160 | - | 9 | low similarity |
| 4 | `0x80022578` | target main EXE | 0.339 | 160 | - | 11 | low similarity |
| 5 | `0x8001B8E0` | target main EXE | 0.337 | 145 | - | 8 | low similarity |

### `0x800836C0` - weapon vertex filter

Source: `source overlay 14 @0x80074000 c9fcfbe4`; 26 instructions; GTE -; calls 1; branches 0.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x800188BC` | target main EXE | 0.499 | 24 | - | 2 | low similarity |
| 2 | `0x80022F08` | target main EXE | 0.485 | 23 | - | 0 | low similarity |
| 3 | `0x8004CBEC` | target overlay 7 @0x8003F000 01d0e3bd | 0.483 | 27 | - | 1 | low similarity |
| 4 | `0x8001B370` | target main EXE | 0.477 | 28 | - | 2 | low similarity |
| 5 | `0x800186A8` | target main EXE | 0.469 | 26 | - | 2 | low similarity |

### `0x8006591C` - multiplayer shot basis

Source region unavailable from the supplied EXE/seeds/captures.
Capture the active reference overlay before matching this landmark.

### `0x8006A76C` - primary shot basis

Source: `source overlay 13 @0x8006A000 3c1c8089`; 65 instructions; GTE -; calls 5; branches 0.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x80038A2C` | target main EXE | 0.427 | 56 | - | 1 | low similarity |
| 2 | `0x8001F464` | target main EXE | 0.427 | 70 | - | 6 | low similarity |
| 3 | `0x80037980` | target main EXE | 0.425 | 69 | - | 6 | low similarity |
| 4 | `0x80038990` | target main EXE | 0.424 | 39 | - | 8 | low similarity |
| 5 | `0x8003920C` | target main EXE | 0.422 | 47 | - | 2 | low similarity |

### `0x8008CE50` - multiplayer render wait

Source: `source overlay 15 @0x8008A000 81b86e73`; 102 instructions; GTE -; calls 3; branches 0.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x800945C0` | target overlay 12 @0x8007F000 7edd35ed | 0.416 | 104 | - | 1 | low similarity |
| 2 | `0x80017628` | target main EXE | 0.392 | 94 | - | 2 | low similarity |
| 3 | `0x8004C394` | target overlay 7 @0x8003F000 01d0e3bd | 0.390 | 94 | - | 3 | low similarity |
| 4 | `0x8001A5B0` | target main EXE | 0.388 | 79 | - | 4 | low similarity |
| 5 | `0x800227F8` | target main EXE | 0.371 | 112 | - | 6 | low similarity |

### `0x8008A440` - multiplayer level entry

Source: `source overlay 15 @0x8008A000 81b86e73`; 46 instructions; GTE -; calls 0; branches 2.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x800174F8` | target main EXE | 0.441 | 41 | - | 2 | low similarity |
| 2 | `0x8004CA3C` | target overlay 7 @0x8003F000 01d0e3bd | 0.438 | 37 | - | 2 | low similarity |
| 3 | `0x80096104` | target overlay 12 @0x8007F000 7edd35ed | 0.413 | 35 | - | 1 | low similarity |
| 4 | `0x80097BB8` | target overlay 12 @0x8007F000 7edd35ed | 0.412 | 29 | - | 0 | low similarity |
| 5 | `0x80038A2C` | target main EXE | 0.411 | 56 | - | 1 | low similarity |

## Review checklist

- Disassemble the source and candidate, not just the matching prefix.
- Confirm arguments, return value, delay-slot behavior, and fatal stores.
- Record the exact active overlay bytes and caller for both sides.
- Add a fail-closed game/overlay/caller guard.
- Prove live invocation and state restoration before enabling stereo.
