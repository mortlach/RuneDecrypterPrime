# Problem input parameters

## RuneInput

```python
api.RuneInput(
    value,
    format=None,
    word_length_information=None,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `value` | `str` or ordered sequence of `int` | **required** | Non-empty text, or non-empty indices in `0..28`. |
| `format` | `RuneInputFormat | None` | `None` | Inferred when omitted. Must agree with the value type when supplied. |
| `word_length_information` | WLI sequence or `None` | `None` | Accepted only for index input; one pair per index. |

Inference rules, in order:

1. An integer sequence is `INDICES`.
2. Text containing rune glyphs is `RUNES`.
3. Text containing `·` or `|` is `RUNE_LATIN`.
4. Other Latin text is `ENGLISH`.

`RuneInputFormat` values are `INDICES`, `RUNES`, `RUNE_LATIN`, and `ENGLISH`.
RuneLatin accepts `|` on input but renders with `·`. Spaces delimit words in
all text formats. Explicit WLI cannot be combined with text input.

English conversion uses `RunSpec.text_direction`; its default is `LTR`.

For each WLI pair, `position >= 0`, `word_length > 0`, and
`position < word_length`.

## SourceReferenceInput

```python
api.SourceReferenceInput(
    source_kind=...,
    asset_id=...,
    asset_version=...,
    reference=...,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `source_kind` | `str` | **required** | Non-empty. Built-in LP kinds are listed below. |
| `asset_id` | `str` | **required** | Non-empty source identity. |
| `asset_version` | `str` | **required** | Non-empty source version. |
| `reference` | mapping | empty mapping | Flat JSON-primitive metadata. |

Built-in Liber Primus source kinds are:

```text
liber_primus.label
liber_primus.locator
liber_primus.partition
```

Use `api.liber_primus.source(label)` for a named run input. The `load_source`
helpers return the numerical data when direct inspection is needed.

For practical use, see [Ciphertext input](../../guides/ciphertext_input.md).
