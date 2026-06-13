Liber Primus Typed Workflows
============================

This guide uses the typed `rune_decrypter_prime.data.liber_primus` APIs.

Principle
---------
- LP models text and fragments.
- Solvers consume payloads (`ct_idx`, `wli`).
- Bridge via `payload_from_locator(...)` / `payload_from_partition_entry(...)`.

Load master transcript
----------------------
```python
from rune_decrypter_prime.data import liber_primus as lp

doc = lp.load_master_transcript(attach_catalogue=True)
```

Retrieve a canon page fragment
------------------------------
```python
from rune_decrypter_prime.data import liber_primus as lp

locator = lp.LPFragmentLocator(page_ref=lp.LPPageRef.canon_page(54))
payload = lp.payload_from_locator(doc, locator)

# solver input
text = payload.ct_idx
wli_data = payload.wli
```

Use a named page alias (solved-page style label)
------------------------------------------------
```python
from rune_decrypter_prime.data import liber_primus as lp

registry = lp.LPRegistry()
alias = lp.LPRegistryLabel(namespace="solved", name="example_page")
registry.register_page_alias(alias, lp.LPPageRef.canon_page(54))

resolved_page = registry.resolve_page_alias(alias)
locator = lp.LPFragmentLocator(page_ref=resolved_page)
payload = lp.payload_from_locator(doc, locator)
```

Retrieve a built-in section partition
-------------------------------------
```python
from rune_decrypter_prime.data import liber_primus as lp

red_rune_entries = lp.build_red_rune_17_partition()
section_15 = red_rune_entries[14]  # ordinal 15
payload = lp.payload_from_partition_entry(doc, section_15)
```

Section/page intersection
-------------------------
```python
from rune_decrypter_prime.data import liber_primus as lp

red_rune_entries = lp.build_red_rune_17_partition()
section_15 = red_rune_entries[14]
payload = lp.payload_from_partition_entry(
    doc,
    section_15,
    intersect_page_ref=lp.LPPageRef.canon_page(54),
)
```

Route variants after retrieval
------------------------------
```python
from rune_decrypter_prime.data import liber_primus as lp

locator = lp.LPFragmentLocator(
    page_ref=lp.LPPageRef.canon_page(54),
    line=0,
    line_end=4,
)

# line family
ltr = lp.payload_from_locator(doc, locator, line_mode=lp.LPLineReadMode.LEFT_TO_RIGHT)
rtl = lp.payload_from_locator(doc, locator, line_mode=lp.LPLineReadMode.RIGHT_TO_LEFT)
bou = lp.payload_from_locator(doc, locator, line_mode=lp.LPLineReadMode.BOUSTROPHEDON)
first = lp.payload_from_locator(
    doc,
    locator,
    line_mode=lp.LPLineReadMode.LEFT_TO_RIGHT,
    selector=lp.LPLineRuneSelector.FIRST_ONLY,
)

# spiral family
spiral = lp.payload_from_locator(
    doc,
    locator,
    spiral_route=lp.LPSpiralRoute(
        direction=lp.LPSpiralDirection.CLOCKWISE,
        start_corner=lp.LPSpiralStartCorner.TOP_LEFT,
    ),
)
```

Notes
-----
- Built-in page schemes are strict typed refs:
  - `transcript_page_id` (0-based)
  - `bound_book_page` (1-based)
  - `canon_unsolved_page` (0-based; last 58 transcript pages)
- Negative indexing is supported only within resolved containers (line/word indices).
