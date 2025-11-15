"""
PermutationKeyOps — tutorial-level contract tests

What this file teaches (and enforces):

1) Domain & shape:
   - A permutation key is a 1-D array of length K containing each integer
     0..K-1 exactly once (dtype KEY_DTYPE / int16).

2) Local moves (search-friendly):
   - mutate(key, rng) performs a small, bijective change (typically a 2-swap).
   - neighbor(key, rng) is also a small bijection (e.g., swap or 3-cycle).

   Why this matters:
   Metaheuristics (SA, Beam, GA) assume "neighbor" means a *local* step,
   not a random jump. Keeping Hamming distance small preserves a smooth
   landscape for incremental improvement.

3) Recombination (GA crossover):
   - recombine(p1, p2, rng) returns a valid permutation
   - recombine(p, p, rng) == p (idempotence)
   - Child genes are a reordering of 0..K-1; no invented values.

4) Batches:
   - make_population(N, rng) returns NxK valid permutations with some diversity.
   - batch_neighbors(base, B, rng) returns B neighbors, each different from base.

5) Determinism & purity:
   - All ops consume only the injected RNG, not global state.
   - Ops never modify their input arrays in-place.

Use these tests as a template when designing your own permutation-style KeyOps.
"""

import numpy as np
import pytest

from rune_decrypter_prime.core.types import KEY_DTYPE
from rune_decrypter_prime.keyops.registry import create
from rune_decrypter_prime.keyops import PermutationKeyOps


def _is_perm(arr: np.ndarray) -> bool:
    "Quick invariant: 1-D KEY_DTYPE and a true permutation of 0..K-1."
    if not isinstance(arr, np.ndarray) or arr.ndim != 1:
        return False
    if arr.dtype != KEY_DTYPE:
        return False
    return np.array_equal(np.sort(arr), np.arange(arr.size, dtype=KEY_DTYPE))


def _hamming(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.count_nonzero(a != b))


def test_random_returns_valid_permutation_with_correct_types():
    K = 12
    ops: PermutationKeyOps = create("permutation", K=K)
    rng = np.random.default_rng(123)
    key = ops.random(rng)
    assert _is_perm(key), "random() must return a true permutation"
    assert key.shape == (K,)
    assert key.flags["C_CONTIGUOUS"]


def test_mutate_is_local_bijective_and_pure():
    K = 16
    ops: PermutationKeyOps = create("permutation", K=K)
    rng = np.random.default_rng(2024)

    base = ops.random(rng)
    base_copy = base.copy()
    nxt = ops.mutate(base, rng)

    # Purity: input is unchanged
    assert np.array_equal(base, base_copy), "mutate() must not modify input"
    # Bijective: still a permutation
    assert _is_perm(nxt)
    # Locality: typical mutate is a 2-swap -> Hamming distance 2
    d = _hamming(base, nxt)
    assert d == 2, f"expected a 2-swap (Hamming 2), got {d}"


def test_neighbor_is_small_bijective_move_and_not_equal():
    K = 18
    ops: PermutationKeyOps = create("permutation", K=K)
    rng = np.random.default_rng(7)

    key = ops.random(rng)
    for _ in range(200):
        nxt = ops.neighbor(key, rng)
        assert _is_perm(nxt), "neighbor() must keep a true permutation"
        d = _hamming(key, nxt)
        # Allow common policies: swap (2) or 3-cycle (3)
        assert 0 < d <= 3, f"neighbor too far or no-op (Hamming {d})"
        key = nxt  # step forward


def test_recombine_child_is_permutation_and_idempotent_on_equal_parents():
    K = 20
    ops: PermutationKeyOps = create("permutation", K=K)
    rng = np.random.default_rng(99)

    p1 = ops.random(rng)
    p2 = ops.random(rng)

    # Idempotence when parents equal
    same = ops.recombine(p1, p1, rng)
    assert np.array_equal(same, p1), "recombine(p,p) should return p"
    assert _is_perm(same)

    # With different parents, child is still a valid permutation
    child = ops.recombine(p1, p2, rng)
    assert _is_perm(child)
    assert child.shape == (K,)
    assert child.dtype == KEY_DTYPE


def test_make_population_and_batch_neighbors_contracts():
    K, N, B = 14, 64, 32
    ops: PermutationKeyOps = create("permutation", K=K)
    rng = np.random.default_rng(11)

    pop = ops.make_population(N, rng)
    assert pop.shape == (N, K)
    assert pop.dtype == KEY_DTYPE and pop.flags["C_CONTIGUOUS"]
    # Every row is a permutation; ensure some diversity
    assert all(_is_perm(row) for row in pop)
    uniq = np.unique(pop.view([("", pop.dtype)] * K))
    assert uniq.size > 1, "population should have at least two distinct permutations"

    base = ops.random(rng)
    batch = ops.batch_neighbors(base, B, rng)
    assert batch.shape == (B, K)
    assert batch.dtype == KEY_DTYPE and batch.flags["C_CONTIGUOUS"]
    for row in batch:
        assert _is_perm(row)
        assert _hamming(base, row) in (2, 3), "neighbors should be small moves"


def test_determinism_same_seed_same_sequence():
    K = 10
    ops_a: PermutationKeyOps = create("permutation", K=K)
    ops_b: PermutationKeyOps = create("permutation", K=K)

    rng1 = np.random.default_rng(12345)
    rng2 = np.random.default_rng(12345)

    a = ops_a.random(rng1)
    b = ops_b.random(rng2)
    assert np.array_equal(a, b)

    # Compare first N mutations under identical RNG streams
    for _ in range(50):
        a = ops_a.mutate(a, rng1)
        b = ops_b.mutate(b, rng2)
        assert np.array_equal(a, b), "mutate sequence should be deterministic with same seed"


def test_small_K_edge_cases():
    # K=1: only one permutation exists; neighbor returns same
    ops1: PermutationKeyOps = create("permutation", K=1)
    rng1 = np.random.default_rng(1)
    k1 = ops1.random(rng1)
    n1 = ops1.neighbor(k1, rng1)
    assert np.array_equal(k1, n1) and _is_perm(n1)

    # K=2: neighbors/mutations are swaps -> Hamming distance 2
    ops2: PermutationKeyOps = create("permutation", K=2)
    rng2 = np.random.default_rng(2)
    k2 = ops2.random(rng2)
    n2 = ops2.neighbor(k2, rng2)
    m2 = ops2.mutate(k2, rng2)
    assert _hamming(k2, n2) == 2 and _hamming(k2, m2) == 2
    assert _is_perm(n2) and _is_perm(m2)
