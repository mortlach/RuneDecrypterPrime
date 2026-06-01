RDP: Col-then-sub benchmark stream (v2)

What you get
------------
1) A benchmark script with separate solve-proof logs:
     tools/benchmarks/bench_solve_periodic_columnar_pipeline_col_then_sub.py

   Persistent (append-only) solve-proof logs:
     tools/benchmarks/solve_proof/proven_solve_pipeline_col_then_sub_log.csv
     tools/benchmarks/solve_proof/proven_solve_pipeline_col_then_sub_solved.jsonl

2) Benchmark-only seed utilities for col_then_sub:
     tools/benchmarks/seed_utils_periodic_columnar_col_then_sub.py

   This provides a deterministic phase-aware periodic-substitution seed pool builder:
     make_periodic_seed_pool_col_then_sub(...)

   It is NOT the canonical seed path yet (by design).

3) Tests for the new benchmark utils:
     tests/utils/test_seed_utils_periodic_columnar_col_then_sub_bench.py

Notes
-----
- No optimiser logic is duplicated. Kaeding/keyops remain the optimiser.
- The new seed pool builder supports an optional pt_unigram_rank_override so tests can
  avoid LM asset requirements.


v3 changes:
- Stage-2 hybrid is now seeded with a deterministic tail permutation pool (initial_keys).
- Seed pool builder supports optional pt_rank_jitter_swaps.
