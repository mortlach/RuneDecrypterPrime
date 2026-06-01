# Stage35 Rank6 Local-Rescue Policy Sketch - 2026-04-30

Status: offline sketch only.

This note records the first predeclared candidate shape after the rank-6
selected-start safety check. It is not a promoted policy and it is not a runtime
launch authorization.

## Source Evidence

- shallow frontier harvest:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/`
- deepening harvest:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T155324Z__stage35_guard_selector_frontier_deepening_harvest_v1/`
- shallow-plus-deepening join:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/`
- selected-start gate safety check:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T014439Z__stage35_rank6_selected_start_gate_safety_v1/`

## Prediction Ledger

These predictions are for calibration/comparison, not blame assignment.

- real late local-rescue phenomenon:
  - `75-85%`
- narrow rank/slice policy improves selected cases:
  - `50-65%`
- general production policy from current signal:
  - `25-40%`
- exact `0.437` threshold survives as-is:
  - `15-25%`

When this analysis branch closes, explicitly compare the final outcome against
this ledger in chat.

## Hard Gate Result

Posthoc hard gate:

- rank `6`
- `selected_start_match_ratio >= 0.437`

Observed dedup result:

- kept deep rows:
  - `6`
- kept better/worse versus shallow:
  - `6 / 0`
- rejected better/worse versus shallow:
  - `4 / 2`
- observed rank-6 deepening regressions removed:
  - `2 / 2`

Read:

- useful safety separator
- too lossy as-is
- rejects real positives, including `1111/search7002 rank 6`

## Softened Candidate Rule

Candidate rule for offline design only:

- candidate rank is `6`
- and either:
  - `selected_start_match_ratio >= 0.437`
  - or `shallow_resume_minus_selected >= 0.400`

Observed dedup result on rank-6 joined rows:

- kept rows:
  - `7`
- kept better/worse versus shallow:
  - `7 / 0`
- mean deep minus shallow:
  - `+0.010143`
- rejected rows:
  - `5`
- rejected better/worse versus shallow:
  - `3 / 2`

What this buys:

- keeps the hard-gate safety behavior on the observed deepening regressions
- recovers the largest rejected positive:
  - `1111/search7002 rank 6 74dfe3cb559629f7`
  - deep-shallow `+0.015`
  - deep-selected `+0.465`

What it still loses:

- rejects three observed deepening positives:
  - `1411/search7005 rank 6`
  - `611/search7003 rank 6`
  - `1411/search7004 rank 6`

## Non-Recommended Variant

The more permissive sketch:

- `selected_start_match_ratio >= 0.437`
- or `shallow_resume_minus_selected >= 0.400`
- or `shallow_resume_best_match_ratio < 0.420`

keeps `9` rows with `9 / 0` better/worse in this tiny dedup set, but the
low-shallow-resume clause is too visibly posthoc and does not yet have a clear
mechanism explanation. Do not use it as the next canary rule.

## Current Decision

- do not launch runtime now
- do not canary the hard `0.437` gate as-is
- carry the softened two-clause rule as the next offline design hypothesis
- before any runtime, write the candidate as a fixed rule and define a tiny
  canary with:
  - one expected hard-gate keep
  - one expected shallow-delta keep
  - one observed regression reject
  - one rejected-positive audit/control cell

## Current Recommendation

The next useful step is a no-runtime candidate-canary design note. It should
choose exact cells, budget, stop conditions, and success/failure rules. Runtime
should not start until that design is explicit.
