# Execution core

The core defines shared runtime types and brings the cipher, key operations, scorer and solver into one execution. Public callers normally reach it through api.run.

## Where to look

- [config/](config/) — Validated configuration for runtime components.
- [problem/](problem/) — Input specification, materialised instance and candidate evaluation.
- [engine/](engine/) — Component construction, execution and finalisation.
- [types.py](types.py) — Shared enums, rune/key types and normalisation.
- [component_contracts.py](component_contracts.py) — Capability and component status definitions.
- [capability_gates.py](capability_gates.py) — Reject unavailable requested capabilities.
- [transpositions.py](transpositions.py) — Permutation validation and inversion.

## Choices and extension

Choose behaviour in the public request. Runtime configuration is its execution representation, not a second set of user settings. When tracing an unexpected result, follow the requested configuration into problem construction, evaluation and finalisation.

Continue with the [guide](../../../docs/guides/pipeline.md) or the [package map](../README.md).
