# SolverSpec parameters

`seed` is optional on every public solver. It defaults to `None`.

The tables below show the **public request defaults**.

Some omitted values are resolved later by the runtime. Those effective defaults
are listed separately at the end of this page. This distinction matters for
reproducibility: `None` in a `SolverSpec` does not always mean the runtime
feature is disabled.

## Beam search

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `width` | `int` | `64` | At least `1`. |
| `rounds` | `int` | `0` (auto) | At least `0`. |
| `restarts` | `int` | `1` | At least `1`. |
| `expansion` | `BeamExpansionMode` | `SWEEP` | `EXHAUSTIVE`, `SAMPLE`, or `SWEEP`. |
| `maximum_children_per_parent` | `int | None` | `None` | At least `1` when supplied. |
| `sample_per_parent` | `int | None` | `None` | At least `1` when supplied. |
| `top_parents_fraction` | `float` | `0.5` | Greater than `0` and at most `1`. |
| `plateau_rounds` | `int | None` | `None` | At least `1` when supplied. |
| `plateau_minimum_delta` | `float` | `0.0` | Finite. |
| `target_score` | `float | None` | `None` | Finite when supplied. |
| `seed` | `int | None` | `None` | Solver seed. |

## Genetic algorithm

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `population_size` | `int` | **required** | At least `1`. |
| `generations` | `int` | **required** | At least `1`. |
| `elite_fraction` | `float` | `0.1` | In `0..1`. |
| `mutation_probability` | `float` | `0.2` | In `0..1`. |
| `crossover_fraction` | `float` | `0.8` | In `0..1`. |
| `tournament_size` | `int` | `3` | At least `2`. |
| `plateau_generations` | `int | None` | `None` | At least `1` when supplied. |
| `plateau_minimum_delta` | `float` | `0.0` | Finite. |
| `target_score` | `float | None` | `None` | Finite when supplied. |
| `seed` | `int | None` | `None` | Solver seed. |

## Simulated annealing

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `iterations` | `int` | **required** | At least `1`. |
| `initial_temperature` | `float | None` | `None` | Finite when supplied. |
| `minimum_temperature` | `float | None` | `None` | Finite when supplied. |
| `cooling_rate` | `float | None` | `None` | Finite when supplied. |
| `automatic_cooling` | `bool` | `False` | Boolean. |
| `reseed_interval` | `int | None` | `None` | At least `0` when supplied. |
| `local_improvement_on_accept` | `bool` | `False` | Boolean. |
| `rescue_drop_absolute` | `float | None` | `None` | Finite when supplied. |
| `rescue_drop_ratio` | `float | None` | `None` | Finite when supplied. |
| `plateau_iterations` | `int | None` | `None` | At least `1` when supplied. |
| `plateau_minimum_delta` | `float` | `0.0` | Finite. |
| `target_score` | `float | None` | `None` | Finite when supplied. |
| `seed` | `int | None` | `None` | Solver seed. |

## Hybrid

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `genetic_algorithm` | GA `SolverSpec` | **required** | Must be a genetic-algorithm spec. |
| `simulated_annealing` | SA `SolverSpec` | **required** | Must be a simulated-annealing spec. |
| `use_beam_search` | `bool` | `True` | Enables the beam phase. |
| `beam_width` | `int | None` | `None` | At least `1` when supplied. |
| `beam_rounds` | `int | None` | `None` | At least `0` when supplied. |
| `beam_expansion` | `BeamExpansionMode` | `SWEEP` | See [Common enums](enums.md). |
| `sample_per_parent` | `int | None` | `None` | At least `1` when supplied. |
| `top_parents_fraction` | `float` | `0.5` | Greater than `0` and at most `1`. |
| `plateau_rounds` | `int | None` | `None` | At least `1` when supplied. |
| `plateau_minimum_delta` | `float` | `0.0` | Finite. |
| `target_score` | `float | None` | `None` | Finite when supplied. |
| `seed` | `int | None` | `None` | Solver seed. |

## Kaeding

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `steps` | `int` | **required** | At least `1`. |
| `restarts` | `int` | **required** | At least `1`. |
| `inner_batch_size` | `int` | **required** | At least `1`. |
| `block_schedule` | `KaedingBlockSchedule` | `ROUND_ROBIN` | `RANDOM` or `ROUND_ROBIN`. |
| `column_batch_size` | `int` | `0` | At least `0`. |
| `column_interval` | `int` | `0` | At least `0`. |
| `slip_blocks` | `int` | `0` | At least `0`. |
| `slip_interval` | `int` | `0` | At least `0`. |
| `slip_policy` | `KaedingSlipPolicy` | `FIXED_INTERVAL` | `FIXED_INTERVAL` or `ON_STALL`. |
| `slip_swaps` | `int` | `0` | At least `0`. |
| `stall_rounds` | `int` | `0` | At least `0`. |
| `stall_slip_limit` | `int` | `0` | At least `0`. |
| `stop_after_stall_slip_limit` | `bool` | `False` | Boolean. |
| `plateau_rounds` | `int | None` | `None` | At least `1` when supplied. |
| `plateau_minimum_delta` | `float` | `0.0` | Finite. |
| `target_score` | `float | None` | `None` | Finite when supplied. |
| `seed` | `int | None` | `None` | Solver seed. |

## Two-period crib search

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `fixed_cribs` | sequence of `(word, position)` | empty | Words are ASCII letters. Positions are non-negative. |
| `candidate_words` | sequence of `str` | empty | Words are ASCII letters. |
| `candidate_positions` | mapping or `None` | `None` | Keys must be listed in `candidate_words`. Positions are non-negative. |
| `starts` | `int` | `96` | At least `1`. |
| `seed` | `int | None` | `None` | Solver seed. |

At least one fixed crib or candidate word is required.

## Serialized construction

`SolverSpec.from_name(name, parameters=None)` reconstructs a public solver spec
from serialized parameters. A serialized seed is accepted as part of that
mapping.

For practical use, see [Solvers](../../guides/solvers.md).

See also [Parameter reference](README.md) and [Defaults at a glance](../defaults.md).

## Effective runtime defaults

The engine fills a few values after the public `SolverSpec` has been translated
to runtime configuration.

### Plateau rounds

When the public plateau field is omitted, the current runtime inserts:

| Solver | Public request | Effective runtime |
| --- | --- | --- |
| Beam | `plateau_rounds=None` | `16` |
| GA | `plateau_generations=None` | `24` rounds |
| SA | `plateau_iterations=None` | `300` iterations |
| Hybrid | `plateau_rounds=None` | `24` rounds |
| Kaeding | `plateau_rounds=None` | `360` rounds |

The public `plateau_minimum_delta` default is `0.0`, and that value is passed
through to the runtime.

### Beam rounds

`rounds=0` is accepted by the public Beam constructor and means automatic
runtime rounds:

```text
max(2 * key_length, 12)
```

It is not a zero-work search.

### Simulated annealing temperatures

When the public SA temperature fields are `None`, the current runtime uses:

```text
initial_temperature = 1.0
minimum_temperature = 0.001
cooling_rate = 0.995
```

`automatic_cooling=False` remains the public and runtime default.

### Hybrid beam phase

`use_beam_search=True` is the public default.

If the beam phase is enabled and `beam_width=None`, the runtime uses a beam
width of `16`.

If `beam_rounds=None`, the Beam phase reaches Beam's normal automatic-round
behaviour.

These runtime defaults are current implementation behaviour. They are recorded
here because they affect the actual search even though the durable request may
contain `None`.

See [Solvers](../../guides/solvers.md) and
[Repeating a run](../../guides/reproducibility.md).


## Typed identity

`kind` identifies the selected SolverSpec family. Constructor arguments are
exposed through its immutable `parameters` mapping. Use the typed constructors
for new requests and the existing parsers for serialized data.
