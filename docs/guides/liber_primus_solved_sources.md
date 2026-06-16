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

## Source labels

Initial solved text sources are named by the red-rune text identity:

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

Aliases such as `solved.welcome_pilgrim` may point to the same source, but the
canonical label remains `red_rune.welcome_pilgrim`.

## Page-label terminology

LP has several page-label systems:

```text
red-rune label        human/source identity, e.g. red_rune.an_end
bound-book page       physical book order used for retrieval/display
transcript page id    zero-based page id in the master transcript parser
canon-unsolved page   existing internal RDP scheme for the last 58 transcript pages
puzzle-maker label    external labels/titles that may not follow numerical order
```

User-facing solved-source labels should not depend on external numerical canon
labels. They should resolve through the bundled master transcript and expose
book-order metadata.

## Boundary policy

The current catalogue resolves solved red-rune labels through the bundled master
transcript using full-page ranges in the existing internal RDP page scheme. Each
payload also records the computed bound-book page range for book-order retrieval
and display.

The current boundary granularity is:

```text
full_canon_pages
```

More precise bound-book page + line-range locators can be added later for any
source whose solved text covers only part of a page. The public source label does
not need to change when that locator is refined.

## Spreadsheet-reference tests

Solved source labels are checked against hardcoded references derived from the
solved-page spreadsheet. The tests compare the loaded numeric stream and WLI word
lengths against the spreadsheet reference values.

This proves that a red-rune label retrieves the expected numeric payload and word
segmentation before any solving routine is built on top.

## Current API

```python
from rune_decrypter_prime.data import liber_primus as lp

labels = lp.list_source_labels()
entry = lp.resolve_source_label("red_rune.welcome_pilgrim")
recipe = lp.resolve_solve_recipe_label("recipe.welcome_pilgrim.vigenere_interruptors")
```

`payload_from_label(...)` loads real solver payloads:

```python
payload = lp.payload_from_label("red_rune.an_end")

text = payload.ct_idx
wli_data = payload.wli
metadata = payload.metadata
```

Payload metadata includes:

```text
source_label
red_rune_sections
canon_start / canon_end
bound_book_start / bound_book_end
line / line_end
boundary_granularity
```

For now `line` and `line_end` are `None` for the solved red-rune sources because
the first live mapping uses full pages. Bound-book page + line locators should be
used when a solved source needs narrower retrieval.

## RunSpec source references

LP labels are also accepted as first-class `SourceInputRef` values:

```python
from rune_decrypter_prime.api import SourceInputRef

source_ref = SourceInputRef(
    source_kind="liber_primus.label",
    asset_id="liber_primus.master_transcript",
    asset_version="<master transcript sha256>",
    ref={"label": "red_rune.welcome_pilgrim"},
)
```

The `ref` payload is intentionally narrow. It contains only the source label.
Solver settings such as period, max iterations, key hints, streams, or
interrupter policy belong in the solve recipe or solver config, not in the source
reference.

## First technical targets

1. Use the live `red_rune.welcome_pilgrim` payload with
   `recipe.welcome_pilgrim.vigenere_interruptors`.
2. Use the live `red_rune.koan_during_lesson` payload with
   `recipe.koan_during_lesson.vigenere_interruptors`.
3. Use the live `red_rune.an_end` payload to build the stream-sequence recipe
   around canonical sequence candidates such as primes-minus-one.
4. Refine any source from full-page boundaries to bound-book page + line ranges
   where the solved text requires a narrower fragment.
