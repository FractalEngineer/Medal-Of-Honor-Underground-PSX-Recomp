# MP all-weapon tracking and SP smoke batch

Date: 2026-10-28. Operator requested this physical checkpoint before further
desktop milestones. All four MP sets and the SP smoke received positive operator
feedback. **Later detailed feedback supersedes blanket acceptance:** grenades
face forward instead of upright, some scales are too large, StG44 retains a hand,
several weapons shoot high and the laser stops in empty space. Tracking/access
worked, but calibration, gun-only masks and aim/laser acceptance remain open.
See [the alpha/calibration study](archive/ALPHA_PLAYABILITY_AND_CALIBRATION.md).

Use **unsandboxed execution in the interactive desktop session** for every
game launch. The first sandbox headset attempt failed OpenXR startup and is
retained as `mp1/headset-sandbox-failed`; it is not headset evidence. The subsequent
unsandboxed MP1 launch loaded slot 1, reported live tracking and fresh submissions,
and advanced 470 VR pairs with zero failures at the sampled checkpoint.

## Prepared session

`analysis/vr-baseline/headset-batch-20261028` contains separate copied save
directories for each case, source hashes, startup receipts and logs. The source
MP saves are root slots 1-4; SP is analysis slot 3. Never swap MP/SP overlays
inside one live process. Close the owned case before starting the next.

Production Release/OpenXR/PGXP, debug tools OFF; binary SHA-256:
`6c39318c2fb27c7574ab90417581beb32a9ff8987c0563a3e6c216f9a063cbf8`.
The runner explicitly uses native `game.toml`, bypassing the general launcher's
interpreter-config auto-selection. All-family calibrated/gun-only/hand-fixed aim
is ON, legacy P38-only aim OFF. MP controller/frustum are ON for MP only.
1080p, world scale 3 / 238.806 units per meter, laser OFF, verification and
capture OFF. No debug TCP or synthetic hands in physical runs.

All five short desktop production startup checks passed: fresh pairs, native
calls, normal exit and unchanged source saves/preferences. These checks do not
exercise all weapon switches or prove physical tracking/impact.

| Case | Native cycle (right B) | Physical status |
| --- | --- | --- |
| mp1 | P38, MP40, StG44, stick grenade | Operator: "Looks good—continue to MP set 2" |
| mp2 | Colt .45, Sten, shotgun, petrol bomb | Operator: "Looks good—continue to MP set 3" |
| mp3 | Silenced pistol, crossbow, scoped rifle, stick grenade | Operator: "Looks good—continue to MP set 4" |
| mp4 | M1 Garand, StG44, Panzerfaust, petrol bomb | Operator: "Looks good—continue to SP smoke" |
| sp | P38 in SP slot 3, including the disappearance scene | Operator: "Looks good" after the laser-enabled restart |

Four MP cycles cover all 13 unique IDs. Use native switching; finite ammo,
throwable depletion and automatic switches still apply. The scoped rifle's
viewmodel is natively hidden while scoped; record that separately from an
unexpected missing model.

MP1 final receipt records 5,160 stereo pairs, unchanged source saves/preferences,
and no forced cleanup. Exit code `3221226505` (`0xC0000409`) means shutdown did
not pass; `transport_passed=false` remains unchanged. Positive operator visual
feedback does not close clean-shutdown or instrumented impact acceptance.
MP2 likewise has positive operator feedback, 3,210 recorded stereo pairs and
unchanged source saves/preferences, but nonzero exit `3489660927` on close.
Its `transport_passed=false` remains a separate shutdown limitation.
MP3 has positive operator feedback, 1,980 recorded stereo pairs and unchanged
source saves/preferences. Window-close returned `3221226505` (`0xC0000409`),
without forced cleanup; clean shutdown remains open.
MP4 has positive operator feedback, 2,190 recorded stereo pairs and unchanged
source saves/preferences. It exited `3221226505` (`0xC0000409`) before the timed
limit without forced cleanup; the cause is not established. All four sets now
have positive visual feedback, covering the 13 unique MP weapon IDs. This does
not establish clean shutdown, a soak pass or instrumented per-ID impact.

SP laser-enabled smoke completed its interval with 4,950 recorded stereo pairs,
zero XR begin/view failures in the final proof, and laser hit/miss activity in
both eyes. Operator feedback was "Looks good" to tracking/fire/reload, flash,
no arms, visibility while walking/turning and performance. No numeric physical
FPS or exact laser/impact alignment is inferred. The final receipt records
unchanged source saves/preferences, no forced cleanup, and exit `3221226505`;
`transport_passed=false` is retained. No game remains running at checkpoint close.

| Weapon ID | Weapon | Operator visual result / set |
| --- | --- | --- |
| 0 | P38 | Looks good / MP1, SP smoke |
| 1 | MP40 | Looks good / MP1 |
| 17 | StG44 | Looks good / MP1 and MP4 |
| 10 | Stick grenade | Looks good / MP1 and MP3 |
| 8 | Colt .45 | Looks good / MP2 |
| 16 | Sten | Looks good / MP2 |
| 4 | Shotgun | Looks good / MP2 |
| 15 | Petrol bomb | Looks good / MP2 and MP4 |
| 9 | Silenced pistol | Looks good / MP3 |
| 14 | Crossbow | Looks good / MP3 |
| 5 | Scoped rifle | Looks good / MP3 |
| 12 | M1 Garand | Looks good / MP4 |
| 13 | Panzerfaust | Looks good / MP4 |

These rows preserve the initial responses, not final calibration acceptance.
They attribute each set-level answer to its designated cycle; they are
operator feedback, not an independently logged per-ID switch or damage trace.
Compact evidence: [headset batch receipt](../../vr/proof/headset-batch-20261028-receipt.json).

## Reproducing a case

Run outside the sandbox, from the repository root:

```powershell
python vr/tools/run_headset_batch.py analysis/vr-baseline/headset-batch-20261028 --case mp2 --seconds 240
```

Then `mp3`, `mp4`, and `sp` (suggest 90 seconds for SP). Each case waits for
headset readiness before its timed interval and requests normal window close
at the end. It records forced cleanup separately if normal shutdown fails.
Existing run directories are never overwritten: prepare a fresh session for
a repeat using `--prepare` and a new path.

Controls: right trigger fires; right A / left X reloads or acts; right B switches;
left stick moves, right stick X turns; left Menu pauses.

The operator additionally requested the laser during SP smoke. The runner now
accepts `--laser`; its separate `sp/headset-laser` directory retains startup and
logs without overwriting the first laser-off smoke. Hold the **right grip/squeeze**
(at least 55%) to show it. This enables the existing diagnostic laser; exact
rendered-barrel/triangle alignment remains deferred in W6.2-W6.3.

For each MP weapon, check grip attachment/scale, independent head and hand motion,
both eyes, complete gun without arms, recoil/reload and flash at barrel. Look at
FOV edges with MP frustum enabled. Fire toward P2 where practical; operator impact
feedback is distinct from instrumented damage evidence. Thrown weapons should
also be checked through hold/release and native switching.

SP smoke: check tracking/fire/reload, no arms, gun visibility while walking and
turning in slot 3, flash and perceived cadence. Record fog symptoms if visible;
the current save does not close R5's missing street/wall reproduction fixture.

W3.5 is reopened by the later specific feedback; the per-ID table above retains
historical initial answers. Full recenter/focus-loss recovery (W3.3), physical
impact (W5.4d/R7), clean exit (S5), broader SP NPC/family validation and measured
performance remain open. Recheck the reported bad profiles and changed paths,
not the full unchanged visual/combat matrix.
