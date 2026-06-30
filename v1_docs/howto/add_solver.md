# Add A Solver

Status: staged V1 draft

Owner paths:
- `src/rune_decrypter_prime/solvers/`
- `src/rune_decrypter_prime/solvers/solver_base.py`
- `src/rune_decrypter_prime/core/types.py`
- `src/rune_decrypter_prime/api/normalize.py`
- `src/rune_decrypter_prime/core/engine/engine.py`
- `src/rune_decrypter_prime/core/solver_engine.py`
- `tests/solvers/`
- `tests/contracts/`

Related coder pages:
- `coder/solver_pipeline.md`
- `coder/telemetry_and_reports.md`
- `coder/extension_points.md`

## Goal

Add a solver search strategy without changing scoring semantics or silently
changing existing solver defaults.

Today this is not a zero-touch registry extension. New solvers require explicit
enum and engine-table wiring.

## Steps

1. Create the solver module under `src/rune_decrypter_prime/solvers/`.
2. Subclass `SolverBase`.
3. Accept the same constructor shape used by existing solvers.
4. Use `self.problem.evaluate_keys(...)` or `self._score_batch(...)` for scoring.
5. Use `self.keyops` for key generation, mutation, normalization, and local
   improvement.
6. Use the shared telemetry helpers from `SolverBase`.
7. Return a `Solution`.
8. Add the solver name to `SolverName` in `core/types.py`.
9. Add normalization support in `api/normalize.py`.
10. Register the solver in `_SOLVER_TABLE` in `core/engine/engine.py`.
11. Check whether the legacy `core/solver_engine.py` table also needs the new
    solver.
12. Add focused solver tests and contract tests.

## Solver Contract

A solver owns search only. It may choose candidate keys, score batches, apply
early stop rules, and report progress.

A solver must not:

- inspect truth data for production ranking
- use oracle data unless it is an explicit test/tutorial fast path
- change objective direction outside the shared scoring/ranking helpers
- silently fall back when a required lane or asset is unavailable
- mutate global configuration

## Determinism Rules

Use the `rng` supplied by the engine. Do not create entropy-seeded random
generators inside solver loops.

Tie-breaks must be deterministic. Prefer stable ordering such as score
descending and index ascending when equal scores are possible.

When using early stopping, report the stop reason. If the solver reaches a
target score, plateaus, exhausts work, or uses a test-key fast path, that reason
must be visible in telemetry or `SolverReport`.

## Reporting Rules

The solver should make these visible where applicable:

- `solver_name`
- `requested_seed`
- `effective_seed`
- normalized solver params
- `stop_reason`
- best score
- best key
- eval count
- token count
- decrypt and score timing
- oracle or truth-data use

Use `build_solver_report` rather than hand-writing report dictionaries.

## Tests

At minimum, cover:

- deterministic repeatability for fixed seed
- valid construction through the engine path
- stop reason reporting
- no hidden truth/oracle ranking path
- stable behavior when scores tie
- requested scorer lanes block or report fallback explicitly

For small changes, start with focused `tests/solvers/` files. Add API or
contract tests when the solver becomes user-selectable.

## Do Not Do

- Do not add long-running benchmarks as tests.
- Do not lower tutorial thresholds to hide solver regressions.
- Do not write generated reports into docs.
- Do not add CLI arguments to helper scripts unless that is explicitly approved.
