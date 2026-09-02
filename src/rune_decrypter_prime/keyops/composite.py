# rune_decrypter_prime/keyops/composite.py
from __future__ import annotations

from dataclasses import dataclass, is_dataclass
from typing import Any, Optional, Sequence

import numpy as np

from rdp.core.types import KeyOpsFamily, KEY_DTYPE
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


def _ncr_limited(n: int, r: int, limit: int) -> int:
    if r < 0 or r > n:
        return 0
    r = min(r, n - r)
    if r == 0:
        return 1
    if limit <= 0:
        return limit + 1
    result = 1
    for i in range(1, r + 1):
        result = result * (n - r + i) // i
        if result > limit:
            return limit + 1
    return result


@dataclass
class CompositeKeyConfig:
    K: int
    mod: int = 29
    interruptors_pool: Sequence[int] = ()
    interruptors_min: int = 0
    interruptors_max: int = 0
    interruptors_sentinel: int = -1
    interruptors_search_strategy: str = "auto"
    interruptors_bruteforce_max: int = 0
    core_family: KeyOpsFamily | str = KeyOpsFamily.VECTOR


@register_keyop(KeyOpsFamily.COMPOSITE)
class CompositeKeyOps(KeyOpBase):
    """
    Composite key: [core key | interruptor positions].

    - Core key is managed by a nested KeyOps family (vector/permutation/etc).
    - Interruptor positions are unique, sorted indices from a fixed pool.
      Unused slots are filled with a sentinel (-1) to support variable counts.
    """

    def __init__(self, cfg_or_K: Optional[Any] = None, **kwargs: Any):
        if is_dataclass(cfg_or_K):
            cfg = cfg_or_K
        elif isinstance(cfg_or_K, (int, np.integer)) or cfg_or_K is None:
            cfg = CompositeKeyConfig(
                K=int(cfg_or_K) if cfg_or_K is not None else int(kwargs.get("K")),
                mod=int(kwargs.get("mod", 29)),
                interruptors_pool=kwargs.get("interruptors_pool", ()),
                interruptors_min=int(kwargs.get("interruptors_min", 0) or 0),
                interruptors_max=int(kwargs.get("interruptors_max", 0) or 0),
                interruptors_sentinel=int(kwargs.get("interruptors_sentinel", -1)),
                interruptors_search_strategy=kwargs.get("interruptors_search_strategy", "auto"),
                interruptors_bruteforce_max=int(kwargs.get("interruptors_bruteforce_max", 0) or 0),
                core_family=kwargs.get("core_family", KeyOpsFamily.VECTOR),
            )
        else:
            cfg = CompositeKeyConfig(
                K=int(kwargs.get("K")),
                mod=int(kwargs.get("mod", 29)),
                interruptors_pool=kwargs.get("interruptors_pool", ()),
                interruptors_min=int(kwargs.get("interruptors_min", 0) or 0),
                interruptors_max=int(kwargs.get("interruptors_max", 0) or 0),
                interruptors_sentinel=int(kwargs.get("interruptors_sentinel", -1)),
                interruptors_search_strategy=kwargs.get("interruptors_search_strategy", "auto"),
                interruptors_bruteforce_max=int(kwargs.get("interruptors_bruteforce_max", 0) or 0),
                core_family=kwargs.get("core_family", KeyOpsFamily.VECTOR),
            )

        self.core_K: int = int(cfg.K)
        self.mod: int = int(cfg.mod)
        self.interrupt_K: int = int(getattr(cfg, "interruptors_max", 0))
        self.interrupt_min: int = int(getattr(cfg, "interruptors_min", 0))
        self.sentinel: int = int(getattr(cfg, "interruptors_sentinel", -1))
        self.core_family = cfg.core_family

        if self.sentinel >= 0:
            raise ValueError("interruptors_sentinel must be negative")
        if self.interrupt_min < 0:
            raise ValueError("interruptors_min must be >= 0")

        pool = np.asarray(list(cfg.interruptors_pool or ()), dtype=np.int64).reshape(-1)
        if pool.size == 0:
            raise ValueError("CompositeKeyOps requires a non-empty interruptors_pool")
        pool = np.unique(pool)
        if np.any(pool < 0):
            raise ValueError("interruptors_pool values must be >= 0")
        if self.interrupt_K <= 0:
            raise ValueError("CompositeKeyOps requires interruptors_max > 0")
        if self.interrupt_min > self.interrupt_K:
            raise ValueError("interruptors_min cannot exceed interruptors_max")
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
            "interruptors_min": self.interrupt_min,
            "interruptors_max": self.interrupt_K,
            "interruptors_sentinel": self.sentinel,
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

        strategy_raw = kwargs.get(
            "interruptors_search_strategy",
            getattr(cfg, "interruptors_search_strategy", "auto"),
        )
        self._interrupt_search_strategy = str(strategy_raw or "auto").strip().lower()
        if self._interrupt_search_strategy not in {"auto", "bruteforce", "keyops"}:
            raise ValueError("interruptors_search_strategy must be 'auto', 'bruteforce', or 'keyops'")

        self._interrupt_bruteforce_max = int(
            kwargs.get(
                "interruptors_bruteforce_max",
                getattr(cfg, "interruptors_bruteforce_max", 0),
            )
            or 0
        )

        base_limit = int(kwargs.get("interruptors_expand_limit", 64) or 64)
        self._expand_limit = self._resolve_expand_limit(base_limit)
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
            if v < 0:
                continue
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
        if len(uniq) < self.interrupt_min:
            for v in pool.tolist():
                if v not in seen:
                    uniq.append(int(v))
                    seen.add(v)
                    if len(uniq) >= self.interrupt_min:
                        break

        if len(uniq) > self.interrupt_K:
            uniq = uniq[: self.interrupt_K]

        uniq = sorted(uniq)
        pad = [self.sentinel] * (self.interrupt_K - len(uniq))
        return np.asarray(uniq + pad, dtype=self.dtype)

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

    def _interruptor_value_cap(self) -> int:
        allow_sentinel = self.interrupt_min < self.interrupt_K
        return int(self.pool_size + (1 if allow_sentinel else 0))

    def _interruptor_combo_count(self, limit: int) -> int:
        if limit <= 0:
            return limit + 1
        total = 0
        n = int(self.pool_size)
        for k in range(int(self.interrupt_min), int(self.interrupt_K) + 1):
            total += _ncr_limited(n, k, limit - total)
            if total > limit:
                return limit + 1
        return total

    def _resolve_expand_limit(self, base_limit: int) -> int:
        base_limit = max(1, int(base_limit))
        if self._interrupt_search_strategy == "bruteforce":
            return max(base_limit, self._interruptor_value_cap())
        if self._interrupt_search_strategy == "auto" and self._interrupt_bruteforce_max > 0:
            combos = self._interruptor_combo_count(self._interrupt_bruteforce_max)
            if combos <= self._interrupt_bruteforce_max:
                return max(base_limit, self._interruptor_value_cap())
        return base_limit

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
        count = int(_rng_integers(rng, self.interrupt_min, self.interrupt_K + 1))
        if count > 0:
            picks = _rng_choice(rng, self.pool, size=count, replace=False)
            picks = sorted(int(v) for v in np.asarray(picks, dtype=np.int64).tolist())
        else:
            picks = []
        pad = [self.sentinel] * (self.interrupt_K - len(picks))
        intr = np.asarray(picks + pad, dtype=self.dtype)
        return np.concatenate([core, intr], axis=0).astype(self.dtype, copy=False)

    def mutate(self, key: np.ndarray, rng) -> np.ndarray:
        base = self.normalize(key)
        core = base[: self.core_K].copy()
        intr = base[self.core_K :].copy()

        mutate_interruptors = (
            self.core_K == 0 or (self.interrupt_K > 0 and rng.random() < self._mut_interrupt_prob)
        )
        if mutate_interruptors:
            used = [int(v) for v in intr.tolist() if int(v) >= 0]
            used_set = set(used)
            count = len(used)
            allow_remove = count > self.interrupt_min
            allow_add = count < self.interrupt_K

            slot = int(_rng_integers(rng, 0, self.interrupt_K))
            remove = allow_remove and (not allow_add or rng.random() < 0.5)
            if remove:
                intr[slot] = self.sentinel
            else:
                avail = [int(v) for v in self.pool.tolist() if v not in used_set]
                if avail:
                    repl = int(_rng_choice(rng, avail, size=None, replace=False))
                    intr[slot] = repl
                elif allow_remove:
                    intr[slot] = self.sentinel
            intr = self._normalize_interruptors(intr)
        else:
            core = np.asarray(self._core_ops.mutate(core, rng), dtype=self.dtype)

        out = np.concatenate([core.reshape(-1), intr.reshape(-1)], axis=0)
        return np.asarray(out, dtype=self.dtype)

    def recombine(self, p1: np.ndarray, p2: np.ndarray, rng) -> np.ndarray:
        a = self.normalize(p1)
        b = self.normalize(p2)
        core = np.asarray(self._core_ops.recombine(a[: self.core_K], b[: self.core_K], rng), dtype=self.dtype)

        intr_a = [int(v) for v in a[self.core_K :].tolist() if int(v) >= 0]
        intr_b = [int(v) for v in b[self.core_K :].tolist() if int(v) >= 0]
        union = sorted(set(intr_a + intr_b))

        count_a = len(intr_a)
        count_b = len(intr_b)
        target = count_a if rng.random() < 0.5 else count_b
        target = max(self.interrupt_min, min(self.interrupt_K, int(target)))

        if target <= 0:
            picks = []
        elif len(union) >= target:
            chosen = _rng_choice(rng, union, size=target, replace=False)
            picks = [int(v) for v in np.asarray(chosen, dtype=np.int64).tolist()]
        else:
            picks = list(union)
            for v in self.pool.tolist():
                if v not in picks:
                    picks.append(int(v))
                if len(picks) >= target:
                    break
        picks = sorted(picks)
        pad = [self.sentinel] * (self.interrupt_K - len(picks))
        intr = np.asarray(picks + pad, dtype=self.dtype)

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
            count = int(_rng_integers(rng, self.interrupt_min, self.interrupt_K + 1))
            if count > 0:
                picks = _rng_choice(rng, self.pool, size=count, replace=False)
                picks = sorted(int(v) for v in np.asarray(picks, dtype=np.int64).tolist())
            else:
                picks = []
            pad = [self.sentinel] * (self.interrupt_K - len(picks))
            intr_rows.append(np.asarray(picks + pad, dtype=self.dtype))
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
        used_vals = [int(v) for v in intr.tolist() if int(v) >= 0]
        used = set(used_vals)
        available = [int(v) for v in self.pool.tolist() if v not in used or v == int(intr[idx])]
        allow_sentinel = (len(used_vals) > self.interrupt_min) or (int(intr[idx]) < 0)
        if allow_sentinel:
            available.append(self.sentinel)
        if not available:
            return base.reshape(1, -1)

        if len(available) > self._expand_limit:
            available = _rng_choice(rng, available, size=self._expand_limit, replace=False).tolist()

        rows = []
        seen = set()
        for v in available:
            cand = base.copy()
            cand[self.core_K + idx] = int(v)
            norm = self.normalize(cand)
            key_bytes = norm.tobytes()
            if key_bytes in seen:
                continue
            seen.add(key_bytes)
            rows.append(norm)
        if not rows:
            return base.reshape(1, -1)
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
        used = intr[intr >= 0]
        assert used.size >= self.interrupt_min, "Interruptor count below minimum"
        assert used.size <= self.interrupt_K, "Interruptor count exceeds maximum"
        assert np.all(np.isin(used, self.pool)), "Interruptor positions must be in pool"
        assert len(np.unique(used)) == used.size, "Interruptor positions must be unique"
        if used.size:
            assert np.all(np.diff(np.sort(used)) >= 0), "Interruptor positions must be sorted"
        if np.any(intr < 0):
            first_neg = int(np.argmax(intr < 0))
            assert np.all(intr[first_neg:] < 0), "Sentinel values must be trailing"
            if used.size:
                assert np.array_equal(intr[:used.size], np.sort(used)), "Interruptor positions must be sorted"


__all__ = ["CompositeKeyConfig", "CompositeKeyOps"]
