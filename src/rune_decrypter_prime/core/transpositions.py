# # ============================================================
# # rune_decrypter_prime/core/transpositions.py
# # Columnar transposition helpers (single/batch); extensible hook
# # for other transpositions via cipher config hints.
# # ============================================================
# repo/core/transpositions.py

from __future__ import annotations
from typing import List, Sequence, TypeVar

T = TypeVar("T")

def assert_is_permutation(perm: Sequence[int], n: int | None = None) -> None:
    """
    Ensures `perm` is a bijection over 0..n-1 (or len(perm) when n is None).
    Raises ValueError with a precise message otherwise.
    """
    if n is None:
        n = len(perm)
    if len(perm) != n:
        raise ValueError(f"Permutation length {len(perm)} does not match n={n}.")
    seen = set(perm)
    if seen != set(range(n)):
        missing = set(range(n)) - seen
        extra = seen - set(range(n))
        details = []
        if missing:
            details.append(f"missing={sorted(missing)}")
        if extra:
            details.append(f"extra={sorted(extra)}")
        raise ValueError("Invalid permutation; " + ", ".join(details))

def invert_permutation(perm: Sequence[int]) -> List[int]:
    n = len(perm)
    assert_is_permutation(perm, n)
    out = [0] * n
    for i, p in enumerate(perm):
        out[p] = i
    return out

def apply_permutation(xs: Sequence[T], perm: Sequence[int]) -> List[T]:
    assert_is_permutation(perm, len(xs))
    return [xs[i] for i in perm]

def apply_inverse_permutation(xs: Sequence[T], perm: Sequence[int]) -> List[T]:
    return apply_permutation(xs, invert_permutation(perm))

