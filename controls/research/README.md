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
For camera timing and basis experiments add `--research-prepare --gate-fire
--research-cases camera_order fire_camera_base fire_camera_yaw fire_camera_pitch
fire_camera_yaw_negative fire_camera_pitch_negative fire_camera_pitch_large`.
The initial incompatible historical slot is not a substitute;
never modify a state header or execution identity.

To return the probe build to its ordinary catalog, configure with
`-DMOHU_MKB_RESEARCH=OFF` and rebuild. `build-release` remains OFF.

## Protocol

The existing debug `mod_cmd` API exposes name `mohu.mkb.research`:

- `arm` / `arm N`: observe the next N owned updates (1..16), without a queued
  angle perturbation. Records are published when the following owned entry
  seals the observation.
- `inject HEX_SITE YAW PITCH [N]`: explicitly perturb one update at the selected
  site, then observe N updates. Deltas are signed native angle units, +/-256;
  they are not mouse counts. Sites are `800892c8`, `8008f984`, `8008f9bc`,
  `8004a744` (owned camera callback). Camera-site windows start at that callback
  and carry the upcoming P1 sequence; other windows start at the P1 callback.
  Exactly one command perturbation is permitted per observation, including
  windows containing multiple updates.
- `direct 1` / `direct 0`: enable/disable the **experimental** suppression of
  native angular correction, retaining native ray calculations. On first owned
  entry, seed input targets from current actor angles to avoid a target snap.
  This persists until disabled, guest restore or session reset. It does not
  imply measured recoil/mounted/other-mode compatibility.
- `prepare 1` / `prepare 0`: experimentally move one native mode-7 camera pitch
  preparation call (`8008ad04`) before the camera callback, only when this
  observation injects pitch there. Carry its target delta through the camera's
  existing smoothing residual and skip the matching later call once. It does
  not alter native shot construction or move the ray producer.
- `fire_gate 1` / `fire_gate 0`: delay an armed window until the low 16 bits of
  the game's sampled P1 button word are nonzero. The isolated runner supplies
  neutral followed only by Cross; this is a diagnostic scheduling control,
  not production mouse eligibility or a general fire-action detector. Upper
  bits are `ffff` even when neutral and must be excluded.
- `dump`: return state and completed observation metadata.
- `row I`: return one completed observation row. Pagination fits the existing
  debug reply limit. No command reads the observation array while it is mutable.

States: 0 idle, 1 armed, 2 recording, 3 ready, 4 configuring. Parameters transfer
to the emulation thread with release/acquire publication; completed rows transfer
back using the same protocol. Reset clears host state without writing guest RAM.
Rows freeze after publication until the serial debug command requests another
observation. Invalid commands return result 0. The runner checks ten invalid
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
| 25..27 | Native cached ray origin, input `+0x1A4..+0x1AC` |
| 28..30 | Native cached ray target, input `+0x1B0..+0x1B8` |
| 31, 32 | Reserved zeros; retired early-ray experiment counters in older local receipts |
| 33 | Number of original native ray calls in this window |
| 34, 35 | Native sampled P1 current / previous button words (addresses `800A04B4/BC`) |
| 36..38 | Observed object's native world position at `+0x220..+0x228` |
| 39 | Observed object's class at `+8` |
| 40..42 | Owned camera input origin, input `+0..+8` |
| 43..51 | Owned camera view matrix from input `+0x100` |
| 52..54 | Camera aim target at input `+0x1C..+0x24` |
| 55 | Camera prepared component at input `+0x28` |
| 56..58 | GTE projection H / OFX / OFY |
| 59, 60 | Native aim-target score / no-selection baseline at `8008e06c` |
| 61..63 | Owned camera actor world position at `+0x220..+0x228` |
| 64..66 | Shot object native flags at `+0x0C/+0x10/+0x14` |
| 67 | Shot native update/lifetime field at `+0x214` |
| 68 | Shot collision state at `+0x298` |
| 69 | Shot's companion/effect pointer at `+0x39C` |
| 70 | Companion flags at `+0x38` |
| 71 | Shot auxiliary value at `+0x34` |

The current schema has 72 fields and capacity 192 rows. Historical committed
receipts use 25 or 40 fields. Synthetic sites `ff000018` / `ff00001c` record early
camera preparation / the matching later call being skipped. `8008d81c` is a
read-only original ray-call observation; `8004815c` records native P38 ray
consumption with RA `800482cc`. The discarded early-ray experiment used
`ff000010` / `ff000014`; those are absent from current source and captures.
`8008e06c` records the native aim-target scoring branch once after each owned
ray call. A score different from the baseline means the ray producer applied
its own target blend; the checker reports the resulting camera/ray angle rather
than requiring them to be identical.
`8008e7a8` records the producer after its cached-target stores, so those fields
describe the ray consumed by that owned update rather than the preceding one.
`80047498` observes the constructed P38 shot's native update entry, while
`ff000024` records its release at `80077e8c`. The checker distinguishes the
collision return `80045df8` from lifetime expiry `800474e8`; only collision
returns are reported as physical impact endpoints. The fire runner releases
Cross after the first shot is observed so a long observation window does not
consume a second round.

Production capture/live-input eligibility is deliberately not weakened for this
research. These explicit debugger experiments run outside the production mouse
input path. Do not ship this command interface as a substitute for that path.
