"""
VectorKeyOps – contract extras that double as tutorial examples.

Why these matter:
- Many solver assume "local" moves. For vector keys, mutate should flip
  exactly one position by ±1 modulo the alphabet (M). This keeps the search
  landscape smooth and reproducible.
- Recombine (single-point crossover) should never invent values — the child
  must be composed of genes from either parent. If parents are equal, the
  child should be exactly that parent (idempotence).
- Population samplers shouldn't be degenerate. We want at least minimal
  diversity per column to avoid identical individuals.
"""
import numpy as np
from rdp.keyops.registry import create
from rdp.keyops.vector import VectorKeyOps

def _hamming(a, b) -> int:
    return int(np.count_nonzero(a != b))

def test_mutate_changes_exactly_one_position_and_by_plusminus_one():
    K, M = (12, 29)
    ops: VectorKeyOps = create('vector', K=K, mod=M)
    rng = np.random.default_rng(123)
    key = ops.random(rng)
    for _ in range(200):
        nxt = ops.mutate(key, rng)
        assert _hamming(key, nxt) == 1, 'mutate must alter exactly one index'
        idx = int(np.flatnonzero(key != nxt)[0])
        delta = (int(nxt[idx]) - int(key[idx])) % M
        assert delta in (1, M - 1), f'expected ±1 mod {M}, got {delta}'
        key = nxt

def test_recombine_child_genes_come_from_parents_only_and_idempotence():
    K, M = (16, 29)
    ops: VectorKeyOps = create('vector', K=K, mod=M)
    rng = np.random.default_rng(7)
    p1 = ops.random(rng)
    p2 = ops.random(rng)
    child_same = ops.recombine(p1, p1, rng)
    assert np.array_equal(child_same, p1)
    child = ops.recombine(p1, p2, rng)
    assert child.shape == (K,)
    assert child.dtype == np.uint8
    assert np.all((child == p1) | (child == p2)), 'crossover must select genes from parents, not invent values'

def test_make_population_shapes_types_and_diversity():
    K, M, N = (10, 29, 128)
    ops: VectorKeyOps = create('vector', K=K, mod=M)
    rng = np.random.default_rng(99)
    pop = ops.make_population(N, rng)
    assert pop.shape == (N, K)
    assert pop.dtype == np.uint8 and pop.flags['C_CONTIGUOUS']
    col_uniqs = [np.unique(pop[:, j]).size for j in range(K)]
    assert all((u > 1 for u in col_uniqs)), 'degenerate population column detected'
