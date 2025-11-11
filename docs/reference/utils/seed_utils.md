# `utils/seed_utils.py`

> Purpose: helper routines for generating deterministic seed permutations used by mono-substitution tutorials and keyops tests. Produces rank-aligned starting keys plus jittered variants for GA/SA solvers.

## Functions
- `_to_ct_indices(ct)` - Normalises ciphertext (string/array) into rune indices.
- `rank_alignment_seed(ct, *, A=29, direction="rtl")` - Aligns ciphertext frequency ranks with language-model unigram ranks to produce a single permutation seed.
- `mutate_seed_once(seed_key, *, swaps=1, rng=None)` - Jitters a permutation by swapping random positions.
- `make_seeds_from_freq(ct, *, n_keys=100, swaps_per_key=2, seed=12345)` - Convenience wrapper returning `[base_seed, jittered_seed_1, ...]`.

## Usage
```python
from rune_decrypter_prime.utils import seed_utils

base_seed = seed_utils.rank_alignment_seed("ᛗᛖᛏᚻᚩᚾ")
seed_pool = seed_utils.make_seeds_from_freq("ᛗᛖᛏᚻᚩᚾ", n_keys=32, seed=999)
```

## Tests
- `tests/tutorials/test_mono_substitution.py` - uses these helpers to provide deterministic GA/SA starts.
- `tests/keyops/test_vector_key_ops.py` - indirectly covers the jitter logic by verifying permutations remain valid.

