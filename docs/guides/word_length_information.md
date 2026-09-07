# Word-length information (WLI)

WLI records the position of each rune inside its word:

```text
(position_in_word, word_length)
```

A three-rune word is represented as:

```text
(0, 3)  (1, 3)  (2, 3)
```

## Where WLI comes from

For `RuneInput`, spaces can be used to derive WLI when the text is prepared
for the solver.

For prepared rune data, WLI can be supplied directly:

```python
problem_input = api.RuneInput(
    value=ct_idx,
    word_length_information=wli,
)
```

For a normal Liber Primus run, a named source carries its ciphertext and WLI
through the run-input boundary:

```python
problem_input = api.liber_primus.source("welcome_pilgrim")
```

When you need to inspect the numeric data directly, load the corresponding
source data:

```python
source_data = api.liber_primus.load_source(
    "welcome_pilgrim"
)
```

## Why WLI matters

The default scorer has both character and word-length lanes enabled. WLI gives
the second lane information that is not present in the bare rune stream.

When the word boundaries are part of the source, this can improve the search.
When the boundaries are uncertain, WLI becomes another hypothesis and is best
tested as such.

A clean comparison keeps the rest of the run fixed:

```text
character scoring only
vs
character + WLI scoring
```

The WLI lane can be disabled with:

```python
scoring = api.ScoringConfig(
    wli_lane_enabled=False,
)
```

`wli_lane_enabled=True` is the library default.

See [Scoring](scoring.md) for the scoring side and
[Scoring parameters](../reference/parameters/scoring.md) for the complete
configuration.

## Related run settings

`RunSpec.word_length_policy` controls how WLI is treated by the run. The default
is `WordLengthPolicy.INFER`.

The full field definition is in
[RunSpec parameters](../reference/parameters/run_spec.md).

For the input side, see [Ciphertext input](ciphertext_input.md). For the scoring
side, see [Scoring](scoring.md).
