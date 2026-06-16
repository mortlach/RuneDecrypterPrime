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

Catalogue entries may be added before their exact transcript locator is
verified, but candidate page ranges must not be silently used as solver input.

The final verified boundary should be stored as a master-transcript locator,
preferably:

```text
bound-book page + line range
```

or, where clearer:

```text
transcript page id + line range
```

Red-rune section numbers and side-art labels are useful metadata, but they are
not sufficient by themselves as the sole source boundary.

## Current API

```python
from rune_decrypter_prime.data import liber_primus as lp

labels = lp.list_source_labels()
entry = lp.resolve_source_label("red_rune.welcome_pilgrim")
recipe = lp.resolve_solve_recipe_label("recipe.welcome_pilgrim.vigenere_interruptors")
```

`payload_from_label(...)` is the direct solving bridge:

```python
payload = lp.payload_from_label("red_rune.welcome_pilgrim")
```

For entries whose exact master-transcript locator is not verified yet, this
fails clearly instead of using candidate ranges:

```text
LP source label 'red_rune.welcome_pilgrim' has no verified master transcript locator yet
```

That is deliberate. The next work block is to verify exact page/line locators
for one solved source at a time, starting with the Vigenere-with-interruptors
examples and `AN END`.

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

1. Verify `red_rune.welcome_pilgrim` exact locator and connect it to
   `recipe.welcome_pilgrim.vigenere_interruptors`.
2. Verify `red_rune.koan_during_lesson` exact locator and connect it to
   `recipe.koan_during_lesson.vigenere_interruptors`.
3. Verify `red_rune.an_end` exact locator and build the stream-sequence recipe
   around canonical sequence candidates such as primes-minus-one.
