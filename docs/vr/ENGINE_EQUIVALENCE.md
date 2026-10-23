# Engine Equivalence

This file is the human-reviewed hook map. A candidate is not a confirmed target
address, and no candidate may be registered until its signature, calling
contract, overlay identity, and live invocation have been checked.

## Required evidence

| Evidence | Purpose |
| --- | --- |
| Reference region | Main EXE or a specific captured overlay generation |
| Target region | Main EXE or a specific captured overlay generation |
| Normalized MIPS sequence | Instruction-structure similarity independent of raw addresses |
| GTE opcode profile | Identifies RTPS/RTPT projection and related geometry paths |
| Call/branch/memory profile | Rejects superficially similar arithmetic blocks |
| Disassembly review | Confirms prologue, parameters, returns, and stores |
| Live invocation | Confirms the function runs in the intended gameplay state |
| Guard design | Fails closed if game ID, overlay bytes, or caller do not match |

## Reference landmarks

The addresses below come from the reference game's current `vr/` source. They
describe Medal of Honor, not Underground.

| Reference address | Reference role | Boundary/region note | Target |
| --- | --- | --- | --- |
| `0x80084718` | Entity transform | Overlay; entity at `$a0`, position fields near `+0x98` | Unknown |
| `0x800814C4` | Geometry entry | Overlay; entity render dispatch | Unknown |
| `0x80080DD4` | Geometry filter | Overlay; alternate entity render path | Unknown |
| `0x800824D0` | Per-model render entry | Overlay; dynamic-object draw path | Unknown |
| `0x8008B3E8` | Level vertex transformer | Overlay; large RTPS-heavy function ending near `0x8008BEF8` | Unknown; missing from retained source capture |
| `0x80016E38` | PsyQ `VSync` wrapper | Main EXE; broad call site, legacy probe only | Unknown |
| `0x80090B80` | Gameplay render wait | Overlay; slot-specific `DrawSync(-1)` replay seam | Unknown |
| `0x8007E414` | Multiplayer weapon geometry | Overlay; not a general weapon path | Unknown |
| `0x800836C0` | Weapon vertex filter | Overlay; guarded by captured mesh evidence | Unknown |
| `0x8006591C` | Multiplayer shot basis | Overlay; separate from first-person shot constructor | Unknown |
| `0x8006A76C` | Primary shot basis | Overlay; current single-player source path | Unknown |
| `0x8008CE50` | Multiplayer render wait | Overlay; mode-specific counterpart | Unknown |
| `0x8008A440` | Multiplayer level entry | Overlay; mode-specific counterpart | Unknown |

## Candidate workflow

Run the matcher from the Underground repository:

```powershell
python tools/match_moh_engine.py `
  --source-exe 'C:\Users\titan\Desktop\Github_Projects\Mine\Medal-Of-Honor-PSX-Recomp\disc\SLUS_009.74' `
  --source-seeds 'C:\Users\titan\Desktop\Github_Projects\Mine\Medal-Of-Honor-PSX-Recomp\seeds\ghidra_funcs.txt' `
  --source-overlays 'C:\Users\titan\Desktop\Github_Projects\Mine\Medal-Of-Honor-PSX-Recomp\analysis\vr-proof\overlay_captures.mods.json' `
  --target-exe disc\SLUS_012.70 `
  --target-seeds seeds\ghidra_funcs.txt `
  --target-overlays build-release\overlay_captures.json `
  --output docs\vr\ENGINE_EQUIVALENCE_REPORT.md
```

The report ranks candidates. It does **not** confirm them.

The current output is
[ENGINE_EQUIVALENCE_REPORT.md](ENGINE_EQUIVALENCE_REPORT.md), with the
machine-readable result in
[ENGINE_EQUIVALENCE_REPORT.json](ENGINE_EQUIVALENCE_REPORT.json).

Preliminary result: the PsyQ `VSync` wrapper is a near-identical static match
(`0x80016E38` -> `0x800186A8`, 26 instructions, only absolute RAM references
changed). It remains a broad library wrapper and is not the gameplay replay
boundary. Every render, geometry, weapon, and HUD candidate still has low
similarity and no live evidence.

Current best candidates from the report:

| Reference | Role | Target candidate | Score | Status |
| --- | --- | --- | ---: | --- |
| `0x80016E38` | PsyQ `VSync` | `0x800186A8` main EXE | 0.948 | Static library match; do not use as gameplay boundary |
| `0x800824D0` | Per-model render entry | `0x800914EC` overlay | 0.660 | Weak candidate; needs disassembly |
| `0x800836C0` | Weapon vertex filter | `0x800188BC` main EXE | 0.499 | Weak candidate; likely false positive |
| `0x80084718` | Entity transform | `0x8006E100` overlay | 0.436 | Low similarity; not usable |
| `0x80090B80` | Gameplay render wait | `0x8006E170` overlay | 0.413 | Low similarity; not usable |
| `0x8008B3E8` | Level vertex transformer | `0x8008DE88` overlay | 0.287 | Low similarity; not usable |

The reference capture used for this report does not cover `0x8006591C`, so that
landmark has no source function yet. All overlay candidates must be rechecked
against the specific capture generation that will run in Underground.

## Mapping table

| Reference | Target address | Overlay identity | Signature | Contract | Live evidence | Confidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Entity transform | TBD | TBD | TBD | TBD | TBD | None | Disabled |
| Level vertex transformer | TBD | TBD | TBD | TBD | TBD | None | Disabled |
| Gameplay render wait | TBD | TBD | TBD | TBD | TBD | None | Disabled |
| Camera source | TBD | TBD | TBD | TBD | TBD | None | Disabled |
| Player/scene roots | TBD | TBD | TBD | TBD | TBD | None | Disabled |
| Weapon geometry | TBD | TBD | TBD | TBD | TBD | None | Disabled |
| Shot basis | TBD | TBD | TBD | TBD | TBD | None | Disabled |
| Native HUD producers | TBD | TBD | TBD | TBD | TBD | None | Disabled |
| PsyQ `VSync` wrapper | `0x800186A8` | Main EXE, `main-6ea5e7d0c719` | 26 instructions; `VSync` mode gate and BIOS vector calls | Static disassembly matches; broad call sites | No gameplay use | High | Static only |

## Guard policy

- Address equality alone is never sufficient.
- The `VSync` match is a static library-function match, not evidence that its
  caller is the correct render checkpoint.
- Overlay-resident code must be keyed by captured bytes or a stable fingerprint,
  not only by its load address.
- A guard mismatch disables the title hook and restores the ordinary flat path.
- A guessed address must not be committed behind an enable flag as if it were
  harmless; a wrong entry hook can corrupt execution even when its feature flag
  is off.
- Same-offset player fields, entity structures, weapon IDs, and render layouts
  remain hypotheses until inspected in Underground.
