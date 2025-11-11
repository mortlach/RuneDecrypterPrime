rune_decrypter_prime/solvers
============================

Search algorithms that explore the key space. All solvers inherit from
`solver_base.SolverBase`, which provides telemetry spans, shared patience logic,
and helper hooks (`_score_batch`, `_maybe_return_test_key_fastpath`, etc.).

Implemented solvers
-------------------
- `beam.py`: deterministic beam search with plateau/patience controls.
- `ga.py`: genetic algorithm (population, crossover, mutation, optional local
  improve pass).
- `sa.py`: simulated annealing with rescue/reseed knobs.
- `hybrid.py`: orchestrates multi-phase runs that combine GA/SA/Beam.

Design notes
------------
- Solvers never touch cipher/scorer objects directly. They call
  `problem.evaluate_keys(pop)` and rely on KeyOps for generating new candidates.
- Seeds are consumed via NumPy’s `Generator`, passed in by `engine.EngineConfig`.
- Telemetry is emitted through `solver_start/progress/end` events with percent
  progress derived from `progress_pct`.
