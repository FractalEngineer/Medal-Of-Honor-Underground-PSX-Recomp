#!/usr/bin/env bash
# Thin wrapper around the shared psxrecomp bundled-release packager.
# Autofilled by tools/new_project_layout/setup_project.{sh,ps1}.
#
# Ships the COMPILED game built from this repo's committed generated/ C:
# executable, runtime data, bundled OpenBIOS, mod catalog, overlay toolchain.
# No sources, emitters, CLI, generated C, or BIOS dumps.
#
# Usage:
#   scripts/package_release.sh <build-dir> <artifact-tag> [recompiler-build-dir]
#
# Writes: dist/mohu-<VERSION>-<artifact-tag>.zip
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="${1:-}"
ARTIFACT_TAG="${2:-}"
RECOMPILER_BUILD="${3:-build-recompiler}"

if [[ -z "${BUILD_DIR}" || -z "${ARTIFACT_TAG}" ]]; then
  echo "usage: $0 <build-dir> <artifact-tag> [recompiler-build-dir]" >&2
  exit 2
fi

PACKAGER="${ROOT}/psxrecomp/tools/package_game_release.sh"
if [[ ! -f "${PACKAGER}" ]]; then
  echo "error: missing ${PACKAGER} (psxrecomp submodule predates bundled releases -- bump it)" >&2
  exit 1
fi
chmod +x "${PACKAGER}" 2>/dev/null || true

EXTRA=()
# Overlay shard cache. It is compiled FROM THE DISC, so CI (no disc) cannot
# build one: the committed static AOT shard is linked into the executable and
# the bundled overlay_toolchain/ compiles the rest from the player's disc at
# runtime. A developer packaging locally with a cache can ship it instead:
#   PSX_OVERLAY_CACHE_ROOT=/path/to/cache scripts/package_release.sh ...
if [[ -n "${PSX_OVERLAY_CACHE_ROOT:-}" ]]; then
  EXTRA+=(--overlay-cache-root "${PSX_OVERLAY_CACHE_ROOT}")
else
  EXTRA+=(--ship-without-overlay-cache-because \
    "no disc at package time: the committed static AOT shard is compiled in and overlay_toolchain/ autocompiles the rest on the player's machine")
fi
# Extra player documents and launch scripts shipped in the archive root.
# Platform launchers are kept to their own archive: .bat/.ps1 on Windows,
# run-flat.sh on Linux. Release notes follow RELEASE_VERSION (or VERSION).
VERSION_FOR_DOCS="${RELEASE_VERSION:-$(tr -d '[:space:]' < "${ROOT}/VERSION" 2>/dev/null || true)}"
VERSION_FOR_DOCS="${VERSION_FOR_DOCS#v}"
DOCS=(DISC.md ALPHA_README.md recomplauncher.json docs/controls/MOUSE_KEYBOARD.md)
if [[ "${ARTIFACT_TAG}" == linux-* ]]; then
  DOCS+=(scripts/linux-release/run-flat.sh)
else
  DOCS+=(scripts/windows-release/Launch.ps1 scripts/windows-release/RunFlat.bat \
    scripts/windows-release/RunVR-VDXR.bat scripts/windows-release/RunVR-SteamVR.bat \
    scripts/windows-release/RunVR-Oculus.bat)
fi
if [[ -n "${VERSION_FOR_DOCS}" && -f "${ROOT}/docs/release/v${VERSION_FOR_DOCS}.md" ]]; then
  DOCS+=("docs/release/v${VERSION_FOR_DOCS}.md")
fi
for _doc in "${DOCS[@]}"; do
  if [[ -f "${ROOT}/${_doc}" ]]; then
    EXTRA+=(--doc "${_doc}")
  fi
done
# The achievements SDK is linked into the game; ship its license with the
# other third-party notices.
if [[ -f "${ROOT}/licenses/rl-achievements-LICENSE" ]]; then
  EXTRA+=(--runtime-file licenses/rl-achievements-LICENSE)
fi

# Linux launchers are tar archives; Windows keeps the zip.
ARCHIVE_ARGS=()
case "${ARTIFACT_TAG}" in
  linux-*) ARCHIVE_ARGS+=(--archive tar.gz) ;;
esac

cd "${ROOT}"
exec bash "${PACKAGER}" \
  --root "${ROOT}" \
  --build-dir "${BUILD_DIR}" \
  --artifact "${ARTIFACT_TAG}" \
  --zip-prefix mohu \
  --exe-name Medal_of_Honor_Underground_Recompiled \
  --display-name "Medal of Honor Underground Recompiled" \
  --recompiler-build "${RECOMPILER_BUILD}" \
  --version-env RELEASE_VERSION \
  --disc-hint "your legally owned Medal of Honor Underground disc" \
  "${ARCHIVE_ARGS[@]}" \
  "${EXTRA[@]}"
