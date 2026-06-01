# Legacy col-then-sub reference map — 2026-04-09

Status: active
Work status: done
Project: benchmark_campaign_v1_1

This note records the preserved older benchmark-only col-then-sub seed/solve
cluster.

## Preserved source files

- `planning/old/v1OLD/README.txt`
- `planning/old/v1OLD/tools/benchmarks/seed_utils_periodic_columnar_col_then_sub.py`
- `planning/old/v1OLD/tools/benchmarks/bench_solve_periodic_columnar_pipeline_col_then_sub.py`
- `planning/old/v1OLD/tests/utils/test_seed_utils_periodic_columnar_col_then_sub_bench.py`

## Why they are worth keeping

### A. Legacy cluster README
Useful because it preserves:
- the older framing for this benchmark-only col-then-sub stream
- the intended relationship between the solve script, seed utility, and test

### B. Seed utility
Useful because it explicitly documents:
- benchmark-only, not canonical, seed generation
- deterministic phase-aware seed pools
- strict validation and no hidden optimiser logic
- separation between seed generation and optimisation

### C. Solve script
Useful because it preserves:
- a practical staged col-then-sub solve shape
- separate solve-proof style logs for that direction
- a historical solve-oriented benchmark path

### D. Matching test
Useful because it preserves:
- intended deterministic/layout behaviour of the seed utility
- a concrete check that the utility was not just an untested draft

## Current role

These files are:
- legacy benchmark/method reference
- useful idea source
- not active project truth
