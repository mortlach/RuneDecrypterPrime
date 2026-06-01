# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Subtopic Synthesis Note

Date: 2026-04-25

## Scope

This note closes the selector checkpoint subtopic for the narrowed upstream
selector:

- family view:
  - `prefix_hamming_le_24`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`

## Final carried claim

The selector checkpoint line is now scientifically coherent enough to carry
forward under reconciliation, but it is not review-ready as packaged.

Carried contract:

- checkpoint window:
  - restart `32`
- field:
  - `phaseA_best_init_match`
- threshold:
  - `0.3865`
- action mode:
  - fallback plus early stop on `filter`
  - no action on `keep`

## Why this line existed

The raw selector was mixed on the fixed `1111` family:

- clean exact win:
  - `7003`
- baseline-positive near win:
  - `7005`
- slight loss:
  - `7004`
- severe collapses:
  - `7001`
  - `7002`

So the question became whether an earlier conditioned checkpoint gate could keep
the viable lanes and filter the collapses.

## Main branch sequence

1. Late live-read correctness passed.
   - usable snapshot on `5 / 5`
   - keep:
     - `7003`
     - `7004`
     - `7005`
   - filter:
     - `7001`
     - `7002`
2. The first explicit both-action canary failed on timing.
   - blocker:
     - timing
   - not:
     - action choice
3. Raw provisional `rank1` closed.
   - too weak
4. Composite refined rule closed.
   - `rank1>=0.30 or best>=0.44`
   - failed kept `7005`
5. Strict restart16 persistence closed.
   - `7002` still moving
6. Stabilization-window audit advanced.
   - restart `32`
   - `phaseA_best_init_match >= 0.3865`
7. Hard-pair action canary advanced.
   - filtered `7001` saved wallclock
   - kept `7005` stayed no-harm
8. Remaining-family microbatch advanced.
   - filtered `7002` saved wallclock
   - kept `7003/7004` stayed no-harm
9. Timing postmortem audit advanced.
   - `7004` slowdown reads as broad throughput loss, not gate-logic failure

## Final family read

Filtered lanes:

- `7001`
- `7002`

Kept lanes:

- `7003`
- `7004`
- `7005`

Operational read:

- filtered lanes save real wallclock
- kept lanes preserve exact outcome
- the only remaining caveat was kept `7004` wallclock inflation
- the postmortem audit localizes that as broad throughput loss rather than a
  checkpoint-contract bug

## What is now justified

- one narrow carried claim under reconciliation:
  - the restart32 best-init checkpoint appears to reproduce the intended fixed
    `1111` keep/filter split
- code/test reconciliation on the shared role-contract path
- one clean remaining-family rerun or equally explicit provenance
  reconciliation

## What is still not justified

- external review on the current package
- automatic live-runtime reopening
- treating the checkpoint rule as already production-promoted
- treating one kept-lane timing anomaly as fully solved at the runtime-policy
  level

## Closing read

This subtopic no longer needs another replay-family study.

If work continues now, it should move to one explicit next decision:

- reconcile and rerun the decisive family bundle
- then rebuild the review handoff
- only after that, decide whether external review or one narrow live canary is
  the next honest step
