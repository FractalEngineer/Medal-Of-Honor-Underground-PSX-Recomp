# Engine Equivalence Candidates

Generated 2026-10-23T13:23:59+00:00.

> Discovery aid only. Similarity does not prove function equivalence.
> Every mapping still requires disassembly review, overlay identity,
> a calling-contract check, and a live gameplay trace before registration.

## Inputs

| Side | Main executable | SHA-256 | Entry | Load | Text size |
| --- | --- | --- | --- | --- | --- |
| Source | `C:\Users\titan\Desktop\Github_Projects\Mine\Medal-Of-Honor-PSX-Recomp\disc\SLUS_009.74` | `19215344b0031358a6f628cbee0bd124f23275d4621aa16ada8f959cfa0792e3` | `0x8001DFD4` | `0x80010000` | `0x2A000` |
| Target | `disc/SLUS_012.70` | `5c4566b7264a29554abb9d868f23cc40e99ebf3b58b9776dfe2f4ae465bbd641` | `0x8001F844` | `0x80010000` | `0x2B800` |

Source overlay captures: `C:\Users\titan\Desktop\Github_Projects\Mine\Medal-Of-Honor-PSX-Recomp\analysis\vr-proof\overlay_captures.mods.json`  
Target overlay captures: `build-vr-diagnostic/overlay_captures.json`  

Overlay captures are separate code generations. A target address is
meaningful only together with the capture identity shown below.

Function starts include stack-frame prologue discovery.

## Landmarks

### `0x80084718` - entity transform

Source: `source overlay 14 @0x80074000 c9fcfbe4`; 41 instructions; GTE -; calls 1; branches 0.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x80093830` | target overlay 17 @0x8008C000 91ef7512 | 0.923 | 41 | - | 1 | strong candidate |
| 2 | `0x80057284` | target overlay 8 @0x80057000 9eac8039 | 0.426 | 44 | - | 1 | low similarity |
| 3 | `0x8009A478` | target overlay 18 @0x80097000 fe5742fb | 0.422 | 41 | - | 5 | low similarity |
| 4 | `0x8006E924` | target overlay 11 @0x8006B000 764bda4b | 0.414 | 36 | - | 2 | low similarity |
| 5 | `0x8008AF90` | target overlay 16 @0x80089000 6667c9b4 | 0.412 | 29 | - | 1 | low similarity |
| 6 | `0x800998D4` | target overlay 18 @0x80097000 fe5742fb | 0.407 | 26 | - | 1 | low similarity |
| 7 | `0x8007A494` | target overlay 14 @0x80076000 a7fc9016 | 0.406 | 48 | - | 2 | low similarity |
| 8 | `0x8004081C` | target overlay 2 @0x80040000 71d0ce25 | 0.402 | 32 | - | 1 | low similarity |

### `0x80013AE4` - entity node transformer

Source: `source main EXE`; 221 instructions; GTE MVMVA:3; calls 3; branches 19.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x80014184` | target main EXE | 0.996 | 221 | MVMVA:3 | 3 | near-identical candidate |
| 2 | `0x80013B40` | target main EXE | 0.990 | 221 | MVMVA:3 | 3 | near-identical candidate |
| 3 | `0x80043098` | target overlay 3 @0x80043000 240385f8 | 0.369 | 237 | MVMVA:1 | 2 | low similarity |
| 4 | `0x800863BC` | target overlay 15 @0x80082000 46bcea65 | 0.368 | 206 | MVMVA:1 | 2 | low similarity |
| 5 | `0x80092BB8` | target overlay 17 @0x8008C000 91ef7512 | 0.353 | 158 | MVMVA:1 | 10 | low similarity |
| 6 | `0x80077FE0` | target overlay 14 @0x80076000 a7fc9016 | 0.335 | 319 | MVMVA:2 | 5 | low similarity |
| 7 | `0x80050C20` | target overlay 6 @0x80050000 b63e4eba | 0.334 | 85 | MVMVA:1 | 3 | low similarity |
| 8 | `0x800506B8` | target overlay 6 @0x80050000 b63e4eba | 0.328 | 346 | MVMVA:5 | 1 | low similarity |

### `0x80013E58` - GTE RT/TR loader

Source: `source main EXE`; 79 instructions; GTE MVMVA:3; calls 0; branches 0.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x80013EB4` | target main EXE | 1.000 | 79 | MVMVA:3 | 0 | near-identical candidate |
| 2 | `0x800144F8` | target main EXE | 1.000 | 79 | MVMVA:3 | 0 | near-identical candidate |
| 3 | `0x80086280` | target overlay 15 @0x80082000 46bcea65 | 0.384 | 79 | MVMVA:2 | 0 | low similarity |
| 4 | `0x80050C20` | target overlay 6 @0x80050000 b63e4eba | 0.357 | 85 | MVMVA:1 | 3 | low similarity |
| 5 | `0x80067EF4` | target overlay 10 @0x80066000 80fa516c | 0.348 | 68 | MVMVA:1 | 1 | low similarity |
| 6 | `0x8006CD3C` | target overlay 11 @0x8006B000 764bda4b | 0.338 | 90 | MVMVA:1 | 1 | low similarity |
| 7 | `0x80013B40` | target main EXE | 0.318 | 221 | MVMVA:3 | 3 | low similarity |
| 8 | `0x80014184` | target main EXE | 0.318 | 221 | MVMVA:3 | 3 | low similarity |

### `0x800814C4` - geometry entry

Source: `source overlay 14 @0x80074000 c9fcfbe4`; 518 instructions; GTE RTPS:3, NCLIP:1, AVSZ3:1, DPCT:1; calls 3; branches 31.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x80090760` | target overlay 17 @0x8008C000 91ef7512 | 0.556 | 669 | RTPS:3, NCLIP:1, AVSZ3:1, DPCT:1 | 3 | low similarity |
| 2 | `0x80099960` | target overlay 18 @0x80097000 fe5742fb | 0.342 | 710 | RTPS:12 | 0 | low similarity |
| 3 | `0x8008FCE8` | target overlay 17 @0x8008C000 91ef7512 | 0.332 | 230 | RTPS:3 | 2 | low similarity |
| 4 | `0x800976D0` | target overlay 18 @0x80097000 fe5742fb | 0.320 | 247 | RTPS:1 | 4 | low similarity |
| 5 | `0x80090224` | target overlay 17 @0x8008C000 91ef7512 | 0.316 | 335 | RTPT:1, NCLIP:1, AVSZ3:1, DPCT:1 | 3 | low similarity |
| 6 | `0x8008DE88` | target overlay 17 @0x8008C000 91ef7512 | 0.314 | 461 | RTPS:1 | 8 | low similarity |
| 7 | `0x80015B90` | target main EXE | 0.312 | 275 | RTPS:6 | 0 | low similarity |
| 8 | `0x8009CB7C` | target overlay 18 @0x80097000 fe5742fb | 0.300 | 267 | RTPS:6 | 0 | low similarity |

### `0x80080DD4` - geometry filter

Source: `source overlay 14 @0x80074000 c9fcfbe4`; 444 instructions; GTE RTPS:3, NCLIP:1, AVSZ3:1, DPCT:1; calls 3; branches 30.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x80090760` | target overlay 17 @0x8008C000 91ef7512 | 0.526 | 669 | RTPS:3, NCLIP:1, AVSZ3:1, DPCT:1 | 3 | low similarity |
| 2 | `0x8008FCE8` | target overlay 17 @0x8008C000 91ef7512 | 0.354 | 230 | RTPS:3 | 2 | low similarity |
| 3 | `0x80090224` | target overlay 17 @0x8008C000 91ef7512 | 0.337 | 335 | RTPT:1, NCLIP:1, AVSZ3:1, DPCT:1 | 3 | low similarity |
| 4 | `0x800976D0` | target overlay 18 @0x80097000 fe5742fb | 0.336 | 247 | RTPS:1 | 4 | low similarity |
| 5 | `0x80099960` | target overlay 18 @0x80097000 fe5742fb | 0.334 | 710 | RTPS:12 | 0 | low similarity |
| 6 | `0x8008DE88` | target overlay 17 @0x8008C000 91ef7512 | 0.328 | 461 | RTPS:1 | 8 | low similarity |
| 7 | `0x80015B90` | target main EXE | 0.322 | 275 | RTPS:6 | 0 | low similarity |
| 8 | `0x8009CB7C` | target overlay 18 @0x80097000 fe5742fb | 0.312 | 267 | RTPS:6 | 0 | low similarity |

### `0x800824D0` - per-model render entry

Source: `source overlay 14 @0x80074000 c9fcfbe4`; 286 instructions; GTE -; calls 9; branches 37.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x800913A0` | target overlay 17 @0x8008C000 91ef7512 | 0.776 | 301 | - | 9 | tentative candidate |
| 2 | `0x80091854` | target overlay 17 @0x8008C000 91ef7512 | 0.421 | 78 | - | 2 | low similarity |
| 3 | `0x8007A554` | target overlay 14 @0x80076000 a7fc9016 | 0.411 | 174 | - | 4 | low similarity |
| 4 | `0x80023CA8` | target main EXE | 0.406 | 183 | - | 20 | low similarity |
| 5 | `0x80041650` | target overlay 2 @0x80040000 71d0ce25 | 0.406 | 195 | - | 6 | low similarity |
| 6 | `0x80073560` | target overlay 13 @0x80072000 b148e588 | 0.395 | 124 | - | 6 | low similarity |
| 7 | `0x80028CC4` | target main EXE | 0.390 | 259 | - | 12 | low similarity |
| 8 | `0x80047498` | target overlay 4 @0x80047000 08425939 | 0.390 | 344 | - | 15 | low similarity |

### `0x8008B3E8` - level vertex transformer

Source: `source overlay 15 @0x8008A000 81b86e73`; 710 instructions; GTE RTPS:12; calls 0; branches 67.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x80099960` | target overlay 18 @0x80097000 fe5742fb | 0.994 | 710 | RTPS:12 | 0 | near-identical candidate |
| 2 | `0x8009CB7C` | target overlay 18 @0x80097000 fe5742fb | 0.403 | 267 | RTPS:6 | 0 | low similarity |
| 3 | `0x80090760` | target overlay 17 @0x8008C000 91ef7512 | 0.367 | 669 | RTPS:3, NCLIP:1, AVSZ3:1, DPCT:1 | 3 | low similarity |
| 4 | `0x80015B90` | target main EXE | 0.310 | 275 | RTPS:6 | 0 | low similarity |
| 5 | `0x8008DE88` | target overlay 17 @0x8008C000 91ef7512 | 0.287 | 461 | RTPS:1 | 8 | low similarity |
| 6 | `0x800976D0` | target overlay 18 @0x80097000 fe5742fb | 0.287 | 247 | RTPS:1 | 4 | low similarity |
| 7 | `0x8008FCE8` | target overlay 17 @0x8008C000 91ef7512 | 0.278 | 230 | RTPS:3 | 2 | low similarity |
| 8 | `0x80010000` | target main EXE | 0.274 | 322 | RTPS:2 | 9 | low similarity |

### `0x80016E38` - VSync wrapper

Source: `source main EXE`; 26 instructions; GTE -; calls 2; branches 1.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x800186A8` | target main EXE | 0.948 | 26 | - | 2 | near-identical candidate |
| 2 | `0x80018B50` | target main EXE | 0.850 | 26 | - | 2 | strong candidate |
| 3 | `0x800219C8` | target main EXE | 0.674 | 19 | - | 2 | weak candidate |
| 4 | `0x80017F88` | target main EXE | 0.639 | 21 | - | 2 | weak candidate |
| 5 | `0x800767D4` | target overlay 14 @0x80076000 a7fc9016 | 0.631 | 16 | - | 2 | weak candidate |
| 6 | `0x8002414C` | target main EXE | 0.620 | 21 | - | 2 | weak candidate |
| 7 | `0x800188BC` | target main EXE | 0.619 | 24 | - | 2 | weak candidate |
| 8 | `0x80018AA4` | target main EXE | 0.614 | 41 | - | 2 | weak candidate |

### `0x80090B80` - gameplay render wait

Source: `source overlay 16 @0x80090000 25b98476`; 110 instructions; GTE -; calls 10; branches 8.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x80087C94` | target overlay 15 @0x80082000 46bcea65 | 0.443 | 101 | - | 4 | low similarity |
| 2 | `0x80083044` | target overlay 15 @0x80082000 46bcea65 | 0.439 | 92 | - | 7 | low similarity |
| 3 | `0x80041D04` | target overlay 2 @0x80040000 71d0ce25 | 0.429 | 119 | - | 5 | low similarity |
| 4 | `0x80070704` | target overlay 12 @0x80070000 def9baa9 | 0.426 | 84 | - | 15 | low similarity |
| 5 | `0x80047CBC` | target overlay 4 @0x80047000 08425939 | 0.426 | 77 | - | 5 | low similarity |
| 6 | `0x80024A04` | target main EXE | 0.426 | 68 | - | 4 | low similarity |
| 7 | `0x8006E414` | target overlay 11 @0x8006B000 764bda4b | 0.424 | 99 | - | 1 | low similarity |
| 8 | `0x80087E28` | target overlay 15 @0x80082000 46bcea65 | 0.421 | 105 | - | 5 | low similarity |

### `0x80013698` - RTPS projection loop

Source: `source main EXE`; 275 instructions; GTE RTPS:6; calls 0; branches 30.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x80015B90` | target main EXE | 0.993 | 275 | RTPS:6 | 0 | near-identical candidate |
| 2 | `0x8009CB7C` | target overlay 18 @0x80097000 fe5742fb | 0.384 | 267 | RTPS:6 | 0 | low similarity |
| 3 | `0x800976D0` | target overlay 18 @0x80097000 fe5742fb | 0.352 | 247 | RTPS:1 | 4 | low similarity |
| 4 | `0x8008FCE8` | target overlay 17 @0x8008C000 91ef7512 | 0.341 | 230 | RTPS:3 | 2 | low similarity |
| 5 | `0x80099960` | target overlay 18 @0x80097000 fe5742fb | 0.333 | 710 | RTPS:12 | 0 | low similarity |
| 6 | `0x80010000` | target main EXE | 0.330 | 322 | RTPS:2 | 9 | low similarity |
| 7 | `0x80011DA0` | target main EXE | 0.330 | 322 | RTPS:2 | 9 | low similarity |
| 8 | `0x8009A614` | target overlay 18 @0x80097000 fe5742fb | 0.312 | 275 | RTPT:1, NCLIP:1, RTPS:1 | 2 | low similarity |

### `0x8007E414` - multiplayer weapon geometry

Source: `source overlay 14 @0x80074000 c9fcfbe4`; 160 instructions; GTE SQR:1; calls 4; branches 8.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x8008D81C` | target overlay 17 @0x8008C000 91ef7512 | 0.576 | 411 | MVMVA:1, SQR:1 | 8 | low similarity |
| 2 | `0x8008E5C8` | target overlay 17 @0x8008C000 91ef7512 | 0.333 | 171 | SQR:2 | 8 | low similarity |
| 3 | `0x8005039C` | target overlay 6 @0x80050000 b63e4eba | 0.326 | 114 | OP:1, SQR:1 | 0 | low similarity |
| 4 | `0x80011AC4` | target main EXE | 0.324 | 145 | SQR:1 | 0 | low similarity |
| 5 | `0x80013864` | target main EXE | 0.324 | 145 | SQR:1 | 0 | low similarity |
| 6 | `0x80050164` | target overlay 6 @0x80050000 b63e4eba | 0.322 | 98 | SQR:1 | 0 | low similarity |
| 7 | `0x8008C620` | target overlay 17 @0x8008C000 91ef7512 | 0.315 | 455 | SQR:1 | 11 | low similarity |
| 8 | `0x80047DF0` | target overlay 4 @0x80047000 08425939 | 0.309 | 61 | SQR:1 | 3 | low similarity |

### `0x800836C0` - weapon vertex filter

Source: `source overlay 14 @0x80074000 c9fcfbe4`; 26 instructions; GTE -; calls 1; branches 0.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x8008A174` | target overlay 16 @0x80089000 6667c9b4 | 0.544 | 30 | - | 0 | low similarity |
| 2 | `0x8004CC58` | target overlay 5 @0x8004C000 2eed43dc | 0.502 | 26 | - | 2 | low similarity |
| 3 | `0x80079FA0` | target overlay 14 @0x80076000 a7fc9016 | 0.501 | 31 | - | 1 | low similarity |
| 4 | `0x800188BC` | target main EXE | 0.499 | 24 | - | 2 | low similarity |
| 5 | `0x800765E8` | target overlay 14 @0x80076000 a7fc9016 | 0.498 | 30 | - | 1 | low similarity |
| 6 | `0x8009AE70` | target overlay 18 @0x80097000 fe5742fb | 0.492 | 28 | - | 1 | low similarity |
| 7 | `0x80018B50` | target main EXE | 0.488 | 26 | - | 2 | low similarity |
| 8 | `0x80022F08` | target main EXE | 0.485 | 23 | - | 0 | low similarity |

### `0x8006591C` - multiplayer shot basis

Source region unavailable from the supplied EXE/seeds/captures.
Capture the active reference overlay before matching this landmark.

### `0x8006A76C` - primary shot basis

Source: `source overlay 13 @0x8006A000 3c1c8089`; 65 instructions; GTE -; calls 5; branches 0.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x80076C28` | target overlay 14 @0x80076000 a7fc9016 | 0.938 | 65 | - | 5 | near-identical candidate |
| 2 | `0x8009BE98` | target overlay 18 @0x80097000 fe5742fb | 0.591 | 48 | - | 3 | low similarity |
| 3 | `0x80076D2C` | target overlay 14 @0x80076000 a7fc9016 | 0.540 | 35 | - | 4 | low similarity |
| 4 | `0x80053D54` | target overlay 7 @0x80053000 804cc7d8 | 0.453 | 66 | - | 3 | low similarity |
| 5 | `0x8006CFC4` | target overlay 11 @0x8006B000 764bda4b | 0.451 | 65 | - | 4 | low similarity |
| 6 | `0x800728E8` | target overlay 13 @0x80072000 b148e588 | 0.446 | 71 | - | 7 | low similarity |
| 7 | `0x80057EFC` | target overlay 8 @0x80057000 9eac8039 | 0.443 | 44 | - | 2 | low similarity |
| 8 | `0x80086B80` | target overlay 15 @0x80082000 46bcea65 | 0.438 | 52 | - | 1 | low similarity |

### `0x8008CE50` - multiplayer render wait

Source: `source overlay 15 @0x8008A000 81b86e73`; 102 instructions; GTE -; calls 3; branches 0.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x8009B3A8` | target overlay 18 @0x80097000 fe5742fb | 0.957 | 112 | - | 3 | near-identical candidate |
| 2 | `0x8009B64C` | target overlay 18 @0x80097000 fe5742fb | 0.407 | 334 | - | 10 | low similarity |
| 3 | `0x80097AAC` | target overlay 18 @0x80097000 fe5742fb | 0.403 | 96 | - | 6 | low similarity |
| 4 | `0x80083044` | target overlay 15 @0x80082000 46bcea65 | 0.397 | 92 | - | 7 | low similarity |
| 5 | `0x80017628` | target main EXE | 0.392 | 94 | - | 2 | low similarity |
| 6 | `0x8001A5B0` | target main EXE | 0.388 | 79 | - | 4 | low similarity |
| 7 | `0x80041D04` | target overlay 2 @0x80040000 71d0ce25 | 0.382 | 119 | - | 5 | low similarity |
| 8 | `0x8004C2BC` | target overlay 5 @0x8004C000 2eed43dc | 0.381 | 148 | - | 5 | low similarity |

### `0x8008A440` - multiplayer level entry

Source: `source overlay 15 @0x8008A000 81b86e73`; 46 instructions; GTE RTPT:2; calls 0; branches 0.

| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 | `0x8008A174` | target overlay 16 @0x80089000 6667c9b4 | 0.367 | 30 | - | 0 | low similarity |
| 2 | `0x80057EFC` | target overlay 8 @0x80057000 9eac8039 | 0.360 | 44 | - | 2 | low similarity |
| 3 | `0x80023F84` | target main EXE | 0.346 | 46 | - | 5 | low similarity |
| 4 | `0x800921D0` | target overlay 17 @0x8008C000 91ef7512 | 0.338 | 39 | - | 2 | low similarity |
| 5 | `0x80095788` | target overlay 17 @0x8008C000 91ef7512 | 0.337 | 46 | - | 4 | low similarity |
| 6 | `0x800174F8` | target main EXE | 0.337 | 41 | - | 2 | low similarity |
| 7 | `0x80072468` | target overlay 13 @0x80072000 b148e588 | 0.335 | 50 | - | 1 | low similarity |
| 8 | `0x80095AF8` | target overlay 17 @0x8008C000 91ef7512 | 0.333 | 45 | - | 5 | low similarity |

## Review checklist

- Disassemble the source and candidate, not just the matching prefix.
- Confirm arguments, return value, delay-slot behavior, and fatal stores.
- Record the exact active overlay bytes and caller for both sides.
- Add a fail-closed game/overlay/caller guard.
- Prove live invocation and state restoration before enabling stereo.
