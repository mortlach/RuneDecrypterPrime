# V1 Configuration Objects

Status: implemented

Public request/configuration values are immutable, typed, inspectable,
serializable, comparable, hashable where their values permit it, and stable for
replay. Typed constructors are the normal authoring route.

## Inputs

| Type | Fields |
| --- | --- |
| `RawTextInput` | `text` |
| `RuneIndexInput` | `indices`, `word_lengths` |
| `SourceReferenceInput` | `source_kind`, `asset_id`, `asset_version`, `reference` |

Rune indices are integers in `0..28`. Word-length data is an ordered sequence
of `(position, word_length)` pairs. Source-reference metadata is restricted to
portable JSON primitives.

## RunSpec

| Field | Meaning |
| --- | --- |
| `problem_input` | Typed problem input. |
| `cipher` | `CipherSpec`. |
| `key_space` | Compatible `KeySpec`. |
| `solver` | `SolverSpec`. |
| `scoring` | `ScoringConfig`. |
| `initial_keys` | Optional immutable seed keys. |
| `logging` | Optional `LoggingConfig`. |
| `word_length_policy` | Word-length resolution policy. |
| `text_direction` | Public text direction. |
| `compute_device` | Requested compute device. |
| `telemetry_enabled` | Telemetry boolean. |
| `text_permutation` | Optional full permutation. |
| `interruptors` | Optional interruptor configuration. |

## CipherSpec, KeySpec, and SolverSpec

`CipherSpec` stores `kind` and immutable `_parameter_items`. `KeySpec` stores
`kind` and immutable `_parameter_items`. `SolverSpec` stores `kind`, `seed`,
and immutable `_parameter_items`. The public `parameters` view is read-only;
the underscore field is the single canonical storage representation, not a
second user-facing model.

Examples:

```python
cipher = api.CipherSpec.periodic_columnar(
    period=13,
    columns=7,
    order=api.advanced.PeriodicColumnarOrder.COLUMNAR_THEN_SUBSTITUTION,
)
key_space = api.KeySpec.periodic_columnar(period=13, columns=7)
solver = api.SolverSpec.genetic_algorithm(
    population_size=128,
    generations=80,
    seed=42,
)
```

## LoggingConfig

| Field | Meaning |
| --- | --- |
| `verbose` | Verbose logging. |
| `show_progress` | Console progress display. |
| `write_event_log` | Structured event-log output. |
| `output_root` | Explicit `Path` output root. |
| `run_category` | Non-empty run category. |
| `label` | Optional run label. |
| `run_directory` | Optional explicit `Path` run directory. |
| `redact_identity` | Redact machine/user identity. |
| `portable_output` | Portable output policy. |
| `write_solver_report` | Solver-report artifact toggle. |
| `write_display_summary` | Display-summary artifact toggle. |
| `write_artifact_manifest` | Artifact-manifest toggle. |

## Enum values

| Public enum | Serialized value |
| --- | --- |
| `TextDirection.LEFT_TO_RIGHT` | `"left_to_right"` |
| `TextDirection.RIGHT_TO_LEFT` | `"right_to_left"` |
| `ComputeDevice.CPU` | `"cpu"` |
| `ComputeDevice.CUDA` | `"cuda"` |

Raw strings are accepted only by explicit parser boundaries. Typed constructors
and `RunSpec` require the enum objects themselves.
