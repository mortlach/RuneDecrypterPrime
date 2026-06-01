# Stage-2 Topk Selected-Family Low-Edge Last-5 Experiments Summary

Date: 2026-04-25

## Scope

This note summarizes the last five experiments on the selector checkpoint
branch, ending with the kept-`7004` timing postmortem audit.

## The last five experiments

### 1. Strict field-persistence audit

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210520Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1/`
- result:
  - `hold`
- what it tested:
  - whether strict restart16 persistence on the provisional checkpoint fields
    was already stable enough to carry a family-wide rule
- what we learned:
  - filtered `7002` was still moving between restart `16` and restart `32`
  - so restart16 was too early to treat as stable

### 2. Stabilization-window audit

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210839Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1/`
- result:
  - `advance`
- what it tested:
  - the earliest checkpoint window where the retained fixed `1111` family
    becomes stable enough for one clean best-init threshold
- what we learned:
  - the first stable separating window is:
    - restart `32`
  - the carried field is:
    - `phaseA_best_init_match`
  - the carried threshold midpoint is:
    - `0.3865`

### 3. Restart32 best-init action microprobe

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T211444Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1/`
- result:
  - `advance`
- what it tested:
  - whether the new restart32 best-init rule works as a real action contract on
    one filtered / one kept pair
- what we learned:
  - filtered `7001` saved real wallclock:
    - saved attempt share:
      - `0.562`
  - kept `7005` stayed no-harm:
    - delta vs prior exact replay:
      - `0.000`

### 4. Remaining-family restart32 best-init microbatch

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T222109Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1/`
- result:
  - `advance`
- what it tested:
  - whether the same contract generalizes across the remaining fixed `1111`
    lanes
- what we learned:
  - verdict match:
    - `3 / 3`
  - filtered `7002` saved real wallclock:
    - saved attempt seconds:
      - `759.7`
    - saved attempt share:
      - `0.570`
  - kept `7003/7004` both stayed no-harm
  - family mean delta vs baseline:
    - `+0.0217`
- caveat it exposed:
  - kept `7004` preserved exact outcome but inflated elapsed wallclock to
    `00:37:37`

### 5. Kept-7004 timing postmortem audit

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T001151Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_v1/`
- result:
  - `advance`
- what it tested:
  - whether the `7004` slowdown was a gate-logic problem or a broader runtime
    anomaly
- what we learned:
  - `7003` stayed timing-stable under the same action wiring
  - `7004` first decided `keep` early at:
    - restart `32`
  - `7004` slowdown was already visible:
    - by restart `64`
    - and deep in Phase B
  - so the `7004` overrun does not read like a gate-logic failure

## Combined read

The last five experiments tell one coherent narrowing story:

- strict restart16 persistence failed honestly
- a later stabilized restart32 window was found
- that restart32 rule then passed:
  - on a hard pair
  - on the remaining family
- the one final kept-lane runtime caveat was then explained well enough to stop
  it from invalidating the contract

## Where we are now

Carried contract:

- restart `32`
- `phaseA_best_init_match >= 0.3865`
- fallback plus early stop on `filter`
- no action on `keep`

Current branch state:

- the selector checkpoint science provisionally survives
- the current review handoff is not review-ready as packaged
- live runtime is still blocked until there is a separate explicit live-canary
  decision

Current blocker:

- the decisive remaining-family microbatch bundle still contains an
  unreconciled provenance/reporting mismatch caused by role-label drift

## Practical takeaway

The branch got better by surviving failures, not by avoiding them.

The two important failures were:

- strict restart16 persistence:
  - too early
- early composite refined rule:
  - not family-stable

The three successful experiments after that were successful because they were
narrower and more honest:

- stabilize later
- prove the action contract on a hard pair
- prove family generalization
- explain the final anomaly before calling the topic complete
