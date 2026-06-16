# Liber Primus solved source labels

This guide describes the first V1 source-label layer for solved Liber Primus
text fragments.

The rule is simple:

```text
source label = which LP text fragment
solve recipe = how RDP tries to solve or replay it
```

A source label must not include the cipher, key, shift, stream, or solving
method. Those belong in a recipe label.

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

## Recipes

Recipes are method-specific and intentionally separate:

```text
recipe.welcome_pilgrim.vigenere_interruptors
recipe.koan_during_lesson.vigenere_interruptors
recipe.an_end.stream_sequence_interruptors
recipe.loss_of_divinity.constant_shift_zero_replay
```

This keeps LP text selection independent from the cipher hypothesis.

## Boundary policy

The current catalogue resolves solved red-rune labels through the bundled master
transcript using full canon-page ranges. Each payload records both the canon page
range and the computed bound-book page range.

The current boundary granularity is:

```text
full_canon_pages
```

More precise bound-book page + line-range locators can be added later for any
source whose solved text covers only part of a page. The public source label does
not need to change when that locator is refined.

Red-rune section numbers and side-art labels remain useful metadata, but solver
payloads are loaded through the master transcript, not by hand-copied text.

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
the first live mapping uses full canon pages.

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
