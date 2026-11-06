# Build policy

- Use `build-release` for configuring, building, testing and launching this
  repository. Separate work with Git branches, not additional build folders.
- Do not create temporary/research/test build directories, including under
  `analysis`. Diagnostic output and copied saves may live there, but builds do not.
- Preserve personal saves, settings, bindings and user-provided assets when
  cleaning outputs. Check for active game/build processes before replacing them.
- Serialize builds and game runs; use two compile jobs per build.
