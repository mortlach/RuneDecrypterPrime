# Periodic-Columnar Solve Proof Matrix

This folder defines a stable, extensible benchmark matrix for proving solve capability over increasing difficulty.

Goals:
- Prove what we can solve now (not just score gains).
- Track timing/work (`seconds`, `evals`) and recovery (`match_ratio`, `bestk_match_ratio`).
- Keep fixtures versioned so we can compare runs over time and fill missing periods later.

## Files
- `fixtures_periodic_columnar_v1.json`: tier ladder (period/columns/length) and defaults.
- `solver_profiles_v1.json`: run profiles (quick vs long).
- `proven_solve_log_template.csv`: append-only schema for solved/not-solved history.

## Usage Model
1. Pick a fixture set and profile.
2. Run benchmark.
3. Append results to the solve log schema.
4. Mark fixture status as `solved` / `partial` / `unsolved` based on recovery thresholds you decide.

## Fixture Philosophy
- Controls first (`columns=1`) to prove substitution path still solves.
- Incremental transposition complexity next.
- Boundary targets (`period=13`) at long text (`L=1200` and full text `L=2376`) last.

## Conventions
- There is no `columns=0` fixture in these benchmarks.
- `columns=1` is the no-op/minimal-transposition control case.
- Fixture ids encode order/shape (for example `focus_*` vs `subcol_*`) to avoid log collisions.

## Proven Autoskip (Default)
- Default behavior is to skip instances already marked solved in the proven log.
- Override only when explicitly requested:
  - `col_then_sub` pipeline: set `RDP_PIPELINE_FORCE_RERUN_PROVEN=1`
  - `sub_then_col` pipeline: set `RDP_SUBCOL_FORCE_RERUN_PROVEN=1`

## Update Policy
- Add new fixture rows instead of rewriting history.
- Keep `fixture_id` stable.
- If you retune a fixture significantly, add a new `fixture_version` row in results.
