# Run pipeline

A normal solve passes through the same main stages regardless of the cipher or
solver selected.

## Where this lives in the code

For source changes, follow the ordinary solver route in this order. Paths are
relative to the repository root, and the names are useful search targets.

| Stage | File and main names |
| --- | --- |
| Public entry | [src/rdp/api/run.py](../../src/rdp/api/run.py): `run()` accepts or builds a `RunSpec`, then calls `_execute()` |
| Input materialisation | [src/rdp/api/run_spec_routing.py](../../src/rdp/api/run_spec_routing.py): `materialize_runspec_problem_input()` calls `normalize_rune_input()` in [src/rdp/api/normalize.py](../../src/rdp/api/normalize.py), or `resolve_source_input_ref()` in [src/rdp/api/source_resolution.py](../../src/rdp/api/source_resolution.py) for a registered source |
| Runtime request | [src/rdp/api/pipeline.py](../../src/rdp/api/pipeline.py): `execute_run()` calls `materialize_cipher_config()` from [src/rdp/core/config/cipher.py](../../src/rdp/core/config/cipher.py) and constructs a `ProblemSpec` from [src/rdp/core/problem/spec.py](../../src/rdp/core/problem/spec.py) |
| Problem instance | [src/rdp/core/problem/instance.py](../../src/rdp/core/problem/instance.py): `ProblemInstance.materialise()` assembles the runtime problem |
| Component builders | [src/rdp/core/engine/builders.py](../../src/rdp/core/engine/builders.py): `build_cipher()` and `build_scorer()` are called during materialisation |
| Bound problem | [src/rdp/core/problem/runtime.py](../../src/rdp/core/problem/runtime.py): `DecryptionProblem` binds the cipher, scorer and configuration |
| Solver dispatch | [src/rdp/core/engine/engine.py](../../src/rdp/core/engine/engine.py): `solve()` uses `_solver_from_cfg()`, then calls the selected solver's `solve()`; for example, `BeamSolver` in [src/rdp/solvers/beam.py](../../src/rdp/solvers/beam.py) |
| Repeated candidate evaluation | [src/rdp/solvers/solver_base.py](../../src/rdp/solvers/solver_base.py): `SolverBase._evaluate_keys()` delegates to `DecryptionProblem.evaluate_keys()` in [src/rdp/core/problem/runtime.py](../../src/rdp/core/problem/runtime.py) for decryption and scoring |
| Finalisation | Back in `execute_run()`, `finalize_solution()` in [src/rdp/core/engine/finalization.py](../../src/rdp/core/engine/finalization.py) finalises the `Solution` defined in [src/rdp/core/config/solution.py](../../src/rdp/core/config/solution.py) |
| Public result | Back in [src/rdp/api/run.py](../../src/rdp/api/run.py), `_result_from_solution()` builds the `RunResult` defined in [src/rdp/api/run_result.py](../../src/rdp/api/run_result.py), then `_write_requested_artifacts()` handles requested output |

Candidate evaluation is a loop inside the solver, not a single stage after it
finishes. The `TWO_PERIOD_CRIBS` solver takes a separate branch in `_execute()`:
`normalize_two_period_cribs_request()` in [src/rdp/api/two_period_cribs.py](../../src/rdp/api/two_period_cribs.py)
feeds `run_two_period_stages()` in [src/rdp/solvers/two_period_cribs.py](../../src/rdp/solvers/two_period_cribs.py),
then rejoins the public result conversion.

## 1. Build the request

The public request contains:

```text
problem input
cipher
key space
solver
scoring
optional run controls
```

The complete request fields and defaults are in
[RunSpec parameters](../reference/parameters/run_spec.md).

## 2. Prepare the input

`RuneInput` and `SourceReferenceInput` are converted into the ciphertext and
WLI needed by the engine.

Liber Primus references are resolved through the same input boundary.

See [Ciphertext input](../guides/ciphertext_input.md).

## 3. Validate the component combination

The cipher, key space and solver need to describe a compatible problem.

Configuration errors are rejected before execution where possible.

This avoids discovering halfway through a long run that two parts never made
sense together.

See [Errors](../reference/errors.md).

## 4. Materialise runtime components

The public specs are translated into the runtime cipher, key operations, solver
and scorer.

The public API remains the durable description of the experiment. Runtime
objects remain implementation details.

## 5. Search and score

The selected solver explores the key space.

Candidate plaintexts are ranked using the configured scoring evidence.

Optional interruptors, starting keys, text permutation and other run choices are
applied through the same request.

See [Solvers](../guides/solvers.md),
[Scoring](../guides/scoring.md) and
[Interruptors](../guides/interruptors.md).

## 6. Record execution evidence

Telemetry can record run context, solver progress, timing, pipeline state and
scorer information.

It is enabled by default.

See [Telemetry](../guides/telemetry.md).

## 7. Return RunResult

The result contains the candidate and the evidence needed to interpret it:

```text
plaintext
key
score
status
solver report
scorer report
effective configuration
reproducibility
oracle information
telemetry
artifacts
```

See [Reading a result](../guides/results.md).

## 8. Save artifacts only when requested

A plain run can remain entirely in memory.

`LoggingConfig` controls saved run files and artifacts.

See [Outputs](../guides/outputs.md).

The pipeline is deliberately the same for a small tutorial and a larger
development run. More advanced work adds capability without changing what the
main stages mean.

## The internal spine

The implementation path can be followed one level deeper as:

```text
RunSpec
-> typed input materialisation
-> CipherConfig + scoring configuration
-> runtime cipher + scorer
-> DecryptionProblem
-> KeyOps
-> solver
-> repeated candidate evaluation
-> Solution
-> RunResult
```

The key point is that the solver sits **after** the cipher, key-operation and
scoring contracts have been bound.

See [Key models and search operations](key_model_and_search.md),
[Candidate evaluation](candidate_evaluation.md) and
[Solver mechanics](solver_mechanics.md).
