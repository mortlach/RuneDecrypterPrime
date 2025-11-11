# `core/engine/engine.py`

> Purpose: Stage-2 orchestrator. Accepts a fully materialised `ProblemInstance`, selects the appropriate solver (Beam/GA/SA/Hybrid), emits top-level telemetry envelopes (`run_start`/`run_end`), and returns a populated `Solution`.

## Key Pieces
| Symbol | Description |
| --- | --- |
| `EngineConfig` dataclass | Solver name, params, seed, stop_score, log interval, optional `seed_keys`. |
| `_child_rng(seed)` | Creates a deterministic `numpy.random.Generator` for solvers. |
| `_solver_from_cfg(kind, problem, params, rng, cfg)` | Instantiates the correct solver class (`BeamSolver`, `GASolver`, `SASolver`, `HybridSolver`). |
| `solve(instance, engine_cfg)` | Entry point called by `api/pipeline.execute_run`. Validates the instance, emits telemetry, constructs the solver, runs it, and wraps up telemetry even on exceptions. |

## Usage
Typically invoked via RunAPI -> pipeline. For integration tests you can operate directly:
```python
from rune_decrypter_prime.core.engine.engine import EngineConfig, solve

eng_cfg = EngineConfig(solver=SolverName.GA, params={"pop_size": 64, "generations": 80}, seed=1234)
solution = solve(problem_instance, eng_cfg)
print(solution.score, solution.meta["telemetry"]["run"]["solver"])
```

## Telemetry
- `tel_run_start` / `tel_run_end` wrap the entire solve run, capturing solver params, device information, and pipeline block.
- Individual solvers emit `solver_start` and `solver_progress` inside their own implementations.

## Tests
- `tests/smoke/test_runapi_determinism.py` - ensures the engine respects seeds/devices and emits consistent telemetry.
- `tests/telemetry/test_solver_pipeline_block.py` - verifies run_start/run_end wrappers keep the pipeline block intact.
- `tests/solvers/test_permutation_optimizers.py` - uses EngineConfig to run GA/SA/Hybrid solvers directly.

## Related Docs
- `docs/reference/api/pipeline.md` - describes how EngineConfig is constructed from SolverSpec.
- `docs/reference/solvers/solver_base.md` - details the shared behaviour all solvers implement.

