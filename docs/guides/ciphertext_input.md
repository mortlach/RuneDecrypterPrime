# Ciphertext input

Most runs start with `RuneInput`:

```python
problem_input = api.RuneInput("THE LOSS OF")
```

It accepts four representations and records the resolved format on
`problem_input.format`.

| Supplied value | Inferred format |
| --- | --- |
| A sequence of integers | `RuneInputFormat.INDICES` |
| A string containing rune glyphs | `RuneInputFormat.RUNES` |
| Latin rune tokens separated by `·` or `|` | `RuneInputFormat.RUNE_LATIN` |
| Other Latin text | `RuneInputFormat.ENGLISH` |

Inference is deterministic. If a short value would be ambiguous, state the
format explicitly:

```python
problem_input = api.RuneInput(
    "TH",
    format=api.RuneInputFormat.RUNE_LATIN,
)
```

## Text forms

Spaces mark word boundaries in rune, RuneLatin, and English input:

```python
runes = api.RuneInput("ᚦᛖ ᛚᚩᛋᛋ")
rune_latin = api.RuneInput("TH·E L·O·S·S")
english = api.RuneInput("THE LOSS")
```

`|` is accepted as a keyboard-friendly RuneLatin delimiter. RDP renders the
canonical form with the middle dot: `TH·E`, not `TH|E`.

English is converted after the input is attached to a `RunSpec`, because its
rune tokenisation depends on `text_direction`. The default is `LTR`; set `RTL`
explicitly when that is the intended encoding:

```python
request = api.RunSpec(
    problem_input=api.RuneInput("THE LOSS"),
    # ...cipher, key_space, and solver...
    text_direction=api.TextDirection.RTL,
)
```

Rune glyphs and Latin characters cannot be mixed in the same input string.

## Rune indices and WLI

Prepared indices can include word-length information:

```python
problem_input = api.RuneInput(
    ct_idx,
    word_length_information=wli,
)
```

Indices must be in `0..28`. WLI must contain one `(position, word_length)` pair
per index. Text inputs derive WLI from spaces, so explicit WLI is accepted only
with index input.

## Liber Primus sources

Use a registered source when its identity is part of the run:

```python
problem_input = api.liber_primus.source("welcome_pilgrim")
```

This returns a `SourceReferenceInput`. The run resolves the canonical
ciphertext and WLI while retaining the source label and transcript version.

See [Problem input parameters](../reference/parameters/inputs.md),
[Text direction](text_direction.md), and
[Word-length information](word_length_information.md).
