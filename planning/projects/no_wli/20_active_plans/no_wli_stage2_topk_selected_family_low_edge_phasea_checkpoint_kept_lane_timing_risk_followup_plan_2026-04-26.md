# Stage-2 Selected-Family Phase-A Checkpoint Kept-Lane Timing-Risk Follow-Up Plan

Date: 2026-04-26

Status:

- closed after one throughput-caveat probe
- existing-log audit complete
- one throughput-caveat probe completed
- no matrix approved

Parent branch:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_reconciliation_note_2026-04-26.md`

## Starting Point

The restart32 `phaseA_best_init_match >= 0.3865` checkpoint is now observed
live on both sides of the intended split:

- filtered `7002`:
  - verdict `filter`
  - fallback plus early stop
  - baseline result preserved
  - material runtime saving
  - provenance clean
- kept `7003`:
  - verdict `keep`
  - no action
  - selected path preserved
  - provenance clean
  - wallclock inflated versus retained exact replay

The live-canary branch is closed as:

- semantic pass
- provenance pass
- kept-lane throughput caveat

Live runtime remains blocked generally.

## Question

Why did the kept/no-action `7003` live canary run materially slower than the
retained exact replay reference even though the checkpoint decision was
semantically correct?

## Suspicion

The slowdown is not a checkpoint-contract failure. It is more likely broader
runtime variance or instrumentation/runtime-surface overhead on a no-action
kept lane.

## Main Alternative

The checkpoint/action wiring introduces enough overhead or execution-path drift
on kept lanes that live runtime use is not operationally safe, even when the
semantic decision is correct.

## Mechanism Layer

- timing / runtime instrumentation
- no-action kept-lane overhead

This is not threshold tuning and not selector development.

## Non-Goals

Do not do these in this follow-up:

- do not tune threshold `0.3865`
- do not retune restart count `32`
- do not run another canary first
- do not launch a matrix
- do not reopen live runtime generally
- do not claim production/general policy

## Evidence To Reconcile First

Use existing bundles only:

- retained exact replay `7003`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T152531Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7003_v1/`
- family microbatch kept `7003`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T170754Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_reconciled_v1/`
- live kept `7003`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T014422Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`
- live kept `7003` provenance audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T021629Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1/`

## Minimum Audit Questions

1. Did live kept `7003` slow before, at, or after restart `32`?
2. Did Phase A throughput differ materially from the retained exact replay?
3. Did Phase B throughput differ materially from the retained exact replay?
4. Did Phase C differ materially from the retained exact replay?
5. Does family-microbatch kept `7003` look timing-stable relative to the
   retained reference?
6. Does the kept `7003` slowdown resemble the earlier kept `7004` slowdown or
   a distinct live-wrapper/instrumentation effect?
7. Is there any evidence that the checkpoint/action wiring changed the final
   selected path?

## Decision Rule

Advance only if the existing logs explain the timing caveat well enough to
justify one more explicitly budgeted throughput probe.

Hold if the logs are insufficient or if the timing caveat cannot be localized.

Close if the timing evidence shows kept/no-action wiring is operationally too
unstable for live use.

## Deliverable

Write one throughput-caveat audit note that states:

- what timing layer inflated
- whether the checkpoint contract is implicated
- whether any new runtime is justified
- exact budget and stop condition if a follow-up runtime probe is proposed

## Audit Result

Audit output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T073234Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_audit_v1/`

Review note:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_audit_note_2026-04-26.md`

The existing logs localize the slowdown to the live kept/no-action runtime
surface:

- retained exact replay `7003`: `1314.422s`
- family action replay `7003`: `1323.015s`, ratio `1.007`
- live kept/no-action `7003`: `1851.437s`, ratio `1.409`
- live/family checkpoint32 ratio: `1.409`
- live/reference Phase B step2112 ratio: `1.347`

The checkpoint contract is not implicated semantically, but precise kept-lane
throughput should not be used as a science claim.

## Runtime Approval

One throughput probe is approved:

- run label: `stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_v1`
- fixture/search: fixed `1111/search7003`
- expected lane: `kept_family`
- expected verdict: `keep`
- action contract: no action
- expected wallclock anchor: `1851.437s`
- intended normal completion: under `1h`
- hard cap: `8h`
- stop condition: exactly one run; stop and hold if the cap is reached without
  usable checkpoint evidence or if the bundle is not auditable

No matrix, threshold tuning, selector development, or broad live-runtime
reopening is approved.

## Probe Result

Probe bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T073609Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_v1/`

Probe provenance audit:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T084800Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_provenance_audit_v1/`

Review note:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_review_note_2026-04-26.md`

The probe completed in `01:07:01`, passed the kept/no-action semantic
contract, and passed provenance audit with zero row mismatches. It also
confirmed the throughput caveat:

- repeat versus retained exact replay: `3.059x`
- repeat versus family action replay: `3.039x`
- repeat versus prior live kept/no-action: `2.172x`
- repeat checkpoint32 versus family action replay checkpoint32: `2.702x`
- repeat Phase B step2112 versus retained exact replay: `2.921x`

Close this follow-up as:

- semantic/provenance pass
- valid long-run evidence saved
- kept-lane throughput caveat confirmed
- live runtime still blocked generally
- no further runtime approved from this branch
