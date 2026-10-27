# 2026-10-27 headset smoke checkpoint

The operator requested documentation and push only. No further implementation,
runtime experiments or headset tests are authorized by this checkpoint.
[Receipt](../../vr/proof/headset-smoke-20261027-receipt.json) records raw evidence
hashes and separates the tested executable from the later build.

Both physical runs used Virtual Desktop XR on the interactive Titan account,
with the committed `29f7157` executable SHA-256
`4204a6f3e2ca2037cfc1e7bc2987399f524e1e12156511eb8501c57d1e3a74d6`.
No full physical acceptance checkbox is closed.

## MP observations and limitations

The 60-second copied slot-1 P38 smoke recorded 59 live/focused/ready hand
samples, 0.4655 m right-hand travel, operator input, 1,131 new XR submissions
and 1,125 new stereo pairs, with zero failed eyes. Verification was OFF
(`verify_checks=0`); this adds no rollback-verification result. Laser was OFF.
The operator said the gun looked okay but reported heavy world culling at the
FOV edges. This is limited feedback, not complete alignment/control acceptance.

The profile enabled SP head frustum handling but omitted the separate
`MOHU_VR_MP_FRUSTUM=1` opt-in. The omission is proven; whether enabling it
removes the physical artifact still needs validation.

The all-family camera observer also required either debug shot recording or
legacy P38 aim. This smoke used all-family aim with legacy P38 aim OFF. The
late companion observer armed `mohu.vr.shot start-p1`, after which 12 recorded
shots all reported aimed/hand-fixed. P2 health had already fallen from fixture
32 to 29 before that observer armed, stayed 29 during observation, and produced
zero linked health writes during those shots. Do not claim these 12 shots
caused the earlier damage or that the whole smoke used working hand-fixed aim.

The child exited with code 1. Its last-run report says `tcp_quit`/`atexit`;
forced cleanup is unknown because the old runner did not record it. The raw
receipt's `complete=true` is superseded by this analysis. Clean shutdown is
unproven; the owned game process was closed.

## SP observations

The second bounded run loaded the isolated SP slot 2 from
`analysis/vr-baseline/saves/openbios`, not root MP slot 2. Its PST SHA-256 is
`2824c5505d9dabf5901fe47a385035d54ac9e87bc79502e8ba2328e88e5e0367`.
Startup was ready, with 27 fresh pairs over the startup interval and zero XR
begin/view failures. One later observation showed 932 submissions / 930 pairs;
these are sample counters, not whole-run totals. Source saves and preferences
were verified unchanged. The bounded launcher finished and owned game closed;
this does not establish clean child shutdown.

Operator feedback:

> yeah looks good there just no weapon control. also poor performance only
> 35fps and something weird with the draw distance/distant fog that seem to be
> indexed to the view; shortest in front of view but turning head to the side
> and looking on the edge of the fov gives you further view distance due to less fog.

SP edge culling looked good. Tracked weapon control is not bound/validated for
this SP fixture; W5.2 remains open. Approximately 35 FPS is the operator's
observation, not an independently captured FPS measurement. The view-dependent
fog/distance issue is unresolved; its producer and depth convention have not
been measured. Do not claim a confirmed cause or tune distance blindly.

## Changes already made before the documentation-only request

The camera predicate now includes `g_weapon_aim`, so refreshing its canonical
camera no longer requires debug recording. The MP probe now sets the MP
frustum opt-in, offers `--hand-fixed`, records the execution account/forced
cleanup, and refuses complete acceptance for nonzero exit or forced cleanup.

Strict C syntax, the active Release build and 11 focused probe unit tests
passed. The rebuilt executable SHA-256 is
`924691b65b561c4aefe0ea135953b3181dc55e8f7f24e0d1112fa19d33808f2c`.
**It has not been runtime/headset retested.** Historical headset receipts retain
their original executable hash. Defaults and framework pins are unchanged.

Current continuation is R4b/R5/R6 in [VR_PLAN.md](VR_PLAN.md), with exact
instructions in [HANDOFF.md](HANDOFF.md). See [SP_PARITY_REPAIR.md](SP_PARITY_REPAIR.md)
for the operator-reopened flash, arms, slot-3 visibility and production performance
findings. W6.2 is deferred behind these SP defects. The unretested-build sentence
above describes the original 2026-10-27 checkpoint, not current runtime status. Do not repeat completed weapon matrices
unless a changed execution path or reproducible regression requires it.
