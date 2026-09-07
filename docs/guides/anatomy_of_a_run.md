# Defining a run

`RunSpec` describes one solve.

Four fields are required:

```text
problem_input
cipher
key_space
solver
```

Everything else is optional or has a library default.

## Problem input

The input may be raw text, prepared rune indices, or a registered source:

```python
api.RawTextInput(...)
api.RuneIndexInput(...)
api.SourceReferenceInput(...)
```

See [Ciphertext input](ciphertext_input.md).

## Cipher

The cipher states the family being tested:

```python
cipher = api.CipherSpec.vigenere()
```

The current public surface also includes Autokey, columnar, rail fence,
substitution, periodic substitution, periodic columnar and the scheduled-stream
families.

The cipher defines what a concrete key means.

## Key space

The key space defines which keys are valid:

```python
key_space = api.KeySpec.repeating(
    length=7,
)
```

That choice also determines the runtime key operations available to the solver.

A repeating key is searched as a vector. A permutation key is mutated and
recombined with permutation-safe operations. Structured periodic keys preserve
their own block structure.

The solver therefore works with generic key operations rather than knowing the
representation of every key family.

See [Keys and key spaces](keyops.md). The runtime binding is described in
[Key models and search operations](../architecture/key_model_and_search.md).

## Solver

The solver controls how the key space is explored:

```python
solver = api.SolverSpec.beam_search(
    width=96,
    rounds=12,
    seed=12345,
)
```

Beam search, genetic algorithm, simulated annealing, hybrid, Kaeding and the
two-period crib solver are available through `SolverSpec`.

The solver chooses which key to evaluate next. It does not define the cipher or
the scoring model.

See [Solvers](solvers.md).

## Scoring

`ScoringConfig()` is the default.

The ordinary language-model lanes are character n-grams and WLI n-grams. Both
are enabled by default.

```python
scoring = api.ScoringConfig(
    character_lane_enabled=True,
    wli_lane_enabled=True,
    character_order_weights={1: 0.3, 2: 0.7},
    wli_order_weights={1: 0.3, 2: 0.7},
)
```

The scorer ranks candidate plaintexts. Search remains the solver's job.

See [Scoring](scoring.md) and
[Scoring and language models](../architecture/scoring_and_language_models.md).

## Other run fields

The current defaults are:

| Field | Default |
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

See [RunSpec parameters](../reference/parameters/run_spec.md) for the full
contract.

## Run

```python
request = api.RunSpec(
    problem_input=problem_input,
    cipher=cipher,
    key_space=key_space,
    solver=solver,
)

result = api.run(request)
```

See [Reading a result](results.md) for the return value and
[Run pipeline](../architecture/pipeline.md) for the runtime path.
