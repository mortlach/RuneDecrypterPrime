# Liber Primus data

The public LP namespace is:

```python
api.liber_primus
```

It provides typed access to the bundled main transcript and solver-ready
payloads.

For the normal solving route, start with
[Ciphertext input](../guides/ciphertext_input.md).

## Named sources

The simplest route for a known source is a label:

```python
payload = api.liber_primus.payload_from_label(
    "welcome_pilgrim"
)
```

The returned solver payload contains:

```text
payload.ct_idx
payload.wli
payload.metadata
```

The metadata includes the canonical source label and the information used to
identify the selected LP material.

That keeps source identity, ciphertext and word information together.

See [Word-length information](../guides/word_length_information.md).

## Use the payload in a run

A solver payload can go directly into `RuneIndexInput`:

```python
problem_input = api.RuneIndexInput(
    indices=payload.ct_idx,
    word_lengths=payload.wli,
)
```

The rest of the run uses the normal public API.

See [Defining a run](../guides/anatomy_of_a_run.md).

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

Complete main-transcript page spans can be turned into solver payloads:

```python
payload = api.liber_primus.payload_from_main_pages(
    start_page,
    end_page,
)
```

## Locators

Typed fragment locators can select a page, line range or other registered
fragment.

Line and spiral routes are available through the LP route types.

```python
payload = api.liber_primus.payload_from_locator(
    locator
)
```

## Partitions

Registered partition entries can also be converted to solver payloads:

```python
payload = api.liber_primus.payload_from_partition_entry(
    entry
)
```

## SourceReferenceInput

A `RunSpec` can also carry a registered LP source reference directly.

The built-in resolver supports label, locator and partition source kinds.

For many solving scripts, loading a solver payload first is simpler because the
ciphertext, WLI and source metadata are immediately available together.

The direct source-reference route is useful when source identity itself should
be part of the durable request.

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
