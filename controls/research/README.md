# Native mouse aim research harness

This is a Phase 1 diagnostic fixture, **not the mouse mod**. It has no mouse
capture or keyboard profile and is excluded from ordinary builds. It requires
debug tools and an empty development release channel; public/playtest builds
cannot enable it. The dedicated research catalog replaces the VR test catalog
only in the explicitly configured probe build.

From the repository root, using the existing debug-enabled Release build:

```powershell
cmake -S . -B build-probe -DMOHU_MKB_RESEARCH=ON -DPSX_DEBUG_TOOLS=ON
cmake --build build-probe --target psx-runtime -j 2
python tools/probe_mkb_native.py analysis/runtime/mkb-research-new --slot 0 --fixtures analysis/runtime/mkb-native-analog-20261105/saves/openbios --research --research-direct
python tools/check_mkb_research.py analysis/runtime/mkb-research-new/receipt.json
```

The fixture path is local, ignored and requires the owner's lawful disc. The
probe copies it, refuses concurrent game sessions, hashes source saves and
preferences, closes its owned process, and records cleanup in `receipt.json`.
For a shorter follow-up add `--research-cases fire_base fire_entry_yaw
fire_settled_yaw`. The initial incompatible historical slot is not a substitute;
never modify a state header or execution identity.

To return the probe build to its ordinary catalog, configure with
`-DMOHU_MKB_RESEARCH=OFF` and rebuild. `build-release` remains OFF.

## Protocol

The existing debug `mod_cmd` API exposes name `mohu.mkb.research`:

- `arm` / `arm N`: observe the next N owned updates (1..8), without a queued
  angle perturbation. Records are published when the following owned entry
  seals the observation.
- `inject HEX_SITE YAW PITCH [N]`: explicitly perturb one update at the selected
  site, then observe N updates. Deltas are signed native angle units, +/-256;
  they are not mouse counts. Sites are `800892c8`, `8008f984`, `8008f9bc`.
  Exactly one command perturbation is permitted per observation, including
  windows containing multiple updates.
- `direct 1` / `direct 0`: enable/disable the **experimental** suppression of
  native angular correction, retaining native ray calculations. On first owned
  entry, seed input targets from current actor angles to avoid a target snap.
  This persists until disabled, guest restore or session reset. It does not
  imply measured recoil/mounted/other-mode compatibility.
- `dump`: return state and completed observation metadata.
- `row I`: return one completed observation row. Pagination fits the existing
  debug reply limit. No command reads the observation array while it is mutable.

States: 0 idle, 1 armed, 2 recording, 3 ready, 4 configuring. Parameters transfer
to the emulation thread with release/acquire publication; completed rows transfer
back using the same protocol. Reset clears host state without writing guest RAM.
Rows freeze after publication until the serial debug command requests another
observation. Invalid commands return result 0. The runner checks seven invalid
requests, complete owned update counts, ordered stages, exact one-shot changes,
stable final direct angles, shot ownership and source/preference preservation.

`applied` / the compact receipt's `writes` count explicit four-field injection
operations, not every native store or the direct-mode initialization. An `arm`
control in direct mode is a no-perturbation control, not proof that native
angular correction is unchanged.

## Row schema

Every value is serialized as an unsigned 32-bit integer. Reinterpret angular
fields as signed Q16; 4096 native angle units = one revolution.

| Index | Meaning |
| --- | --- |
| 0 | Observed address; low bit set denotes the post-perturbation synthetic record, not a real PC |
| 1, 2 | Guest cycle low/high words |
| 3 | Research-owned update-entry sequence (not a production replay-safe token yet) |
| 4 | Current owned SP player |
| 5 | Return address |
| 6 | Observed actor or owned shot |
| 7 | Player input flags |
| 8, 9 | Observed object's pitch/yaw |
| 10, 11 | Player pitch/yaw angular increments |
| 12, 13 | Input pitch/yaw targets (`+0x184/+0x190`) |
| 14, 15 | Input fields `+0x188/+0x194` |
| 16, 17 | Input fields `+0x18C/+0x198` |
| 18, 19 | Input native context / previous context (`+0x1D4/+0x1D8`) |
| 20 | CPU `$s5` |
| 21 | Whether the queued perturbation has been applied |
| 22, 23 | Player pitch/yaw, independently of shot orientation |
| 24 | CPU `$a3` |

Production capture/live-input eligibility is deliberately not weakened for this
research. These explicit debugger experiments run outside the production mouse
input path. Do not ship this command interface as a substitute for that path.
