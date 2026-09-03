from __future__ import annotations

from itertools import permutations
from typing import List, Sequence, Tuple

import numpy as np


def enumerate_column_permutations(
    columns: int,
    *,
    max_exact_columns: int = 7,
    sample_size: int = 6000,
    seed: int = 0,
) -> List[Tuple[int, ...]]:
    """
    Return deterministic column-permutation candidates for sub_then_col workflows.

    - For small columns, return all permutations (exact search).
    - For larger columns, return a deterministic sampled pool that includes
      identity plus a few local swaps.
    """
    c = int(columns)
    if c <= 0:
        raise ValueError("columns must be >= 1")
    if c == 1:
        return [(0,)]

    if c <= int(max_exact_columns):
        return list(permutations(range(c)))

    rng = np.random.default_rng(int(seed))
    sample_n = max(c * 12, int(sample_size))
    out: List[Tuple[int, ...]] = []
    seen: set[Tuple[int, ...]] = set()

    ident = tuple(range(c))
    out.append(ident)
    seen.add(ident)

    # Local adjacency swaps from identity.
    for i in range(c - 1):
        t = list(range(c))
        t[i], t[i + 1] = t[i + 1], t[i]
        k = tuple(t)
        if k not in seen:
            seen.add(k)
            out.append(k)

    # A few long-range swaps from identity.
    for i in range(0, c // 2):
        j = c - 1 - i
        if i == j:
            continue
        t = list(range(c))
        t[i], t[j] = t[j], t[i]
        k = tuple(t)
        if k not in seen:
            seen.add(k)
            out.append(k)

    while len(out) < sample_n:
        k = tuple(int(x) for x in rng.permutation(c).tolist())
        if k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def undo_columnar_with_perm(
    ct_idx: Sequence[int] | np.ndarray,
    *,
    perm: Sequence[int],
) -> np.ndarray:
    """
    Undo simple columnar transposition for one key permutation.

    `perm` is the read-out order used during encryption.
    """
    ct = np.asarray(ct_idx, dtype=np.uint8).reshape(-1)
    p = np.asarray(perm, dtype=np.int64).reshape(-1)
    c = int(p.size)
    if c <= 0:
        raise ValueError("perm must be non-empty")
    if np.unique(p).size != c or int(p.min()) != 0 or int(p.max()) != c - 1:
        raise ValueError("perm must be a permutation of [0..columns-1]")
    if c == 1:
        return ct.copy()

    L = int(ct.size)
    rows = (L + c - 1) // c
    rem = L % c
    col_lens = np.full((c,), rows - 1, dtype=np.int64)
    if rem == 0:
        col_lens[:] = rows
    else:
        col_lens[:rem] = rows

    cols: List[np.ndarray] = [np.empty((0,), dtype=np.uint8) for _ in range(c)]
    pos = 0
    for col_idx in p.tolist():
        ln = int(col_lens[int(col_idx)])
        cols[int(col_idx)] = ct[pos : pos + ln]
        pos += ln

    out = np.empty((L,), dtype=np.uint8)
    w = 0
    for r in range(rows):
        for col in range(c):
            if r < int(col_lens[col]):
                out[w] = cols[col][r]
                w += 1
    return out
