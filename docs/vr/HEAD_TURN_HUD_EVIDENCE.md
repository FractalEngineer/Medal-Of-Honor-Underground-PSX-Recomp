# Head-turn, resolution, and flat-HUD evidence

Date: 2026-10-24

This checkpoint addresses three operator-visible defects in the Underground
diagnostic stereo path:

1. the headset image was rendered from the 240-line native buffer;
2. world geometry disappeared around a 90-degree side look;
3. a flat HUD projection stayed fixed over the rotating world.

The result is headless evidence plus a null-HMD OpenXR integration run. It is
not a physical-headset acceptance claim.

## Resolution

The shared VR launcher previously forced `PSX_INTERNAL_RESOLUTION=native`.
It now defaults to `1080p`, matching the reference game's normal VR profile.
The runtime reports:

```text
psxrecomp: internal resolution 1080p (reference 240 lines): 5x requested
```

`-InternalResolution native` remains available for an A/B control.

## Per-eye world visibility

Underground's level selector at `0x80099960` is a 710-instruction match for the
accepted reference selector. Its visibility tree uses the same short bounds,
leaf count, PVS masks, and three child links. The diagnostic now collects the
complete leaf queue from the actual eye view before writing guest RAM:

- queue capacity: 1000 leaves;
- traversal stack: 256 nodes;
- visit bound: 8192 nodes;
- full function-byte guard before every override;
- malformed tree or overflow falls back to the untouched native selector.

The measured masks, queue, and sentinel are:

| Item | Underground address |
| --- | --- |
| PVS masks | `0x800B7490`, `0x800B7494` |
| Mask bypass | `0x800B7498` |
| Queue count | `0x800B74B4` |
| Queue | `0x800B74B8` |
| Queue sentinel | `0x800C8458` |
| GTE H restore | `0x800A7140` |

At zero and both 90-degree poses, every eye replay used the host selector and
had zero fallbacks. The final side runs each completed 240 pairs with
`frustum=960/960 fallback=0/0`.

## Fixed flat HUD

The fixed overlay was not a second OpenXR layer. It was 2D content inside each
eye image. The renderer found two components:

- HUD text producer `0x8006B64C`, guarded by its 692-byte FNV-1a hash;
- the health/bar/compass packet block and the small gold bar packet.

The text producer is skipped only inside an active stereo eye transaction.
The packet unlink operates on the regenerated OT and removes only the measured
HUD packet block. Both changes are covered by the existing rollback transaction,
so normal play and the native OT are restored after each eye.

This is intentionally a temporary HUD policy: gameplay HUD content is hidden
while stereo is active because the hand/wrist HUD port is not implemented yet.
`-KeepFlatHud` restores the old head-locked HUD for comparison.

## Evidence

The three panels in [head-turn-hud-fix.png](../../vr/proof/head-turn-hud-fix.png)
are left-eye captures at zero yaw, positive 89 degrees, and negative 89 degrees.
The world changes at both sides, no head-locked compass/text/bar remains, and
the pitch and side geometry are still populated.

Final zero-offset control:

| Eye | SHA-256 |
| --- | --- |
| Left | `AEECA835133FAE5DADF3047D28D612AA0258FE087098BEE04EAFB46E3C23735B` |
| Right | `AEECA835133FAE5DADF3047D28D612AA0258FE087098BEE04EAFB46E3C23735B` |

The final null-HMD run reported:

```text
active bindings=17 ... head_frustum=1 openxr=1 flat_hud=1
stereo_proof attempt=30 pairs=30 rendered=1 ... xr_ends=30
frustum=120/120 fallback=0/0 hud_skips=30/30 hud_unlinked=525/525
```

The 1080p capture image size is `2560x1200` per eye. Left/right differences at
the side poses remained large (2,163,070 and 2,714,982 changed pixels), so the
HUD policy did not collapse the two eye images.

## Residual ghost observed after the HUD fix

After the operator tested this checkpoint in the headset, the dominant fixed
HUD ghost was gone. The operator then reported a smaller residual ghost visible
only in the sky. Their description is a headset-indexed flat render of the
whole scene: the stereo world appears to occlude it, leaving it visible only
where the sky is otherwise unobstructed.

This is an operator observation and a working hypothesis, not a confirmed
cause. The next investigation must distinguish at least these cases:

- a stale native/menu OpenXR quad or retained native surface;
- a flat full-scene packet or texture used behind the stereo world;
- a stale eye texture reused by the clear/background path;
- compositor reprojection of an old pair rather than application content.

Useful controls are the submitted OpenXR layer/source counters, a clear-only
frame, an app-layer versus eye-texture comparison, and a distinctive clear
colour to show whether the ghost is behind world geometry. Do not label this as
a native-layer defect or a game-packet defect until one control separates them.

## Remaining limits

- The operator checked the image in the headset, but no instrumented headset
  motion capture or root-cause receipt exists for the residual sky-only ghost.
- The HUD is hidden in stereo until its hand/wrist implementation is ported.
- Additional scenes, pitch/translation sweeps, transitions, and near-wall
  positions still need the same coverage.
- The flat HUD packet addresses are generation-specific and fail closed when
  their guarded function bytes do not match.

## Follow-up: residual sky ghost isolated

The follow-up [SKY_GHOST_EVIDENCE.md](SKY_GHOST_EVIDENCE.md) reproduces the
operator observation in raw eyes and the submitted application layer. A native
OT submission/display tail was still running inside frame replay before the
cleaned per-eye OT was submitted. Skipping that fully guarded tail removes the
flat courtyard behind the rotating world. Re-enabling it in the same executable
restores the defect, with the measured foreground pixels unchanged.

The small gold packet previously called a "bar" is the ammo artwork. Its second
buffer, 40 bytes after the first, was missing from the old rule. Both captured
payloads are now guarded and removed. This follow-up has zero-offset identity,
populated ±90-degree views, rollback checks, and null-HMD application-layer
evidence. Physical-headset confirmation of the follow-up remains pending.
