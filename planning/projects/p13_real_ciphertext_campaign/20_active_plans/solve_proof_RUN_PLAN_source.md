# Solve Proof Run Plan

## Phase 1: Capability Sanity (30 min)
- Profile: `proof_quick_30m`
- Goal: confirm we still solve easy/control fixtures and recover high match ratio quickly.

## Phase 2: Incremental Difficulty (2 hours)
- Profile: `proof_standard_2h`
- Goal: establish period/column envelope where recovery starts to fail.

## Phase 3: Boundary Push (overnight)
- Profile: `proof_overnight_8h`
- Goal: measure best proven boundary for period 13 with long/full text.

## What to log every run
- `run_id`, `profile_id`, `fixture_id`
- `seconds`, `evals`
- `sol_pct`, `sol_raw_full`
- `match_ratio`, `bestk_match_ratio`
- `n_unique_tails_topk`
- mode (`none|seed_raw|seed_tail_diverse|seed_pct_rerank`)

## Status update rule
- Update `solve_status_v1.json` after each benchmark family.
- Append run rows to `proven_solve_log_template.csv`-compatible file.
- Do not overwrite prior records; keep history for trend analysis.
