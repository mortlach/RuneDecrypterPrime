# No-WLI Pipeline Design Review Plan

Date: 2026-02-21

## Scope

This plan covers `tools/benchmarks/bench_solve_periodic_columnar_pipeline_no_wli.py` and shared benchmark config modules for future reuse by other benchmark attack scripts.

The target scoring schedule is:

- `A_char1` (explore)
- `M_char12` (rerank/promote)
- `B_char34` (refine/confirm)

## Review Findings (No-WLI Impact)

1. No-WLI reduces score discriminative power and increases local-optima risk.
2. Stage-level scorer intent must be explicit; mixing a single scorer across all stages hides signal quality issues.
3. Stage-1 needs diversity telemetry, not only best score.
4. Stage-2 results should be promoted with both rank-by-score and rank-by-match to preserve basin diversity.
5. Stage-3 gate quality should be evaluated with the Stage-3 scorer (`B_char34`), not a weaker stage score.
6. Config needs to be deterministic and reviewer-readable (typed profile + logged effective config).

## Implemented in Current Pass

1. Added shared typed profile module:
   - `tools/benchmarks/config/no_wli_pipeline_profiles.py`
   - Production profile: `no_wli_a1_m12_b34_v1`.
2. Added benchmark config package docs:
   - `tools/benchmarks/config/README.md`
3. No-WLI pipeline now imports profile defaults from shared config module.
4. Stage schedule is explicit in setup output and run config:
   - Stage-1 `A_char1`, Stage-2 `M_char12`, Stage-3 `B_char34`.
5. Stage-2 hybrid fallback is active for columns above exact-tail range.
6. Stage-2 archive/promote data is logged with:
   - `top_score_mid`, `top_score_judge`, and `top_match`.
7. Stage-3 seeding uses promoted Stage-2 keys with deterministic local mutations.
8. Output clarity improved:
   - `run_config.json`
   - `best/best_instance.json`
   - `best/best_preview.txt`

## Remaining Hardening Tasks

1. Add deterministic replay check script for no-WLI benchmark profile:
   - same config + seed must reproduce key metrics.
2. Add explicit period/harmonic diagnostic fields:
   - candidate period quality and harmonic warning notes.
3. Add optional diversity metrics:
   - sampled pairwise key-distance in Stage-1 archive.
4. Add short benchmark doc table for thresholds and interpretation:
   - “mid score uplift”, “judge score uplift”, “seed stability”.

## Acceptance Criteria

1. Script compiles and runs with no-WLI assets only.
2. Run artifacts always include effective config and best-instance outputs.
3. Stage logs make stage schedule and promoted-basin behavior explicit.
4. Profile selection is centralized in shared config and can be reused by other benchmark scripts without modifying solver-core.

## Non-Goals for This Change

1. No changes to other benchmark scripts yet.
2. No solver-core API changes.
3. No WLI-based scoring or WLI assets in this benchmark.

