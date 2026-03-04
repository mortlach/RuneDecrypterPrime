# Sub-Then-Col Flavor

Runner for order `sub_then_col` periodic substitution + transposition benchmarking.

Entrypoint:
- `tools/benchmarks/bench_solve_periodic_columnar_pipeline_sub_then_col.py` (recommended)
- `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`

Example:
- `python tools/benchmarks/bench_solve_periodic_columnar_pipeline_sub_then_col.py`

Campaign integration notes:
- Exposes `configure_campaign_run(...)` for community campaign dispatch.
- Writes outputs under `output/tools/benchmarks/periodic_sub_trans/sub_then_col/...`.

