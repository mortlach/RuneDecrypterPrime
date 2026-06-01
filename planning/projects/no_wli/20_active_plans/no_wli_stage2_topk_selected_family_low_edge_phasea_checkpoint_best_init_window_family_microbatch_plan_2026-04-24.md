# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Best-Init Window Family Microbatch Plan

Date: 2026-04-24

Status:

- completed

## Why this note exists

The selector checkpoint branch is now narrow enough that one remaining-family
microbatch is the honest next step.

Already closed:

- late live-read correctness:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061044Z__stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1/`
- first late both-action timing canary:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T161225Z__stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1/`
- raw provisional `rank1`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T175849Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1/`
- composite refined checkpoint rule:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T193014Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1/`
- strict restart16 field persistence:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210520Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1/`

Advanced:

- stabilization-window audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210839Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1/`
  - earliest stable window:
    - restart `32`
  - field:
    - `phaseA_best_init_match`
  - threshold midpoint:
    - `0.3865`
- first best-init action canary:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T211444Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1/`
  - filtered `7001` saved real wallclock
  - kept `7005` stayed no-harm

So the remaining question is no longer whether the restart32 best-init rule can
work at all.

It is whether that same action contract generalizes across the remaining fixed
`1111` family lanes.

## Main question

Does the restart32 best-init action contract generalize across the remaining
fixed `1111` family lanes:

- filtered `7002`
- kept `7003`
- kept `7004`

## Mechanism layer

- selection
- stop-discipline
- provisional action contract

## Pre-run block

Question:

- after the first successful hard-pair action canary, does the same restart32
  best-init rule hold on the remaining fixed `1111` family?

Suspicion:

- `7002` should flip to `filter` at restart `32`
- `7002` should fall back to the retained baseline and stop early
- `7003` should flip to `keep` at restart `32`
- `7003` should continue without action and stay no-harm
- `7004` should flip to `keep` at restart `32`
- `7004` should continue without action and stay no-harm

Main alternative:

- at least one remaining lane may fail the restart32 best-init contract
- or filtered `7002` may still save too little wallclock to justify carrying
  the rule forward

If suspicion is true, expect:

- `7002`
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
- `7003`
  - observed gate verdict:
    - `keep`
  - first action checkpoint:
    - restart `32`
  - action:
    - none
  - outcome:
    - no-harm relative to the prior exact replay
- `7004`
  - observed gate verdict:
    - `keep`
  - first action checkpoint:
    - restart `32`
  - action:
    - none
  - outcome:
    - no-harm relative to the prior exact replay

If alternative is true, expect:

- `7002` will save only a small wallclock share even with the restart32 rule
- or one of `7003/7004` will fail the no-harm read

Decision rule:

- advance only if all three remaining lanes match the expected keep/filter split
  at restart `32`, `7002` saves real wallclock, and `7003/7004` stay no-harm
  relative to their prior exact replays
- refine if correctness holds but `7002` saves only a small wallclock share
- hold if any remaining lane fails the current action contract

## Why this is the right science-method step now

This stays narrow and honest:

- do not reopen live runtime yet
- do not widen back to another checkpoint-rule search
- do not assume the first hard pair was enough family evidence

The method step is:

1. keep the provisional rule fixed
2. keep the action contract fixed
3. run the remaining family lanes only
4. decide whether the full fixed `1111` family now supports the contract

## Lanes

Filtered lane:

- `1111/search7002`
- reason:
  - remaining filtered family member under the restart32 best-init split

Kept lanes:

- `1111/search7003`
- `1111/search7004`
- reason:
  - remaining kept family members under the restart32 best-init split

## Runtime budget proof

Completed exact replay anchors from the same current family:

- `7002`
  - `00:22:13`
  - `1333.3s`
- `7003`
  - `00:21:54`
  - `1314.4s`
- `7004`
  - `00:24:17`
  - `1457.4s`

Anchored three-lane total:

- `4105.1s`
- about `01:08:25`

Intended session budget:

- `01:30:00`

Stop condition:

- after each completed lane, recompute the projected three-lane total from:
  - observed completed rows
  - remaining completed-family anchors
- if that projection exceeds `01:30:00`, stop before launching the next lane

This fits well inside the user's current `8h` autonomy window, so it is an
honest autonomous data-taking batch.

## Implementation

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1.py`

Underlying exact replay wrapper:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`

Focused proof:

- `tests/tools/test_no_wli_phasea_checkpoint_best_init_window_family_microbatch_v1.py`
- `tests/tools/test_no_wli_phasea_checkpoint_best_init_window_action_microprobe_v1.py`

## Required outputs

The run must emit:

- one state JSON
- one event log JSONL
- one per-lane rows CSV
- one per-lane rows JSONL
- one summary JSON
- one recommendation JSON
- one short readout

What the readout must answer:

- did filtered `7002` save real wallclock under the restart32 best-init rule?
- did kept `7003` and `7004` stay no-harm relative to their prior exact replays?
- did all three lanes first decide at restart `32`?
- is the selector checkpoint subtopic now complete enough for synthesis / review?

## Completion

Bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T222109Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1/`

Result:

- `advance`

Elapsed:

- `01:09:23`

Per-lane read:

- `7002`
  - observed gate verdict:
    - `filter`
  - action applied:
    - `1`
  - first checkpoint:
    - restart `32`
  - saved attempt seconds:
    - `759.7`
  - saved attempt share:
    - `0.570`
  - landed at retained baseline:
    - `0.754`
- `7003`
  - observed gate verdict:
    - `keep`
  - action applied:
    - `0`
  - first checkpoint:
    - restart `32`
  - delta vs reference exact replay:
    - `0.000`
- `7004`
  - observed gate verdict:
    - `keep`
  - action applied:
    - `0`
  - first checkpoint:
    - restart `32`
  - delta vs reference exact replay:
    - `0.000`
  - elapsed:
    - `00:37:37`

Summary:

- verdict match count:
  - `3 / 3`
- kept no-harm count:
  - `2 / 2`
- family mean delta vs baseline:
  - `+0.0217`
- mean checkpoint share of reference attempts:
  - `0.421`

Operational caveat:

- kept `7004` preserved outcome but inflated elapsed wallclock versus its
  reference exact replay anchor
- so the next honest move is a short timing/postmortem audit before review or
  live-runtime reopening
