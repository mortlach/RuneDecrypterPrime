rune_decrypter_prime/core
=========================

Stage-2 “engine room”. Converts API configs into runnable problems, builds
solvers/scorers, and owns telemetry/Problem lifecycle.

Important modules
-----------------
- `config/`: dataclasses (`CipherConfig`, `ScoringConfig`, `SolverConfig`,
  `LoggingConfig`, `Solution`) shared across API and engine layers.
- `problem/`: `ProblemSpec`, `ProblemInstance`, and `runtime.py`’s
  `DecryptionProblem`, which binds cipher, scorer, ciphertext, and KeyOps.
- `engine/engine.py`: deterministic orchestrator that builds the requested
  solver, emits run_start/run_end telemetry, and enforces cache cleanup hooks
  (e.g., scorer WLI caches).
- `engine/builders.py`: factory helpers for ciphers and scorers.
- `solver_engine.py` / `factory.py`: legacy entry points kept for backwards-
  compatible code paths.
- `types.py`: strict enums (direction, solver kind, Channel, ObjectiveSpec, etc.)
  used throughout the repo.

Design notes
------------
- Everything here is deterministic; seeds flow in via `EngineConfig`.
- `DecryptionProblem` owns the single KeyOps instance and is the only code that
  calls cipher/scorer primitives during evaluation.
- Telemetry is plumbed in once at this layer (run_start, run_end, solution meta).

How to extend
-------------
1. **New config fields:** add them to the relevant dataclass in `core/config`,
   default them sensibly, and make sure `api` layers populate them. Keep the
   dataclasses pickle-friendly for future tooling.
2. **New solver kinds:** register the implementation in `engine/_SOLVER_TABLE`,
   expose an enum value in `types.py`, and cover the run/telemetry contract in
   `tests/solvers` + `tests/telemetry`.
3. **Cache/cleanup hooks:** if a subsystem needs reset semantics (e.g., scorer
   caches), attach them in `engine.solve()` so every run leaves the problem in
   a clean state.
