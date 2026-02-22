# User Docs

This section is the shortest path for running RuneDecrypterPrime without touching internals.

## Start here

1. Install the project: `docs/setup/installation.md`
2. Run first tutorial: `docs/guides/quickstart.md`
3. If something fails: `docs/guides/troubleshooting.md`

## Common workflows

- Tutorials (first run):
  - `python tutorials/v1/Start_Here.py`
- Benchmarks (periodic substitution + transposition):
  - `python tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
  - `python tools/benchmarks/periodic_sub_trans/col_then_sub/bench_solve_periodic_columnar_pipeline_col_then_sub.py`
  - `python tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`

## Where outputs go

- Tutorials: `output/tutorials/...`
- Tests: `output/tests/...`
- Benchmarks: `output/tools/benchmarks/periodic_sub_trans/<flavor>/...`

## Next level docs

- Architecture: `docs/guides/architecture.md`
- Solver details: `docs/guides/solvers.md`
- Scoring details: `docs/guides/scoring_deep.md`
- Benchmarking notes: `docs/howto/benchmarking.md`
