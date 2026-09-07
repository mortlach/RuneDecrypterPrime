# api.liber_primus parameters

The namespace returns loaded Liber Primus data and typed source references.

## Named source

```python
api.liber_primus.source(label)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `label` | `str` | **required** | Registered source label or alias. |

Returns `SourceReferenceInput` with canonical source label and the current
transcript asset ID/version. Resolve it through `RunSpec.problem_input`.

For direct numeric inspection, `api.liber_primus.load_source(label)` returns
`SourceData` containing `indices`, `word_length_information` and source
metadata. Its shorter `ct_idx` and `wli` properties are convenient when working
with the data. It does not replace the source reference used by a normal run.

## Main transcript

```python
api.liber_primus.load_main_transcript(
    attach_catalogue=True,
)
```

| Parameter | Type | Default | Purpose |
| --- | --- | --- | --- |
| `attach_catalogue` | `bool` | `True` | Attach the source catalogue to the parsed transcript. |

## Section data

```python
api.liber_primus.get_section(
    section_id,
    split="page",
)
```

```python
api.liber_primus.load_section_indices(
    section_id,
    split="page",
)
```

```python
api.liber_primus.load_section_inputs(
    section_id,
    split="page",
)
```

The section helpers share these parameters:

| Parameter | Type | Default | Purpose |
| --- | --- | --- | --- |
| `section_id` | `int` | **required** | Section identifier. |
| `split` | `str` | `"page"` | Section split used by the LP data view. |

`load_section_indices` returns `(ct_idx, wli)`. `load_section_inputs` returns the
same data in a small input mapping.

## Main-transcript section

```python
api.liber_primus.load_main_section_indices(
    section_id,
    split="page",
)
```

The parameters are the same as the section helpers above, but the data is
extracted from the parsed main transcript.

## Complete main pages

```python
api.liber_primus.load_source_from_main_pages(
    start_page,
    end_page=None,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `start_page` | `int` | **required** | Zero-based main-transcript page, at least `0`. |
| `end_page` | `int | None` | `None` | `None` selects one page. Otherwise not below `start_page`. |

## Fragment locator

```python
api.liber_primus.FragmentLocator(
    page_ref=...,
    line=None,
    line_end=None,
    word=None,
    word_end=None,
)
```

| Parameter | Type | Default | Purpose |
| --- | --- | --- | --- |
| `page_ref` | `PageReference` | **required** | Page identity. |
| `line` | `int | None` | `None` | Optional starting line. |
| `line_end` | `int | None` | `None` | Optional ending line. |
| `word` | `int | None` | `None` | Optional starting word. |
| `word_end` | `int | None` | `None` | Optional ending word. |

A locator becomes loaded source data with:

```python
api.liber_primus.load_source_from_locator(
    locator,
    line_mode=None,
    selector=None,
    spiral_route=None,
)
```

| Parameter | Type | Default | Purpose |
| --- | --- | --- | --- |
| `locator` | `FragmentLocator` | **required** | Fragment to load. |
| `line_mode` | `LineReadMode | None` | `None` | Optional line-reading route. |
| `selector` | `LineRuneSelector | None` | `None` | Effective default is `ALL`. |
| `spiral_route` | `SpiralRoute | None` | `None` | Optional spiral-reading route. |

`LineReadMode` values are `LEFT_TO_RIGHT`, `RIGHT_TO_LEFT` and
`BOUSTROPHEDON`. `LineRuneSelector` values are `ALL`, `FIRST_ONLY` and
`LAST_ONLY`.

## SpiralRoute

```python
api.liber_primus.SpiralRoute(
    direction=...,
    start_corner=...,
    skip_empty=True,
)
```

The public namespace exports the route type. Its defaults are clockwise, top
left, and `skip_empty=True`.

## PageReference

`PageReference` identifies a transcript page using a page scheme and number.
The underlying type also provides constructors for transcript page ids,
bound-book pages and canon-unsolved pages.

Transcript and canon page numbers are zero-based. Bound-book page numbers start
at `1`.

## PartitionEntry

```python
api.liber_primus.PartitionEntry(
    scheme=...,
    ordinal=...,
    start_page=...,
    end_page=...,
    display_name=None,
    tags=(),
)
```

A partition entry becomes loaded source data with:

```python
api.liber_primus.load_source_from_partition_entry(
    entry,
    intersect_page_ref=None,
)
```

| Parameter | Type | Default | Purpose |
| --- | --- | --- | --- |
| `entry` | `PartitionEntry` | **required** | Registered or constructed partition span. |
| `intersect_page_ref` | `PageReference | None` | `None` | Optional page intersection. |

For practical use, see [Ciphertext input](../../guides/ciphertext_input.md).

See also [Parameter reference](README.md) and [Defaults at a glance](../defaults.md).
