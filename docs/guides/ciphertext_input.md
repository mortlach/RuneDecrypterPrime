# Ciphertext input

`RunSpec` accepts three public input forms:

```python
api.RawTextInput(...)
api.RuneIndexInput(...)
api.SourceReferenceInput(...)
```

They cover the three common cases: text, prepared rune data, and a registered
source.

## Text input

`RawTextInput` accepts a non-empty string:

```python
problem_input = api.RawTextInput(
    text="ᚠᚢᚦ ᚩᚱᚳ",
)
```

Rune strings and ordinary Latin text are accepted by the current normalisation
route. Spaces are preserved as word boundaries and can be used to derive WLI.

## Rune-index input

Use `RuneIndexInput` when the ciphertext is already in canonical rune indices:

```python
problem_input = api.RuneIndexInput(
    indices=(1, 28, 21, 15, 12, 0),
)
```

WLI can be supplied with the same input:

```python
problem_input = api.RuneIndexInput(
    indices=ct_idx,
    word_length_information=wli,
)
```

`indices` must contain values from `0` to `28`. If
`word_length_information` is supplied,
it must contain one WLI pair for each rune.

## Liber Primus sources

The `api.liber_primus` namespace provides solver-ready data from the bundled
transcript and source catalogue:

```python
problem_input = api.liber_primus.source("welcome_pilgrim")
```

This returns a source reference preserving the canonical label and transcript
version. The run resolves the ciphertext and WLI. Use `load_source` when you
want the numeric data and metadata directly.

## Registered source references

`SourceReferenceInput` records the identity of a registered source in the run
request. The built-in resolver currently supports Liber Primus labels, locators
and partitions.

This is useful when source identity is part of the experiment and should be
recorded with it.

## Conversion and display

RDP also contains public display and conversion helpers for rendering solver
data and moving between supported text forms. These are separate from the
`RunSpec` input itself. The run request still records one explicit input form.

The exact constructor parameters are listed in
[Problem input parameters](../reference/parameters/inputs.md).

## Where this appears in the tutorials

`tutorials/v1/getting_started/07_liber_primus_source.py` loads a named Liber
Primus source and inspects its recorded identity.

`tutorials/v1/getting_started/10_prepare_a_real_source_search.py` carries that
source data into a full `RunSpec`.

See [Tutorials and examples](../tutorials/README.md).

For the word-information side, continue with
[Word-length information](word_length_information.md). For the registered LP
source API, see [Liber Primus data](../reference/liber_primus.md).
