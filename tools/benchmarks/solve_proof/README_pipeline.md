# Col-Then-Sub Solve Pipeline

Canonical entrypoint:

- `tools/benchmarks/periodic_sub_trans/col_then_sub/bench_solve_periodic_columnar_pipeline_col_then_sub.py`

Implementation module:

- `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`

## Purpose

- Staged solving for periodic-columnar (order `col_then_sub`).
- Stop per instance when solved (`match_ratio >= 0.90`) or stalled.
- Keep append-only solved history.

## Stages

1. `stage1_sub`: periodic substitution candidate search.
2. `stage2_col_attempt_*`: column-tail search (exact for small columns, hybrid for hard columns).
3. `stage3_full_refine`: full periodic-columnar refine.

## Outputs

- Run folder under:
  - `output/tools/benchmarks/periodic_sub_trans/col_then_sub/<timestamp>__bench_solve_col_then_sub_pipeline__<tag>/`
- Key run files:
  - `instances.json`, `instances.csv`
  - `stages.json`, `stages.csv`
  - `summary.json`
  - `final_instances/*.json`
- History append:
  - `tools/benchmarks/solve_proof/proven_solve_pipeline_col_then_sub_log.csv`
  - `tools/benchmarks/solve_proof/proven_solve_pipeline_col_then_sub_solved.jsonl`

## Run controls

Edit constants at the top of
`tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`:

- `PIPELINE_RUN_MODE`
- `FORCE_RERUN_PROVEN`
- `KEY_SEEDS_OVERRIDE`
- `TIERS_REGEX_OVERRIDE`
- `TIERS_PERIOD_SWEEP`
- `TIERS_MIN_COLUMNS`
- `AVOID_REPEAT_FAIL`
- `FAILED_RETRY_SEED_DELTA`
- `STAGE2_HYBRID_SUB_CANDIDATES`
- `STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS`

## Failed-repeat diversification

- Failed repeats for the same fixture/config get deterministic seed offsets.
- Instance notes include:
  - `cfg=<fingerprint>;retry=<n>;soff=<offset>`
