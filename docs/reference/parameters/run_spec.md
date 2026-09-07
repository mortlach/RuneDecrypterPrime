# RunSpec and api.run parameters

## RunSpec

| Parameter | Type | Default | Purpose / constraint |
| --- | --- | --- | --- |
| `problem_input` | `ProblemInput` | **required** | `RawTextInput`, `RuneIndexInput`, or `SourceReferenceInput`. |
| `cipher` | `CipherSpec` | **required** | Cipher family and cipher-specific parameters. |
| `key_space` | `KeySpec` | **required** | Keys the solver may search. Must be compatible with the cipher. |
| `solver` | `SolverSpec` | **required** | Search method and its budget. |
| `scoring` | `ScoringConfig` | `ScoringConfig()` | Candidate scoring. |
| `initial_keys` | `InitialKeys | None` | `None` | Optional tuple of concrete starting keys. |
| `logging` | `LoggingConfig | None` | `None` | Enables saved run output when supplied. |
| `word_length_policy` | `WordLengthPolicy` | `INFER` | `DISABLED`, `INFER`, or `REQUIRE`. |
| `text_direction` | `TextDirection` | `RTL` | `LTR` or `RTL`; long aliases are also available. |
| `compute_device` | `ComputeDevice` | `CPU` | `CPU` or `CUDA`. |
| `telemetry_enabled` | `bool` | `True` | Collect run telemetry. |
| `text_permutation` | `IndexPermutation | None` | `None` | Optional permutation of text positions. Must be a complete `0..n-1` permutation. |
| `interruptors` | `InterruptorConfig | None` | `None` | Exact or searched interruptor positions. |

For `RuneIndexInput`, a supplied `text_permutation` must have the same length as
the input indices.

## api.run runtime controls

When a `RunSpec` is passed directly, two runtime-only controls may also be
supplied:

| Parameter | Type | Default | Purpose / constraint |
| --- | --- | --- | --- |
| `progress_callback` | `ProgressCallback | None` | `None` | Called with progress data. Must be callable. |
| `progress_interval` | `int | None` | `None` | Progress interval. Must be at least `1` when supplied. |

`api.run(...)` also has a keyword form that accepts the durable `RunSpec`
components directly. The defaults are the same as the table above.

For practical use, see [Defining a run](../../guides/anatomy_of_a_run.md).

See also [Parameter reference](README.md) and [Defaults at a glance](../defaults.md).
