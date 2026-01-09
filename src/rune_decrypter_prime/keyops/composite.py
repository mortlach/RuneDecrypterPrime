# rune_decrypter_prime/keyops/composite.py
from __future__ import annotations

from dataclasses import dataclass, is_dataclass
from typing import Any, Iterable, Optional, Sequence

import numpy as np

from rune_decrypter_prime.core.types import KeyOpsFamily, KEY_DTYPE
from rune_decrypter_prime.io.rng import RNGController
from .base_keyops import KeyOpBase, KeyCaps
from .registry import register_keyop


def _rng_integers(rng, low: int, high: int, size=None):
    if hasattr(rng, "integers"):  # Generator
        return rng.integers(low, high, size=size, endpoint=False)
    return rng.randint(low, high, size=size)


def _rng_choice(rng, values, size=None, replace=False):
    if hasattr(rng, "choice"):
        return rng.choice(values, size=size, replace=replace)
    raise TypeError("RNG must support .choice (Generator/RandomState).")


@dataclass
class CompositeKeyConfig:
    K: int
    mod: int = 29
    interruptors_pool: Sequence[int] = ()
    interruptors_max: int = 0
    core_family: KeyOpsFamily | str = KeyOpsFamily.VECTOR


@register_keyop(KeyOpsFamily.COMPOSITE)
class CompositeKeyOps(KeyOpBase):
    """
    Composite key: [core key | interruptor positions].

    - Core key is managed by a nested KeyOps family (vector/permutation/etc).
    - Interruptor positions are unique, sorted indices from a fixed pool.
    """

    def __init__(self, cfg_or_K: Optional[Any] = None, **kwargs: Any):
        if is_dataclass(cfg_or_K):
            cfg = cfg_or_K
        elif isinstance(cfg_or_K, (int, np.integer)) or cfg_or_K is None:
            cfg = CompositeKeyConfig(
                K=int(cfg_or_K) if cfg_or_K is not None else int(kwargs.get("K")),
                mod=int(kwargs.get("mod", 29)),
                interruptors_pool=kwargs.get("interruptors_pool", ()),
                interruptors_max=int(kwargs.get("interruptors_max", 0) or 0),
                core_family=kwargs.get("core_family", KeyOpsFamily.VECTOR),
            )
        else:
            cfg = CompositeKeyConfig(
                K=int(kwargs.get("K")),
                mod=int(kwargs.get("mod", 29)),
                interruptors_pool=kwargs.get("interruptors_pool", ()),
                interruptors_max=int(kwargs.get("interruptors_max", 0) or 0),
                core_family=kwargs.get("core_family", KeyOpsFamily.VECTOR),
            )

        self.core_K: int = int(cfg.K)
        self.mod: int = int(cfg.mod)
        self.interrupt_K: int = int(cfg.interruptors_max)
        self.core_family = cfg.core_family

        pool = np.asarray(list(cfg.interruptors_pool or ()), dtype=np.int64).reshape(-1)
        if pool.size == 0:
            raise ValueError("CompositeKeyOps requires a non-empty interruptors_pool")
        pool = np.unique(pool)
        if np.any(pool < 0):
            raise ValueError("interruptors_pool values must be >= 0")
        if self.interrupt_K <= 0:
            raise ValueError("CompositeKeyOps requires interruptors_max > 0")
        if pool.size < self.interrupt_K:
            raise ValueError("interruptors_pool must contain at least interruptors_max entries")
        self.pool = np.sort(pool)
        self.pool_size = int(self.pool.size)

        if self.core_K is None or self.core_K <= 0:
            raise ValueError("CompositeKeyOps requires K (core key length) > 0")

        # Build nested core KeyOps
        from rune_decrypter_prime.keyops.registry import create as create_keyops
        core_family = self.core_family
        if hasattr(core_family, "value"):
            core_family = core_family.value
        core_family = str(core_family).lower().strip()
        if core_family in {"composite", "param"}:
            raise ValueError("CompositeKeyOps core_family must be non-composite")

        core_kwargs = {"K": self.core_K}
        if core_family == KeyOpsFamily.VECTOR.value:
            core_kwargs["mod"] = self.mod
        self._core_ops = create_keyops(core_family, **core_kwargs)

        total_K = self.core_K + self.interrupt_K
        traits = {
            "family": KeyOpsFamily.COMPOSITE,
            "core_family": core_family,
            "core_length": self.core_K,
            "interruptors_max": self.interrupt_K,
        }
        ops = {
            "random",
            "normalize",
            "mutate",
            "recombine",
            "make_population",
            "batch_neighbors",
            "expand_position",
        }
        self.caps = KeyCaps(length=total_K, prefers_batch=True, traits=traits, ops=ops)
        self.dtype = KEY_DTYPE
        super().__init__(self.caps)

        self._expand_limit = int(kwargs.get("interruptors_expand_limit", 64) or 64)
        self._mut_interrupt_prob = float(kwargs.get("interruptors_mut_prob", 0.2) or 0.2)

    # --------------------------- helpers ---------------------------------
    def _normalize_interruptors_1d(self, raw: np.ndarray) -> np.ndarray:
        if self.interrupt_K == 0:
            return np.empty(0, dtype=self.dtype)
        if raw.size != self.interrupt_K:
            raise ValueError(f"Expected interruptor segment of length {self.interrupt_K}, got {raw.size}")

        # Snap values to nearest pool entry (deterministic).
        pool = self.pool
        mapped = []
        for val in raw.tolist():
            v = int(val)
            idx = int(np.searchsorted(pool, v))
            if idx <= 0:
                mapped.append(int(pool[0]))
            elif idx >= pool.size:
                mapped.append(int(pool[-1]))
            else:
                left = int(pool[idx - 1])
                right = int(pool[idx])
                mapped.append(left if abs(v - left) <= abs(v - right) else right)

        # Enforce uniqueness, then fill missing from pool in ascending order.
        seen = set()
        uniq = []
        for v in mapped:
            if v not in seen:
                uniq.append(v)
                seen.add(v)
        if len(uniq) < self.interrupt_K:
            for v in pool.tolist():
                if v not in seen:
                    uniq.append(int(v))
                    seen.add(v)
                    if len(uniq) == self.interrupt_K:
                        break

        uniq = sorted(uniq)
        return np.asarray(uniq, dtype=self.dtype)

    def _normalize_interruptors(self, raw: np.ndarray) -> np.ndarray:
        raw = np.asarray(raw, dtype=np.int64)
        if raw.ndim == 1:
            return self._normalize_interruptors_1d(raw)
        if raw.ndim == 2:
            rows = [self._normalize_interruptors_1d(row) for row in raw]
            return np.ascontiguousarray(np.stack(rows, axis=0), dtype=self.dtype)
        raise ValueError("Interruptor segment must be 1-D or 2-D array")

    def _split(self, key: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        arr = np.asarray(key, dtype=self.dtype).reshape(-1)
        if arr.size != (self.core_K + self.interrupt_K):
            raise ValueError(f"Composite key length {arr.size} != {self.core_K + self.interrupt_K}")
        core = arr[: self.core_K]
        intr = arr[self.core_K :]
        return core, intr

    def split_key(self, key_or_batch: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        arr = self.normalize(key_or_batch)
        if arr.ndim == 1:
            core, intr = self._split(arr)
            return core.astype(self.dtype, copy=False), intr.astype(np.intp, copy=False)
        if arr.ndim == 2:
            core = arr[:, : self.core_K]
            intr = arr[:, self.core_K :]
            return core.astype(self.dtype, copy=False), intr.astype(np.intp, copy=False)
        raise ValueError("Composite split_key expects (K,) or (B,K) array")

    # --------------------------- required verbs ---------------------------
    def normalize(self, key_or_batch: np.ndarray) -> np.ndarray:
        arr = np.asarray(key_or_batch)
        if arr.ndim == 1:
            core, intr = self._split(arr)
            core_norm = self._core_ops.normalize(core)
            intr_norm = self._normalize_interruptors(intr)
            out = np.concatenate([core_norm.reshape(-1), intr_norm.reshape(-1)], axis=0)
            return np.asarray(out, dtype=self.dtype)
        if arr.ndim == 2:
            if arr.shape[1] != (self.core_K + self.interrupt_K):
                raise ValueError(f"Composite key length {arr.shape[1]} != {self.core_K + self.interrupt_K}")
            core = arr[:, : self.core_K]
            intr = arr[:, self.core_K :]
            try:
                core_norm = self._core_ops.normalize(core)
                if core_norm.ndim != 2:
                    raise ValueError("core normalize did not return batch")
            except Exception:
                core_norm = np.stack([self._core_ops.normalize(row) for row in core], axis=0)
            intr_norm = self._normalize_interruptors(intr)
            out = np.concatenate([core_norm, intr_norm], axis=1)
            return np.ascontiguousarray(out, dtype=self.dtype)
        raise ValueError("Composite normalize expects (K,) or (B,K) array")

    def random(self, rng) -> np.ndarray:
        core = np.asarray(self._core_ops.random(rng), dtype=self.dtype).reshape(-1)
        intr = _rng_choice(rng, self.pool, size=self.interrupt_K, replace=False)
        intr = np.sort(np.asarray(intr, dtype=self.dtype))
        return np.concatenate([core, intr], axis=0).astype(self.dtype, copy=False)

    def mutate(self, key: np.ndarray, rng) -> np.ndarray:
        base = self.normalize(key)
        core = base[: self.core_K].copy()
        intr = base[self.core_K :].copy()

        mutate_interruptors = (
            self.core_K == 0 or (self.interrupt_K > 0 and rng.random() < self._mut_interrupt_prob)
        )
        if mutate_interruptors:
            used = set(int(v) for v in intr.tolist())
            avail = [int(v) for v in self.pool.tolist() if v not in used]
            if avail:
                slot = int(_rng_integers(rng, 0, self.interrupt_K))
                repl = int(_rng_choice(rng, avail, size=None, replace=False))
                intr[slot] = repl
                intr = self._normalize_interruptors(intr)
            else:
                core = np.asarray(self._core_ops.mutate(core, rng), dtype=self.dtype)
        else:
            core = np.asarray(self._core_ops.mutate(core, rng), dtype=self.dtype)

        out = np.concatenate([core.reshape(-1), intr.reshape(-1)], axis=0)
        return np.asarray(out, dtype=self.dtype)

    def recombine(self, p1: np.ndarray, p2: np.ndarray, rng) -> np.ndarray:
        a = self.normalize(p1)
        b = self.normalize(p2)
        core = np.asarray(self._core_ops.recombine(a[: self.core_K], b[: self.core_K], rng), dtype=self.dtype)

        intr_a = a[self.core_K :]
        intr_b = b[self.core_K :]
        union = sorted(set(int(v) for v in np.concatenate([intr_a, intr_b], axis=0).tolist()))
        if len(union) >= self.interrupt_K:
            chosen = _rng_choice(rng, union, size=self.interrupt_K, replace=False)
            intr = np.sort(np.asarray(chosen, dtype=self.dtype))
        else:
            intr = list(union)
            for v in self.pool.tolist():
                if v not in intr:
                    intr.append(int(v))
                if len(intr) == self.interrupt_K:
                    break
            intr = np.asarray(sorted(intr), dtype=self.dtype)

        out = np.concatenate([core.reshape(-1), intr.reshape(-1)], axis=0)
        return np.asarray(out, dtype=self.dtype)

    # --------------------------- batch helpers ---------------------------
    def make_population(self, n: int, rng) -> np.ndarray:
        n = int(n)
        if n <= 0:
            return np.empty((0, self.core_K + self.interrupt_K), dtype=self.dtype)

        if "make_population" in getattr(self._core_ops.caps, "ops", set()):
            core = self._core_ops.make_population(n, rng)
        else:
            core = np.stack([self._core_ops.random(rng) for _ in range(n)], axis=0)
        core = np.asarray(core, dtype=self.dtype)

        intr_rows = []
        for _ in range(n):
            picks = _rng_choice(rng, self.pool, size=self.interrupt_K, replace=False)
            intr_rows.append(np.sort(np.asarray(picks, dtype=self.dtype)))
        intr = np.ascontiguousarray(np.stack(intr_rows, axis=0), dtype=self.dtype)

        out = np.concatenate([core, intr], axis=1)
        return np.ascontiguousarray(out, dtype=self.dtype)

    def batch_neighbors(self, base: np.ndarray, n: int, rng) -> np.ndarray:
        n = int(n)
        base_norm = self.normalize(base)
        out = np.empty((n, base_norm.size), dtype=self.dtype)
        for i in range(n):
            out[i] = self.mutate(base_norm, rng)
        return np.ascontiguousarray(out, dtype=self.dtype)

    def expand_position(self, key: np.ndarray, pos: int, rng) -> np.ndarray:
        base = self.normalize(key)
        pos = int(pos)
        if pos < 0 or pos >= base.size:
            return base.reshape(1, -1)

        if pos < self.core_K:
            core_base = base[: self.core_K]
            intr = base[self.core_K :]
            if "expand_position" in getattr(self._core_ops.caps, "ops", set()):
                core_exp = self._core_ops.expand_position(core_base, pos, rng)
            else:
                core_exp = np.tile(core_base, (self.mod, 1)).astype(self.dtype, copy=False)
                core_exp[:, pos] = np.arange(self.mod, dtype=self.dtype)
            intr_tile = np.tile(intr, (core_exp.shape[0], 1)).astype(self.dtype, copy=False)
            return np.concatenate([core_exp, intr_tile], axis=1)

        idx = pos - self.core_K
        intr = base[self.core_K :].copy()
        used = set(int(v) for v in intr.tolist())
        available = [int(v) for v in self.pool.tolist() if v not in used or v == int(intr[idx])]
        if not available:
            return base.reshape(1, -1)

        if len(available) > self._expand_limit:
            available = _rng_choice(rng, available, size=self._expand_limit, replace=False).tolist()

        rows = []
        for v in available:
            cand = base.copy()
            cand[self.core_K + idx] = int(v)
            rows.append(self.normalize(cand))
        return np.ascontiguousarray(np.stack(rows, axis=0), dtype=self.dtype)

    # --------------------------- misc helpers ---------------------------
    def materialize(self, seed: int | None = None):
        base_seed = int(seed) if seed is not None else 0
        controller = RNGController(seed=base_seed, prefix="keyops.composite")
        rng = controller.child("materialize")
        return self.random(rng)

    def validate(self, key) -> None:
        k = np.asarray(key, dtype=self.dtype)
        assert k.ndim == 1, f"Composite key must be 1-D, got shape {k.shape}"
        assert k.size == (self.core_K + self.interrupt_K), "Composite key length mismatch"
        intr = k[self.core_K :]
        assert np.all(np.isin(intr, self.pool)), "Interruptor positions must be in pool"
        assert len(np.unique(intr)) == self.interrupt_K, "Interruptor positions must be unique"
        assert np.all(np.diff(np.sort(intr)) >= 0), "Interruptor positions must be sorted"


__all__ = ["CompositeKeyConfig", "CompositeKeyOps"]
