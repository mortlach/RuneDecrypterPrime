# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Refined Confirmation Microprobe Plan

Date: 2026-04-24

Status:

- completed
- hold

## Why this note exists

The checkpoint-refinement audit is now complete:

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T192446Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1/`
- result:
  - `advance`
- selected refined rule:
  - `rank1_ge_0p30_or_best_ge_0p44`
- trusted late-family fit:
  - `5 / 5`
- provisional canary fit on `7002/7003`:
  - shared checkpoint:
    - restart `16`
  - mean checkpoint elapsed share:
    - `0.212`
  - mean share improvement versus late gate:
    - `0.674`

So the next honest question is no longer whether any refined rule exists.

It is whether that refined rule survives a second filtered and kept pair in the
same exact-replay family.

## Main question

Does the refined provisional rule `rank1>=0.30 or best>=0.44` hold on one
second filtered `1111` lane and one second kept `1111` lane before the current
late gate surface?

## Mechanism layer

- selection
- stop-discipline
- checkpoint-surface refinement

## Pre-run block

Question:

- if the refined provisional rule is tested on:
  - filtered `7001`
  - kept `7005`
- does it reproduce the expected split at a shared early checkpoint in the same
  exact-replay family?

Suspicion:

- the refined rule should confirm on:
  - `7001`
  - `7005`
- at the same early restart `16` checkpoint that already worked on:
  - `7002`
  - `7003`

Main alternative:

- the refined rule may overfit the first pair
- or the second filtered / kept pair may only match too late to matter

If suspicion is true, expect:

- `7001`
  - provisional verdict:
    - `filter`
- `7005`
  - provisional verdict:
    - `keep`
- both canaries should match at a shared checkpoint before restart `64`
- timing should still beat the current late gate by a meaningful margin

If alternative is true, expect:

- either `7001` or `7005` will fail the refined rule
- or the first shared matching checkpoint will be too late to support the next
  action branch honestly

Decision rule:

- advance only if both confirmation canaries match the expected verdict at a
  shared checkpoint before restart `64` with materially earlier timing than the
  current late gate
- hold if either lane fails the refined rule on this second pair

## Why this is the right science-method step now

This was still the smallest honest runtime confirmation:

- do not jump straight to a refined action contract
- do not widen to another family batch
- do not reopen the raw provisional branch

The method step is:

- take the offline refined rule
- test it on one new filtered lane
- test it on one new kept lane
- only then decide whether the next branch is a refined action microprobe

## Canaries

Filtered confirmation lane:

- `1111/search7001`
- reason:
  - filtered in the trusted late family
  - harder than `7002` because the late `best_init` stays elevated at `0.378`

Kept confirmation lane:

- `1111/search7005`
- reason:
  - kept in the trusted late family
  - useful moderate positive rather than the strongest clean positive

## Runtime budget proof

Completed exact replay anchors from the same current family:

- `7001`
  - `00:23:41`
  - `1421.2s`
- `7005`
  - `00:24:23`
  - `1462.8s`

Anchored two-canary total:

- `2884.0s`
- about `00:48:04`

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

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1.py`

Underlying exact replay wrapper:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`

Focused proof:

- `tests/tools/test_no_wli_phasea_checkpoint_refined_confirmation_microprobe_v1.py`
- `tests/tools/test_no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1.py`

## Required outputs

The run must emit:

- one state JSON
- one event log JSONL
- one per-checkpoint rows CSV
- one per-checkpoint rows JSONL
- one summary JSON
- one recommendation JSON
- one short readout

What the readout must answer:

- does the refined rule still work on the second filtered / kept pair?
- what is the earliest shared checkpoint?
- what trigger path fired:
  - `rank1_floor`
  - or `high_best_rescue`
- is the next honest move:
  - refined action microprobe
  - or richer checkpoint persistence

## Result

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T193014Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1/`
- recommendation:
  - `hold`
- reason:
  - the refined provisional rule did not reproduce the expected split on both
    confirmation canaries at a shared checkpoint

Per-lane result:

- `7001`
  - matched `filter` at checkpoints:
    - `16 / 32 / 48 / 64`
  - provisional `best_init`:
    - `0.378`
- `7005`
  - misfired as `filter` at checkpoints:
    - `16 / 32 / 48 / 64`
  - expected:
    - `keep`
  - provisional `best_init`:
    - `0.395`

Branch consequence:

- do not reopen the refined action microprobe
- move next to:
  - richer provisional field persistence
  - and a missing-lane provisional completion canary if required
