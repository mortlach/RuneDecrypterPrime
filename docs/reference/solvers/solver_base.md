# `solvers/solver_base.py`

> Purpose: shared base class for Beam/GA/SA/Hybrid solvers. Handles RNG seeding, telemetry spans, progress reporting, patience logic, and ensures every solver exposes a consistent API to the engine.

## Key Components
| Symbol | Description |
| --- | --- |
| `SolverBase` | Base class that manages RNGs, device/direction metadata, telemetry spans, patience logic, and solution finalisation. Concrete solvers implement `_solve()`-style methods on top of this scaffolding. |
| `_unwrap_params_dict(p)` | Accepts either `{"params": {...}}` or a flat dict and returns a flat dict; keeps UI inputs flexible without complicating solver logic. |
| `TelemetrySpan` | Context manager that emits `solver_start`/`solver_progress`/`solver_end` events automatically. |
| `OptimizerMeta` | Small dataclass describing the solver's name/params/seed; attached to solutions for inspection. |

## Responsibilities of `SolverBase`
- Normalise solver parameters (including legacy aliases like `no_improve_rounds` -> `patience_rounds`).
- Configure device/direction info from the `ProblemInstance` (`Device`, `Direction` enums).
- Track progress percentage (`progress_pct`) and emit telemetry buckets.
- Implement generic patience/early-stop logic used by all solvers.
- Provide helper methods to convert plaintext/ciphertext indices into strings (`Runeglish`) for logs.
- Finalise `Solution` objects with telemetry metadata via `attach_telemetry_to_meta`.

Concrete solvers (e.g., `BeamSolver`, `GASolver`, `SASolver`, `HybridSolver`) inherit from `SolverBase` to access these capabilities.

## Tests
- `tests/solvers/test_permutation_optimizers.py`, `tests/tutorials/test_ga_stage2_regression.py`, etc., all run through `SolverBase` when instantiating GA/SA/Hybrid solvers.
- `tests/telemetry/test_solver_pipeline_block.py` and `tests/telemetry/test_progress_events.py` rely on the telemetry spans emitted here.

## Related Docs
- `docs/reference/core/engine/engine.md` - shows how `SolverBase` instances are created and invoked.
- `docs/reference/telemetry/events.md` - events emitted by `TelemetrySpan`.

