# Solve Pipeline Benchmark

Script: `tools/benchmarks/bench_solve_periodic_columnar_pipeline.py`

Purpose:
- Practical staged solving (no cribs) for periodic-columnar.
- Stop early when solved (`match_ratio >= 0.90`) or stalled.
- Keep append-only history.

Stages:
1. `stage1_sub`: periodic substitution solve (char-only scorer).
2. `stage2_col_attempt_*`: columnar solve from top Stage-1 substitution candidates.
3. `stage3_full_refine`: full periodic-columnar Kaeding refine.

Outputs:
- Run folder under `output/tools/benchmarks/*__bench_solve_pipeline__*`
  - `instances.json/csv`
  - `stages.json/csv`
  - `summary.json`
- History append:
  - `tools/benchmarks/solve_proof/proven_solve_pipeline_log.csv`

