# Selector Checkpoint Reconciliation Plan

Date: 2026-04-25

Status:

- completed

Completion note:

- closed 2026-04-25 as review-ready after provenance reconciliation
- final handoff archive note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_final_handoff_archive_note_2026-04-25.md`
- final hardened audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T190612Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1/`
- live runtime remains blocked
- production/general policy is not claimed

## Question

After the first external-review pass found a provenance/reporting mismatch in
the decisive remaining-family microbatch bundle, can the selector checkpoint
branch be reconciled into an evidence-clean review handoff without widening the
science question?

## Current branch truth

- the carried checkpoint contract still looks provisionally sound on fixed
  `1111/search7001-7005`
- the current review pack is not review-ready as packaged
- the blocker is not a new empirical contradiction
- the blocker is a provenance/reporting contradiction caused by role-label drift
  in the shared row-builder

## Carried contract under reconciliation

- restart `32`
- field:
  - `phaseA_best_init_match`
- threshold:
  - `0.3865`
- `filter`:
  - fallback plus early stop
- `keep`:
  - no action

## Hypothesis

The shared row-builder misclassified `filtered_family` as a kept-style lane,
which wrote one wrong row-level flag and left the original family-microbatch
run-control artefacts at `hold`. After a shared role-contract fix and focused
regression coverage, a rerun or fully explicit reconciliation should produce:

- rows, state, events, summary, recommendation, and readout that all agree
- the same carried keep/filter split already suggested by the raw measurement
  columns

## Main alternative

Once the shared role-contract bug is fixed, the rerun or reconciled audit may
show that the family branch does not actually pass cleanly, or that a second
evidence mismatch still exists.

## If hypothesis is true, expect

- `7002` remains a successful filtered lane:
  - verdict `filter`
  - action applied `1`
  - current result equals baseline
- `7003/7004` remain successful kept lanes:
  - verdict `keep`
  - action applied `0`
  - current result equals prior selected replay
- the remaining-family bundle recommendation becomes internally consistent
  everywhere

## If alternative is true, expect

- the corrected family bundle still fails internally
- or one lane changes behaviour enough that the carried contract must be
  narrowed further

## Decision rule

Treat the selector checkpoint subtopic as ready for external review only after:

1. the shared role-contract fix is landed
2. focused regression tests pass in the normal repo environment
3. the decisive family bundle is rerun or explicitly reconciled
4. the evidence layers agree:
   - rows
   - state
   - events
   - summary
   - recommendation
   - readout

Otherwise keep review and live runtime blocked.

## Immediate work order

1. Patch the shared role-contract logic.
2. Add focused regression tests for `filtered_family` and `kept_family`.
3. Record the first external-review verdict in the planning surface.
4. Prepare a clean remaining-family rerun.

## Runtime note

- the decisive remaining-family rerun is still a multi-lane exact-replay
  microbatch with a retained anchor of about `01:08:25`
- that exceeds the standing `~1h` self-run limit, so it should be treated as a
  user-launched runtime step after the code/test reconciliation is complete
