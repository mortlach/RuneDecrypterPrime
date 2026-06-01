# Liber Primus reference registry and route API review bundle

This bundle is a **review package**, not a drop-in repo patch.

Its aim is to make the Liber Primus corpus layer inside RDP:

- first-class and solver-friendly
- typed in core, with enums for built-ins
- extensible through a registry rather than ad hoc helper methods
- human-friendly through a thin UI parsing layer that sits **outside** core
- ready for line-wise and shape-wise rune traversal after fragment lookup

## Why this bundle exists

The current LP code already has a strong backbone:

- one canonical glyph stream
- indexed words, lines, pages, and sections
- `GlyphSpan.ct_wli()` for solver hand-off
- a master loader that maps the last 58 transcript pages to canon `0.jpg` to `57.jpg`

What it does **not** yet have is a first-class registry model for:

- multiple page reference systems
- multiple partition schemes
- page/section aliases and human-readable labels
- post-retrieval traversal routes such as right-to-left, boustrophedon, first-rune-per-line, and spiral

## Design decisions in this bundle

### 1. Core stays typed

Core API objects use enums and dataclasses.
There are no bare magic strings in the proposed core interface.

### 2. Human text parsing is UI-only

Things like:

- `54.jpg`
- `54`
- `page 54`
- `p54`

belong in a forgiving **UI parser**, not in the strict core API.

This matters because `page 54` is **not** the same thing as canon page `54.jpg`:

- `page 54` means the 54th page in bound-book order, including title/front matter
- `54.jpg` means canon unsolved page 54 among the last 58 pages

### 3. Registry entries always reduce to canon coordinates

Users should be able to add labels and aliases by saying where the text lives in canon-based coordinates.
That keeps the extension story simple and stable.

### 4. Retrieval happens first; traversal happens second

First retrieve a fragment.
Then apply a traversal route to the retrieved fragment:

- left-to-right by line
- right-to-left by line
- boustrophedon
- first rune of each line
- last rune of each line
- spiral over a line grid

## Bundle contents

- `docs/lp_registry_spec_v1.md`
  Detailed spec.
- `docs/lp_interface_design_v1.md`
  File-by-file interface design.
- `src/rune_decrypter_prime/data/liber_primus/lp_registry_v1.py`
  Typed registry model and built-in reference helpers.
- `src/rune_decrypter_prime/data/liber_primus/lp_route_v1.py`
  Post-retrieval route helpers.
- `src/rune_decrypter_prime/data/liber_primus/lp_ui_parse_v1.py`
  UI-only parsing helpers for human tokens.
- `tests/data/liber_primus/`
  Focused contract tests.

## Quick examples

### Typed core page lookup

```python
from rune_decrypter_prime.data.liber_primus.lp_registry_v1 import LPPageRef

canon_54 = LPPageRef.canon_page(54)
bound_54 = LPPageRef.bound_book_page(54)
```

### UI-only token parsing

```python
from rune_decrypter_prime.data.liber_primus.lp_ui_parse_v1 import parse_page_token

assert parse_page_token('54.jpg') == LPPageRef.canon_page(54)
assert parse_page_token('54') == LPPageRef.canon_page(54)
assert parse_page_token('page 54') == LPPageRef.bound_book_page(54)
```

### Traversal after retrieval

```python
from rune_decrypter_prime.data.liber_primus.lp_route_v1 import (
    LPLineReadMode,
    LPLineRuneSelector,
    read_lines,
)

lines = ['ABC', 'DEF', 'GHI']
assert read_lines(lines, mode=LPLineReadMode.LEFT_TO_RIGHT) == 'ABCDEFGHI'
assert read_lines(lines, mode=LPLineReadMode.RIGHT_TO_LEFT) == 'CBAFEDIHG'
assert read_lines(lines, mode=LPLineReadMode.BOUSTROPHEDON) == 'ABCFEDGHI'
assert read_lines(lines, mode=LPLineReadMode.LEFT_TO_RIGHT, selector=LPLineRuneSelector.FIRST_ONLY) == 'ADG'
```

## Review status

The tests in this bundle are self-contained and exercise the proposed contracts.
They do **not** patch the uploaded repo directly.
