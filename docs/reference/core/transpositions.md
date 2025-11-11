# `core/transpositions.py`

> Purpose: utility helpers for permutation math (swap columns, invert indices) shared by pipeline tracking and key-ops logic.

## Functions
- `invert_permutation(perm)` - Returns the inverse permutation such that `perm ∘ inv == identity`. Used when RunAPI reinjects plaintext or when telemetry needs to describe how text was rearranged.

## Usage
```python
from rune_decrypter_prime.core.transpositions import invert_permutation

perm = [2, 0, 1]
inverse = invert_permutation(perm)  # -> [1, 2, 0]
```

## Tests
- `tests/pipeline/test_permutation_tracking.py` - ensures permutations sent into RunAPI are inverted/logged correctly.
- `tests/api/test_normalize_text_permutation.py` - checks canonical permutation handling that eventually calls this helper.

## Related Docs
- `docs/reference/api/normalize.md` - describes how permutations enter the pipeline.
- `docs/reference/api/pipeline.md` - uses the inverted permutation when building telemetry blocks.

