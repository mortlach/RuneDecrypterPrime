# Defaults at a glance

These are library defaults, not tutorial recommendations.

The full parameter tables are under
[Parameter reference](parameters/README.md).

## RunSpec

| Parameter | Default |
| --- | --- |
| `scoring` | `ScoringConfig()` |
| `initial_keys` | `None` |
| `logging` | `None` |
| `word_length_policy` | `WordLengthPolicy.INFER` |
| `text_direction` | `TextDirection.RTL` |
| `compute_device` | `ComputeDevice.CPU` |
| `telemetry_enabled` | `True` |
| `text_permutation` | `None` |
| `interruptors` | `None` |

`problem_input`, `cipher`, `key_space` and `solver` are required.

See [RunSpec parameters](parameters/run_spec.md) and
[Defining a run](../guides/anatomy_of_a_run.md).

## ScoringConfig

The main defaults are:

| Parameter | Default |
| --- | --- |
| character lane | enabled |
| WLI lane | enabled |
| character n-gram order | `2` |
| WLI n-gram order | `2` |
| objective | percentile log probability, window `10` |
| backend | `AUTO` |
| compute dtype | `FLOAT32` |
| accumulator dtype | `FLOAT64` |
| Hamming | disabled |
| span-Hamming | disabled |
| word n-gram judge | disabled |

See [Scoring](../guides/scoring.md) and
[Scoring parameters](parameters/scoring.md).

## LoggingConfig

| Parameter | Default |
| --- | --- |
| `verbose` | `False` |
| `show_progress` | `True` |
| `write_event_log` | `False` |
| `output_root` | `None` |
| `run_category` | `"run"` |
| `label` | `None` |
| `run_directory` | `None` |
| `redact_identity` | `False` |
| `portable_output` | `True` |
| `write_solver_report` | `False` |
| `write_display_summary` | `False` |
| `write_artifact_manifest` | `False` |

See [Outputs](../guides/outputs.md) and
[Logging parameters](parameters/logging.md).

## Solver and component defaults

Solver defaults vary by constructor because each solver has a different search
model.

Cipher and key constructors likewise have defaults only where there is a
sensible ordinary value.

Use:

- [Cipher parameters](parameters/ciphers.md)
- [Key parameters](parameters/keys.md)
- [Solver parameters](parameters/solvers.md)
- [Interruptor parameters](parameters/interruptors.md)

for the exact constructor defaults.

## Solver request and runtime defaults

Solver constructor tables show public request defaults. A few `None` or zero
values are resolved by the runtime.

Notably:

- Beam `plateau_rounds=None` -> effective `16`
- GA `plateau_generations=None` -> effective `24`
- SA `plateau_iterations=None` -> effective `300`
- Hybrid `plateau_rounds=None` -> effective `24`
- Kaeding `plateau_rounds=None` -> effective `360`
- Beam `rounds=None` -> `max(2 * key_length, 12)`
- SA omitted temperatures -> `1.0`, `0.001`, `0.995`
- Hybrid enabled beam with no width -> width `16`

See [Solver parameters](parameters/solvers.md).

Beam can be constructed with `SolverSpec.beam_search()`: width `64`, rounds
`None` (automatic), and requested seed `None` with effective seed `0`. Other solver
settings and the default scoring configuration are unchanged.
