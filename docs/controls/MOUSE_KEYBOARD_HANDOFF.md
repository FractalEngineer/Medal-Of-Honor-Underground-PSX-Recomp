# Mouse and keyboard handoff

Update this file every work turn. This is the current task's continuation
record; evidence and commands belong here or in the linked detailed reports.

## Objective and authorization

Implement the supplied opt-in flat mouse/keyboard plan on branch `mkb`, adapted
to **Medal of Honor: Underground SLUS-01270**. The owner approved that title
adaptation and requested a handoff update each turn, followed by continued work.
Work solo. Do not publish/tag releases. Preserve personal saves, active sessions,
ordinary input profiles, generated C and unrelated edits.

## Current state

- Branch `mkb`, original checkpoint `2cbc92a` (research probe and evidence).
  Continuation work below follows that commit; read `git log -1` for current HEAD.
- Production mod is not implemented. Phase 1 native aim research is in progress.
- Game baseline `53e4a50071a3c8240a3b0285c4b4342d3a1c4044`, VERSION 0.1.1.
- Framework pin `e57fd0279b86edf48cfe42364da4388046772bad`; launcher pin
  `a95615751b413e043983944441ed8912066c65ce`; do not float submodules.
- Pre-existing framework edits: `runtime/include/mod_plugins.h`,
  `runtime/src/gpu_gl_renderer.c`, `runtime/src/psx_openxr.c`,
  `runtime/tests/test_openxr_input.c`. Root `.commandcode/` is unrelated.
- Central Beads database is unavailable; no local substitute was initialized.
- No Ghidra tool is exposed. Use resident bytes, existing debugger and source
  evidence; never guess an address, representation or update token.

## Prior turn — 2026-11-05

Created `mkb`, built both existing Release configurations, cold-booted the lawful
local disc to campaign, created an isolated compatible serializer fixture, and
ran five baseline tests (all passed). Original copied SP slot 3 is incompatible
with the current execution profile; do not modify its header or identity.

Detailed state: [native hook evidence](MOUSE_KEYBOARD_HOOKS.md) and
[test/build report](MOUSE_KEYBOARD_TEST_REPORT.md). Tool:
`tools/probe_mkb_native.py`. All bulky data remains ignored in `analysis/`.

Working fixture:
`analysis/runtime/mkb-native-analog-20261105/saves/openbios/state_8001F844_slot00.pst`
and its thumbnail. Copy it for each run; do not overwrite the source.
Final prior receipt: `analysis/runtime/mkb-final-probe-20261105/receipt.json`.

SP player root is `0x800AA17C`, actor input at `+0x39C` (SP `actor+0x3FC`).
Actor pitch/yaw are 32-bit at `+0x23C/+0x240`; input target candidates are
`+0x184/+0x190`. Native adjustment means a +32-unit target perturbation produces
only +27 actor yaw units and changes pitch. A target-only implementation fails
the direct proportionality requirement. Player update is `0x800892C8`, native
look processing `0x8008EAF0`, adjustment candidate `0x8008D81C`. Exact instruction
words and hash guards are in the evidence file.

Unknowns: adjustment/centering path preserving recoil, correct after-look /
before-consumer injection boundary, simulation-update ownership token, actual
shot/impact agreement, mounted constraints and complete native action contexts.
No capture policy, bindings profile, package or GUI has been installed.

## Current turn — 2026-11-05, continuation

**Result:** internal call order and small proportional actor-angle changes are
now observed in a bounded owned update. The native cached firing ray remains
an open release requirement. This is diagnostic progress, not a playable mod.

### Changes

- Added this per-turn handoff, the dedicated default-OFF
  `MOHU_MKB_RESEARCH` CMake option, and `controls/research/` with its own trusted
  package and C implementation. This requires debug tools and refuses a named
  public/playtest release channel. Ordinary builds do not link/stage it.
- Extended `tools/probe_mkb_native.py` with bounded native research, selected
  cases, explicit angular-correction experiments, ray write traces, native
  pause recovery, source hash receipts and seven invalid-command checks.
- Added `tools/check_mkb_research.py`, which checks observed behavior: complete
  owned update counts and ordering, single consumption, exact before/after
  field changes, final actor angles, shot ownership and cleanup.
- Added the compact checked `MOUSE_KEYBOARD_RESEARCH_RECEIPT.json` and updated
  the detailed hook/test reports. No framework/launcher source changes or pin
  bumps were made; their four pre-existing dirty files remain untouched.

### Findings and rejected approaches

1. Changing the old trace filter to virtual addresses alone did not fix entry
   coverage. The executable had **zero cached-native overlay calls**; internal
   dirty-RAM calls bypass these compiled-entry/dispatch rings. The existing
   `xprobe_watch` recorder exposes the actual JAL/JALR order with guest cycles.
   Its 16K detail ring can evict interesting rows between host requests, so use
   the new sealed observations for complete owned-update evidence.
2. Measured order: owned player callback `0x800892C8` (RA `0x800784DC`), native
   look processing, instruction `0x8008F984`, adjustment return `0x8008F9BC`,
   player integration `0x80078FBC` (RA `0x8007862C`), actor basis `0x80076C28`.
   Weapon construction occurs earlier within the callback than look processing.
   The harness generates an entry sequence at the validated owner call and
   seals a requested 1..8-update observation on the following owned entry.
3. Applying +32 units to both actor and input targets while leaving native
   adjustment intact still drifts (yaw +27 with pitch cross-coupling; pitch
   +29.375 in the coupled test). Source-target writes alone are insufficient.
4. Selecting the native direct-target branch by altering `$v0` at `0x8008F988`
   makes actor angles exact, but skips the cached ray producer. P38 shots then
   keep their old direction even after settling. This approach was removed.
5. Current experiment retains the whole adjustment function and suppresses only
   its five guarded angular-increment stores for the owned P1 in modes 7/8.
   It seeds source targets from current actor orientation once on activation,
   then preserves native ray computation. Six +32 pitch/yaw injections at
   three different boundaries produce exactly +32 requested units and zero
   cross-axis motion after settling. No source code or angle field is guessed;
   exact words and ownership checks are recorded in the detailed evidence.
6. P38 uses the cached origin at input `+0x1A4..+0x1AC` and target at
   `+0x1B0..+0x1B8` through `0x8004815C -> 0x80047DF0`. Ray target writers are
   `0x8008E1E0/1F0/200`, origin writers `0x8008E540/544/548`, inside adjustment.
   Current correction-only control: baseline shot yaw -210, immediate +32
   actor-yaw shot still -210, settled +32 actor-yaw shot -182. The 28-unit
   settled change may include native parallax/quantization/assistance; those
   causes are not distinguished. Do not claim shot/impact alignment yet.
7. Nulling the target argument at `0x80047FE8` was not useful: that path was not
   used by this P38 fixture. The failed experiment was removed, and no native
   aim-assist option has been established.
8. Repeated load/pad presentation can enter native pause. The runner now presses
   native Start and releases it, then verifies pause=0 before arming; it never
   edits a pause flag. A too-large debug reply was fixed by paging frozen rows,
   rather than extending the framework's existing reply limit.

### Reproduction and checks

See `controls/research/README.md` for command protocol and the 25-field row
schema. Injection deltas here are native angle units, not mouse counts.
`applied`/`writes` counts explicit perturbations, not native stores or the
direct-mode initial synchronization.

```powershell
cmake -S . -B build-probe -DMOHU_MKB_RESEARCH=ON -DPSX_DEBUG_TOOLS=ON
cmake --build build-probe --target psx-runtime -j 2
python tools/probe_mkb_native.py analysis/runtime/mkb-new --slot 0 --fixtures analysis/runtime/mkb-native-analog-20261105/saves/openbios --research --research-direct
python tools/check_mkb_research.py analysis/runtime/mkb-new/receipt.json
```

The final run used `analysis/runtime/mkb-final-owned-receipt-20261105`:
**10/10 research cases checked**, seven invalid commands rejected; one injection
per requested window, no dropped rows, correct owned update counts, six exact
angular changes, three owned P38 firing observations. Exit 0, no remaining game
processes, unchanged source saves and production preferences. The checker does
not require shot alignment and explicitly leaves the production feature false.
Exact executable/source/raw-receipt hashes are in the committed compact receipt.

Also passed: debug probe build, ordinary `build-release` build with
`MOHU_MKB_RESEARCH=OFF` / `PSX_DEBUG_TOOLS=OFF`, four framework input/capture
tests, one launcher binding test, strict C11 `-Wall -Wextra -Werror` syntax
check, and Python compilation. Existing upstream compiler warnings remain.
Whitespace checking uses `cr-at-eol` for the repository's existing Windows
line endings. No generated C was edited, no unrelated source was committed,
and no release was published.

Useful local receipts (all ignored):

- `mkb-virtual-filter-20261105/aim_xprobe.json`: observed internal JAL/JALR order.
- `mkb-owned-update-paged-20261105/receipt.json`: coupled writes with native
  correction intact; negative proportionality control.
- `mkb-direct-shot-latency-20261105/receipt.json`: rejected whole-call bypass.
- `mkb-angular-correction-only-20261105/receipt.json`: retained native ray work.
- `mkb-ray-writers-20261105/aim_ray_writes.json`: exact source-vector writers.
- `mkb-final-owned-receipt-20261105/receipt.json`: final complete checked matrix.

Current local build state: `build-probe` has research ON and its dedicated
catalog (12 packages); `build-release` has research OFF and its original
catalog (13 packages). No game process remains. Keep builds and runs serialized,
two compile jobs per build. Both use shared fetched dependency build paths, so
switching configurations may rebuild dependencies.

### Next work

1. Continue at the cached native shot-ray producer. Determine how the player
   camera/reticle matrix, world target, native parallax/spread and collision
   feed `+0x1A4/+0x1B0`. Resolve same-update fire without skipping the producer,
   moving the muzzle, overwriting spread or advancing player simulation twice.
   Native P38 shot construction is observed at basis RA `0x8004860C` with
   `$s2 == P1`, `$s0 == shot`. Keep every code/owner/type guard.
2. Extend evidence to recoil, native aim/scoping, movement heading, yaw wrap,
   pitch limits, other weapon classes and mounted constraints. The current
   hook/store guards and test matrix cover only the measured campaign context.
   Investigate actual impacts and camera agreement; actor fields are not enough.
3. Prove cached-native overlay coverage (current probes report zero native
   overlay calls), execution/replay/restore eligibility and a production
   consume-once token before turning research into a production plugin.
4. Then implement remaining plan phases: pure count-to-angle math and lifecycle,
   bundled disabled-by-default feature/options, generic host takeover axes and
   live-input guard, isolated two-slot gameplay/menu profiles in existing
   `keybinds.ini`, semantic launcher Controls bridge and Configure Controls
   navigation, clear incompatibility refusal, packaging and gameplay matrix.

Source specification remains `C:/Users/titan/Downloads/MOUSE_KEYBOARD_PLAN.md`
(hash in test report). Preserve its key contracts: displacement-based mouse
aim (no dt/stick cap); click capture with no acquisition shot; Escape release,
P pause; no stale input after interruption/restore; defaults do not overwrite
ordinary P1/P2 binds; primary/secondary/unbind/reset via GUI; all sensitivities
persist through mod options; no netplay/split-screen or simultaneous active VR.
Do not advertise mouse support or completion from this diagnostic harness.
