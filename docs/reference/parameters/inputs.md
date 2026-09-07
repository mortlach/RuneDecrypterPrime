# Problem input parameters

## RawTextInput

```python
api.RawTextInput(text=...)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `text` | `str` | **required** | Non-empty string. |

The current normalisation route accepts rune text and Latin text. Spaces are
used when deriving WLI.

## RuneIndexInput

```python
api.RuneIndexInput(
    indices=...,
    word_length_information=...,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `indices` | ordered sequence of `int` | **required** | Non-empty. Every value must be in `0..28`. |
| `word_length_information` | WLI sequence or `None` | `None` | One `(position, word_length)` pair per rune when supplied. |

For every WLI pair, `position >= 0`, `word_length > 0`, and
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

Each LP source kind has a stricter reference shape enforced by the resolver.
Use `api.liber_primus.source(label)` for a named run input. The `load_source`
helpers are useful when direct numerical inspection is needed.

For practical use, see [Ciphertext input](../../guides/ciphertext_input.md).

See also [Parameter reference](README.md) and [Defaults at a glance](../defaults.md).
