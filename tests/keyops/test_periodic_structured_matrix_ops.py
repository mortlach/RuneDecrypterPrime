import numpy as np
from rdp.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps

def _assert_perm(block: np.ndarray, size: int) -> None:
    assert np.array_equal(np.sort(block.astype(np.int64)), np.arange(size, dtype=np.int64))

def test_random_and_mutate_preserve_blocks():
    ops = PeriodicStructuredMatrixKeyOps(K=21, period=3, A=7)
    rng = np.random.default_rng(0)
    k = ops.random(rng)
    for r in range(3):
        _assert_perm(k[r * 7:(r + 1) * 7], 7)
    k2 = ops.mutate(k, rng)
    for r in range(3):
        _assert_perm(k2[r * 7:(r + 1) * 7], 7)

def test_tail_permutation_preserved():
    ops = PeriodicStructuredMatrixKeyOps(K=14, period=2, A=5, columns=4)
    rng = np.random.default_rng(1)
    k = ops.random(rng)
    for r in range(2):
        _assert_perm(k[r * 5:(r + 1) * 5], 5)
    _assert_perm(k[10:14], 4)
    k2 = ops.mutate(k, rng)
    _assert_perm(k2[10:14], 4)

def test_recombine_preserves_invariants():
    ops = PeriodicStructuredMatrixKeyOps(K=14, period=2, A=5, columns=4)
    rng = np.random.default_rng(2)
    a = ops.random(rng)
    b = ops.random(rng)
    child = ops.recombine(a, b, rng)
    for r in range(2):
        _assert_perm(child[r * 5:(r + 1) * 5], 5)
    _assert_perm(child[10:14], 4)

def test_normalize_repairs_blocks():
    ops = PeriodicStructuredMatrixKeyOps(K=14, period=2, A=5, columns=4)
    bad = np.zeros(14, dtype=np.int64)
    fixed = ops.normalize(bad)
    for r in range(2):
        _assert_perm(fixed[r * 5:(r + 1) * 5], 5)
    _assert_perm(fixed[10:14], 4)
