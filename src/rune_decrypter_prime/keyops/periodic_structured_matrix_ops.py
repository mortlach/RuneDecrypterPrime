# rune_decrypter_prime/keyops/periodic_structured_matrix_ops.py
from __future__ import annotations
from typing import Any, Optional
import numpy as np

from rune_decrypter_prime.core.types import KeyOpsFamily, KEY_DTYPE
from rune_decrypter_prime.keyops.base_keyops import KeyOpBase, KeyCaps
from rune_decrypter_prime.keyops.registry import register_keyop


def _rng_integers(rng, low: int, high: int, size=None):
    if hasattr(rng, "integers"):
        return rng.integers(low, high, size=size, endpoint=False)
    return rng.randint(low, high, size=size)


def _rng_random(rng, size=None):
    if hasattr(rng, "random"):
        return rng.random(size)
    return rng.random_sample(size)


def _rng_shuffle(rng, arr: np.ndarray) -> None:
    if hasattr(rng, "shuffle"):
        rng.shuffle(arr)
        return
    raise TypeError("RNG must support shuffle")


def _is_perm_1d(vec: np.ndarray, size: int) -> bool:
    arr = np.asarray(vec, dtype=np.int64).reshape(-1)
    if arr.size != size:
        return False
    if arr.min() < 0 or arr.max() >= size:
        return False
    return np.unique(arr).size == size


def _repair_to_perm_1d(vec: np.ndarray, size: int) -> np.ndarray:
    v = np.asarray(vec, dtype=np.int64).reshape(-1)
    if v.size != size:
        raise ValueError(f"Expected length {size}, got {v.size}")
    order = np.argsort(v, kind="mergesort")
    out = np.empty_like(order, dtype=KEY_DTYPE)
    out[order] = np.arange(order.size, dtype=KEY_DTYPE)
    return out


def _ox(a: np.ndarray, b: np.ndarray, rng) -> np.ndarray:
    k = int(a.size)
    if k <= 1:
        return a.copy()
    i = int(_rng_integers(rng, 0, k))
    j = int(_rng_integers(rng, 0, k - 1))
    if j >= i:
        j += 1
    if i > j:
        i, j = j, i
    child = np.full(k, -1, dtype=KEY_DTYPE)
    child[i : j + 1] = a[i : j + 1]
    used = set(int(x) for x in child[i : j + 1].tolist())
    cursor = (j + 1) % k
    for val in np.concatenate((b[j + 1 :], b[: j + 1])):
        ival = int(val)
        if ival in used:
            continue
        child[cursor] = ival
        cursor = (cursor + 1) % k
    return child


@register_keyop(KeyOpsFamily.MATRIX)
class PeriodicStructuredMatrixKeyOps(KeyOpBase):
    """
    Structured key:
      - p blocks of size A (each a permutation of 0..A-1)
      - optional tail of size W (permutation of 0..W-1)
    """

    def __init__(self, cfg_or_K: Optional[Any] = None, **kwargs: Any):
        if isinstance(cfg_or_K, (int, np.integer)):
            K = int(cfg_or_K)
        elif cfg_or_K is None:
            K = int(kwargs.get("K", 0) or 0)
        else:
            K = int(getattr(cfg_or_K, "K", 0) or getattr(cfg_or_K, "length", 0) or 0)

        period = kwargs.get("period", None)
        if period is None:
            raise ValueError("PeriodicStructuredMatrixKeyOps requires period")
        A = kwargs.get("A", kwargs.get("alphabet_size", 29))
        columns = kwargs.get("columns", None)

        self.period = int(period)
        self.A = int(A)
        self.columns = int(columns) if columns is not None else 0
        if self.period <= 0:
            raise ValueError("period must be >= 1")
        if self.A <= 0:
            raise ValueError("alphabet_size must be >= 1")
        if self.columns < 0:
            raise ValueError("columns must be >= 0")
        if self.columns > 255:
            raise ValueError("columns must be <= 255 (uint8 column limit)")

        sub_len = self.period * self.A
        expected = sub_len + (self.columns if self.columns else 0)
        if K <= 0:
            K = expected
        if K != expected:
            if self.columns:
                raise ValueError(
                    f"Expected K == period*A + columns ({expected}), got {K}"
                )
            raise ValueError(f"Expected K == period*A ({expected}), got {K}")

        traits = {
            "family": KeyOpsFamily.MATRIX,
            "structure": "periodic_structured",
            "alphabet_size": int(self.A),
            "period": int(self.period),
            "has_columnar": bool(self.columns),
        }
        if self.columns:
            traits["columns"] = int(self.columns)

        self.sub_len = sub_len
        self.K = int(K)
        self.dtype = KEY_DTYPE
        self._col_swap_prob = float(kwargs.get("col_swap_prob", 0.15) or 0.15)
        prefers_batch = bool(kwargs.get("prefers_batch", True))

        self.caps = KeyCaps(
            length=self.K,
            prefers_batch=prefers_batch,
            traits=traits,
        )
        super().__init__(self.caps)

        self._id_block = np.arange(self.A, dtype=self.dtype)
        self._id_cols = (
            np.arange(self.columns, dtype=self.dtype) if self.columns else None
        )

    def _normalize_1d(self, key: np.ndarray) -> np.ndarray:
        arr = np.asarray(key, dtype=np.int64).reshape(-1)
        if arr.size != self.K:
            raise ValueError(f"Expected key length {self.K}, got {arr.size}")
        out = np.empty(self.K, dtype=self.dtype)
        for r in range(self.period):
            start = r * self.A
            end = start + self.A
            block = arr[start:end]
            if not _is_perm_1d(block, self.A):
                block = _repair_to_perm_1d(block, self.A)
            out[start:end] = block
        if self.columns:
            tail = arr[self.sub_len : self.sub_len + self.columns]
            if not _is_perm_1d(tail, self.columns):
                tail = _repair_to_perm_1d(tail, self.columns)
            out[self.sub_len : self.sub_len + self.columns] = tail
        return out

    def random(self, rng) -> np.ndarray:
        parts = []
        for _ in range(self.period):
            block = self._id_block.copy()
            _rng_shuffle(rng, block)
            parts.append(block)
        if self.columns:
            tail = self._id_cols.copy()
            _rng_shuffle(rng, tail)
            parts.append(tail)
        return np.concatenate(parts, axis=0).astype(self.dtype, copy=False)

    def normalize(self, key_or_batch: np.ndarray) -> np.ndarray:
        arr = np.asarray(key_or_batch)
        if arr.ndim == 1:
            return self._normalize_1d(arr).astype(self.dtype, copy=False)
        if arr.ndim == 2:
            rows = [self._normalize_1d(row) for row in arr]
            return np.ascontiguousarray(np.stack(rows, axis=0), dtype=self.dtype)
        raise ValueError("normalize expects (K,) or (B,K) array")

    def _mutate_1d(self, key: np.ndarray, rng, strength: int = 1) -> np.ndarray:
        out = self._normalize_1d(key).astype(self.dtype, copy=True)
        steps = max(1, int(strength))
        for _ in range(steps):
            do_col = self.columns and (_rng_random(rng) < self._col_swap_prob)
            if do_col:
                if self.columns < 2:
                    continue
                i = int(_rng_integers(rng, 0, self.columns))
                j = int(_rng_integers(rng, 0, self.columns - 1))
                if j >= i:
                    j += 1
                a = self.sub_len + i
                b = self.sub_len + j
            else:
                r = int(_rng_integers(rng, 0, self.period))
                i = int(_rng_integers(rng, 0, self.A))
                j = int(_rng_integers(rng, 0, self.A - 1))
                if j >= i:
                    j += 1
                a = r * self.A + i
                b = r * self.A + j
            out[a], out[b] = out[b], out[a]
        return out

    def mutate(
        self, key: np.ndarray, rng, prob: Optional[float] = None, strength: int = 1
    ) -> np.ndarray:
        arr = np.asarray(key)
        if arr.ndim == 1:
            return self._mutate_1d(arr, rng, strength=strength)
        if arr.ndim == 2:
            base = self.normalize(arr)
            out = np.ascontiguousarray(base.copy(), dtype=self.dtype)
            if prob is None:
                prob = 1.0
            mask = _rng_random(rng, size=out.shape[0]) < float(prob)
            rows = np.nonzero(mask)[0]
            for idx in rows:
                out[idx] = self._mutate_1d(out[idx], rng, strength=strength)
            return out
        raise ValueError("mutate expects (K,) or (B,K) array")

    def _batch_mutate(
        self, base: np.ndarray, rng, batch_size: int, strength: int = 1
    ) -> np.ndarray:
        base_norm = self._normalize_1d(base)
        out = np.empty((int(batch_size), self.K), dtype=self.dtype)
        for i in range(int(batch_size)):
            out[i] = self._mutate_1d(base_norm, rng, strength=strength)
        return out

    def batch_neighbors(
        self, base: np.ndarray, n: int, rng, policy: Optional[str] = None
    ) -> np.ndarray:
        return self._batch_mutate(base, rng, batch_size=int(n), strength=1)

    def recombine(self, p1: np.ndarray, p2: np.ndarray, rng) -> np.ndarray:
        if np.asarray(p1).ndim == 2 and np.isscalar(p2):
            raise TypeError("batch recombine not supported")

        a = self._normalize_1d(p1)
        b = self._normalize_1d(p2)
        child = np.empty_like(a, dtype=self.dtype)

        for r in range(self.period):
            start = r * self.A
            end = start + self.A
            if _rng_random(rng) < 0.5:
                child[start:end] = a[start:end]
            else:
                child[start:end] = b[start:end]

        if self.columns:
            tail_a = a[self.sub_len : self.sub_len + self.columns]
            tail_b = b[self.sub_len : self.sub_len + self.columns]
            if self.columns <= 1:
                child[self.sub_len : self.sub_len + self.columns] = tail_a
            else:
                if _rng_random(rng) < 0.5:
                    tail = _ox(tail_a, tail_b, rng)
                else:
                    tail = _ox(tail_b, tail_a, rng)
                child[self.sub_len : self.sub_len + self.columns] = tail

        return self._normalize_1d(child)

    def make_population(self, n: int, rng) -> np.ndarray:
        rows = [self.random(rng) for _ in range(int(n))]
        return np.ascontiguousarray(np.stack(rows, axis=0), dtype=self.dtype)


__all__ = ["PeriodicStructuredMatrixKeyOps"]
