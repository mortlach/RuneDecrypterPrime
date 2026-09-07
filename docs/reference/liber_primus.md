# Liber Primus data

The public LP namespace is:

```python
api.liber_primus
```

It provides typed access to the bundled main transcript and loaded source data.

For the normal solving route, start with
[Ciphertext input](../guides/ciphertext_input.md).

## Named sources

For a normal run, use a named, versioned source reference:

```python
problem_input = api.liber_primus.source("welcome_pilgrim")
```

The returned `SourceReferenceInput` preserves the canonical label, asset ID and
transcript version. Pass it directly as `RunSpec.problem_input`. The existing
resolver loads ciphertext/WLI and rejects a mismatched installed transcript.
Unknown labels raise `KeyError`. No local path is part of the reference.

### Loading source data

`api.liber_primus.load_source(label)` loads numeric rune indices, WLI and source
metadata directly. It returns `SourceData`, not a run-input reference. Use
`source(label)` for an ordinary named-source run so the request retains its
source identity.

## Main transcript

Load the parsed main transcript with:

```python
doc = api.liber_primus.load_main_transcript()
```

## Sections

For the section view:

```python
ct_idx, wli = api.liber_primus.load_section_indices(
    section_id
)
```

or:

```python
section = api.liber_primus.get_section(
    section_id
)
```

## Page spans

Complete main-transcript page spans can be loaded as source data:

```python
source_data = api.liber_primus.load_source_from_main_pages(
    start_page,
    end_page,
)
```

## Locators

Typed fragment locators can select a page, line range or other registered
fragment.

Line and spiral routes are available through the LP route types.

```python
source_data = api.liber_primus.load_source_from_locator(
    locator
)
```

## Partitions

Registered partition entries can also be loaded as source data:

```python
source_data = api.liber_primus.load_source_from_partition_entry(
    entry
)
```

## SourceReferenceInput

A `RunSpec` can also carry a registered LP source reference directly.

The built-in resolver supports label, locator and partition source kinds.

Use `source(label)` for ordinary named-source runs. `load_source(label)` is
useful when inspecting rune indices, WLI or metadata before constructing a
request.

See [Problem inputs](inputs.md).

## Parameters and examples

The complete helper and type parameters are listed in
[Liber Primus parameters](parameters/liber_primus.md).

`tutorials/v1/getting_started/07_liber_primus_source.py` is the numbered source
loading example.

`tutorials/v1/getting_started/10_prepare_a_real_source_search.py` carries LP data
into a full search request.

See [Tutorials and examples](../tutorials/README.md).

## Page labels and catalogue identity

A solved-source label identifies text, not a solve recipe. Aliases for a label
must resolve to the same `ct_idx` and WLI payload. Puzzle filenames are not
transcript indices: in the current catalogue `0.jpg` begins at transcript page
15, `56.jpg` identifies `an_end` at page 71, and `57.jpg` identifies `parable` at
page 72. Bound-book display numbers are another numbering system.

Use catalogue resolution rather than arithmetic on a filename. Source references
carry source identity and location. Solver budgets, key hints and interruptor
policy belong in the run's cipher/key/solver configuration.
