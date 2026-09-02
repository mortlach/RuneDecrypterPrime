"""
Contract: PermutationKeyOps produces true permutations, respects shapes/dtypes,
and consumes only the injected RNG. With the same seed, sequences are identical.
"""
import numpy as np
import pytest
from rdp.core.types import KEY_DTYPE
from rune_decrypter_prime.keyops.registry import create
from rune_decrypter_prime.keyops import PermutationKeyOps

def _is_perm(arr: np.ndarray) -> bool:
    arr = np.asarray(arr)
    return arr.dtype == KEY_DTYPE and arr.ndim == 1 and np.array_equal(np.sort(arr), np.arange(arr.size, dtype=KEY_DTYPE))

def test_random_and_mutate_preserve_permutation_invariants():
    K = 16
    ops: PermutationKeyOps = create('permutation', K=K)
    rng = np.random.default_rng(42)
    key = ops.random(rng)
    assert _is_perm(key)
    for _ in range(500):
        key = ops.mutate(key, rng)
        assert _is_perm(key), 'mutate must keep a true permutation'
    for _ in range(200):
        key = ops.neighbor(key, rng)
        assert _is_perm(key), 'neighbor must keep a true permutation'

def test_batch_neighbors_and_population_shapes_and_types():
    K, B = (12, 32)
    ops: PermutationKeyOps = create('perm', K=K)
    rng = np.random.default_rng(7)
    key = ops.random(rng)
    batch = ops.batch_neighbors(key, B, rng)
    assert isinstance(batch, np.ndarray)
    assert batch.shape == (B, K)
    assert batch.dtype == KEY_DTYPE
    assert all((np.array_equal(np.sort(row), np.arange(K)) for row in batch))

def test_recombine_child_is_valid_permutation():
    K = 20
    ops: PermutationKeyOps = create('permutation', K=K)
    rng = np.random.default_rng(99)
    p1, p2 = (ops.random(rng), ops.random(rng))
    child = ops.recombine(p1, p2, rng)
    assert child.shape == (K,)
    assert child.dtype == KEY_DTYPE
    assert np.array_equal(np.sort(child), np.arange(K))

def test_determinism_same_seed_same_sequence():
    K = 10
    ops_a: PermutationKeyOps = create('permutation', K=K)
    ops_b: PermutationKeyOps = create('permutation', K=K)
    rng1 = np.random.default_rng(12345)
    rng2 = np.random.default_rng(12345)
    a1 = ops_a.random(rng1)
    b1 = ops_b.random(rng2)
    assert np.array_equal(a1, b1)
    N = 50
    for _ in range(N):
        a1 = ops_a.mutate(a1, rng1)
        b1 = ops_b.mutate(b1, rng2)
        assert np.array_equal(a1, b1), 'mutation sequence must be deterministic with same seed'
'\nExtra, robust checks for PermutationKeyOps:\n\n- neighbor() is bijective AND does not mutate its input\n- small-K behavior (K=1, K=2) is sensible and still bijective\n- make_population() returns a batch of valid permutations with some diversity\n- recombine(p, p) returns p (idempotence on identical parents)\n- batch_neighbors() produce "local" moves (small Hamming distance)\n- all verbs return contiguous KEY_DTYPE arrays\n'

def _hamming(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.count_nonzero(a != b))

def test_neighbor_is_bijective_and_pure():
    K = 16
    ops: PermutationKeyOps = create('permutation', K=K)
    rng = np.random.default_rng(123)
    base = ops.random(rng)
    base_copy = base.copy()
    neigh = ops.neighbor(base, rng)
    assert np.array_equal(base, base_copy), 'neighbor must not mutate input key'
    assert _is_perm(neigh), 'neighbor must keep a true permutation'
    assert neigh.dtype == KEY_DTYPE and neigh.flags['C_CONTIGUOUS']

def test_neighbor_small_K_behavior():
    ops1: PermutationKeyOps = create('permutation', K=1)
    rng1 = np.random.default_rng(1)
    k1 = ops1.random(rng1)
    n1 = ops1.neighbor(k1, rng1)
    assert np.array_equal(k1, n1)
    assert _is_perm(n1)
    ops2: PermutationKeyOps = create('permutation', K=2)
    rng2 = np.random.default_rng(2)
    k2 = ops2.random(rng2)
    n2 = ops2.neighbor(k2, rng2)
    assert _is_perm(n2)
    assert _hamming(k2, n2) in (0, 2)

def test_make_population_returns_valid_and_diverse_batch():
    K, B = (10, 64)
    ops: PermutationKeyOps = create('perm', K=K)
    rng = np.random.default_rng(7)
    pop = ops.make_population(B, rng)
    assert isinstance(pop, np.ndarray)
    assert pop.shape == (B, K)
    assert pop.dtype == KEY_DTYPE
    assert pop.flags['C_CONTIGUOUS']
    for row in pop:
        assert _is_perm(row)
    uniq = np.unique(pop.view([('', pop.dtype)] * K))
    assert uniq.size > 1, 'population should contain at least two different permutations'

def test_recombine_idempotence_when_parents_equal():
    K = 18
    ops: PermutationKeyOps = create('permutation', K=K)
    rng = np.random.default_rng(99)
    p = ops.random(rng)
    child = ops.recombine(p, p, rng)
    assert _is_perm(child)
    assert np.array_equal(child, p), 'recombine(p, p) should return p'

def test_batch_neighbors_locality_and_types():
    K, B = (14, 50)
    ops: PermutationKeyOps = create('perm', K=K)
    rng = np.random.default_rng(5)
    base = ops.random(rng)
    batch = ops.batch_neighbors(base, B, rng)
    assert batch.shape == (B, K)
    assert batch.dtype == KEY_DTYPE
    assert batch.flags['C_CONTIGUOUS']
    for row in batch:
        assert _is_perm(row)
        d = _hamming(base, row)
        assert 0 < d <= 3, f'neighbor too far from base (Hamming distance {d})'

def is_perm(x):
    return np.array_equal(np.sort(x), np.arange(len(x), dtype=x.dtype))

@pytest.mark.parametrize('K', [5, 7, 12])
def test_permutation_ops_invariants_and_shapes(K):
    ops = create('permutation', K=K)
    rng = np.random.default_rng(12345)
    key = ops.random(rng)
    assert key.dtype == KEY_DTYPE
    assert key.shape == (K,)
    assert is_perm(key)
    for _ in range(100):
        key_m = ops.mutate(key, rng)
        key_n = ops.neighbor(key, rng) if hasattr(ops, 'neighbor') else ops.mutate(key, rng)
        assert key_m.shape == (K,) and key_m.dtype == KEY_DTYPE and is_perm(key_m)
        assert key_n.shape == (K,) and key_n.dtype == KEY_DTYPE and is_perm(key_n)
    parent_a = ops.random(rng)
    parent_b = ops.random(rng)
    child = ops.recombine(parent_a, parent_b, rng)
    assert child.shape == (K,) and child.dtype == KEY_DTYPE and is_perm(child)

def test_permutation_make_population_and_batch_neighbors():
    K, N, B = (9, 16, 8)
    ops = create('permutation', K=K)
    rng = np.random.default_rng(7)
    pop = ops.make_population(N, rng)
    assert pop.shape == (N, K) and pop.dtype == KEY_DTYPE
    assert all((is_perm(pop[i]) for i in range(N)))
    base = ops.random(rng)
    neigh = ops.batch_neighbors(base, B, rng) if hasattr(ops, 'batch_neighbors') else np.stack([ops.mutate(base, rng) for _ in range(B)])
    assert neigh.shape == (B, K) and neigh.dtype == KEY_DTYPE
    assert all((is_perm(neigh[i]) for i in range(B)))
    assert np.any((neigh != base).any(axis=1))
