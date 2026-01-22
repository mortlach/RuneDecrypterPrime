rune_decrypter_prime/solvers
============================

Search algorithms that explore the key space. All solvers inherit from
`solver_base.SolverBase`, which provides telemetry spans, shared plateau logic,
and helper hooks (`_score_batch`, `_maybe_return_test_key_fastpath`, etc.).

Implemented solvers
-------------------
- `beam.py`: deterministic beam search with plateau controls.
- `ga.py`: genetic algorithm (population, crossover, mutation, optional local
  improve pass).
- `sa.py`: simulated annealing with rescue/reseed knobs.
- `hybrid.py`: orchestrates multi-phase runs that combine GA/SA/Beam.
- `kaeding_periodic_structured.py`: block-focused solver for periodic structured keys.

Design notes
------------
- Solvers never touch cipher/scorer objects directly. They call
  `problem.evaluate_keys(pop)` and rely on KeyOps for generating new candidates.
- Seeds are consumed via NumPy’s `Generator`, passed in by `engine.EngineConfig`.
- Telemetry is emitted through `solver_start/progress/end` events with percent
  progress derived from `progress_pct`.

Adding a solver
---------------
1. Subclass `solver_base.SolverBase`, implement `_initial_key_and_score`,
   neighbour/selection logic, and `solve()`.
2. Register the solver in `core/engine/_SOLVER_TABLE` and expose a builder in
   `api/specs.SolverSpec`.
3. Emit useful telemetry fields via `self._progress_pct(...)` so tutorials and
   dashboards can track convergence. Add regression tests under
   `tests/solvers/` and `tests/telemetry/`.
