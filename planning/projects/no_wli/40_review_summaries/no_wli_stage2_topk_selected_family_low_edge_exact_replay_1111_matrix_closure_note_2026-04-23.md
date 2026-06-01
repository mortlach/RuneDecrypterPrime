# Stage-2 Topk Selected-Family Low-Edge Exact Replay Matrix Closure Note: 1111 Family

Date: 2026-04-23

Status:

- closed
- refine
- mixed exact-family result

## Scope

This note closes the bounded exact-replay family matrix for the narrowed
upstream selector:

- family view:
  - `prefix_hamming_le_24`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`

Matrix bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/`

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1.py`

Log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_2026-04-23.log`

This closes the unconditioned exact-replay family question on fixed
`1111/search7001-7005`.

It does not prove that every upstream representative-selection idea is false.

## Why this study existed

The first exact execution gate on fixed `1111/search7004` closed negative.

That left one honest family-level question:

- was `7004` just a local negative lane
- or does the saved handoff gain collapse consistently across the fixed `1111`
  family?

The science-method role here was:

- stay on the same mechanism layer:
  - `selection`
- avoid a new live runtime family
- collect one bounded exact-family read before deciding whether the selector
  line should:
  - close
  - refine
  - or earn anything larger

## Hypothesis block

Question:

- across fixed `1111/search7001-7005`, does
  `selected_family_low_edge_eps_0p016_v1` ever survive exact Stage-3 replay as
  a real improvement, or does the saved handoff gain collapse consistently at
  replay time?

Suspicion:

- `7004` may be only one local negative
- at least one additional `1111` lane may convert the saved handoff gain into a
  real exact replay improvement

Main alternative:

- the selector line is exact-negative enough across the family that it should
  close before any more replay or runtime

Decision rule:

- advance only if the family produces at least two clean wins versus both the
  artifact baseline and the retained Stage-3 reference
- refine only for a mixed family with at least one clean win
- close if the family remains flat or worse overall

## What happened

Runtime:

- started:
  - `2026-04-23T14:39:25Z`
- finished:
  - `2026-04-23T16:31:39Z`
- elapsed:
  - `01:52:14`

Completion evidence:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/matrix_run_state.json`
- fields:
  - `status = "completed"`
  - `completed_jobs = 5`
  - `elapsed = "01:52:14"`
  - `planned_jobs = 5`

Observed warm in-process job range:

- fastest child:
  - `00:21:49`
- slowest child:
  - `00:24:17`

## Cross-checked result

Matrix summary:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/selected_family_low_edge_exact_replay_1111_matrix_summary.json`
- fields:
  - `recommendation.recommendation = "refine"`
  - `recommendation.clean_win_count = 1`
  - `recommendation.baseline_win_count = 2`
  - `recommendation.best_search_seed = 7003`
  - `recommendation.best_delta_vs_baseline = 0.068`
  - `recommendation.best_delta_vs_retained_stage3_reference = 0.153`
  - `recommendation.family_mean_delta_vs_baseline = -0.121`

Per-seed rows:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/selected_family_low_edge_exact_replay_1111_matrix_rows.csv`

Lane read:

- `7003`
  - clean exact win
  - baseline `0.408`
  - retained Stage-3 reference `0.323`
  - replay `0.476`
  - delta vs baseline `+0.068`
  - delta vs retained `+0.153`
- `7005`
  - baseline-only supporting win
  - baseline `0.372`
  - retained Stage-3 reference `0.416`
  - replay `0.413`
  - delta vs baseline `+0.041`
  - delta vs retained `-0.003`
- `7004`
  - slight local loss
  - baseline `0.423`
  - retained Stage-3 reference `0.432`
  - replay `0.420`
  - delta vs baseline `-0.003`
  - delta vs retained `-0.012`
- `7001`
  - severe collapse
  - baseline `0.428`
  - retained Stage-3 reference `0.420`
  - replay `0.161`
  - delta vs baseline `-0.267`
  - delta vs retained `-0.259`
- `7002`
  - severe collapse
  - baseline `0.754`
  - retained Stage-3 reference `0.752`
  - replay `0.310`
  - delta vs baseline `-0.444`
  - delta vs retained `-0.442`

One important structural fact stayed constant across the family:

- `candidate_truth_delta_vs_baseline_row = 0.070`

So the line is not failing because the saved-row swap never happened.

It is failing because the same saved handoff gain produces sharply different
execution outcomes by lane.

## Interpretation

The selector line is now narrower and more informative than the first
`7004` exact negative alone suggested.

What is now true:

- the selector is not uniformly exact-negative across the fixed `1111` family
- one lane is a real clean exact positive:
  - `7003`
- one second lane is at least baseline-positive and almost retained-neutral:
  - `7005`
- but the family is still not solver-usable as a general rule
- the collapses on `7001` and `7002` are too large to ignore
- family mean delta versus baseline remains:
  - `-0.121`

So this is not:

- a promotion result
- a live-runtime authorization
- or a clean family-wide closure

It is a refine result.

## Decision

Decision on the unconditioned exact-replay matrix:

- `refine`

Meaning:

- do not promote the raw selector line to live runtime
- do not describe the selector as uniformly negative anymore
- keep the branch on upstream selection, but move to a cheaper explanatory /
  conditioned refinement step

## Carry-forward lesson

The next honest move should be:

- a conditioned selector postmortem / refinement audit
- focused on what distinguishes:
  - `7003` clean exact win
  - `7005` near win
  - from the `7001` and `7002` collapses

The next honest move should not be:

- another unconditioned replay family by habit
- a live runtime launch
- or a return to generic family-diversity or entry-allocation work
