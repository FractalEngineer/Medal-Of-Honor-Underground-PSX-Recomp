# Underground mouse and keyboard research gate

2026-11-05, Asia/Taipei. Target: **SLUS-01270**, Windows campaign.

**Phase 1 is open. There is no production mouse mod on this branch.** The
attached specification originally targets Medal of Honor SLUS-00974; the owner
approved adapting it to Underground. Reference-game addresses are not valid
Underground addresses. No production hook has been selected or registered.

The continuation results below supersede the initial empty-ring blocker. See
[the handoff](MOUSE_KEYBOARD_HANDOFF.md) for the current continuation state.

## Reproduced native state

`tools/probe_mkb_native.py` cold-boots the owner's disc through the native
menus, or loads a copied, compatible campaign fixture. It explicitly requests
a DualShock for analog controls. The actor and input data below were observed
in the opening campaign street. Heap addresses identify this fixture only.

| Item | Underground observation | Ownership / scope |
| --- | --- | --- |
| SP root | word at `0x800AA17C` | Observed actor `0x800F0BE0`; require aligned RAM pointer and actor word `+8 == 1` |
| Input root | word at actor `+0x39C` | Observed `0x800F0FDC == actor +0x3FC`; re-read after load |
| Player update | `0x800892C8`, size `0xF20` | SHA-256 `6517965996647b2589bf95f282f5c3bd7f1b8c6bf0118b0a3b6495960e16d401`, matches existing engine map |
| Player pitch | actor `+0x23C`, 32 bits | Native integration adds actor `+0x248`; other branches overwrite it from input targets |
| Player yaw | actor `+0x240`, 32 bits | Native integration adds actor `+0x24C`; not a 16-bit Euler array |
| Pitch target candidate | input `+0x184`, 32 bits | Subtracted native look delta is stored here; temporary perturbation changes player pitch |
| Yaw target candidate | input `+0x190`, 32 bits | Native turn delta is accumulated here; temporary perturbation changes player yaw |
| Native look processing | `0x8008EAF0` | Called from player update at `0x80089DE4`; also handles native movement and aim contexts |
| Camera / targeting adjustment candidate | `0x8008D81C` | Called at `0x8008F994` for context values 7/8; produces pitch/yaw angular increments |
| Native orientation integration | `0x80078FBC` | Stores at `0x80079018` / `0x80079034` observed in write trace |
| Shot basis | `0x80076C28` | Reads a **shot object's** orientation, not proof of authoritative player look |

These are research observations, not production guards. No complete ownership,
code-residency, execution-scope and once-per-update contract is established for
a proposed input injection site.

## Instruction evidence

Small instruction anchors come from resident memory and the runtime disassembler.
The complete local dumps remain ignored under `analysis/runtime/mkb-*`.

| Address | Word | Observed operation / implication |
| --- | --- | --- |
| `0x800892EC` | `0x8E30039C` | Load player input from actor `+0x39C` |
| `0x80089DE4` | `0x0C023ABC` | Call `0x8008EAF0`, after earlier weapon/action handling in this function |
| `0x8008F468` | `0xAE020190` | Store native yaw target at input `+0x190` |
| `0x8008F8F0` | `0x3C0302AA` | Construct upper pitch clamp `0x02AA0000` |
| `0x8008F90C` | `0x3C03FD56` | Construct lower pitch clamp `0xFD560000` |
| `0x8008F928` | `0xAE020184` | Store clamped pitch target at input `+0x184` |
| `0x8008F994` | `0x0C023607` | Call adjustment function `0x8008D81C` |
| `0x8008F9AC` | `0xAE82023C` | Alternate branch copies input pitch to actor pitch |
| `0x8008F9B8` | `0xAE820240` | Alternate branch copies input yaw to actor yaw |
| `0x80079018` | `0xAE02023C` | Store integrated actor pitch |
| `0x80079034` | `0xAE020240` | Store integrated actor yaw |
| `0x80076C90` | `0x8602023E` | Read high half of shot pitch for basis construction |
| `0x80076C9C` | `0x86020242` | Read high half of shot yaw for basis construction |

The stores, high-half angle reads and 4096-unit angular differences support
Q16 storage with 4096 angle units per revolution. The observed pitch-branch
limits are +/-682 native units, approximately +/-59.94 degrees. Full rotation,
all native control modes and mounted constraints remain unverified.

## Temporary perturbation result

The opt-in research command changes one byte of an already traced input angle
in a copied-save process. It does not install a mouse policy or change code.
Changing one byte avoids a partially written four-byte target between debugger
requests. The host pad stays neutral during the perturbation.

| Experiment | Input target change | Settled actor result |
| --- | --- | --- |
| Yaw | `257047552 -> 259144704`, exactly +32 native units | `255197184 -> 256966656`, +27 native units; pitch also changes |
| Pitch | `3916800 -> 6013952`, exactly +32 native units | `3956736 -> 6021120`, +31.5 native units; yaw also changes |

Both the normal configuration and requested interpreter diagnostic controls
reproduced the settled values. Backend coverage was not established by the
empty entry rings. Samples are successive live reads, not atomic per-update snapshots.
The experiment establishes that these targets affect orientation. It does
**not** establish exact proportional mouse look, instantaneous response, shot
impact alignment, or the cause of all cross-axis changes.

## Native action mapping

Existing Underground evidence in `../vr/MOVEMENT_EVIDENCE.md` and
`../vr/FLAT_LOCAL_INPUT.md` documents Cross=fire, Square=reload/action,
Circle=cycle, Triangle=jump, L2=crouch, R2=aim/look, Start=pause, with
Cross/ Triangle as menu confirm/back. Native LX turns, LY moves, RX strafes
and RY looks vertically in the measured analog layout.

This session independently exercised both LX and RY signs and Cross firing.
It did not revalidate every action in a fresh and existing-save control
scheme. The existing evidence is not a completed Phase 1 action matrix.

## Exact unresolved gate

1. Identify the adjustment/centering/aim-assist branches and a correction that
   removes pad smoothing from mouse input while retaining native recoil and
   spread. The target-only experiment above fails the proportionality gate.
2. Prove an injection boundary after native look resolution and before the
   movement, shot and camera consumers. `0x8008F984` is a research candidate,
   not an approved production address. Player-update entry alone is insufficient.
3. Establish a simulation-update token independent of render/VBlank counters,
   including actor ownership, repeated entries, restores and replay exclusion.
4. Measure actual player-shot direction and impacts, mounted constraints,
   native aim state, full yaw wrap and all supported action contexts.

The existing dispatch and function-entry debug rings returned no internal
player entries in these attempts, including the documented interpreter
override. Zero trace rows cannot establish call ordering. The probe records
`call_order_verified = false` for that condition. Further work needs a working
instruction/entry observation path at these boundaries (or Ghidra plus live
per-update instrumentation); do not replace missing evidence with a guessed
token or renderer hook.

Per the supplied plan's Phase 1 exit rule, subsequent package, framework,
binding-profile and GUI phases have not been started. The requested feature
is unfinished.

## Continuation: ordered observations and angular control

The empty function-entry rings did not mean the player callbacks were absent.
The probe executable reported **zero cached-native overlay calls**. Internal
dirty-RAM calls bypass those rings; the existing `xprobe_watch` recorder does
observe their JAL/JALR transfers. In the opening street it establishes this
order (actual guest cycles, not timing inferred from host reads):

1. `0x800784D4` calls the owned player's `0x800892C8` callback, RA `0x800784DC`.
2. The callback processes weapon/actions, then calls look processing at
   `0x80089DE4 -> 0x8008EAF0`.
3. `0x8008F984` follows native look resolution; `0x8008F994` calls the
   adjustment function; `0x8008F9BC` follows that call.
4. `0x80078624 -> 0x80078FBC` integrates the owned player's movement/angles.
5. `0x800786E0 -> 0x80076C28` rebuilds the actor basis.

A dedicated `MOHU_MKB_RESEARCH` build now observes those sites within a bounded
owned player-update window. It records CPU/data on the emulation thread,
publishes completed observations to the debug thread, and pages small replies
through the existing mod command interface. The package is a development-only
fixture, not the production mouse package. Disabled builds do not link it.
Guest writes require explicit research commands; no mouse policy is installed.

The observed update-entry sequence is a useful ownership token candidate:
increment on the validated `0x800892C8` call for P1 with RA `0x800784DC`, then
consume at a later validated boundary only once for that sequence. The final
production design still needs execution-scope/replay/restore eligibility and
cached-native coverage. A host frame counter is not used as the token.

Two experiments distinguish angular response from native firing geometry:

- Bypassing the adjustment call through the existing direct-target branch at
  `0x8008F988` produces exact body angle changes, **but leaves the cached native
  firing ray stale**. This experiment is rejected and is absent from the final
  harness implementation.
- Suppressing only the adjustment function's angular output preserves its ray
  calculation. In the current harness the guarded stores at `0x8008D8C8`,
  `0x8008D8F4`, `0x8008E7A8` write pitch increments (`0xAEC20248`), and
  `0x8008D910`, `0x8008E660` write yaw increments (`0xAEC2024C`). Their source
  register `$v0` is set to zero only for the owned P1/default mode 7/8 in the
  explicit research mode. Original instructions still execute; guest code is
  not patched. The complete input/layout and SP update hash checks remain.

The six +32-unit pitch/yaw experiments (at update entry, after native input,
and after adjustment) all retain **exactly +32 requested units, zero cross-axis
motion**, after 120 host VBlanks. The read-only control remains unchanged.
Each one-update observation contains exactly one owned entry and one injection;
four-update firing controls contain four distinct owned update sequences.

The correction-only experiment still does not close the shot gate. P38 shots
use `0x8004815C`, which copies the origin from input `+0x1A4/+0x1A8/+0x1AC`
and aims toward input `+0x1B0` through native `0x80047DF0`. This is a cached
native ray, so a same-update player-angle change need not reach that shot.
The measured baseline shot yaw was -210; a settled +32 player-yaw change moved
it to -182 (+28), while an immediate shot still used -210. Preserve these
negative controls: do not claim exact shot alignment from exact actor fields.
The next tracing target is the producer, timing, quantization and possible
aim assistance of that cached ray, plus preservation of its origin/spread.

The experimental nullable target argument at `0x80047FE8` was not used by the
P38 path in this fixture. It does not establish an aim-assist toggle; that
ineffective experiment was removed from the final harness.

A write trace independently identified the ray producers in `0x8008D81C`:
target writes at `0x8008E1E0/+0x1B0`, `0x8008E1F0/+0x1B4`,
`0x8008E200/+0x1B8`; origin writes at `0x8008E540/+0x1A4`,
`0x8008E544/+0x1A8`, `0x8008E548/+0x1AC`. Local receipt:
`analysis/runtime/mkb-ray-writers-20261105/aim_ray_writes.json`.
The settled shot's 28-unit change might include native ray quantization,
parallax or assistance. This session does not distinguish those causes.

The compact, mechanically checked observations are in
[MOUSE_KEYBOARD_RESEARCH_RECEIPT.json](MOUSE_KEYBOARD_RESEARCH_RECEIPT.json).
They verify the ten bounded research cases, not actual mouse event delivery,
impact alignment, recoil parity, mounted constraints or campaign completion.

## Continuation: camera ownership and same-update firing

The latest camera experiment retains original ray and projectile call order.
An earlier experiment moving the ray calculation was unnecessary and removed.
The current candidate boundary is the owned camera callback, immediately before
the next P1 update. These are measured SLUS-01270 campaign facts, not copied
SLUS-00974 addresses.

| Site / field | Guard and evidence | Ordering / use |
| --- | --- | --- |
| Camera root `800AA160` | Aligned valid actor, class 2, input = actor+3FC, callback at +380 = `8004A744`; input+0C handle index <512 resolves through `800AA1A0` to P1 | Camera belongs to the campaign player; fixture actor `800F2180` |
| Camera update `8004A744` | 1E8 bytes, FNV A707D113; a0 = owned camera, RA `800784DC` | Approximately 19,042 guest cycles before the next P1 callback in the four-update observation |
| Camera preparation `8008AD04` | 130 bytes, FNV C1B54110; P1/input/camera-input arguments; normal call `8008F9C0`, RA `8008F9C8` in mode 7 | Reads input pitch high half at +186, uses native sin/cos, writes camera input +28; normally after the ray call |
| Camera input +1C / +28 | Native smoothing in `80049FCC`; shift at `8004A010`; world-Q16 camera target component | Experimental early preparation carries only the queued pitch target delta into +1C, retaining the previous smoothing residual; later matching preparation call skipped once |
| Camera input +100 | Native matrix stores `8004C3C4` and following, in `8004C2BC`, called by `8004C50C` | Read by original ray producer; neither matrix nor world camera position is replaced by the harness |
| Ray producer `8008D81C` | 1058 bytes, FNV 787AC4B0, P1/input arguments, RA `8008F99C` | One original call after look resolution and before adjustment-end observation |
| P38 cached-ray consumer `8004815C` | DC bytes, FNV 073B3393; a0=P1, a1=shot class 13F6, RA `800482CC` | Call instruction `800482C4` in caller `80048288`; observed AFTER P1 integration/basis, before owned shot basis |
| Native sampled buttons `800A04B4/BC` | Reader `800834FC`, 6C bytes, FNV 141AED00 | Low 16 bits change 0000 -> 0040 for debug Cross, previous remains 0000. Upper bits are FFFF even when neutral. Research scheduling waits for this native sample |

Camera observations carry the upcoming owned P1 sequence. The native fire gate
eliminates the ambiguity of separate debugger arm/fire commands landing in
adjacent updates. It is a research-only neutral-to-Cross control and must not be
used as production live-input eligibility.

With direct angular control and early camera pitch preparation, the checked
four-case gated run recorded baseline shot pitch/yaw 40/-210, +32 yaw shot
40/-178, and +32 pitch shot 76/-214. Each shot was constructed in the first
owned update of its window; body changes remained exactly +32 on the requested
axis. Every shot's world position exactly equalled the native cached ray origin.
Pitch's +36 shot change and -4 yaw change still require explanation and impact
validation. `80047DF0` derives the angles from cached target minus native origin
using native atan/sqrt helpers; this geometric path was retained. Do not infer
an aim-assist toggle or exact impact alignment from these fields.

The constructor/basis trace clarifies the earlier description of weapon/action
processing: the P1 callback queues actions before look resolution, but this P38
fixture's actual cached-ray consumption happens after the original ray update.
Moving the whole ray producer is therefore not required for this measured path.
Other weapons and native aim modes still need their own ordering evidence.

## Continuation: post-write ray and target-score control

The 2026-11-06 basis run adds two observations inside the original ray producer:

| Site / field | Evidence |
| --- | --- |
| `8008E06C` | `125E0059` (`beq $s2,$fp`), actor target-scoring branch. A score different from the baseline takes the native blend at `8008E074..8008E1D0` |
| `8008E7A8` | `AEC20248`; the guarded pitch-increment store also serves as the post-cache marker. Its cached target fields are current, unlike a `RAY` entry observation from the same update |
| Camera input `+100` | 9 signed Q12 coefficients used by the native view/ray calculation |
| Camera input origin / actor `+220` | Kept separately because the ray producer loads the actor position, while the input origin is a distinct camera-space source |

The no-target score stayed equal to its baseline in baseline, +/-yaw and
+/-pitch/+64 firing cases. This rules out the scoring blend as the cause of the
measured shot-angle deltas in this fixture; target-present aim-assist behavior
remains untested.

| Input | Player result | Shot result |
| --- | --- | --- |
| yaw +32 | exact +32 | yaw +32, pitch unchanged |
| yaw -32 | exact -32 | yaw -37, pitch unchanged |
| pitch +32 | exact +32 | pitch +36, yaw -4 |
| pitch -32 | exact -32 | pitch -32, yaw -7 |
| pitch +64 | exact +64 | pitch +68, yaw +2 |

Every shot used the first owned update and its native muzzle origin. The
remaining differences arise after the camera/view and native target point are
formed; colliding-target selection, fixed muzzle parallax and Q16 target
quantization are candidate contributors, not yet separated. Actual impact and
visible camera-projection agreement remain open.

## Continuation: native physical endpoints

The 2026-11-06 impact matrix follows the first P38 object past its cached-ray
construction. The read-only hooks are:

| Site / function | Guard and observation |
| --- | --- |
| `80047498` shot update | Exact prologue, caller RA `800784dc`, live shot type `13F6`, first construction pointer only; records `+0x220` position and native flags |
| `80077e8c` release | The released pointer must equal the tracked shot and still carry type `13F6`; records the pre-release position and caller RA |
| `80045df0 -> 80045df8` | Collision-path release. The same path allocates an impact effect at `80045d04` and supplies shot `+0x220` as the effect point at `80045d24` |
| `800474e0 -> 800474e8` | Shot lifetime-expiry release. It is not an impact and the checker classifies it separately |

The final checked run recorded one round per firing case and one release for the
tracked shot. Baseline, +32 yaw, +32/-32/+64 pitch cases followed the collision
path. Their endpoints were respectively 1.000, 2.449, 5.000, 1,349.863 and
4.243 world units from the cached collision target. The four aligned cases were
within 5 world units; negative pitch hit a nearer surface while retaining a
20.712-unit endpoint angle versus a 20.307-unit camera angle.

The -32 yaw shot did not hit within the bounded window. It remained active for
15 update entries and released through `800474e8`; its final point was 4,942.344
world units from the cached target. It is recorded as expired, never as an
impact. These results show that actual surface agreement must be tested
separately from the shot Euler angles and from the cached target. Pixel-space
reticle projection, target-present aim assist, scoped/recoil/mounted contexts
and other weapon families remain open.
