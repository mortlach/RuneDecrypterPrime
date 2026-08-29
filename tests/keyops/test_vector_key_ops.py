"""
Contract: VectorKeyOps uses modulo arithmetic with fixed K and mod, implements
partial_mask over positions (not boolean mask), and is deterministic with a
given RNG seed. All verbs return uint8 arrays with correct shapes.
"""
import numpy as np
import pytest
from rune_decrypter_prime.keyops.registry import create
from rune_decrypter_prime.keyops import VectorKeyOps

def test_random_and_mutate_bounds_and_types():
    K, MOD = (8, 29)
    ops: VectorKeyOps = create('vector', K=K, mod=MOD)
    rng = np.random.default_rng(2024)
    key = ops.random(rng)
    assert key.shape == (K,)
    assert key.dtype == np.uint8
    assert int(key.min()) >= 0 and int(key.max()) < MOD
    for _ in range(500):
        key = ops.mutate(key, rng)
        assert key.shape == (K,)
        assert key.dtype == np.uint8
        assert int(key.min()) >= 0 and int(key.max()) < MOD

def test_partial_mask_returns_expected_positions():
    K, L, depth = (3, 8, 2)
    ops: VectorKeyOps = create('vector', K=K, mod=29)
    pos = ops.partial_mask(L=L, depth=depth)
    expected = np.where(np.arange(L, dtype=np.int32) % K < depth)[0]
    assert pos.dtype.kind in ('i', 'u')
    assert np.array_equal(pos, expected), 'partial_mask must return absolute positions affected by first `depth` columns'

def test_batch_neighbors_and_expand_position_contracts():
    K, MOD = (6, 29)
    ops: VectorKeyOps = create('vector', K=K, mod=MOD)
    rng = np.random.default_rng(11)
    key = ops.random(rng)
    batch = ops.batch_neighbors(key, 16, rng)
    assert batch.shape == (16, K)
    assert batch.dtype == np.uint8
    assert int(batch.max()) < MOD
    pos = 3
    expanded = ops.expand_position(key, pos, rng)
    assert expanded.shape == (MOD, K)
    assert expanded.dtype == np.uint8
    other_cols_equal = np.all(expanded[:, np.r_[0:pos, pos + 1:K]] == key[np.r_[0:pos, pos + 1:K]])
    assert other_cols_equal
    assert np.array_equal(np.sort(expanded[:, pos].astype(int)), np.arange(MOD))

def test_determinism_same_seed_same_sequence():
    K, MOD = (10, 29)
    ops_a: VectorKeyOps = create('vector', K=K, mod=MOD)
    ops_b: VectorKeyOps = create('vector', K=K, mod=MOD)
    rng1 = np.random.default_rng(777)
    rng2 = np.random.default_rng(777)
    a1 = ops_a.random(rng1)
    b1 = ops_b.random(rng2)
    assert np.array_equal(a1, b1)
    for _ in range(50):
        a1 = ops_a.mutate(a1, rng1)
        b1 = ops_b.mutate(b1, rng2)
        assert np.array_equal(a1, b1), 'mutation sequence must be deterministic with same seed'

@pytest.mark.parametrize('K,mod', [(5, 29), (8, 13)])
def test_vector_mutate_within_bounds_and_recombine(K, mod):
    ops = create('vector', K=K, mod=mod)
    rng = np.random.default_rng(2024)
    key = ops.random(rng)
    assert key.shape == (K,) and key.dtype == np.uint8
    assert (key < mod).all()
    for _ in range(100):
        key = ops.mutate(key, rng)
        assert (0 <= key).all() and (key < mod).all()
    a = ops.random(rng)
    b = ops.random(rng)
    child = ops.recombine(a, b, rng)
    assert child.shape == (K,) and child.dtype == np.uint8 and (child < mod).all()
    agree = ((child == a) | (child == b)).mean()
    assert agree > 0.2

def test_vector_make_population_and_expand_position():
    K, mod, N = (6, 17, 10)
    ops = create('vector', K=K, mod=mod)
    rng = np.random.default_rng(99)
    pop = ops.make_population(N, rng)
    assert pop.shape == (N, K) and pop.dtype == np.uint8 and (pop < mod).all()
    key = ops.random(rng)
    pos = 2
    expanded = ops.expand_position(key, pos, rng) if hasattr(ops, 'expand_position') else None
    if expanded is not None:
        assert expanded.shape[1] == K
        assert (expanded[:, pos] != key[pos]).any()
        assert (expanded < mod).all()
