# RunSpec and api.run parameters

## RunSpec

| Parameter | Type | Default | Purpose / constraint |
| --- | --- | --- | --- |
| `problem_input` | `ProblemInput` | **required** | `RuneInput` or `SourceReferenceInput`. |
| `cipher` | `CipherSpec` | **required** | Cipher family and cipher-specific parameters. |
| `key_space` | `KeySpec` | **required** | Keys the solver may search. Must be compatible with the cipher. |
| `solver` | `SolverSpec` | **required** | Search method and its budget. |
| `scoring` | `ScoringConfig` | `ScoringConfig()` | Candidate scoring. |
| `initial_keys` | `InitialKeys | None` | `None` | Optional tuple of concrete starting keys. |
| `logging` | `LoggingConfig | None` | `None` | Enables saved run output when supplied. |
| `word_length_policy` | `WordLengthPolicy` | `INFER` | `INFER` preserves or derives WLI, `REQUIRE` fails when aligned WLI is unavailable, and `DISABLED` removes WLI. WLI-required scoring cannot be combined with `DISABLED`. |
| `text_direction` | `TextDirection` | `LTR` | `LTR` or `RTL`; long aliases are also available. English `RuneInput` conversion uses this value. |
| `compute_device` | `ComputeDevice` | `CPU` | `CPU` or `CUDA`. |
| `telemetry_enabled` | `bool` | `True` | Collect run telemetry. |
| `text_permutation` | `IndexPermutation | None` | `None` | Optional permutation of text positions. Must be a complete `0..n-1` permutation. |
| `interruptors` | `InterruptorConfig | None` | `None` | Exact or searched interruptor positions. |

For an index-format `RuneInput`, a supplied `text_permutation` must have the
same length as the input indices.

## api.run runtime controls

When a `RunSpec` is passed directly, one runtime-only control may also be
supplied:

| Parameter | Type | Default | Purpose / constraint |
| --- | --- | --- | --- |
| `progress_callback` | `ProgressCallback | None` | `None` | Called with one JSON-safe progress mapping. Must be callable. |

Progress cadence is solver-specific. Generic solver events include
`best_key` as a list of integers when a candidate key is available. Hybrid
events identify their child phase, and the two-period solver emits its existing
stage summaries. Exceptions raised by the callback propagate to the caller.

`api.run(...)` also has a keyword form that accepts the durable `RunSpec`
components directly. The defaults are the same as the table above.

For practical use, see [Building a run](../../guides/building_a_run.md).
