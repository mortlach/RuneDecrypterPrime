from __future__ import annotations
import pytest
import numpy as np
from rune_decrypter_prime.api.normalize import (
    normalize_text_permutation, apply_permutation, invert_permutation
)

def test_normalize_permutation_accepts_list_tuple_range():
    n = 5
    p_list = [2, 0, 4, 1, 3]
    p_tuple = tuple(p_list)
    p_range = list(range(n))[::-1]

    assert normalize_text_permutation(p_list, n) == p_list
    assert normalize_text_permutation(p_tuple, n) == p_list
    assert normalize_text_permutation(p_range, n) == p_range

def test_normalize_permutation_accepts_numpy_if_available():
    n = 4
    try:
        import numpy as np  # optional; skip if not installed
    except Exception:
        pytest.skip("numpy not installed")
    p_np = np.array([1, 0, 3, 2], dtype=np.int64)
    assert normalize_text_permutation(p_np, n) == [1, 0, 3, 2]

def test_normalize_permutation_rejects_bad_shapes_and_values():
    n = 4
    with pytest.raises(ValueError):
        normalize_text_permutation([0, 1, 2], n)             # wrong length
    with pytest.raises(ValueError):
        normalize_text_permutation([0, 1, 1, 3], n)          # duplicate
    with pytest.raises(ValueError):
        normalize_text_permutation([-1, 0, 1, 2], n)         # out of range
    with pytest.raises(TypeError):
        normalize_text_permutation(["0", "1", "2", "3"], n)  # wrong types

def test_apply_and_invert_permutation_roundtrip():
    tokens = list("ABCDE")
    perm = [2, 0, 4, 1, 3]
    permuted = apply_permutation(tokens, perm)
    assert "".join(permuted) == "CAEBD"

    inv = invert_permutation(perm)
    back = apply_permutation(permuted, inv)
    assert back == tokens

def test_apply_permutation_validates_length():
    tokens = [10, 20, 30]
    perm = [1, 0, 2, 3]
    with pytest.raises(ValueError):
        apply_permutation(tokens, perm)
