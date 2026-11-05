# Mouse and keyboard implementation checkpoint

Date: 2026-11-05, Asia/Taipei. Branch: `mkb`.

The initial checkpoint below is historical. Current research continues in
[MOUSE_KEYBOARD_HANDOFF.md](MOUSE_KEYBOARD_HANDOFF.md); the same-date continuation
in [MOUSE_KEYBOARD_HOOKS.md](MOUSE_KEYBOARD_HOOKS.md) resolves the empty-ring issue
and records the direct-angle experiments and remaining cached-shot-ray gate.

**Requested feature is not implemented. Phase 0 baseline work is complete;
Phase 1 has unresolved native aim and update-order requirements.** No mod
package, mouse policy, special binding profile or launcher UI was added.
The attached plan requires stopping at this research gate before proceeding.

## Scope and starting state

The owner explicitly approved adapting the original Medal of Honor plan to
this Underground repository and the USA **SLUS-01270** disc. Its original
SLUS-00974 addresses and reviewed game/framework revisions do not transfer.
The source attachment SHA-256 is
`ff4fd771b52e59eebae7a854538cf66049fe85a19eca7b76a202bea6a6750c8a`.

| Component | Actual starting revision |
| --- | --- |
| Underground | `53e4a50071a3c8240a3b0285c4b4342d3a1c4044`, `master`, VERSION `0.1.1` |
| psxrecomp gitlink and checkout | `e57fd0279b86edf48cfe42364da4388046772bad` |
| recomp-ui gitlink and checkout | `a95615751b413e043983944441ed8912066c65ce` |
| recomp-net nested gitlink | `7a4d330ecf995b881d167234da3c0b01675fd512` |
| retcomm-rbengine nested gitlink | `28a2a472986a7d692d0378a22e756b0936413507` |

`framework_pins.txt` contains an older framework snapshot; gitlinks are
authoritative. Submodules were already initialized and were not updated.
Starting untracked `.commandcode/` was preserved. The framework already had
uncommitted edits in `runtime/include/mod_plugins.h`,
`runtime/src/gpu_gl_renderer.c`, `runtime/src/psx_openxr.c` and
`runtime/tests/test_openxr_input.c`; this task did not change or commit them.
Therefore the baseline executable receipt includes local framework changes
and is not a clean-pin release receipt.

Root `AGENTS_VR.MD` is absent. Framework `AGENTS.md`, `CLAUDE.md`, nearby engine
evidence and relevant build/input interfaces were inspected. The central
`F:/Software/beads/issues` database is unavailable; no substitute was created.
No Ghidra tools are exposed in this session. Native evidence was collected
with the existing TCP debugger, resident bytes and local disassembly.

## Builds and baseline

Both builds use the installed Retcomm Clang 22.1.8 toolchain, bundled Ninja,
SDL3, OpenGL, OpenBIOS, committed generated game C and two build jobs.

```powershell
cmake --build build-release --target psx-runtime -j 2
cmake --build build-probe --target psx-runtime -j 2
```

Both passed. Existing `build-release` remains Release / `PSX_DEBUG_TOOLS=OFF`;
existing `build-probe` remains Release / `PSX_DEBUG_TOOLS=ON`. Both have
`MOHU_VR_DIAGNOSTICS=ON` compiled in, without requesting VR at runtime.
The production catalog verification passed for 13 existing packages.

| Executable | SHA-256 |
| --- | --- |
| Production Release | `dd7e84d8ffbc4f06e30fa93bdbe87e6f18541959a3fb359cb456c1cbf35b0b34` |
| Debug-enabled Release probe | `b6c64dc43af25279f4a15e3b3c56fbe10f1378d4ed6f83d6a5859afef1ea68fe` |

The debug-enabled executable cold-booted the owner's disc through native
menus into the opening campaign street in flat, hidden-OpenGL mode. Its
`baseline.png` was inspected and showed the world, HUD and pistol. No headset
or XR runtime was activated. This is automated flat gameplay observation,
not a physical mouse or production-release playtest.

The old copied campaign slot 3 was refused with
`enhancement_memory_layout_or_execution_profile_or_host_provider`.
No header or identity was modified. A fresh compatible slot 0 was created
through the runtime serializer after cold boot, solely under the probe's own
isolated save directory. Subsequent runs copied that fixture. Each process
quit normally with exit code 0; source saves and production preferences had
unchanged hashes, and no game process remained.

## Existing automated tests

The relevant targets were taken from current repository CMake definitions.
Framework tests were configured in `analysis/mkb-framework-make` with
`MinGW Makefiles`, Release, Clang, system SDL3, OpenBIOS, `BUILD_TESTING=ON`,
`PSX_RECOMP_UI=OFF`, `PSX_OPENXR=OFF`, `PSX_DEBUG_TOOLS=OFF`. Existing fetched
libchdr and libwebp sources from `build-release/_deps` were supplied with
`FETCHCONTENT_SOURCE_DIR_PSX_LIBCHDR` / `FETCHCONTENT_SOURCE_DIR_PSX_LIBWEBP`.
The installed toolchain's `deps` directory was the `CMAKE_PREFIX_PATH`.

The initial standalone Ninja test build was rejected because the framework's
runtime and oracle targets declare `generated/OpenBIOS_full.c` as an output
twice. The independent MinGW Makefiles test configuration built the actual
test targets without changing framework source or generated C.

```powershell
cmake --build analysis/mkb-framework-make --target local_mouse_policy_test pad_external_input_test mouse_binding_suppression_test keyboard_pad_chord_test -j 2
ctest --test-dir analysis/mkb-framework-make --output-on-failure -R '^(local_mouse_policy_test|pad_external_input_test|mouse_binding_suppression_test|keyboard_pad_chord_test)$'
cmake --build analysis/mkb-launcher-tests --target recomp-ui-psx-binds-test -j 2
ctest --test-dir analysis/mkb-launcher-tests --output-on-failure -R '^recomp-ui-psx-binds$'
python -m py_compile tools/probe_mkb_native.py
```

Framework: **4/4 passed**. Launcher: **1/1 passed**. The launcher test used a
separate Ninja/Release configuration with `BUILD_TESTING=ON` and the same
Clang/system-SDL3 toolchain. These are baseline regression tests, not tests
of a new mouse implementation. SDL2, Linux and macOS were not tested.

## Native research reproduction

Requires the existing debug-enabled build, lawful local disc and the existing
Python probe dependencies. Each output directory must be new. The tool refuses
to start while another game is running. It checks SP actor ownership, the
measured input layout and the existing player-update code hash before sampling
or optional target perturbation. It does not install a production input hook.

```powershell
python tools/probe_mkb_native.py analysis/runtime/mkb-new-cold --cold
python tools/probe_mkb_native.py analysis/runtime/mkb-new-targets --slot 0 --fixtures analysis/runtime/mkb-new-cold/saves/openbios --inject
```

`--inject` is explicitly a research option: it changes a small native input
angle in the disposable process and sends a normal Cross press. In the
recorded fixture, the pistol magazine changed from 8 to 7. Bullet impacts and
shot direction were not measured. `--interpreter` requests the documented
diagnostic interpreter controls; empty trace output must never be read as
successful call-order verification.

Local research receipts and data are ignored under:

- `analysis/runtime/mkb-native-cold-20261105`: successful cold gameplay boot.
- `analysis/runtime/mkb-native-analog-20261105`: explicit analog controls and
  compatible serializer-created slot 0.
- `analysis/runtime/mkb-native-input-20261105`: actor/input angle snapshots and
  native-store write traces.
- `analysis/runtime/mkb-native-inject-20261105`: target perturbations and shot
  button/clip observation.
- `analysis/runtime/mkb-native-interp-entry-20261105`: requested interpreter
  control; still no internal player entries in the function-entry ring.
- `analysis/runtime/mkb-final-probe-20261105`: final collector verification with
  actor/input ownership and overlay hash guards enabled. Collection completed;
  native mouse aim and call ordering remained explicitly unverified. Exit 0,
  unchanged source/preference hashes, no remaining process.

The key numeric result and exact instruction anchors are preserved in
[MOUSE_KEYBOARD_HOOKS.md](MOUSE_KEYBOARD_HOOKS.md). No disc, RAM dump, ripped
code, personal save or user preference file is added to Git.

## Remaining release requirements

The initial target-only and empty-ring results above are historical. The
continuations now establish guarded player/camera ownership, actual owned
update sequences, proportional body angles and same-update P38 cached-ray
consumption. The full 19-case camera matrix passes, with ten invalid commands
rejected, one original ray call per update, matching one-time native camera
preparation/skips and exact native cached shot origins. See
[camera receipt](MOUSE_KEYBOARD_CAMERA_RECEIPT.json) and
[handoff](MOUSE_KEYBOARD_HANDOFF.md) for source/binary hashes and reproduction.

Phase 1 remains open. The 2026-11-06 basis matrix added negative and larger
controls: yaw +32/-32 produced shot yaw +32/-37; pitch +32/-32/+64 produced
shot pitch +36/-32/+68 with small yaw coupling. The native scoring branch stayed
at its no-selection baseline in every case, so assistance is not the measured
cause in this fixture.

The impact continuation now measures the first P38 object through release.
Baseline, +32 yaw, +32/-32/+64 pitch followed the collision path and landed
1.000, 2.449, 5.000, 1,349.863 and 4.243 world units from the cached target.
The -32 yaw shot stayed alive for fifteen shot updates and expired without an
impact, so the checker reports no surface endpoint for it. Collision and expiry
are distinguished by release RA `80045df8` versus `800474e8`. The four aligned
collisions were within five world units of the cached target, but the
negative-pitch case hit a nearer surface. See the
[impact receipt](MOUSE_KEYBOARD_IMPACT_RECEIPT.json) and
[camera basis receipt](MOUSE_KEYBOARD_CAMERA_BASIS_RECEIPT.json).

Pixel-space reticle projection, target-present assistance, scoped/recoil/moving
contexts and other weapon families remain unmeasured. Collision-point selection
and Q16 quantization are still not individually separated.

The 2026-11-06 projection continuation closes the basic pixel checkpoint. It
captures the native camera RT/TR immediately before its `MVMVA`, projects the
cached target and released endpoint through native `H/OFX/OFY`, and captures a
nonblank `screenshot_hires` frame at shot release. The six-case matrix produced
one collision endpoint per aligned case except the known negative-yaw expiry.
Every fired target projected `18.23..18.91` pixels from the `512x240` camera
centre. Reprojection from the muzzle revealed `10.79..15.31` pixels of
origin-parallax displacement. Aligned collision endpoints landed within
`0.09..0.44` pixels of the target projection; the negative-pitch nearer
surface differed by `4.84` pixels. See
[MOUSE_KEYBOARD_PROJECTION_RECEIPT.json](MOUSE_KEYBOARD_PROJECTION_RECEIPT.json).

This fixture does not render a centre crosshair, so the comparison uses the
native GTE `OFX/OFY` projection centre as the aim axis. Target-present
assistance, scoped/recoil/moving modes, other weapons and production input
remain open.

Recoil, other weapons/modes, action mapping and cached-native execution also remain unproven.
The production mouse/keyboard feature is not implemented.

After resolving that gate, all package/settings, capture takeover/eligibility,
contextual binding persistence, launcher controls, incompatibility refusal,
lifecycle, weapon/mounted coverage and packaging requirements in the supplied
plan remain. GUI capture, physical mouse capture, netplay/split-screen refusal,
feature-off comparison against a completed mod, VR regressions and packaged
relaunch tests have not been performed. No build was published or tagged.
