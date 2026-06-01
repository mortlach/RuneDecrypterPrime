# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Best-Init Window Family Microbatch Closure Note

Date: 2026-04-24

## Outcome

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T222109Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1/`
- result:
  - `advance`
- next branch:
  - `stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_full_family_synthesis`

## Question

After the hard-pair action pass, does the same restart32 best-init contract
generalize across the remaining fixed `1111` family lanes:

- filtered `7002`
- kept `7003`
- kept `7004`

## Read

- filtered `7002`:
  - observed gate verdict:
    - `filter`
  - action applied:
    - `1`
  - first checkpoint:
    - restart `32`
  - elapsed:
    - `00:09:34`
  - saved attempt seconds:
    - `759.7`
  - saved attempt share:
    - `0.570`
  - landed at retained baseline:
    - `0.754`
- kept `7003`:
  - observed gate verdict:
    - `keep`
  - action applied:
    - `0`
  - first checkpoint:
    - restart `32`
  - elapsed:
    - `00:22:03`
  - delta vs reference exact replay:
    - `0.000`
  - final best match:
    - `0.476`
- kept `7004`:
  - observed gate verdict:
    - `keep`
  - action applied:
    - `0`
  - first checkpoint:
    - restart `32`
  - elapsed:
    - `00:37:37`
  - delta vs reference exact replay:
    - `0.000`
  - final best match:
    - `0.420`
- summary:
  - verdict match count:
    - `3 / 3`
  - kept no-harm count:
    - `2 / 2`
  - family mean delta vs baseline:
    - `+0.0217`
  - mean checkpoint share of reference attempts:
    - `0.421`

## What We Learned

- the restart32 best-init contract now matches the full fixed `1111` family
  semantically
- the filtered branch is now a real operational save, not just a descriptive
  audit:
  - `7001`
  - `7002`
- the kept branch now stays no-harm across:
  - `7003`
  - `7004`
  - `7005`
- that means the selector checkpoint subtopic is no longer blocked on family
  generalization

Operational caveat:

- kept `7004` preserved the exact result but ran much longer than its reference
  exact replay
- the next honest branch is therefore a short timing / postmortem audit on the
  `7004` slowdown before:
  - external review
  - or any live runtime reopening

## Integrity Note

- the first live runner summary incorrectly marked the filtered lane as not
  behaving as expected because it only recognized lane role
  `filtered_canary`
- the saved measurement columns were correct, but the saved derived row field
  `action_behaved_as_expected` for `7002` was wrong
- the runner was patched to evaluate `filtered_family` and `kept_family`
  locally
- the final bundle summary, recommendation, and readout were then rewritten
  from the saved rows

## Review Follow-up

- first external review later judged this bundle:
  - not review-ready as packaged
- reason:
  - the original rows / state / final event still say `hold`
  - later regenerated summary / recommendation / readout say `advance`
- current interpretation:
  - the family measurements still appear to support the carried contract
  - but the provenance mismatch must be reconciled before external handoff

## Decision

- keep the family-generalization science provisionally passed
- do not treat this original bundle as evidence-clean external-review material
- keep live runtime blocked while the `7004` runtime anomaly is audited
