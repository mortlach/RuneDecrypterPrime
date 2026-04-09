# Experiment Plan

Input bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T041415Z__score_stop_shadow_v2`

Study seeds:

- discriminators: `1111`, `1311`, `1411`
- reference wins: `411`, `611`, `1011`

Execution stance:

- consume frozen `row_scores.jsonl`, `run_shadow_summary.jsonl`,
  `case_explanations.jsonl`
- optionally read `threshold_matrix_rows.jsonl`
- build one row per `(seed, family)`
- build one digest per seed
- keep deterministic tie-breaks and fixed boundary order

Success condition:

- at least one of `1111`, `1311`, `1411` gets a clearer family-level read than
  the current row-level stop explanation provides

Failure condition:

- family-level winners, agreement, persistence, and trends do not separate the
  accepted miss from the false-fire cases any better than the stop harness
