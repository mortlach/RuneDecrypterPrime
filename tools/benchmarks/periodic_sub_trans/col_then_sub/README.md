# Col-Then-Sub Flavor

Runner for order `col_then_sub` periodic substitution + transposition benchmarking.

Entrypoints:
- `tools/benchmarks/bench_solve_periodic_columnar_pipeline_col_then_sub.py` (recommended)
- `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`

Example:
- `python tools/benchmarks/bench_solve_periodic_columnar_pipeline_col_then_sub.py`

Campaign integration notes:
- Exposes `configure_campaign_run(...)` for community campaign dispatch.
- Writes outputs under `output/tools/benchmarks/periodic_sub_trans/col_then_sub/...`.

