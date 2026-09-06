# Public API surface

Normal code imports:

```python
from rdp import api
```

The V1 surface is intentionally small enough to navigate from that namespace.

## Operations

```text
run
encrypt
decrypt
```

`run` executes a solver request.

`encrypt` and `decrypt` are the known-key path.

See [RunSpec](run_spec.md), [RunResult](run_result.md) and
[Known-key encrypt and decrypt](known_key.md).

## Run and configuration objects

```text
RunSpec
RunResult
CipherSpec
KeySpec
SolverSpec
ScoringConfig
LoggingConfig
InterruptorConfig
RawTextInput
RuneIndexInput
SourceReferenceInput
ProblemInput
```

See [Configuration objects](configuration.md) and
[Parameter reference](parameters/README.md).

## Public value types

```text
ConcreteKey
RuneIndices
InitialKeys
TextDirection
ComputeDevice
WordLengthPolicy
RunStatus
```

The common enum values are listed in
[Common public enums](parameters/enums.md).

## Stable public errors

```text
RdpError
ConfigurationError
CapabilityUnavailableError
AssetUnavailableError
NonInvertibleCipherError
ExecutionError
```

See [Public errors](errors.md).

## Namespaces

```text
advanced
display
liber_primus
experimental
```

`advanced` contains typed specialist enums, reports and scoring contracts.

`display` contains the standard human-readable and JSON summary helpers.

`liber_primus` contains the LP data-access surface.

`experimental` contains typed experimental cipher definitions that still use
the normal run machinery.

See [Displaying results](../guides/displaying_results.md),
[Liber Primus data](liber_primus.md) and [Experimental ciphers](experimental.md).

For the reasoning behind keeping this surface small, see
[Project aims and design principles](../project_overview.md).
