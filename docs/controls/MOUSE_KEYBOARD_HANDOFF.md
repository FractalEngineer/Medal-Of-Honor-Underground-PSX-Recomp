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

## Continuation — camera and cached-ray timing, 2026-11-05

The owner requested continuation again. Work resumes from checkpoint `35f8181`.
This turn extends Phase 1 only; the production feature remains unimplemented.

### New evidence and experiments

- Owned camera root `0x800AA160` resolves to class 2, input at `camera+0x3FC`.
  Its `input+0x0C` handle resolves through `0x800AA1A0 + index*4` to P1.
  Update callback `0x8004A744` (size `0x1E8`, FNV `0xA707D113`) runs after the
  previous P1 update and approximately 19,042 guest cycles before the next one.
  Its generic actor-call RA is `0x800784DC`. Camera observations now carry the
  upcoming owned P1 sequence; camera-anchored windows contain complete updates.
- The ray producer `0x8008D81C` (size `0x1058`, FNV `0x787AC4B0`) uses the
  camera input's `+0x100` matrix. Native matrix writes were traced to
  `0x8004C3C4` and following stores in `0x8004C2BC`, called by `0x8004C50C`.
  The camera look-at target stores are `0x8004B100/114/128` in `0x8004ADA8`.
- An explicit `refresh 1` experiment moves the original ray producer to P1
  entry and filters its later matching native call. Four owned updates each
  showed one refresh and one skip. Baseline P38 yaw -210 changed to -178 when
  +32 was applied at camera entry. This does NOT establish that moving the ray
  producer is necessary: a subsequent control with refresh OFF also produced
  -178 in the same owned update. Prefer retaining original order if confirmed.
- Pitch needs its own camera preparation: native `0x8008AD04` (size `0x130`,
  FNV `0xC1B54110`) reads input pitch and prepares camera input `+0x28` using
  native sine/cosine; later `0x80049FCC` smooths `+0x1C` toward it. Its usual
  mode-7 call is `0x8008F9C0`, RA `0x8008F9C8`, after the native ray producer.
  An explicit `prepare 1` experiment runs it once after a queued camera pitch
  perturbation, carries its target delta into `+0x1C` preserving the existing
  smoothing residual, then skips only the matching later mode-7 native call.
  Body pitch stays exactly +32. The first refreshed ray now changes immediately;
  observed P38 pitch changes 40 -> 76 and yaw -210 -> -214. Native parallax,
  projection quantization, assistance and actual impact agreement remain open.
  No shot-angle, shot-origin, spread or collision stores were replaced.
- The constructor actually calls `0x8004815C` from `0x800482C4`, RA
  `0x800482CC` (the earlier reference to 0x80048288 identified the caller's
  function entry, not that call instruction). New read-only constructor and
  original ray-call observations will resolve the exact consumption ordering.

Local receipts: `mkb-camera-order-20261105`, `mkb-camera-refresh-20261105`,
`mkb-camera-matrix-writers-20261105`, `mkb-camera-target-writers-20261105`,
`mkb-camera-prepared-20261105`, `mkb-camera-native-ray-order-20261105`, all under
`analysis/runtime/`. All completed runs exited 0, preserved source saves and
production preferences, and left no game process. The first refresh/preparation
matrices pass the current behavior checker, which does not assert shot alignment.
The historical committed ten-case receipt remains unchanged.

### Final outcome of this continuation

The native-order/preparation run completed. It confirmed one original ray call
per owned update, followed by actual P38 cached-ray consumption after P1 basis.
The early-ray experiment and its command/CLI switch were removed. Current
source only observes that original ray call and optionally moves the small
native pitch preparation, preserving original ray/projectile ordering.

Separate arm/fire commands sometimes put shots in the next owned update.
Queuing them during a host pause did not guarantee a first-update shot either;
that attempt and switch were removed. A research-only gate now waits for the
native sampled P1 button word at `800A04B4` (reader `800834FC`, 6C bytes, FNV
141AED00). The first gate mistakenly considered the always-FFFF upper bits;
the checker caught the resulting scheduling failure. Masking to low 16 bits
corrected it: neutral 0000 -> Cross 0040, previous word at `800A04BC` still 0000.
The checker now requires this actual fresh sample and a shot in that same P1
sequence, alongside constructor ownership, native origin, and call counts.

Final full run: `analysis/runtime/mkb-camera-complete-matrix-20261105`.
**19/19 cases pass**, ten invalid requests rejected. Includes prior controls,
negative deltas, crossing 4096 yaw units, camera windows and six firing cases.
All six firing cases constructed shots in the first observed owned update,
with exact native cached muzzle origins. Every update ran the original ray
producer once, with no early-ray replacement. Each queued camera pitch change
performed one early preparation and one matching later skip. Raw yaw crossed
3894 -> 4150 without native canonicalization; production still needs deliberate
wrapping. The checker compares yaw deltas modulo one revolution.

The final gated camera shots are baseline 40/-210, yaw +32 -> 40/-178, pitch
+32 -> 76/-214. Body angles retain exact requested displacement. This narrows
the same-update stale-ray problem but does not resolve pitch geometry, native
assistance, actual impacts or all gameplay contexts. The original entry-yaw
negative control still fires -210, proving boundary selection matters.

Committed compact evidence is `docs/controls/MOUSE_KEYBOARD_CAMERA_RECEIPT.json`;
the prior ten-case receipt remains historical and unchanged. Current research
source SHA256 is `3209174449d36a20f60ffe69f3086f63b9393c7306e975e390c70b66e008d8e5`;
binary SHA256 is `31b052e35d2f7f412858e07204d4222e805f6428cde4851a27ef56bb38efe442`.
The schema now has 40 fields, capacity 128; see the research README. All runs
closed normally, left no game process and preserved source saves/preferences.

```powershell
cmake --build build-probe --target psx-runtime -j 2
python tools/probe_mkb_native.py analysis/runtime/mkb-next --slot 0 --fixtures analysis/runtime/mkb-native-analog-20261105/saves/openbios --research --research-direct --research-prepare --gate-fire
python tools/check_mkb_research.py analysis/runtime/mkb-next/receipt.json
```

Also passed this turn: strict C11 warnings-as-errors syntax, Python compilation,
and whitespace checking. Framework/launcher code and production CMake selection
did not change; their earlier five passing tests and release-OFF build remain
the latest baseline checks. Probe remains research ON, release remains OFF.

### Next work after this checkpoint

1. Explain and measure native view/ray/projectile agreement, particularly the
   +36 pitch / -4 yaw result from +32 pitch input. Preserve `80047DF0`'s native
   atan/sqrt, collision, origin, spread and target ownership. Capture actual
   impacts and reticle projection, rather than asserting exact shot angles.
2. Extend camera preparation beyond this mode-7 fixture only after measuring
   native aim/scoping, recoil, other weapons, moving headings and constraints.
   Inspect unhandled angular stores (e.g. `8008E4F4`) before wider mode support.
3. Finish action mapping, fresh/save/profile checks and cached-native hook
   coverage (current local runs still report zero cached-native overlay calls).
   Keep the Phase 1 gate open. Production math/lifecycle, input transport,
   package/options, profiles and GUI work remain the later plan phases.
