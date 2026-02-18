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

Hardcoded run controls (edit at top of
`tools/benchmarks/bench_solve_periodic_columnar_pipeline.py`):
- `FORCE_RERUN_PROVEN`: rerun fixtures even if proven solved.
- `KEY_SEEDS_OVERRIDE`: override key seeds list (`None` keeps profile defaults).
- `TIERS_REGEX_OVERRIDE`: run only tiers whose `tier.name` matches (`None` disables).
- `AVOID_REPEAT_FAIL`: if enabled, failed repeats with the same
  fixture/text/key seed/config fingerprint are auto-diversified.
- `FAILED_RETRY_SEED_DELTA`: retry step for diversification.
- `STAGE2_HYBRID_SUB_CANDIDATES` / `STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS`:
  cap how many Stage-1 substitution candidates enter expensive Stage-2 hybrid column search
  (important for `c>=10` runtime).

Failed-repeat diversification:
- The benchmark keeps the same synthetic fixture key seed, but shifts search randomness
  by a deterministic seed offset on repeated failed attempts.
- Per-instance history `notes` now includes `cfg=<fingerprint>;retry=<n>;soff=<offset>`.
