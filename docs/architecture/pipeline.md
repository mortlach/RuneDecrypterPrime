# Run pipeline

A normal solve passes through the same main stages regardless of the cipher or
solver selected.

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

`RawTextInput`, `RuneIndexInput` and `SourceReferenceInput` are converted into
the ciphertext and WLI needed by the engine.

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

