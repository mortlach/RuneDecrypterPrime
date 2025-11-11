"""
Why: Core must only ever see a true permutation of indices. The public API is the place
     to be forgiving on container types (list/tuple/np.ndarray) but strict on content.
Proves: api.normalize.normalize_text_permutation:
  - coerces to list[int]
  - validates length and domain (0..n-1)
  - rejects duplicates, out-of-range, and string digits
"""

import pytest
import numpy as np

from rune_decrypter_prime.api.normalize import normalize_text_permutation


@pytest.mark.parametrize("src", [
    [2, 0, 1],
    (2, 0, 1),
    np.array([2, 0, 1], dtype=np.int64),
])
def test_accepts_list_tuple_numpy_and_returns_list_int(src):
    out = normalize_text_permutation(src, n_tokens=3)
    assert isinstance(out, list)
    assert out == [2, 0, 1]
    assert all(isinstance(x, int) for x in out)


@pytest.mark.parametrize("bad", [
    [0, 1, 1],       # duplicate
    [0, 2],          # wrong length (expects length=3)
    [0, 1, 3],       # out of range (3 not in 0..2)
    ["0", "1", "2"], # string digits forbidden
    np.array([0.0, 1.0, 2.0]),  # float array should fail strict mode
])
def test_rejects_non_permutations(bad):
    with pytest.raises(Exception):
        normalize_text_permutation(bad, n_tokens=3)
