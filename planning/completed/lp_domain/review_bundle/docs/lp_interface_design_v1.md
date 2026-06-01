# Liber Primus interface design v1

## File layout

### New files

- `src/rune_decrypter_prime/data/liber_primus/lp_registry.py`
- `src/rune_decrypter_prime/data/liber_primus/lp_routes.py`
- `src/rune_decrypter_prime/data/liber_primus/lp_ui_parse.py` (UI-only)

### Existing files to extend later

- `src/rune_decrypter_prime/data/liber_primus/lp_transcript.py`
- `src/rune_decrypter_prime/data/liber_primus/lp_master.py`
- `src/rune_decrypter_prime/data/liber_primus/lp_data.py`
- public LP export file

---

## Core types

### `LPBuiltInPageScheme`

```python
class LPBuiltInPageScheme(Enum):
    TRANSCRIPT_PAGE_ID = auto()
    BOUND_BOOK_PAGE = auto()
    CANON_UNSOLVED_PAGE = auto()
```

### `LPBuiltInPartitionScheme`

```python
class LPBuiltInPartitionScheme(Enum):
    LEGACY_SECTIONS = auto()
    RED_RUNE_17 = auto()
    SIDE_ART_10 = auto()
    SIDE_ART_RED_RUNE_NESTED = auto()
    SOLVED_PLAINTEXT_PAGES = auto()
```

### `LPSectionOrdinal`

Typed ordinal label for partitions.

Examples:

```python
LPSectionOrdinal.of(8)
LPSectionOrdinal.of(8, 1)
```

### `LPPageRef`

```python
LPPageRef.transcript_page(53)
LPPageRef.bound_book_page(54)
LPPageRef.canon_page(54)
```

### `LPFragmentLocator`

```python
LPFragmentLocator(
    page_ref=LPPageRef.canon_page(33),
    line=-1,
)
```

This means: last line of canon page 33.

---

## Registry types

### `LPRegistryLabel`

Fallback typed key for custom labels when a user enum is not available.

```python
LPRegistryLabel(namespace='user', name='a_waning')
```

### `LPPageAliasEntry`

Maps a typed label to a page ref.

### `LPPartitionEntry`

Describes one named partition item using canon coordinates.

Recommended fields:

- `scheme`
- `ordinal`
- `start_page`
- `end_page`
- `display_name`
- `tags`

### `LPPageFeature`

Attaches human features to a canon page.

Examples:

- side-art label
- solved/unsolved
- custom aliases
- future marginalia flags

---

## Public adapter methods on `LPTranscript`

These do not need to exist yet, but this is the intended shape.

### Page resolution

```python
resolve_page(self, page_ref: LPPageRef) -> PageView
```

### Fragment resolution

```python
resolve_fragment(self, locator: LPFragmentLocator) -> LPResolvedFragment
```

### Partition resolution

```python
resolve_partition_entry(
    self,
    scheme: LPBuiltInPartitionScheme | LPRegistryLabel | Enum,
    ordinal: LPSectionOrdinal,
) -> LPResolvedFragment
```

### Page features

```python
page_features(self, page_ref: LPPageRef) -> LPPageFeature | None
```

---

## Resolved fragment interface

A resolved fragment should be lightweight and solver-friendly.

### Recommended methods

- `text()`
- `lines()`
- `glyph_span()`
- `run_inputs()`
- `read(mode=..., selector=...)`
- `spiral(direction=..., start_corner=...)`

### Example

```python
frag = doc.resolve_fragment(
    LPFragmentLocator(
        page_ref=LPPageRef.canon_page(33),
        line=-1,
    )
)

text = frag.text()
ct_idx, wli = frag.run_inputs()
rtl = frag.read(mode=LPLineReadMode.RIGHT_TO_LEFT)
edge = frag.read(mode=LPLineReadMode.LEFT_TO_RIGHT, selector=LPLineRuneSelector.FIRST_ONLY)
```

---

## UI parser design

This is intentionally separate from core.

### Why

Humans say:

- `54.jpg`
- `54`
- `page 54`
- `p54`

Core code should use typed refs.

### Suggested helpers

```python
parse_page_token('54.jpg') -> LPPageRef.canon_page(54)
parse_page_token('54') -> LPPageRef.canon_page(54)
parse_page_token('page 54') -> LPPageRef.bound_book_page(54)
parse_page_token('p54') -> LPPageRef.bound_book_page(54)
```

This keeps convenience without weakening the core contract.

---

## Built-in catalogue content for first implementation

### Page systems

- transcript page ids
- bound-book pages
- canon unsolved pages

### Partitions

- red-rune 17
- side-art 10
- nested side-art/red-rune

### Features

- solved/unsolved tag scaffold
- side-art display names
- future solved plaintext alias scaffold

---

## Edge-case rules

### Negative indices

Negative indexing is allowed only after the containing object is known.

Examples:

- `line=-1` is valid only after the page is known
- `word=-1` is valid only after the line or fragment is known

### Out-of-range behaviour

- out-of-range positive index -> `IndexError`
- out-of-range negative index -> `IndexError`
- unknown registry label -> `KeyError`
- unsupported raw string in core -> `TypeError`

---

## Suggested real-repo migration order

1. add `lp_registry.py`
2. add `lp_routes.py`
3. add self-contained tests
4. add adapter methods onto `LPTranscript`
5. add UI parser helpers
6. update README/examples
7. only then deprecate string-heavy entrypoints where appropriate
