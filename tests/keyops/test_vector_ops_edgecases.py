"""
Edge cases clarify contracts and prevent "works on my data" regressions.

- partial_mask depth boundaries and errors
- normalize vs validate responsibilities (wrapping & length vs. shape/type)
- expand_position bounds checking
"""

import numpy as np
import pytest
from rune_decrypter_prime.keyops.registry import create
from rune_decrypter_prime.keyops import VectorKeyOps


def test_partial_mask_boundaries_and_errors():
    K, L = (4, 10)
    ops: VectorKeyOps = create("vector", K=K, mod=29)
    assert ops.partial_mask(L=L, depth=0).size == 0
    assert np.array_equal(ops.partial_mask(L=L, depth=K), np.arange(L, dtype=np.int32))
    with pytest.raises(ValueError):
        ops.partial_mask(L=L, depth=K + 1)
    with pytest.raises(ValueError):
        ops.partial_mask(L=L, depth=-1)


def test_normalize_wraps_and_enforces_length_while_validate_checks_shape_dtype():
    K, M = (5, 29)
    ops: VectorKeyOps = create("vector", K=K, mod=M)
    with pytest.raises(ValueError):
        ops.normalize(np.zeros(K + 1, dtype=np.int64))
    raw = np.array([-1, M, 58, -30, 0], dtype=np.int64)
    fixed = ops.normalize(raw)
    assert fixed.dtype == np.uint8
    assert np.array_equal(fixed.astype(int), np.array([M - 1, 0, 0, -30 % M, 0]))
    ops.validate(fixed)
    with pytest.raises(AssertionError):
        ops.validate(fixed.reshape(1, -1))


def test_expand_position_bounds():
    K, M = (6, 29)
    ops: VectorKeyOps = create("vector", K=K, mod=M)
    key = ops.random(np.random.default_rng(0))
    out = ops.expand_position(key, pos=K - 1)
    assert out.shape == (M, K)
    with pytest.raises(IndexError):
        ops.expand_position(key, pos=K)
    with pytest.raises(IndexError):
        ops.expand_position(key, pos=-1)
