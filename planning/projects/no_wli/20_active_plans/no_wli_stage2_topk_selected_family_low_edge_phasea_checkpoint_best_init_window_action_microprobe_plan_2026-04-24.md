# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Best-Init Window Action Microprobe Plan

Date: 2026-04-24

Status:

- completed
- advance

## Why this note exists

The checkpoint field-persistence branch is now materially resolved:

- strict persistence audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210520Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1/`
  - result:
    - `hold`
  - reason:
    - filtered `7002` was still moving at restart `16`
- stabilization-window audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210839Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1/`
  - result:
    - `advance`
  - selected field:
    - `phaseA_best_init_match`
  - earliest stable separating window:
    - restart `32`
  - filtered max:
    - `0.378`
  - kept min:
    - `0.395`
  - threshold midpoint:
    - `0.3865`

So the next honest question is no longer what checkpoint surface to trust.

It is whether that simpler restart-32 best-init rule works as a real action
contract.

## Main question

If the retained `1111` family stabilizes at restart `32` on
`phaseA_best_init_match >= 0.3865`, does wiring that rule as both fallback and
early stop save real wallclock on filtered `7001` while keeping `7005`
no-harm relative to its prior exact replay?

## Mechanism layer

- selection
- stop-discipline
- provisional action contract

## Pre-run block

Question:

- once the checkpoint signal is simplified to:
  - restart `32`
  - `phaseA_best_init_match >= 0.3865`
- does that rule save real time on one hard filtered lane without harming one
  hard kept lane?

Suspicion:

- `7001` should defer at restart `16`
- `7001` should flip to `filter` at restart `32`
- `7001` should fall back to the retained baseline and stop early
- `7005` should defer at restart `16`
- `7005` should flip to `keep` at restart `32`
- `7005` should continue without action and stay no-harm

Main alternative:

- even the restart-32 best-init window may still save too little wallclock on
  the filtered lane
- or the kept lane may drift enough that the simpler action contract is not
  honest yet

If suspicion is true, expect:

- `7001`
  - observed gate verdict:
    - `filter`
  - first action checkpoint:
    - restart `32`
  - action:
    - fallback and early stop
  - outcome:
    - retained baseline
  - wallclock:
    - materially below the prior exact replay
- `7005`
  - observed gate verdict:
    - `keep`
  - first decision checkpoint:
    - restart `32`
  - action:
    - none
  - outcome:
    - no-harm relative to the prior exact replay

If alternative is true, expect:

- `7001` will save only a small wallclock share even with the restart-32 rule
- or `7005` will fail the no-harm read

Decision rule:

- advance only if filtered `7001` applies the restart-32 best-init contract
  cleanly and kept `7005` stays no-harm relative to the prior exact replay
- refine if correctness holds but the filtered lane still saves too little
  wallclock
- hold if either canary fails the first best-init window action contract

## Why this is the right science-method step now

This stays narrow and honest:

- do not widen to a family microbatch yet
- do not reopen live runtime
- do not keep auditing checkpoint fields after the rule is already concrete

The method step is:

1. take the simplified provisional rule
2. wire it as one action contract
3. test one hard filtered lane
4. test one hard kept lane
5. only then consider widening or review

## Canaries

Filtered canary:

- `1111/search7001`
- reason:
  - hardest filtered lane under the stabilized best-init split
  - filtered max:
    - `0.378`

Kept canary:

- `1111/search7005`
- reason:
  - weakest kept lane under the stabilized best-init split
  - kept min:
    - `0.395`

## Runtime budget proof

Completed exact replay anchors from the same current family:

- `7001`
  - `00:22:43`
  - `1362.7s`
- `7005`
  - `00:22:37`
  - `1357.1s`

Anchored two-canary total:

- `2719.9s`
- about `00:45:20`

Intended session budget:

- `01:00:00`

Stop condition:

- after the first completed canary, recompute the projected two-canary total
  from:
  - the observed completed row
  - the remaining completed-family anchor
- if that projection exceeds `01:00:00`, stop before launching the second
  canary

## Implementation

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1.py`

Underlying exact replay wrapper:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`

Focused proof:

- `tests/tools/test_no_wli_phasea_checkpoint_best_init_window_action_microprobe_v1.py`
- `tests/tools/test_no_wli_phasea_checkpoint_refined_both_action_microprobe_v1.py`
- `tests/tools/test_no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1.py`

## Required outputs

The run must emit:

- one state JSON
- one event log JSONL
- one per-canary rows CSV
- one per-canary rows JSONL
- one summary JSON
- one recommendation JSON
- one short readout

What the readout must answer:

- did `7001` save real wallclock under the restart-32 best-init contract?
- did `7005` stay no-harm relative to the prior exact replay?
- did both canaries first decide at restart `32`?
- is the next honest move:
  - a wider best-init family microbatch
  - or more action refinement

## Result

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T211444Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1/`
- recommendation:
  - `advance`
- reason:
  - the restart-32 best-init contract behaved correctly on the filtered and
    kept canaries, and the filtered lane saved material wallclock

Key read:

- `7001`
  - checkpoint:
    - restart `32`
  - verdict:
    - `filter`
  - action applied:
    - `1`
  - saved attempt share:
    - `0.562`
- `7005`
  - checkpoint:
    - restart `32`
  - verdict:
    - `keep`
  - action applied:
    - `0`
  - delta vs prior exact replay:
    - `0.000`

Branch consequence:

- the next honest move is a wider best-init window family microbatch
