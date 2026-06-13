# How-To: Add a Solver

> Tracks: **Hands-on** shows how to evolve a tutorial preset into a reusable solver; **Expert** explains the required telemetry hooks, registrations, and tests.

Audience: Expert contributors
Time: 30-60 minutes
Outcome: New solver subclass registered, with tests and telemetry
Prereqs: Python 3.11+, pytest, familiarity with `SolverSpec` and `SolverBase`

## Hands-on Checklist
- Prototype the idea inside a tutorial (e.g., tweak GA/SA presets) and confirm logs land in `output/tutorials/...`.
- Capture deterministic seeds and telemetry snapshots so you can compare against the promoted solver later.
- Note any new CLI flags or tutorial instructions that future readers will need.

## Expert Implementation Steps
1. **Subclass** `solvers/solver_base.SolverBase` (or compose from it) under `src/rune_decrypter_prime/solvers/<name>.py`.
2. **Implement** `_solve()` using the provided RNG (`self._rng`) and emit telemetry via `self._progress_pct(...)`, `self._start_span(...)`, and `self._end_span(...)`.
3. **Register** the solver in `core/engine/_SOLVER_TABLE` and add a builder helper (e.g., `SolverSpec.my_solver(...)`) in `api/specs.py`.
4. **Expose** presets/tutorial knobs by updating `docs/tutorials/<name>.md` or extending existing tutorials (Hands-on readers need concrete parameters).
5. **Write tests** in `tests/solvers/test_<name>.py` that verify:
   - Deterministic output for fixed seeds.
   - Key bijection/preservation (for permutation solvers).
   - `solver_progress` buckets and `solution.meta["work"]` fields.

## Verification
- `pytest tests/solvers -k <name> -q`
- Tutorial regression (existing or new) `pytest tests/tutorials -k <name> -q`
- Inspect `output/tests/<run>/logs/app.jsonl` for `telemetry.solver_spans.<name>` entries containing your params/results.

## Tips
- Accept RNG objects (`numpy.random.Generator`) instead of global modules to honor determinism.
- Stage-based solvers (beam -> SA, GA -> SA) should annotate each span so telemetry dashboards can reason about the pipeline.
- Update `docs/guides/telemetry.md` and `docs/guides/architecture.md` whenever a solver changes required telemetry fields or pipeline flow.
