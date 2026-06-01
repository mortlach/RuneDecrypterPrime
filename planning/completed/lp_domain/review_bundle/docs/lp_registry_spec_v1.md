# Liber Primus registry + route API spec v1

## Purpose

Define a first-class LP corpus interface for RDP that is:

- solver-friendly
- typed in core
- human-friendly through a separate convenience layer
- extensible through a registry
- explicit about reference systems and indexing rules

This spec is grounded in the current LP implementation that already provides:

- one canonical glyph stream
- indexed words, lines, pages, and sections
- optional canon page catalogue attachment
- custom split support
- `ct_idx` and `wli` extraction from spans

## Verified starting point from current code

The current parser stores:

- `glyphs`
- `words`
- `lines`
- `pages`
- custom section splits

and supports page catalogue attachment plus canon-page lookup.
The master transcript helper maps the last 58 transcript pages to canon `0.jpg` to `57.jpg`.

The current split API and LP data API are still string-based.
This spec replaces that string-heavy surface with typed enums and value objects in core.

## Non-goals

This v1 does **not** attempt to:

- infer page-side artwork from images automatically
- infer paragraph or clause boundaries from images automatically
- define every solved-page plaintext label in core before they are curated
- replace the existing parser backbone

Instead, it provides a clean way to attach those things later.

---

## 1. Core design rule: separate three different concepts

### A. Reference systems
How a user identifies a page or fragment.

Examples:
- canon unsolved page 54
- bound-book page 54
- transcript page id 53

### B. Partition schemes
How the corpus is sliced into meaningful chunks.

Examples:
- legacy sections
- red-rune 17-way split
- side-art 10-way split
- nested side-art/red-rune split

### C. Page features / labels / aliases
Human cues attached to pages or fragments.

Examples:
- `solved`
- `unsolved`
- `spirals`
- `mobius`
- `a_waning`
- `raven_page`

These are not the same thing and should not share one overloaded mechanism.

---

## 2. Built-in page reference systems

Core built-ins should be enums.

### `LPBuiltInPageScheme`

- `TRANSCRIPT_PAGE_ID`
  - zero-based internal page id
- `BOUND_BOOK_PAGE`
  - one-based page numbering in transcript order, including title/front matter
- `CANON_UNSOLVED_PAGE`
  - zero-based canon numbering for the last 58 pages (`0.jpg` to `57.jpg`)

### Why `page 54` must not mean canon page 54

The user requirement is explicit:

- `page 54` means bound-book order
- `54.jpg` means canon unsolved page 54

These are different references and must resolve differently.

### UI parsing rule

The forgiving UI layer may parse:

- `54.jpg` -> `LPPageRef.canon_page(54)`
- `54` -> `LPPageRef.canon_page(54)`
- `page 54` -> `LPPageRef.bound_book_page(54)`
- `p54` -> `LPPageRef.bound_book_page(54)`

The strict core should not accept those raw strings.

---

## 3. Built-in partition schemes

### `LPBuiltInPartitionScheme`

- `LEGACY_SECTIONS`
- `RED_RUNE_17`
- `SIDE_ART_10`
- `SIDE_ART_RED_RUNE_NESTED`
- `SOLVED_PLAINTEXT_PAGES` (reserved; incomplete until curated)

### Canonical section keys

Use a typed ordinal value object rather than free strings.

Examples:

- `LPSectionOrdinal.of(8)`
- `LPSectionOrdinal.of(8, 1)`

UI rendering may display these as:

- `8`
- `8-1`
- `8.1`

but core storage should keep one canonical typed form.

---

## 4. Registry model

Core extensions should use:

- enums for built-ins
- user enums where possible
- `LPRegistryLabel(namespace, name)` as the fallback for custom labels

No bare strings in core registration APIs.

### Registry responsibilities

The registry stores:

- page aliases
- page features
- partition entries
- custom fragment labels

### Registration rule

Every custom label must reduce to one of the core canon coordinate forms.

That means a user can add a custom label by saying, in canon-based coordinates, where the text lives.

Examples:

- a custom page alias resolves to `LPPageRef.canon_page(54)`
- a custom section resolves to a page range or start/end fragment locator defined in canon coordinates
- a solved-page label resolves to a fragment locator in canon coordinates

---

## 5. Fragment location model

### `LPPageRef`
Typed page reference.

### `LPFragmentLocator`
Describes a fragment inside the corpus, for example:

- whole page
- a page plus a line
- a page plus a line range
- a page plus word range
- a start/end pair across a wider fragment

Recommended fields:

- `page_ref: LPPageRef`
- `line: int | None`
- `line_end: int | None`
- `word: int | None`
- `word_end: int | None`

### Negative indexing rule

Negative indexing is allowed for intra-container access:

- `line=-1` -> last line in the selected page
- `word=-1` -> last word in the selected line or fragment

### Base rule

- transcript page ids are zero-based
- canon unsolved pages are zero-based
- bound-book pages are one-based
- line and word coordinates inside a resolved container are zero-based, with negative indexing allowed

This keeps the human book-page reference natural while still supporting Python-style negative indexing for sub-items.

---

## 6. Retrieval vs traversal

### Retrieval phase
Resolve the fragment.

Examples:

- whole canon page 33
- last line of canon page 33
- side-art section 8
- nested section 8-1

### Traversal phase
Apply a route to the retrieved fragment.

This is intentionally separate.

Reasons:

- the same fragment may be read in multiple ways
- route logic should not pollute the core locator model
- solver pipelines often want to retrieve once, then test many traversal hypotheses

---

## 7. Route model

### Built-in line-wise read modes

`LPLineReadMode`

- `LEFT_TO_RIGHT`
- `RIGHT_TO_LEFT`
- `BOUSTROPHEDON`

### Built-in line selectors

`LPLineRuneSelector`

- `ALL`
- `FIRST_ONLY`
- `LAST_ONLY`

These combine naturally.

Examples:

- left-to-right, all runes
- right-to-left, all runes
- boustrophedon, all runes
- left-to-right, first rune of each line
- left-to-right, last rune of each line

### Spiral and other shape routes

Spiral is a shape route, not a simple line-direction mode.

To support it cleanly, introduce a 2D line grid projection.

#### `LPSpiralDirection`
- `CLOCKWISE`
- `COUNTERCLOCKWISE`

#### `LPSpiralStartCorner`
- `TOP_LEFT`
- `TOP_RIGHT`
- `BOTTOM_RIGHT`
- `BOTTOM_LEFT`

#### Grid rule

A retrieved fragment is projected to a ragged line grid:

- each line is a sequence of rune cells
- shorter lines leave empty cells
- spiral traversal visits the bounding rectangle
- empty cells are skipped unless strict rectangular mode is later requested

This handles both regular and ragged lines.

### Future custom routes

The route interface should be extensible enough for:

- diagonal walks
- zig-zag by column
- knight-like jumps
- user-defined cell orderings

The clean extension point is:

- route takes `Sequence[str]` or `RuneGrid`
- route returns ordered rune cells / ordered rune string

---

## 8. Built-in LP catalogue values for v1 review

These should be reviewable constants, not inferred at runtime.

### Red-rune 17-way partition

Use the user-supplied page ranges:

1. `0.jpg–2.jpg`
2. `3.jpg`
3. `3.jpg–6.jpg`
4. `6.jpg–7.jpg`
5. `7.jpg`
6. `8.jpg–14.jpg`
7. `15.jpg`
8. `15.jpg–22.jpg`
9. `23.jpg–26.jpg`
10. `27.jpg–32.jpg`
11. `33.jpg`
12. `33.jpg–39.jpg`
13. `39.jpg`
14. `40.jpg–53.jpg`
15. `54.jpg–55.jpg`
16. `56.jpg`
17. `57.jpg`

### Side-art 10-way partition

1. `0.jpg–2.jpg` -> `sign_post_cross`
2. `3.jpg–7.jpg` -> `spirals`
3. `8.jpg–14.jpg` -> `branches`
4. `15.jpg–22.jpg` -> `mobius`
5. `23.jpg–26.jpg` -> `mayfly`
6. `27.jpg–32.jpg` -> `wing_tree`
7. `33.jpg–39.jpg` -> `cuneiform`
8. `40.jpg–55.jpg` -> `spiral_branches`
9. `56.jpg` -> `an_end`
10. `57.jpg` -> `parable`

### Nested side-art/red-rune partition

For each side-art section, number the overlapping red-rune entries in order.

Examples:

- `1-1` = first red-rune block inside side-art section 1
- `8-1` = first red-rune block inside side-art section 8
- `8-2` = second red-rune block inside side-art section 8

This gives a very human-friendly nested handle without giving up typed canonical storage.

---

## 9. Public API shape

The public-facing LP document object should grow methods like:

```python
page = doc.resolve_page(LPPageRef.canon_page(54))
line = doc.resolve_fragment(LPFragmentLocator(page_ref=LPPageRef.canon_page(33), line=-1))
section = doc.resolve_partition_entry(LPBuiltInPartitionScheme.SIDE_ART_10, LPSectionOrdinal.of(8))
chunk = doc.resolve_partition_entry(LPBuiltInPartitionScheme.SIDE_ART_RED_RUNE_NESTED, LPSectionOrdinal.of(8, 1))
```

The returned fragment object should then support:

- `text()`
- `lines()`
- `glyph_span()`
- `run_inputs()`
- `read(mode=...)`
- `route(spec=...)`

---

## 10. Tests that should exist in the real repo

### Core lookup tests

- canon page 54 resolves to a different transcript page from bound-book page 54
- negative line index resolves to the last line
- page aliases resolve to the expected canon coordinates
- nested partition `8-1` resolves to the first red-rune block within side-art section 8

### Route tests

- left-to-right by line
- right-to-left by line
- boustrophedon
- first-rune-per-line
- last-rune-per-line
- spiral on a simple rectangular grid
- spiral on a ragged grid, skipping empty cells

### Integration tests against current master transcript

- `load_master_transcript()` still maps the last 58 pages to canon numbering
- canon page references and partition references agree on page boundaries for a few known examples
- the text returned for a small known canon slice matches the same slice reached through the registry-based path

---

## 11. Migration notes

This spec is meant to sit on top of the current parser rather than replace it.

Likely repo touchpoints:

- `lp_transcript.py`
- `lp_master.py`
- `lp_data.py`
- public LP API exports

The smallest safe path is:

1. add typed registry + route helpers
2. add a thin adapter from current `LPTranscript` to the new reference model
3. add UI-only parsing helpers
4. migrate examples/docs/tests
5. only then consider renaming or deprecating older string-based split calls
