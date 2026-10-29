# VR Implementation Root

All VR-specific implementation, tools, tests, and captured-function metadata
live under this directory.

- `underground/` contains the active Underground-specific mappings/adapters.
- `preloaded/` contains the opt-in VR diagnostic mod catalog.
- `tools/` contains offline utilities and owned diagnostic probes.
- `tests/` contains source-owned tests for those tools.

The local `build-release` includes the guarded VR plugin and serves both normal
Flat and VR launchers. Flat mode clears VR activation flags. Do not create a
second maintained flat executable/build or place diagnostic executables beside
the playable one.

Personal saves live only in root `saves/`. Automated tools copy frozen sources
from `analysis/fixtures/sp` or `analysis/fixtures/mp` into unique test outputs;
they must not select personal saves implicitly. Every actual game launch is
outside the sandbox, one game at a time.

VR documentation lives under `docs/vr/`, keeping all retained project
documentation in the documentation tree.

Read `docs/vr/WORKSPACE_LAYOUT.md` and update `docs/vr/HANDOFF.md` before ending
every implementation session. Superseded task queues are in `docs/vr/archive`.
