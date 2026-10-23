# VR Implementation Root

All VR-specific implementation, tools, tests, and captured-function metadata
live under this directory.

- `underground/` contains Underground-specific mappings and future adapters.
- `preloaded/` contains the opt-in VR diagnostic mod catalog.
- `tools/` contains offline analysis utilities.
- `tests/` contains source-owned tests for those tools.

The current flat `psx-runtime` target does not include these files. Do not add a
VR source to the build until the relevant engine mapping has a fail-closed guard
and the flat launch path has been rechecked.

VR documentation lives under `docs/vr/`, keeping all retained project
documentation in the documentation tree.

Update `docs/vr/HANDOFF.md` before ending every implementation session.
