#!/bin/sh
# Flat launcher for the Linux release.
#
# Extracts beside the game executable, so keep it in the release root. The
# Linux build is flat-only; clear any VR variables a shell may have exported
# so this launch cannot accidentally take the OpenXR path.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

for name in $(env | sed -n 's/^\(MOHU_VR_[A-Za-z0-9_]*\)=.*/\1/p'); do
    unset "$name"
done
for name in $(env | sed -n 's/^\(PSX_VR_[A-Za-z0-9_]*\)=.*/\1/p'); do
    unset "$name"
done
for name in $(env | sed -n 's/^\(PSX_OPENXR[A-Za-z0-9_]*\)=.*/\1/p'); do
    unset "$name"
done
unset XR_RUNTIME_JSON 2>/dev/null || true
PSX_DEV_INPUT=0
export PSX_DEV_INPUT

cd "$here"
exec "$here/Medal_of_Honor_Underground_Recompiled" \
    --game "$here/game.toml" \
    --memcard-dir "$here/saves" \
    --no-launcher \
    "$@"
