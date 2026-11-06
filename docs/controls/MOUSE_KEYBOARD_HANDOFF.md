# Mouse and keyboard handoff

Update this file every work turn. This is the current task's continuation
record; evidence and commands belong here or in the linked detailed reports.

**Latest checkpoint:** usable MKB checkpoint with WASD/E/Q menu controls,
2026-11-06, in the final continuation section. Start there; earlier research
next-work lists are historical.

## Objective and authorization

Implement the supplied opt-in flat mouse/keyboard plan on branch `mkb`, adapted
to **Medal of Honor: Underground SLUS-01270**. The owner approved that title
adaptation and requested a handoff update each turn, followed by continued work.
Work solo. Do not publish/tag releases. Preserve personal saves, active sessions,
ordinary input profiles, generated C and unrelated edits.

## Current state

- Branch `mkb`, original checkpoint `2cbc92a` (research probe and evidence).
  Continuation work below follows that commit; read `git log -1` for current HEAD.
- An experimental normal-build plugin and default-OFF package are implemented
  in the working tree. The playable acceptance checks are still in progress;
  see the latest continuation below. Historical research-only status and
  next-work lists below are superseded by the practical plan.
- The next implementation route is the reduced-scope
  [practical plan](MOUSE_KEYBOARD_PRACTICAL_PLAN.md): native input paths,
  always-on normal crosshair, native sniper scope, and no custom ADS.
- Owner correction: ordinary native R2 aim prevents walking and must NOT be
  entered. Right mouse retains R2 only for scoped rifle ID 5. Crosshair
  visibility is independent of the player's aim state.
- Game baseline `53e4a50071a3c8240a3b0285c4b4342d3a1c4044`, VERSION 0.1.1.
- Framework pin `0e4c7c5fe6c03a46a1fc8a7ae436f6f67e3dc4be` (captured wheel support);
  launcher pin
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

## Continuation — camera basis and native aim-target scoring, 2026-11-06

The owner requested continuation again. Work resumes from checkpoint `8eb8a7c`.
This turn remains Phase 1 research only; no production input path is enabled.

### New evidence and outcome

- The P38 ray producer resolves the camera matrix at input `+0x100`, gathers a
  native collision point, then runs a scene-actor target-scoring loop before it
  caches the ray. The scoring branch is at `8008E06C` (`125E0059`,
  `beq $s2,$fp`). If the score changes, `8008E074..8008E1D0` blends the target
  point before the final `+0x1B0/+0x1B4/+0x1B8` stores.
- Research rows now retain the nine owned-camera view-matrix coefficients,
  camera input origin, camera actor position, native GTE projection values,
  and the aim-target score/baseline. The checker reports the angle between the
  cached shot vector and the inverse camera forward instead of assuming they
  must be identical.
- `8008E7A8` marks the producer after the cached-target stores. The first
  post-write trace shows the scoring loop at `score == baseline` in all seven
  cases, so native aim assist did not select a target in this fixture. The
  earlier assumption that assistance caused the shot-angle discrepancy is not
  supported by this control.
- Added gated P38 firing controls for negative yaw, negative pitch and +64
  pitch. These distinguish fixed geometric bias from nonlinear native scoring
  and test linearity around the checked +32 cases.

Final run: `analysis/runtime/mkb-camera-final-basis-20261106`.
**7/7 cases checked**, ten invalid requests rejected, no dropped rows, one
original ray call per owned update and every shot constructed in its first
observed owned update. P1 body angles and native muzzle origins remain exact.

| Case | Input yaw/pitch | Shot pitch/yaw | Shot delta | Preparation / skip |
| --- | --- | --- | --- | --- |
| baseline | 0/0 | 40/-210 | 0/0 | 0/0 |
| yaw positive | +32/0 | 40/-178 | 0/+32 | 0/0 |
| yaw negative | -32/0 | 40/-247 | 0/-37 | 0/0 |
| pitch positive | 0/+32 | 76/-214 | +36/-4 | 1/1 |
| pitch negative | 0/-32 | 8/-217 | -32/-7 | 1/1 |
| pitch large | 0/+64 | 112/-208 | +68/+2 | 1/1 |

The cached ray target moved with the changed camera view, while the native
target score stayed unchanged. The shot vector is computed from that target
minus the native muzzle, not from the actor angle directly, so a fixed muzzle
offset plus collision-point selection and Q16 target quantization can produce
the measured nonlinear deltas. This control does not yet decompose those
contributions or prove physical impact agreement.

Committed compact evidence is
`docs/controls/MOUSE_KEYBOARD_CAMERA_BASIS_RECEIPT.json`. Current research
source SHA256 is `3c460d438f4abefb37d342d3e7ce9a30e524e72df3ed8948b869647611866b96`;
binary SHA256 is `ab0e4ba4604629903b75025b6cf940910ab3649568dd972fd677c4e8769059da`.
The final raw receipt SHA256 is
`30432d5ce933a796c4565937334ad110844f2fabf1c4be3fc5d3acd962b5072b`.
The compact checked receipt SHA256 is
`958fdeb47945b9082788bdeb78eaa77335857c0e9d062f22aeff661608a082e6`.
The row schema has 64 fields and capacity 128; see the research README.

```powershell
cmake --build build-probe --target psx-runtime -j 2
python tools/probe_mkb_native.py analysis/runtime/mkb-next --slot 0 --fixtures analysis/runtime/mkb-native-analog-20261105/saves/openbios --research --research-direct --research-prepare --gate-fire --research-cases camera_order fire_camera_base fire_camera_yaw fire_camera_yaw_negative fire_camera_pitch fire_camera_pitch_negative fire_camera_pitch_large
python tools/check_mkb_research.py analysis/runtime/mkb-next/receipt.json --out docs/controls/MOUSE_KEYBOARD_CAMERA_BASIS_RECEIPT.json
```

All runs closed normally, left no game process and preserved source saves and
production preferences. No generated game C, production source or pre-existing
framework edit was changed.

### Next work after this checkpoint

1. Measure the actual surface/actor impact and camera projection for these six
   firing cases. Compare the cached collision target, muzzle-to-target ray and
   resulting decal/effect position. Separate collision-point selection from
   Q16 quantization and muzzle parallax; do not call the inactive scoring loop
   the cause without a target-present control.
2. Extend basis evidence to native aim/scoping, recoil, movement and mounted
   constraints, then to other weapon classes. Inspect unhandled angular stores
   such as `8008E4F4` before widening mode support.
3. Finish action mapping, fresh/save/profile checks and cached-native hook
   coverage before production math/lifecycle, input transport, options,
   profiles and launcher controls. Keep every production feature OFF and do not
   advertise mouse support from this diagnostic result.

## Continuation — physical shot endpoints, 2026-11-06

The owner requested continuation again. Work resumes from checkpoint `9e0f72f`.
This turn remains Phase 1 research only; no production input path is enabled.

### New evidence and outcome

- The harness now follows the first P38 object constructed in a firing window.
  It records `80047498` shot-update entries and observes `80077e8c` release
  calls only for that object. The runner releases Cross at the first
  construction, so the longer sixteen-update observation cannot consume a
  second round.
- Release RA `80045df8` identifies the native collision path. At `80045d04`
  that path allocates its impact effect, and at `80045d24` passes the shot's
  `+0x220` position as the effect point. The release row therefore records the
  native collision endpoint before the shot object is freed.
- Release RA `800474e8` identifies lifetime expiry inside the shot updater.
  The checker never reports that endpoint as an impact. This control caught a
  negative-yaw shot that remained in flight for fifteen shot updates and then
  expired rather than colliding.
- The final matrix is `analysis/runtime/mkb-impact-sealed-20261106`:
  **7/7 cases checked**, ten invalid commands rejected, one ammo decrement per
  firing case, no dropped rows and no remaining game process.

| Case | Endpoint | Target residual | Camera / endpoint angle |
| --- | --- | --- | --- |
| baseline | collision | 1.000 world unit | 17.088 / 16.947 units |
| yaw +32 | collision | 2.449 | 16.336 / 16.573 |
| pitch +32 | collision | 5.000 | 16.501 / 16.383 |
| yaw -32 | expired, no impact | 4,942.344 from cached target | 18.907 camera only |
| pitch -32 | collision | 1,349.863 | 20.307 / 20.712 |
| pitch +64 | collision | 4.243 | 9.760 / 9.344 |

Four aligned shots hit within five world units of the cached collision target.
The negative-pitch shot collided with a nearer surface than the cached target,
while its endpoint direction remained close to the camera direction. The
negative-yaw control expired without any impact. This proves physical endpoint
agreement is not equivalent to comparing actor or shot Euler angles, and it
does not yet prove a pixel-space reticle match.

Committed compact evidence is
`docs/controls/MOUSE_KEYBOARD_IMPACT_RECEIPT.json`. Current research source
SHA256 is `c483acd6920ee3f799fc4fe2d5bf81df42c78683991a8f26b565f8322d440ec3`;
binary SHA256 is `44131209dd2511e49b118c4466f9d52fe0eb3d63d4ab5e50e739290a09ae3019`.
The final raw receipt SHA256 is
`e83a30478fc459e3f706678a5401d5868d7dad6b1d5db59121c45e3edd2a5415`.
The compact checked receipt SHA256 is
`863da777bbed41a622a9aa92470d505ca4f05046d16e1f48ab0d1bcd264e8323`.
The row schema has 72 fields and capacity 192; firing windows can request up to
16 owned updates.

```powershell
cmake --build build-probe --target psx-runtime -j 2
python tools/probe_mkb_native.py analysis/runtime/mkb-next --slot 0 --fixtures analysis/runtime/mkb-native-analog-20261105/saves/openbios --research --research-direct --research-prepare --gate-fire --research-cases camera_order fire_camera_base fire_camera_yaw fire_camera_yaw_negative fire_camera_pitch fire_camera_pitch_negative fire_camera_pitch_large
python tools/check_mkb_research.py analysis/runtime/mkb-next/receipt.json --out docs/controls/MOUSE_KEYBOARD_IMPACT_RECEIPT.json
```

All runs closed normally, preserved source saves and production preferences,
and left no game process. No generated game C, production source or pre-existing
framework edit was changed.

### Next work after this checkpoint

1. Add a reticle-pixel comparison using the measured camera matrix and capture
   nonblank frames at the endpoint, rather than extrapolating agreement from
   view angles alone.
2. Trace the native collision query that produces the negative-pitch nearer
   surface. Determine why its endpoint differs from the cached ray target and
   how collider selection, quantized target storage and muzzle parallax
   contribute without changing shot motion.
3. Add a target-present aim-assist control, then repeat scoped, recoil, moving,
   mounted and other weapon/mode cases. Keep the production mouse feature and
   all gameplay writes OFF until those contexts and cached-native hook coverage
   are proven.

## Continuation - pixel-space projection, 2026-11-06

The next checkpoint captures the camera transform that the native ray producer
actually installs. At `8008DAA4` the transform RT/TR values are complete and the
input vector address is formed; `MVMVA` immediately follows. The checker
normalizes the three measured Q12 RT columns and projects world points with
the native `H/OFX/OFY` values. It also captures one `screenshot_hires` frame
when the tracked shot releases, or at the end of the bounded window if release
was observed too late.

The final matrix is `analysis/runtime/mkb-projection-final-20261106`:
**6/6 cases checked**, ten invalid commands rejected, one ammo decrement per
firing case, six nonblank endpoint frames and no remaining game process.
Every screenshot is `2048x960` at scale 4, preserving the native `512x240`
display geometry.

| Case | Endpoint | Projected endpoint | Offset from camera centre | Muzzle parallax |
| --- | --- | --- | --- | --- |
| baseline | collision | 259.24 / 138.10 | 18.39 px | 11.88 px |
| yaw +32 | collision | 257.97 / 138.31 | 18.42 px | 10.79 px |
| pitch +32 | collision | 256.77 / 137.93 | 17.95 px | 13.56 px |
| yaw -32 | expired | 254.25 / 133.34 | 13.46 px | 13.23 px |
| pitch -32 | collision | 255.17 / 135.74 | 15.76 px | 15.31 px |
| pitch +64 | collision | 260.33 / 137.60 | 18.13 px | 15.17 px |

The fired ray target itself projects at `257.03..260.39` x and
`137.94..138.66` y in all six cases, a perpendicular offset of
`18.23..18.91` px from the `256/120` camera projection centre. The fixed
screen-space displacement is therefore measured, not inferred from Euler
angles. Reprojecting each target from the native muzzle origin instead of the
camera origin moves it `10.79..15.31` px, which isolates the origin-parallax
component of the discrepancy.

For the four aligned collisions, the released endpoint projects within
`0.09..0.44` px of the cached target. The negative-pitch case hit a nearer
surface and moves `4.84` px from its cached target. The negative-yaw shot
expired with no impact and is not compared as a hit.

Committed compact evidence is
`docs/controls/MOUSE_KEYBOARD_PROJECTION_RECEIPT.json`. Current research source
SHA256 is `14cf90525a318b66e7a05078923ed97d78bbf8832081290fa6580278d8c3eba3`;
binary SHA256 is `7e88daf3dde589c63f0bbc79d10d393d630a70f114434577239fd9da831863b2`.
The final raw receipt SHA256 is
`241041568b813d4a1b41615fac1f13d84ede579bdfb4bee721bcecda0e02cdfc`.
The compact checked receipt SHA256 is
`4da274f3074d494aa81bed4dcb69cbea07b9c6ea8a6a95b0ce8187db2792e6a6`.

```powershell
cmake --build build-probe --target psx-runtime -j 2
python tools/probe_mkb_native.py analysis/runtime/mkb-next --slot 0 --fixtures analysis/runtime/mkb-native-analog-20261105/saves/openbios --research --research-direct --research-prepare --gate-fire --research-cases fire_camera_base fire_camera_yaw fire_camera_pitch fire_camera_yaw_negative fire_camera_pitch_negative fire_camera_pitch_large
python tools/check_mkb_research.py analysis/runtime/mkb-next/receipt.json --out docs/controls/MOUSE_KEYBOARD_PROJECTION_RECEIPT.json
```

The final matrix run closed normally, preserved source saves and production
preferences, and left no game process. The fixture does not draw a centre
crosshair, so
`OFX/OFY` is used as the native aim axis rather than an image-detected reticle.
No production input path or gameplay write was enabled.

### Next work after this checkpoint

1. Add a target-present aim-assist control and measure whether the projected
   target moves relative to the fixed camera axis.
2. Repeat projection and impact checks for scoped, recoil, moving, mounted and
   other weapon/mode cases. Do not generalize the P38 result.
3. Trace the negative-pitch nearer collision and Q16 target quantization
   separately now that endpoint, target and muzzle-origin pixels are recorded.
4. Finish cached-native lifecycle and action-mapping coverage before any
   production mouse input, options, profiles or launcher work. Keep all
   production features OFF.

## Continuation - experimental native-input implementation, 2026-11-06

The owner's correction is authoritative: do not use ordinary native R2 aiming.
It makes the movement inputs pitch/lean and prevents walking. Sniper weapon ID
5 alone retains native R2. The practical plan now reflects this correction.

### Implemented in the working tree

- `controls/mouse_keyboard/moh_mkb.c`, `moh_mkb_input.c`, `moh_mkb.h` and
  two focused test programs; normal-build CMake integration and an experimental
  `mohu.input.mouse-keyboard` package, default OFF in its manifest.
- Temporary P1 sampling profile, persistent click-to-capture, Escape release,
  and reset on interruptions. Capture-across-transitions is deliberately not
  enabled. Ordinary saved bindings are not overwritten. The current temporary
  profile supplies fixed defaults; editable MKB bindings still need integration.
- One final pad transform preserves incoming sticks. W/S drive LY; A/D drive
  RX. Mouse X drives LX, and mouse Y uses RY. The measured native layout is
  **LX turn, LY walk, RX strafe, RY pitch** (also recorded in HOOKS.md).
  During capture keyboard strafe is supplied via the mouse policy RX output,
  so the generic right-stick takeover gate cannot release capture just because
  A/D is held. No player angle or aim-state writes are made.
- Native input source approach was removed: its source-owned axes discarded
  the virtual host's movement/look. Do not restore it without addressing the
  physical/source merge order. Mouse counts now commit once per guest VBlank;
  repeated sampling does not consume a pulse.
- R2 is released for ordinary weapons in the **final transform**, after
  physical/source buttons are merged. The original source-level OR was an
  active-low release, not an assertion, but could not cancel physical RMB.
- Native crosshair renderer is `8008C124..8008C620`, FNV1a `71C28163`.
  Instruction hook `8008C1B4`, expected word `30420020`, changes only scratch
  `$v0` for its visibility check. Later native flag reads, scope selection,
  crosshair style and drawing remain stock. Guards require the complete
  renderer bytes, owned SP actor/input, unpaused gameplay, active package,
  non-sniper weapon and no active XR or split-screen. `game.toml` lists the
  instruction site for cached-native code. No guest code word is patched.
- Mouse reducer preserves fractional counts, bounds large input, rejects
  non-finite motion, clears on reset, and skips the native 37-count dead zone
  for nonzero pulses. Diagonal keyboard input uses approximately 0.707 per
  axis, rather than the earlier half-strength diagonals. Native turn-rate and
  smoothing remain; raw proportional mouse feel is not yet proven.

### Verification and evidence

Normal SDL3 Release build: `build-mkb-probe/Medal_of_Honor_Underground_Recompiled.exe`.
Current tested SHA256:
`b9e93120eb990e8c8a05790dde192065a347167baa9fbe576def014950678309`.

Four root tests pass: plugin audit, reducer, actual plugin with controlled
host/guest services, and staged mod catalog. The plugin test checks final merged
R2 release, sniper passthrough, supported-mode eligibility, native axis
preservation, correct keyboard axes, simultaneous captured mouse-turn/keyboard
strafe, and reset/teardown.

Four focused existing framework tests rebuilt and passed in
`analysis/mkb-framework-make`: local mouse policy, binding suppression, keyboard
pad chords and external-input ordering. These are deterministic lifecycle tests,
not physical OS capture verification.

Runtime evidence:

- `analysis/runtime/mkb-crosshair-gate-20261106`: original campaign renderer
  bytes read from the compatible research fixture.
- `analysis/runtime/mkb-render-cold-20261106/neutral.png`: inspected native
  red crosshair while player flags remain `0x80000` (aim bit `0x20` clear).
  Its renderer hook executed 77 times during that cold-start check.
- `analysis/runtime/mkb-layout-check-20261106/receipt.json`: all **6/6** final
  host-pipeline gameplay checks pass. Ordinary RMB + forward moves the player,
  aim bit stays clear, final pad R2 is released, LX look changes the actual yaw
  target, P38 fire decrements ammo 8 -> 7, and release leaves ammo at 7. The
  native crosshair hook executed 185 times. No game process remained; source
  saves and ordinary preferences were unchanged.
- The earlier `mkb-gameplay-final-20261106` result used an insufficient actor
  rotation check: RX strafing also changes camera bob. The final check requires
  the yaw target to change and uses the correct LX turn input. Do not cite that
  earlier rotation-only check as mouse-look proof.

Old research save ABI `131107` is incompatible with the normal build ABI `35`.
Do not edit its header. A fresh normal-build fixture was created by cold boot
in `analysis/runtime/mkb-gameplay-20261106/saves/openbios`, slot 0. Its source
PST SHA256 is `a26269c586907de27d0c3514faf997ff79af607741a3be1518516a4d9d599717`.
Copy that fixture for normal-build checks. The failed old-save attempt and the
failed source-axis attempt are retained in analysis for diagnosis.

```powershell
cmake --build build-mkb-probe --target psx-runtime mohu_mkb_input_test mohu_mkb_plugin_test -j 2
ctest --test-dir build-mkb-probe --output-on-failure
cmake --build analysis/mkb-framework-make --target local_mouse_policy_test mouse_binding_suppression_test keyboard_pad_chord_test pad_external_input_test -j 2
ctest --test-dir analysis/mkb-framework-make --output-on-failure -R '^(local_mouse_policy_test|mouse_binding_suppression_test|keyboard_pad_chord_test|pad_external_input_test)$'
python tools/probe_mkb_native.py analysis/runtime/mkb-next --slot 0 --fixtures analysis/runtime/mkb-gameplay-20261106/saves/openbios --gameplay-checks --exe build-mkb-probe/Medal_of_Honor_Underground_Recompiled.exe
```

`probe_mkb_native.py` also accepts `--dump-hud`, `--aim-states`, and `--exe`.
The aim-state movement receipt now uses the immediate aim-forward starting
position instead of an earlier unrelated baseline.

### Next work

1. Physically validate click capture/no acquisition shot, vertical direction,
   simultaneous mouse + WASD, Escape, focus loss, pause and restore in an owned
   disposable window. The headless host-pad check cannot validate OS mouse
   capture or mouse feel. Verify that the VBlank pulse cadence feels acceptable.
2. Obtain a compatible normal-build sniper fixture and verify native scope
   entry/exit and reticle appearance. The old personal sniper slot is ABI
   incompatible; do not alter it. Sniper passthrough currently has deterministic
   plugin coverage, not an in-game scoped screenshot.
3. Verify reload/use, cycle, crouch/jump, menu aliases, held automatic fire,
   feature-OFF behavior, and same-shot impact alignment with the visible reticle.
4. Finish editable bindings through the existing controls store. Fixed temporary
   defaults work without saving over ordinary bindings, but launcher edits do
   not currently change the temporary profile.

The first-playable acceptance checklist is not complete. Keep the package
experimental and default OFF. No commits or publication were made this turn;
generated game C, submodule pins, personal saves and unrelated framework edits
were preserved. Working build's pre-existing local `mods/state.toml` selects
the package for these tests; the packaged manifest remains default OFF.

## Continuation - owner playtest corrections, 2026-11-06

The owner confirmed the existing normal-build save works and then reported
two issues during play: inverted vertical mouse look and abnormally slow
combined forward/back + strafe. Both are corrected in the rebuilt candidate:

- Mouse Y now maps to `128 + signed_pulse` instead of subtracting it. The
  reducer and plugin expectations cover the corrected positive/negative
  direction and clamping.
- Keyboard diagonals now send full native axis values (0/255 on both held
  axes), rather than the previous 38/218 pre-scaling. The native nonlinear
  analog curve made those reduced bytes too slow. Opposing keys still cancel.
  The earlier 0.707 scaling note is superseded; physical diagonal speed/feel
  remains for the owner to confirm.
- The normal Release executable was relinked after the owner explicitly
  approved restarting and loading the existing save. SHA256:
  `858978d5cac50b83d2b46a6c41f7d749c1d4e205b77aa1c5f98aca6cc9ac3d26`.
  All four root CTest checks pass with these corrections.

The game is deliberately LEFT RUNNING for the owner:

- Owned process at launch: PID `18828` (recheck rather than assuming it persists).
- Session directory: `analysis/runtime/mkb-physical-fix-20261106`.
- Copied saves: that directory's `saves/openbios`, slot 0 loaded successfully.
- Session receipt: `session.json`; stdout/stderr are in the same directory.
- Source was `analysis/runtime/mkb-physical-20261106/saves/openbios`; its PST
  and thumbnail hashes still match the compatible fixture recorded above.
- No debug pad/host override remains: real local input owns the controls.

`tools/mkb_live_control.py` now has `start --path <new-directory> --fixtures
<source-directory>` to launch one guarded disposable window, copy the selected
fixture, load it, clear injected input and record launch/save/preference hashes.
Its `snapshot --path <file>` records ammo, pitch/yaw targets, pad and counters.
The `load` action now fully clears injection rather than leaving a neutral host
layer that would mask physical input. Run against only the owned session.

Computer Use was initialized using the bundled computer-use skill. The owner
used physical Escape, and the helper stopped Computer Use; no more UI automation
was attempted afterward. Do not claim completed automated capture/escape tests:
the only observed snapshots had native aim clear, local pad input active and
the native crosshair visible. The owner is now checking the corrected build.

Continue from owner feedback. Preserve this active session until another
restart is authorized or it exits. Sniper scope, complete action mapping,
editable bindings and the remaining acceptance checks above remain pending.

## Continuation - direct mouse look and weapon controls, 2026-11-06

The owner rejected the stick-emulated mouse path as sluggish/laggy and explicitly
requested direct control like VR. That instruction supersedes the practical
plan's earlier no-angle-writes decision. They also requested R reload, mouse
wheel cycling in both directions and number-key quick selection.

### Current implementation

- Mouse events accumulate fractional displacement. The old analog mouse pulse
  reducer, dead-zone skip and VBlank commit are removed. The owned campaign
  camera callback `8004A744` consumes displacement exactly once before native
  camera matrix/ray/player updates. One mouse count = one native angle unit,
  represented in Q16; yaw wraps at 4096 units and pitch retains +/-682 units.
  Positive mouse Y produces negative pitch, preserving the owner's corrected
  normal vertical direction. No delta-time multiplier, stick curve or byte cap.
- Direct writes update owned player pitch/yaw and matching input targets. The
  existing native ray producer still runs. The five previously measured angular
  increment stores are suppressed only for captured, owned, unpaused SP in
  native modes 7/8. At `8008F984`, native pitch centering is prevented from
  pulling the mouse target back. All complete code hashes and ownership guards
  come from the recorded research; no generated C or guest code words changed.
- The measured native mode-7 pitch preparation is moved before the camera
  update when pitch changes; its target delta is carried through the existing
  camera residual and its matching later call is skipped once. Camera position,
  original ray construction, projectile and weapon routines remain native.
- Capture/reset/restore discard pending mouse and weapon requests. Render-only
  passes are excluded. Mouse sampling presents only keyboard strafe through RX;
  mouse look never emits LX/RY stick displacement. Keyboard movement also clears
  keyboard LX turning when uncaptured, so A/D no longer turn as well as strafe.
- R is the primary native Square reload/use binding (E remains an alias).
  Wheel up = previous weapon; wheel down = next weapon, while captured.
  Number keys 1..8 select owned native inventory slots; unowned/out-of-range
  slots are ignored, and held keys do not retrigger.
- Weapon selection calls the original `800891AC` switch routine (11C bytes,
  FNV `5A361CFB`), replacing only its next-slot result at instruction `800891D0`
  (`00408021`) for that owned call. It does not fabricate inventory, ammunition,
  weapon identity or viewmodel state. Native inventory count is `800AB5B4`,
  ownership is reserve != -1, reserve array is input+5E, current slot input+5C.
  Only the measured maximum eight-slot layout is accepted.
- The existing mouse policy gained a captured, eligible, timestamp-checked wheel
  event. Its event struct is unchanged; enum value 5 carries detents in dx/dy.
  SDL normalizes flipped wheel direction. This adds changes in framework
  `local_mouse_policy.h/.cpp`, `local_mouse_sdl.cpp` and its focused test, plus
  the existing dirty `mod_plugins.h`; preserve the unrelated VR edits there.
- Debug builds alone expose `mohu.mkb.test` requests: `motion DX DY`, `select N`,
  `wheel N`, `release`. The debug thread queues atomic requests; the owned game
  update executes them. These bypass OS capture solely for explicit isolated
  tests. Ordinary play and builds without debug tools use actual capture only.

### Validation

Normal SDL3 Release executable SHA256:
`4087e26607cd3152a17f41faf1923c1874dfe251ba93bb4378c6558b3163d396`.

Four root tests and four focused framework tests pass, including direct count
consumption, fractional accumulation, yaw wrap, pitch clamp, native button/axis
preservation, number-key edges, wheel direction/reset and capture gating.

`analysis/runtime/mkb-direct-final-20261106/receipt.json` passes **10/10** runtime
checks on the normal-build fixture: exact +32 yaw, zero drift over 90 VBlanks,
exact +32 pitch, full +200 fast-flick yaw (not capped to a stick byte), exact
return to the starting pose, native fire, native reload, number selection,
previous wheel and next wheel. It changed P38 clip 8 -> 7 -> 8, selected petrol
bomb slot 1, returned to P38 slot 0, then selected slot 1 again. Source fixtures
and ordinary preferences were unchanged; the test exited cleanly with no game
process remaining. `mkb-direct-first-20261106` is the preceding equivalent run.

```powershell
cmake --build build-mkb-probe --target psx-runtime mohu_mkb_input_test mohu_mkb_plugin_test -j 2
ctest --test-dir build-mkb-probe --output-on-failure
cmake --build analysis/mkb-framework-make --target local_mouse_policy_test mouse_binding_suppression_test keyboard_pad_chord_test pad_external_input_test -j 2
ctest --test-dir analysis/mkb-framework-make --output-on-failure -R '^(local_mouse_policy_test|mouse_binding_suppression_test|keyboard_pad_chord_test|pad_external_input_test)$'
python tools/probe_mkb_native.py analysis/runtime/mkb-next-direct --slot 0 --fixtures analysis/runtime/mkb-gameplay-20261106/saves/openbios --direct-checks --exe build-mkb-probe/Medal_of_Honor_Underground_Recompiled.exe
```

These runtime checks exercise the actual direct-angle and native weapon-switch
paths through explicit debug input, not physical wheel/number events or measured
end-to-end latency. Physical feel, sniper scope and broad recoil/impact coverage
remain pending. Keep the feature experimental/default OFF. No commits, releases,
submodule pin changes or edits to personal saves were made. The owner's prior
PID 18828 session had already exited before the builds/tests began.

The tested direct build was then launched for the owner and LEFT RUNNING:
PID `52684` at launch, session directory
`analysis/runtime/mkb-direct-play-20261106`, successful slot-0 load, no injected
pad input. `session.json` records its executable and source-save hashes. Preserve
that session until it exits or the owner authorizes a restart. Recheck the PID
and command line before acting; do not assume the old physical-test PID lives.

## Continuation - petrol-bomb and unwanted-turn regressions, 2026-11-06

The owner reports that direct look is substantially better, though still a bit
laggy. New reports were: petrol-bomb selection stops all mouse look, forward
movement into the brick wall in their new slot 01 turns/moves left, and steep
downward look causes an uncommanded left spin. All three are addressed below.

### Causes and fixes

- Petrol bomb uses native input mode **9**. The direct-look gate accepted only
  7/8, so it discarded all motion for that weapon. Direct look now accepts
  7/8/9, and the same verified native pitch-preparation path is used for mode
  9 as for 7. This was checked with actual petrol-bomb yaw and pitch changes.
- The near-collision/steep-pitch projection fallback has three additional
  angular stores inside the already byte-guarded `8008D81C` routine:
  `8008E4A0` and `8008E4A8` write yaw velocity (`AEC2024C`), while `8008E4F4`
  writes pitch velocity (`AEC20248`). These were absent from the five-hook
  suppression list. They are now registered and listed in `game.toml`, bringing
  coverage to every nonzero angular store in that native routine (eight total).
  Native collision and ray calculation still execute; the unwanted angular
  outputs alone are zeroed during owned captured direct look.
- The plugin regression test checks registration and suppression of all eight
  sites, explicitly covering the three missed ones and rejecting mode 6.

### Reproduction and validation

Source fixtures are in `analysis/runtime/mkb-direct-play-20261106/saves/openbios`.
The owner created slot 01 there for the wall reproduction. Slots 00 and 01 are
preserved byte-for-byte. Before closing the owned session, a separate checkpoint
was saved into unused slot **11** to preserve its current progress. New window
launches now copy all available save slots, not just the selected slot.

Valid before/after evidence:

- `analysis/runtime/mkb-bugs-repro-20261106/receipt.json`: petrol-bomb mode 9
  stayed at exactly the same angles after requested motion; wall walking changed
  direct yaw from Q16 `66387968` to `4325376` with no mouse delta.
- `analysis/runtime/mkb-bugs-verified-20261106/receipt.json`: **7/7 regression
  checks pass**. Petrol-bomb +32 yaw/+16 pitch is exact. The slot-01 wall run
  holds yaw at `66387968` throughout contact and release, with zero angular
  velocity. A -500-unit downward pitch stays exact with zero yaw change and
  no idle drift. Inspected screenshots show the wall straight ahead and the
  downward ground view. Normal native wall sliding is not replaced.
- `analysis/runtime/mkb-direct-post-bugs-20261106/receipt.json`: all previous
  **10/10** direct-look/fire/reload/weapon-selection checks still pass.
- All four root CTest checks pass; Python helper compilation passes.
- Source saves and ordinary preferences remain unchanged; isolated runs exited
  cleanly. Compact evidence is `docs/controls/MOUSE_KEYBOARD_BUGFIX_RECEIPT.json`.

Tested executable SHA256:
`9da20044d14ea7cc29446ca0ced902c37903619007041e69ddef81aebeb6776f`.

```powershell
cmake --build build-mkb-probe --target psx-runtime mohu_mkb_plugin_test -j 2
ctest --test-dir build-mkb-probe --output-on-failure
python tools/probe_mkb_regressions.py analysis/runtime/mkb-next-regression
python tools/probe_mkb_native.py analysis/runtime/mkb-next-direct --slot 0 --fixtures analysis/runtime/mkb-gameplay-20261106/saves/openbios --direct-checks --exe build-mkb-probe/Medal_of_Honor_Underground_Recompiled.exe
```

The new regression runner copies both owner fixtures and verifies that the
debugger listener's actual process ID matches the process it launched before
driving it. The live-session helper uses the same ownership check. Process
enumeration failures now abort rather than pretending no game exists. Use an
approved/escalated execution context for these local-debugger tools when the
sandbox denies socket/process inspection. An initial sandboxed attempt and a
buffered-log ownership check were aborted; neither is valid regression evidence.

Remaining small latency, physical feel after these fixes, scoped sniper and the
rest of the earlier acceptance checklist remain pending. Keep the feature
experimental/default OFF. No generated C, submodule pins or unrelated framework
edits changed, and no commit or release was made this turn.

The verified bugfix build is LEFT RUNNING for the owner at slot **01**:
PID `1128` at launch, directory `analysis/runtime/mkb-bugfix-play-20261106`.
All source save slots (00, 01 and checkpoint 11) were copied and their hashes
recorded in `session.json`; startup verifies debugger ownership against the
launched PID. There is no debug pad override. Preserve this session for the
owner's physical confirmation, and recheck identity before any future restart.

## Continuation - menu controls and committed checkpoint, 2026-11-06

The owner confirms the controls are now very usable and requested WASD in
menus, E = Cross/confirm, Q = Triangle/back, then a commit and push of progress.

- Frontend and native pause menus now map WASD to D-pad directions, with E/Q
  confirm/back. Arrow keys, Enter/Backspace and left-mouse confirm remain.
- A separate temporary menu profile is selected at guest VBlank before physical
  input folding. Q therefore emits Triangle without also emitting gameplay
  Circle. E is Cross in menus and remains native use/reload in gameplay.
- E/Q held across a menu transition are suppressed until release, preventing
  menu confirmation/back from becoming an immediate gameplay action.
- Saved ordinary keyboard/controller profiles remain untouched. Menu tests cover
  frontend/pause context, direction cancellation, correct button words, profile
  switching and held-key transition suppression. Four root and four focused
  framework tests pass. User-facing bindings are in `MOUSE_KEYBOARD.md`.
- The framework wheel support is committed and pushed on the fork's branch
  `mkb/local-mouse-wheel`, commit
  `0e4c7c5fe6c03a46a1fc8a7ae436f6f67e3dc4be`. The game pins this commit, so
  its MKB implementation has a reachable, self-contained framework dependency.
  Only wheel changes were staged in that commit. The four pre-existing VR
  framework edits remain dirty and are intentionally excluded.
- The game checkpoint is on branch `mkb`; use `git log -1` and its remote
  tracking state for the final commit and push status. Commits include the MKB
  plugin/package/tests, input hooks, tools, evidence and documentation. They
  exclude `.commandcode/`, the loose reducer-test EXE, saves and generated C.

Menu-build executable SHA256:
`927033b8d0b36edddc202b61a098fa13d27daf53fecb889bddabc267719bc413`.
The earlier regression receipts identify their own binaries; do not substitute
the menu build hash into older receipts. Final copied-save regression output
is in `analysis/runtime/mkb-menu-regressions-20261106`.

Next priorities after this checkpoint:

1. Verify native sniper scope and capture/focus/pause/restore lifecycle with a
   compatible scoped-rifle fixture, then broader weapons and campaign contexts.
2. Expose mouse sensitivity and editable MKB bindings through the existing
   controls/settings store instead of the fixed temporary defaults.
3. Measure the remaining input-to-render delay and tune sampling/presentation
   based on that evidence; direct look already removes pad acceleration/drift.
4. Finish feature-OFF/controller compatibility and package acceptance checks
   before widening beyond experimental, default-OFF campaign support.

Implementation commit `91582007421b6c0cd9e265546db05680a0e38877` is pushed to
`origin/mkb`; the remote game and framework branch hashes were verified.
The menu build is LEFT RUNNING for the owner at slot 01: PID `10452` at launch,
session `analysis/runtime/mkb-menu-play-20261106`. Slots 00, 01 and checkpoint
11 were copied and startup verified debugger ownership. The four unrelated VR
framework edits remain local; `.commandcode/` and the loose test executable are
also excluded from the commits. Recheck the active session before any restart.
