#!/usr/bin/env bash
# Apply the title's upstream-PR-ready psxrecomp changes to the submodule
# working tree.
#
# The framework gitlink stays the authority: no fork, no floating branch. Each
# patch under framework/patches/ is applied once, and a second run is a no-op.
# Once the corresponding psxrecomp PR is merged, delete the patch and bump the
# submodule pointer instead.
#
# Local builds and release CI both run this before configuring.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRAMEWORK="${ROOT}/psxrecomp"
PATCHES="${ROOT}/framework/patches"

if [[ ! -d "${FRAMEWORK}/.git" && ! -f "${FRAMEWORK}/.git" ]]; then
  echo "error: psxrecomp submodule is not checked out; run: git submodule update --init --recursive" >&2
  exit 1
fi
if [[ ! -d "${PATCHES}" ]]; then
  echo "No framework patches to apply."
  exit 0
fi

shopt -s nullglob
for patch in "${PATCHES}"/*.patch; do
  name="$(basename "${patch}")"
  if git -C "${FRAMEWORK}" apply --reverse --check "${patch}" >/dev/null 2>&1; then
    echo "already applied: ${name}"
    continue
  fi
  if ! git -C "${FRAMEWORK}" apply --check "${patch}" >/dev/null 2>&1; then
    echo "error: ${name} does not apply to psxrecomp at $(git -C "${FRAMEWORK}" rev-parse --short HEAD)" >&2
    echo "       rebase framework/patches/ against the submodule gitlink" >&2
    exit 1
  fi
  git -C "${FRAMEWORK}" apply "${patch}"
  echo "applied: ${name}"
done
