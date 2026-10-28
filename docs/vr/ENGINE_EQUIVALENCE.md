# Engine Equivalence

This file is the human-reviewed hook map. A candidate is not a confirmed target
address, and no candidate may be registered until its signature, calling
contract, overlay identity, and live invocation have been checked.

The initial discovery tables below retain historical candidates. They are not
the current work queue: SP replay/visibility, first-person meshes, P1 MP eye
replay and W1/W2.1/W2.2 are implemented. Use [HANDOFF.md](HANDOFF.md),
[WEAPON_MAPPING.md](WEAPON_MAPPING.md), the MP selector/frustum evidence and
current guarded source for those contracts. Do not restart a completed mapping
because an early table still says Unknown or read-only. For reusable code and
the remaining target-specific bindings, see
[REFERENCE_REUSE_AUDIT.md](REFERENCE_REUSE_AUDIT.md).

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
python vr\tools\match_moh_engine.py `
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

The slot-0 gameplay capture produced high-confidence matches for three core
paths. All three source and target functions were observed executing in their
captured overlay generation:

| Reference | Role | Underground | Evidence |
| --- | --- | --- | --- |
| `0x80084718` | Entity transform | `0x80093830` | 41/41 mnemonics; 7 token differences, all absolute RAM references |
| `0x80013AE4` | Entity node transformer | `0x80013B40` | 221/221 mnemonics; live call ring, caller/callee pair matches |
| `0x80013E58` | GTE RT/TR loader | `0x80013EB4` | Byte-identical function; live call ring |
| `0x8008B3E8` | Level vertex transformer | `0x80099960` | 710/710 mnemonics; 12 RTPS on both sides; 9 address-only differences |
| `0x80090B80` | Gameplay render wait | `0x8009D828` | 110/110 mnemonics; 10 calls and 8 branches on both sides; 29 address-only differences |

The confirmed target functions live in overlay captures based at `0x80097000`
and `0x8008C000`. Whole-capture hashes change as the runtime's capture windows
advance, so they are observations only. Each function's exact byte hash and
FNV-1a guard are stored in `vr/underground/engine_map.c`.

The PsyQ `VSync` wrapper is also a near-identical static match
(`0x80016E38` -> `0x800186A8`). It remains a broad library wrapper and is not the
gameplay replay boundary.

The live call ring disambiguates duplicated main-EXE code. The confirmed
Underground entity transform calls `0x80013B40`, not its near-identical twin
`0x80014184`; `0x80013B40` in turn calls `0x80013EB4`, not `0x800144F8`.
This establishes the active scene-transform chain, but the camera itself is
still represented through matrices read by this chain rather than a named
camera object.

Current best candidates from the report:

| Reference | Role | Target candidate | Score | Status |
| --- | --- | --- | ---: | --- |
| `0x8008B3E8` | Level vertex transformer | `0x80099960` overlay | 0.994 | Confirmed static and live; 12 RTPS |
| `0x80090B80` | Gameplay render wait | `0x8009D828` overlay | 0.880 | Confirmed static and live |
| `0x80084718` | Entity transform | `0x80093830` overlay | 0.920 | Confirmed static and live |
| `0x800824D0` | Per-model render entry | `0x800914EC` overlay | 0.660 | Weak candidate; needs disassembly |
| `0x80016E38` | PsyQ `VSync` | `0x800186A8` main EXE | 0.948 | Static library match; not a gameplay boundary |

The reference capture used for this report does not cover `0x8006591C`, so that
landmark has no source function yet. All overlay candidates must be rechecked
against the specific capture generation that will run in Underground.

## Mapping table

| Reference | Target address | Overlay identity | Signature | Contract | Live evidence | Confidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Entity transform | `0x80093830` | `91ef75121345` @ `0x8008C000` | 41 instructions | `$a0` entity, position fields still unverified | Capture execution | High | Read-only diagnostic hook |
| Entity node transformer | `0x80013B40` | Main EXE | 221 instructions | Recursive node walk; caller chain confirmed | Live call ring | High | Live trace only |
| GTE RT/TR loader | `0x80013EB4` | Main EXE | 79 instructions | Loads view/model matrix and translation into GTE | Live call ring | High | Live trace only |
| Level vertex transformer | `0x80099960` | Overlay @ `0x80097000` | 710 instructions, 12 RTPS | Register/contract still being decoded | Capture execution | High | Read-only diagnostic hook |
| Gameplay render wait | `0x8009D828` | Overlay @ `0x80097000` | 110 instructions, 10 calls | Replay seam still being decoded | Capture execution | High | Read-only diagnostic hook |
| Camera source | GTE RT at level transform | GTE RT at `0x80099960` | 12-RTPS camera-relative projector | Read per draw; TR remains zero | Live turn trace | High | Read-only |
| Player/scene roots | `0x8009D64C` / `0x8009D654` | `0x800AA174` / `0x800AA17C` | Pointer globals | Read pointer, then actor fields | Live root/input trace | High | Read-only |
| MP first-person geometry | `0x800892E8` | MP caller RA `0x8008A544` | Complete function/producer guards in `weapon.h` | `[actor+0x114] == input+0x9F0`; animated producer `0x8008DB98` | 13-ID flat and both-eye controls; WEAPON_MAPPING | High | Guarded opt-in implementation; not an open hook search |
| Shot basis | TBD | TBD | TBD | TBD | TBD | None | Disabled |
| Native HUD producers | Reference native HUD capture/hand surfaces | SP `8006C874`, `8006B64C`, `8008F9F4` | Full-span hashes; native owned text/packet banks | NATIVE_HAND_HUD regions and ownership | SP fire/reload/pause/load + null-HMD fallback | High for tested SP fixture | H1 implemented; H2 physical/transitions open |
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
