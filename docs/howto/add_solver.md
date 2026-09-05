# Add a solver

A solver chooses which keys to try next. The cipher, key operations and scorer
already define how a candidate is represented, decrypted and scored; a new
search strategy should reuse those parts.

If the difference is only a search budget or an existing option, start with
the appropriate `api.SolverSpec` constructor. This guide covers a new algorithm
using the ordinary engine path. Adding a public solver family requires a
separate contract decision; the accepted V1 surface is already settled.

## Implement the search

Start with [`SASolver`](../../src/rdp/solvers/sa.py) for a compact example and
[`SolverBase`](../../src/rdp/solvers/solver_base.py) for the shared helpers.
Place the implementation under [`src/rdp/solvers/`](../../src/rdp/solvers/).

1. Subclass `SolverBase` and implement `solve()`. The engine calls that method
   directly.
2. Match the constructor used by `_solver_from_cfg` in
   [`engine.py`](../../src/rdp/core/engine/engine.py): `problem`, `opt_cfg`,
   and the supplied RNG, seed keys, stopping, logging and progress settings.
   Validate the algorithm's parameters and pass the shared settings to the base.
3. Use `self.rng` for random choices and `self.keyops` for supported key
   generation, mutation and local improvement. A cipher may have its own key
   type and search operations; use its capabilities rather than assuming every
   key is a permutation.
4. Score candidate batches through `self._score_batch(...)`. It evaluates
   them through the problem and applies the shared ranking direction. Preserve
   deterministic ordering when scores tie.
5. Use `_start_span()`, `_progress_pct(...)` and `_end_span(...)` to report
   progress, work and the reason for stopping. Close the span on failure too.
6. Return the shared `Solution` through `_finalize_solution(...)`, following
   the existing solver's completion path. Read this helper before using it:
   it can perform final local improvement as well as construct the result.

Use the RNG supplied by the engine throughout the search. Creating a fresh
generator inside a loop changes reproducibility. Keep known-answer validation
and report-only diagnostics separate from production ranking, stopping,
tie-breaks and candidate selection; any explicit test or oracle path must
remain visible in the reports.

## Connect the implementation

An ordinary engine solver needs a runtime `SolverName` in
[`core/types.py`](../../src/rdp/core/types.py) and an entry in the engine's
`_SOLVER_TABLE`. Check its early-stop defaults there as well.

Making it available through `api.run` also involves the typed request,
validation, runtime binding and report conversion. Follow the existing solver
through these owners:

- [`api/specs.py`](../../src/rdp/api/specs.py): `SolverSpec` construction and
  parameter validation.
- [`api/normalize.py`](../../src/rdp/api/normalize.py) and
  [`api/_resolve.py`](../../src/rdp/api/_resolve.py): runtime name and parameter
  normalisation.
- [`api/run.py`](../../src/rdp/api/run.py): `_runtime_solver_config` and
  `_runtime_solver_parameters` bind the typed request to the engine; the same
  module assembles the public result.
- [`api/solver_report.py`](../../src/rdp/api/solver_report.py) and
  [`api/stop_reason_contract.py`](../../src/rdp/api/stop_reason_contract.py):
  typed solver reporting and stop status.

The public `SolverKind` and internal `SolverName` are distinct enums. Registering
a runtime class alone does not add a public constructor. Extend the public
surface only when that change is approved, with its request, reporting and
contract tests updated together.

## Check the behaviour

Use small, focused cases in [`tests/solvers/`](../../tests/solvers/) and the
relevant API or contract tests. Cover:

- repeatability with a fixed seed, including tied scores;
- valid keys and the required key-operation capabilities;
- construction through the intended engine and public routes;
- parameter validation, initial keys and stopping conditions;
- truthful work counters, stop status and any known-answer use.

If the solver is taught in an example, describe its purpose, assets, runtime
and expected result in the [tutorial catalogue](../../tutorials/v1/README.md).
Keep long qualification campaigns separate from the focused development checks.
