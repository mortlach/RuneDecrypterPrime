# Selector Checkpoint External Review First-Pass Note

Date: 2026-04-25

## Verdict

- review result:
  - `not review-ready as packaged`
- scientific status:
  - provisionally survives
- live runtime status:
  - still blocked

## Main finding

The decisive remaining-family microbatch bundle is not evidence-clean.

The review found:

- the raw measurement columns for filtered `7002` support the intended
  checkpoint behaviour
- but the original derived row/control artefacts still record:
  - `action_behaved_as_expected = 0`
  - run recommendation `hold`
- later regenerated summary/readout artefacts reinterpret the same measurements
  as:
  - `advance`

So the blocker is:

- provenance / reporting contradiction

not:

- a new empirical contradiction in the checkpoint science

## Likely cause

The shared row-builder only recognized lane role `filtered_canary`, while the
remaining-family microbatch introduced:

- `filtered_family`
- `kept_family`

That role-label drift caused the filtered family lane to be judged with
kept-style logic in the original row/control layer.

## Carried claim that still survives

On the fixed `1111/search7001-7005` replay family, the restart32
`phaseA_best_init_match >= 0.3865` checkpoint still appears to reproduce the
intended keep/filter split:

- filtered lanes:
  - `7001`
  - `7002`
  - fall back to baseline with material wallclock saving
- kept lanes:
  - `7003`
  - `7004`
  - `7005`
  - preserve their prior exact replay outcomes

## Decision

- do not widen the science branch
- do not reopen live runtime
- fix the shared role-contract bug
- add regression coverage
- rerun or explicitly reconcile the decisive family bundle
- rebuild the review pack only after the evidence layers agree
