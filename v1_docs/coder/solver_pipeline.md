# Solver Pipeline

Status: staged V1 draft

Owner paths:
- `src/rune_decrypter_prime/api/specs.py`
- `src/rune_decrypter_prime/core/engine/engine.py`
- `src/rune_decrypter_prime/solvers/`
- `src/rune_decrypter_prime/telemetry/events.py`

Related tests:
- `tests/solvers/`
- `tests/smoke/`
- `tests/telemetry/`
- `tests/api/`

Stability:
- Public V1 surface for `SolverSpec`
- Semi-stable contributor surface for solver implementations

## Purpose

The solver layer searches candidate keys. It should not implement cipher math
or scoring logic directly.

## What This Layer Owns

- solver selection
- solver parameter handling
- deterministic RNG use
- candidate search strategy
- progress events
- stop reasons
- seed-key handling
- final solution construction

## What This Layer Must Not Own

- cipher decrypt internals
- scoring objective implementation
- report-only diagnostic ranking effects
- artifact path writing
- hidden truth/oracle control flow

## Main Objects

| Object | Owner path | Role |
| --- | --- | --- |
| `SolverSpec` | `src/rune_decrypter_prime/api/specs.py` | Public declarative solver choice. |
| `EngineConfig` | `src/rune_decrypter_prime/core/engine/engine.py` | Runtime solver kind, params, seed, and knobs. |
| `_SOLVER_TABLE` | `src/rune_decrypter_prime/core/engine/engine.py` | Maps `SolverName` to solver class. |
| `SolverBase` | `src/rune_decrypter_prime/solvers/solver_base.py` | Shared telemetry, scoring, early-stop, and seed helpers. |
| concrete solvers | `src/rune_decrypter_prime/solvers/` | Implement beam, GA, SA, hybrid, and kaeding-style search. |

## How It Fits Into A Run

```text
SolverSpec
  -> SolverConfig
  -> EngineConfig
  -> solver class selected by SolverName
  -> solver proposes candidate keys
  -> DecryptionProblem evaluates keys
  -> solver returns Solution
```

## Contracts And Invariants

- The engine applies deterministic default seed `0` when no seed is supplied.
- Solvers evaluate keys through the problem boundary.
- Solver progress should flow through telemetry helpers.
- Stop reasons should be explicit.
- Test-key or known-key fast paths must be visible in reports.

## Determinism Notes

- Solver randomness comes from the engine-created NumPy generator.
- Seed keys are validated; invalid seed keys should block clearly.
- Plateau and stop-score behaviour must be explicit.
- Backend/device assumptions belong in telemetry/report surfaces.

## Report And Telemetry Outputs

Solver reports can include solver name, requested/effective seed, normalised
params, stop reason, best score, best key, work counters, timings, oracle use,
truth-data policy, and scorer-lane details.

## Extension Checklist

1. Add a `SolverSpec` factory or supported name.
2. Implement or subclass solver logic under `src/rune_decrypter_prime/solvers/`.
3. Register the solver in the engine solver table.
4. Emit progress through shared telemetry helpers.
5. Define stop reasons clearly.
6. Add focused tests under `tests/solvers/` and `tests/telemetry/`.
7. Update docs and reports if public behaviour changes.

## What Not To Rely On

- Private solver helper methods.
- Exact console progress wording.
- Entropy-based randomness.
- Oracle/test-key data as hidden production ranking input.
