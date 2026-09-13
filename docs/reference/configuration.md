# Configuration objects

The main typed configuration objects are `CipherSpec`, `KeySpec`, `SolverSpec`,
`ScoringConfig`, `LoggingConfig` and `InterruptorConfig`.

They describe different parts of the experiment. Keeping those parts separate
is one of the main RDP design choices.

`RunSpec` is the complete durable request. The result's `configuration` section
distinguishes requested and effective component configuration,
`reproducibility` records its owned replay metadata, and `telemetry` records
execution observations.

See [Project aims and design principles](../project_overview.md).

## CipherSpec

`CipherSpec` identifies the cipher family and its cipher-specific settings.

See [Cipher parameters](parameters/ciphers.md) and
[Building a run](../guides/building_a_run.md).

## KeySpec

`KeySpec` describes the search space rather than one concrete key.

See [Key parameters](parameters/keys.md) and
[Keys and key spaces](../guides/keyops.md).

## SolverSpec

`SolverSpec` records the search method, budget, stopping controls and seed.

See [Solver parameters](parameters/solvers.md) and
[Solvers](../guides/solvers.md).

## ScoringConfig

`ScoringConfig` owns the language-model scoring and the optional specialist
lanes.

The scoring objective owns ranking sense. V1 rejects the unimplemented
`INCLUDE_BOUNDARIES` boundary mode and the redundant `MINIMIZE` score direction
instead of accepting no-op settings.

See [Scoring parameters](parameters/scoring.md) and
[Scoring](../guides/scoring.md).

## LoggingConfig

`LoggingConfig` controls saved run output.

`RunSpec.logging` is `None` by default.

It owns output location, portable/redacted metadata and the optional solver
report, display summary and artifact manifest. Live progress is instead a
runtime-only callback passed to `api.run(...)`.

See [Logging parameters](parameters/logging.md) and
[Outputs](../guides/outputs.md).

## InterruptorConfig

`InterruptorConfig` represents disabled, exact, or searched interruptor
positions.

See [Interruptor parameters](parameters/interruptors.md) and
[Interruptors](../guides/interruptors.md).

The enum values used by these objects are listed in
[Common public enums](parameters/enums.md).
