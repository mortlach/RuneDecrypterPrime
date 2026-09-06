# Scoring

Scoring gives the solver a way to rank candidate plaintexts.

The default `ScoringConfig` enables two language-model lanes:

- character n-grams
- word-length n-grams

Both default n-gram orders are `2`.

## Where the language model sits

The solver proposes keys. The cipher decrypts them. The scorer sees the
candidate plaintext and WLI and turns that evidence into a score.

Character and WLI n-gram tables are loaded by the language-model runtime.
Direction, n-gram order and objective determine how that evidence is used.

For the internal path, see
[Scoring and language models](../architecture/scoring_and_language_models.md).

## Character lane

The character lane scores rune sequences. It is enabled by default:

```python
scoring = api.ScoringConfig(
    character_lane_enabled=True,
)
```

## Word-length lane

The WLI lane uses the word-position information attached to the input. It is
also enabled by default:

```python
scoring = api.ScoringConfig(
    word_length_lane_enabled=True,
)
```

See [Word-length information](word_length_information.md).

If the input has no meaningful word boundaries, the lane can be disabled:

```python
scoring = api.ScoringConfig(
    character_lane_enabled=True,
    word_length_lane_enabled=False,
)
```

## Order weights

Weights can be supplied per n-gram order:

```python
scoring = api.ScoringConfig(
    character_order_weights={1: 0.3, 2: 0.7},
    word_length_order_weights={1: 0.3, 2: 0.7},
)
```

If no explicit order-weight map is supplied, the scorer uses the rest of the
configuration to build its normal lane behaviour.

## Objective

The default objective is percentile log probability with a window size of 10.

Alternative typed objectives are exposed through
`api.advanced.ScoringObjective`.

The complete objective and scoring defaults are listed in
[Scoring parameters](../reference/parameters/scoring.md).

## Direction

Text direction is part of `RunSpec`, not `ScoringConfig`.

Directional scoring uses the direction supplied by the run:

```python
request = api.RunSpec(
    ...,
    text_direction=api.TextDirection.RIGHT_TO_LEFT,
)
```

See [Text direction](text_direction.md).

## Backend and numeric types

The default backend is `ScorerBackend.AUTO`.

The default compute dtype is `FLOAT32` and the accumulator dtype is `FLOAT64`.

These are execution choices rather than new cryptanalytic evidence, so they are
best changed separately when comparing performance or numerical behaviour.

See [CPU, CUDA and scoring](../setup/scorer_backend_selection.md).

## Specialist lanes

`ScoringConfig` also contains optional Hamming, span-Hamming, hard-crib and word
n-gram judge controls. They are off by default.

These options are useful for specific investigations and are documented in the
full [Scoring parameter reference](../reference/parameters/scoring.md).

New scoring ideas belong in the same scoring system rather than a parallel
solver path. See [Extending RDP](extending_rdp.md).

## Interpreting a score

A score ranks candidates under one scoring setup.

It is not a percentage solved and not a probability that the plaintext is
correct.

Known-answer recovery, where available, remains a separate check.

See [Reading a result](results.md).

## Runnable example

`tutorials/v1/getting_started/02_first_search.py` shows a small explicit scoring
configuration.

See [Tutorials and examples](../tutorials/README.md).
