# Liber Primus solved source labels

This guide describes the first V1 source-label layer for solved Liber Primus
text fragments.

The rule is simple:

```text
source label = which LP text fragment
solve recipe = how RDP tries to solve or replay it
```

A source label must not include the method, key, stream, or shift. Those belong
in a recipe label.

## User-facing labels

Users can use short labels:

```text
warning
some_wisdom
welcome_pilgrim
koan_a_man
loss_of_divinity
koan_during_lesson
instruction
an_end
parable
```

The canonical internal source labels remain namespaced:

```text
red_rune.warning
red_rune.some_wisdom
red_rune.welcome_pilgrim
red_rune.koan_a_man
red_rune.loss_of_divinity
red_rune.koan_during_lesson
red_rune.instruction
red_rune.an_end
red_rune.parable
```

Aliases such as `solved.welcome_pilgrim` also resolve to the same source.

## Page-label terminology

LP has several page-label systems:

```text
red-rune label        human/source identity, e.g. red_rune.an_end
master page id        zero-based page id in the bundled master transcript
bound-book page       one-based book-order page number, useful for display
puzzle-maker label    external label/title; not guaranteed to match local order
```

Solved-source retrieval uses complete integer master transcript pages. User code
should normally use labels, not page numbers.

Known examples:

```text
warning          -> master page 0
welcome_pilgrim  -> master pages 1-2
some_wisdom      -> master page 3
an_end           -> master page 56
parable          -> master page 57
```

## Boundary policy

The current catalogue resolves solved labels through the bundled master
transcript using full master-page ranges. Each payload records both the master
page range and the computed bound-book page range.

The current boundary granularity is:

```text
full_master_pages
```

Line locators can still be used later where needed, but the solved pages in this
catalogue should normally be complete pages.

## Spreadsheet-reference tests

Solved source labels are checked against hardcoded references derived from the
solved-page spreadsheet and page images. The tests compare the loaded numeric
stream and WLI word lengths against the reference values.

This proves that a simple label retrieves the expected numeric payload and word
segmentation before any solving routine is built on top.

## Current API

```python
from rune_decrypter_prime.data import liber_primus as lp

payload = lp.payload_from_label("welcome_pilgrim")
text = payload.ct_idx
wli_data = payload.wli
metadata = payload.metadata
```

Payload metadata includes:

```text
source_label
requested_label
red_rune_sections
master_page_start / master_page_end
bound_book_start / bound_book_end
line / line_end
boundary_granularity
```

For solved full-page labels, `line` and `line_end` are `None`.

## RunSpec source references

LP labels are also accepted as first-class `SourceInputRef` values:

```python
from rune_decrypter_prime.api import SourceInputRef

source_ref = SourceInputRef(
    source_kind="liber_primus.label",
    asset_id="liber_primus.master_transcript",
    asset_version="<master transcript sha256>",
    ref={"label": "welcome_pilgrim"},
)
```

The `ref` payload is intentionally narrow. It contains only the source label.
Solver settings such as period, max iterations, key hints, streams, or
interrupter policy belong in the solve recipe or solver config, not in the source
reference.

## First technical targets

1. Use the live `welcome_pilgrim` payload with
   `recipe.welcome_pilgrim.vigenere_interruptors`.
2. Use the live `koan_during_lesson` payload with
   `recipe.koan_during_lesson.vigenere_interruptors`.
3. Use the live `an_end` payload to build the stream-sequence recipe around
   canonical sequence candidates such as primes-minus-one.
