# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Refined Both-Action Microprobe Plan

Date: 2026-04-24

Status:

- prepared
- blocked on the active refined confirmation microprobe

## Why this note exists

The branch is very likely to need one next step immediately after the active
confirmation microprobe:

- if the refined provisional rule confirms on the second filtered / kept pair
- then the next honest question is no longer whether the rule exists
- it is whether that rule works as a real action contract

This note records that next contract in advance so the repo stays ready to
launch without improvising after the confirmation result arrives.

## Main question

If the refined provisional rule `rank1>=0.30 or best>=0.44` is wired as both
fallback and early stop, does one filtered `1111` lane save real wallclock
while one kept `1111` lane stays no-harm relative to the prior exact replay?

## Mechanism layer

- selection
- stop-discipline
- provisional action contract

## Launch gate

Do not launch this microprobe unless the active confirmation bundle on:

- `7001`
- `7005`

finishes with:

- recommendation:
  - `advance`
- and a shared matching checkpoint before restart `64`

If the confirmation microprobe returns `hold`, this plan stays blocked.

## Pre-run block

Question:

- once the refined provisional rule confirms on the second filtered / kept
  pair, does wiring that rule as a real action contract recover actual
  filtered-lane wallclock without harming the kept lane?

Suspicion:

- filtered `7001` should stop at an early provisional checkpoint and fall back
  to the retained baseline
- kept `7005` should keep running without stop and reproduce the prior exact
  replay read

Main alternative:

- the refined provisional action may still save too little wallclock on the
  filtered lane
- or the kept lane may drift enough that the action contract is not honest yet

If suspicion is true, expect:

- `7001`
  - verdict:
    - `filter`
  - action:
    - fallback and early stop
  - outcome:
    - retained baseline
  - wallclock:
    - materially below the prior exact replay anchor
- `7005`
  - verdict:
    - `keep`
  - action:
    - no stop
  - outcome:
    - no-harm relative to the prior exact replay

If alternative is true, expect:

- `7001` will save only a small wallclock share even with the refined
  provisional rule
- or `7005` will fail the no-harm read

Decision rule:

- advance only if the filtered canary applies the refined both-action contract
  cleanly and the kept canary stays no-harm relative to the prior exact replay
- refine if correctness holds but the filtered lane still saves too little
  wallclock
- hold if either canary fails the first refined action contract

## Why this is the right science-method step after confirmation

This stays narrow:

- do not jump straight to a family microbatch
- do not widen to live runtime
- do not reopen checkpoint refinement if confirmation already passes

The branch order is:

1. confirm the refined provisional rule on a second filtered / kept pair
2. wire that confirmed rule as one action contract
3. test one filtered lane for actual saved wallclock
4. test one kept lane for no-harm
5. only then consider a wider family batch or review

## Canaries

Filtered canary:

- `1111/search7001`
- reason:
  - already the harder filtered lane under the refined rule

Kept canary:

- `1111/search7005`
- reason:
  - already the moderate kept lane rather than the strongest clean kept lane

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

Prepared runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_both_action_microprobe_v1.py`

Underlying exact replay wrapper:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`

Supporting provisional-action plumbing:

- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`

Focused proof:

- `tests/tools/test_no_wli_phasea_checkpoint_refined_both_action_microprobe_v1.py`
- `tests/tools/test_no_wli_artifact_resume.py`
- `tests/tools/test_no_wli_selected_family_low_edge_exact_replay_1111_7004.py`

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

- did `7001` save real wallclock under the refined both-action contract?
- did `7005` stay no-harm relative to the prior exact replay?
- what checkpoint fired the action or keep decision?
- is the next honest move:
  - a wider refined family microbatch
  - or more action refinement
