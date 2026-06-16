# Liber Primus solved source labels

This guide describes the first V1 source-label layer for solved Liber Primus
text fragments.

The rule is simple:

```text
source label = which LP text fragment
solve recipe = how RDP tries to solve or replay it
```

The solved-source label layer is a thin convenience layer over the existing LP
master transcript. It is not a redesign of the LP transcript, locator, page, or
section APIs.

## User-facing labels

Users should normally use short labels:

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

Namespaced aliases may also exist:

```text
red_rune.welcome_pilgrim
solved.welcome_pilgrim
```

Puzzle-maker filename labels may also be aliases where useful, for example:

```text
56.jpg
p56
canon.56
57.jpg
p57
canon.57
```

Those filename-style labels are **not** master transcript page ids. They are
external page names/filenames from the puzzle history.

## Page-label terminology

LP page naming is not trivial. The collection grew organically as the puzzle
progressed, and several label systems coexist:

```text
source label          human RDP label, e.g. welcome_pilgrim
master transcript id  zero-based page order in the bundled master transcript
bound-book page       one-based display/order alias for the master transcript
puzzle filename       puzzle-maker filename/canon-style label, e.g. 56.jpg
red-rune section      visual/section grouping from red-rune material
side-art section      visual/section grouping from side art
```

Do not assume these label systems are numerically equivalent. In particular,
`56.jpg` does not mean `master transcript page 56` unless the catalogue entry
explicitly says that after verification.

In the current master transcript, the puzzle-maker filename sequence starts only
after the initial solved/introduction pages. The first filename page, `0.jpg`,
starts at master transcript page 15. Therefore the filename aliases used here map
as:

```text
p56 / 56.jpg / canon.56 -> an_end  -> master transcript page 71
p57 / 57.jpg / canon.57 -> parable -> master transcript page 72
```

For RDP, the retrieval ground truth is:

```text
label -> catalogue entry -> master transcript page/span -> ct_idx + wli
```

The user normally supplies the label. The catalogue records which master
transcript pages that label resolves to.

## Low-level access remains available

The existing low-level typed APIs still exist for direct page/line work:

```python
from rune_decrypter_prime.data import liber_primus as lp

doc = lp.load_master_transcript()
locator = lp.LPFragmentLocator(page_ref=lp.LPPageRef.transcript_page(0))
payload = lp.payload_from_locator(doc, locator)
```

The public data helper can also load complete master pages directly for debugging
or manual work:

```python
from rune_decrypter_prime.api import load_lp_payload_from_master_pages

payload = load_lp_payload_from_master_pages(1, 2)
```

That is low-level access. Solved-page workflows should prefer labels:

```python
from rune_decrypter_prime.data import liber_primus as lp

payload = lp.payload_from_label("welcome_pilgrim")
```

## Boundary policy

Solved-source entries should resolve to complete integer master transcript pages
where possible. Each payload records the master transcript page span and the
bound-book display range.

Current boundary granularity for solved full-page labels is:

```text
full_master_pages
```

Line locators can still be used later if a future source label needs a narrower
fragment.

## Spreadsheet-reference tests

Solved source labels are checked against hardcoded references derived from the
solved-page spreadsheet and page images. The tests compare the loaded numeric
stream and WLI word lengths against the reference values.

This proves that a simple label retrieves the expected numeric payload and word
segmentation before any solving routine is built on top.

## RunSpec source references

LP labels are accepted as first-class `SourceInputRef` values:

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

## Current solved-source targets

The first solved-source work is to verify the label mapping and then build
solving/replay routines on top of it:

```text
welcome_pilgrim       Vigenere/interrupter solved-page reproduction
koan_during_lesson    Vigenere/interrupter solved-page reproduction
an_end                stream-sequence/interrupter solved-page reproduction
parable               solved reference page
```

The important contract is not the spelling of a single label. The contract is
that all accepted aliases for a page resolve to the same master-transcript
payload and therefore the same `ct_idx` and `wli`.
