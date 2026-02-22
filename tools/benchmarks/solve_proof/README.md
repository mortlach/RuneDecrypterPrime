# Periodic-Columnar Solve Proof

This folder stores shared fixture/profile data and append-only solved history logs
used by periodic substitution + transposition benchmark flavors.

## Goals

- Prove solved capability, not only score improvements.
- Track runtime/work (`seconds`, `evals`) and recovery quality (`match_ratio`).
- Keep history append-only so tuning changes are comparable over time.

## Core files

- `fixtures_periodic_columnar_v1.json`: tier ladder (period/columns/length).
- `solver_profiles_v1.json`: profile presets.
- `proven_solve_log_template.csv`: canonical history schema.
- `solve_status_v1.json`: rolling campaign status.
- `RUN_PLAN.md`: staged run plan notes.

## Flavor-specific history logs

- `proven_solve_pipeline_col_then_sub_log.csv`
- `proven_solve_pipeline_col_then_sub_solved.jsonl`
- `proven_solve_pipeline_sub_then_col_log.csv` (written by sub-then-col runner)
- `proven_solve_pipeline_sub_then_col_solved.jsonl` (written by sub-then-col runner)
- `proven_solve_pipeline_no_wli_log.csv`

## Canonical runners

- `tools/benchmarks/periodic_sub_trans/col_then_sub/bench_solve_periodic_columnar_pipeline_col_then_sub.py`
- `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`

## Autoskip behavior

- Solved-instance autoskip is default for benchmark sweeps.
- To rerun solved rows, edit the runner constants in the corresponding script
  (`FORCE_RERUN_PROVEN` in col-then-sub/no_wli, equivalent constant in sub-then-col).

## Update policy

- Add rows; do not rewrite prior history.
- Keep `fixture_id` stable.
- If fixture logic changes materially, bump version metadata in output rows.
