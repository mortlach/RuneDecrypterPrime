# Stage-2 Topk Selected-Family Low-Edge Exact Replay Matrix Plan: 1111 Family

Date: 2026-04-23

Status:

- completed
- refine
- mixed exact-family result

## Why this note exists

The first exact execution gate for the narrowed selector is now closed negative
on fixed `1111/search7004`.

That does not yet tell us whether the selector line is:

- uniformly exact-negative across the full `1111` family
- or mixed, with real wins on some exact lanes and a local loss on `7004`

The next honest data-taking step is therefore still execution-facing, but not a
new live runtime family.

It is a bounded exact-replay family matrix.

## Main question

Across fixed `1111/search7001-7005`, does
`selected_family_low_edge_eps_0p016_v1` ever survive exact Stage-3 replay as a
real improvement, or does the saved handoff gain collapse consistently across
the family?

## Mechanism layer

- selection

## Pre-run block

Question:

- once the concrete selector is applied across the fixed `1111` family, does
  any exact replay beat both the artifact baseline and the retained Stage-3
  reference?

Suspicion:

- `7004` may be only one local negative
- other `1111` lanes may still convert the saved handoff gain into a real exact
  replay improvement

Main alternative:

- the saved handoff gain collapses consistently across the `1111` family
- the selector line should close before any second replay family or live
  runtime

If suspicion is true, expect:

- at least one additional exact replay beats both the artifact baseline and the
  retained Stage-3 reference
- the family-level read stays mixed or positive enough to justify a narrower
  follow-up rather than closure

If alternative is true, expect:

- no clean wins versus both floors
- or a family mean delta versus artifact baseline that stays non-positive

Tomorrow's decision rule:

- advance only if the family produces at least two clean wins versus both the
  artifact baseline and retained Stage-3 reference
- refine only for a mixed family with at least one clean win
- close if the family remains flat or worse overall

## Why this is the right step now

The current branch discipline is:

- do not launch a second live runtime by inertia
- do not widen back to generic family-diversity or entry-allocation work
- use the already-anchored exact replay family to decide whether the selector
  deserves any more runtime at all

This matrix was still data-taking, but it was cheaper and more interpretable
than starting a new live runtime class.

## Runtime budget proof

Current anchored exact replay family:

- completed canary:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
- elapsed:
  - `01:07:53`

Planned job order:

1. `1111/search7004`
2. `1111/search7001`
3. `1111/search7003`
4. `1111/search7005`
5. `1111/search7002`

Budget read:

- anchored per-job estimate:
  - about `1.13h`
- anchored serial estimate for five jobs:
  - about `5.66h`
- intended session budget:
  - `8.0h`

This is therefore an honest serial microbatch on current evidence.

## Stop condition

This run must stop if either of these becomes true:

- total elapsed already exceeds the written `8h` session budget
- after any completed job, the observed projected serial total exceeds `8h`

If that happens:

- stop before launching another cell
- keep the partial family matrix as a valid rescued coverage read

## What happened

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/`

Completion log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_2026-04-23.log`

Observed runtime:

- `5 / 5` jobs completed
- total elapsed:
  - `01:52:14`
- observed warm in-process job range:
  - `00:21:49`
  - to `00:24:17`

## Outcome

Recommendation:

- `refine`

Cross-checked summary:

- `selected_family_low_edge_exact_replay_1111_matrix_summary.json`
- fields:
  - `clean_win_count = 1`
  - `baseline_win_count = 2`
  - `best_search_seed = 7003`
  - `best_delta_vs_baseline = 0.068`
  - `best_delta_vs_retained_stage3_reference = 0.153`
  - `family_mean_delta_vs_baseline = -0.121`

Per-seed read:

- `7003`
  - clean exact win
- `7005`
  - baseline-positive near win
- `7004`
  - slight local loss
- `7001`
  - severe collapse
- `7002`
  - severe collapse

Branch read:

- the selector is not uniformly exact-negative across the fixed `1111` family
- the selector is also not stable enough to promote as a live runtime rule
- the next honest move is a conditioned selector postmortem / refinement audit
  before any live runtime

## Runtime shape

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1.py`

Historical exact per-cell runner reused inside the matrix:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`

Logging:

- repo-native progress in Python
- matrix run state and run events under the matrix output dir
- child per-cell exact replay bundles under the normal analysis output root

## Required outputs

This matrix must emit:

- one machine-readable per-cell table
- one machine-readable matrix summary
- one short human readout
- one explicit advance / refine / close recommendation
- partial coverage state if the batch stops before full completion
