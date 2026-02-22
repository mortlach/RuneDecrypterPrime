# Benchmarks Folder

Benchmark runners, fixtures, solve-proof logs, and community harness tools.

## Current benchmark structure

- `tools/benchmarks/periodic_sub_trans/` active periodic substitution + transposition runners.
- `tools/benchmarks/solve_proof/` shared fixture/profile files and append-only solved history.
- `tools/benchmarks/community/` campaign validation/manifest/sharding/aggregation tools.
- `tools/benchmarks/config/` shared benchmark config resources.

## Canonical periodic_sub_trans entrypoints

- `python tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- `python tools/benchmarks/periodic_sub_trans/col_then_sub/bench_solve_periodic_columnar_pipeline_col_then_sub.py`
- `python tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`
