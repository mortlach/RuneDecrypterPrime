# rune_decrypter_prime/keyops/permutation_ops.py
# -*- coding: utf-8 -*-
"""
Permutation KeyOps
- Public config: PermutationKeyConfig
- Public class:  PermutationKeyOps  (alias: PermutationKey)
- Contracts kept:
  * uses KeyOpBase and KeyCaps (old names)
  * sets self.caps.length (critical for OptimizerBase)
  * accepts either PermutationKeyConfig OR raw K (positional/kwarg)
  * returns dtype uint8, shapes (K,) or (B,K)
  * provides capability verbs: random, normalize, mutate, neighbor, recombine,
    make_population, batch_neighbors, local_improve, expand_position (optional)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any
import numpy as np

from rune_decrypter_prime.core.types import KeyKind, KeyOpsFamily, KEY_DTYPE
from rune_decrypter_prime.io.rng import RNGController
from .base_keyops import KeyOpBase, KeyCaps
from .registry import register_keyop

@dataclass(frozen=True)
class PermutationKeyConfig:
    """Configuration for permutation keys: K = permutation length."""
    K: int

@register_keyop(KeyOpsFamily.PERMUTATION)
class PermutationKeyOps(KeyOpBase):
    """
    Key space: permutations of [0..K-1] (uint8).
    Exposes generic capability verbs so solver remain key-agnostic.
    """

    # -------- construction / caps --------
    def __init__(self, cfg_or_K=None, **kwargs):
        # Unwrap config or raw args
        if isinstance(cfg_or_K, PermutationKeyConfig):
            K = int(cfg_or_K.K)
        elif isinstance(cfg_or_K, (int, np.integer)):
            K = int(cfg_or_K)
        elif "K" in kwargs:
            K = int(kwargs["K"])
        else:
            raise TypeError("PermutationKeyOps expects PermutationKeyConfig or K=int")

        if K <= 0:
            raise ValueError("PermutationKeyOps: K must be >= 1")

        # Caps (KEEP THESE NAMES)
        self.caps = KeyCaps(
            length=K,                      # <-- critical for OptimizerBase
            prefers_batch=True,
            traits={"family": KeyOpsFamily.PERMUTATION},  # unify with registry canonical
        )
        # todo used in sa get rid
        self.caps.kind = KeyKind.PERM
        self.K = K
        self.dtype = KEY_DTYPE
        super().__init__(self.caps)

        # Work buffers
        self._id = np.arange(self.K, dtype=self.dtype)
        self._tmp = np.empty(self.K, dtype=self.dtype)
        self._inv = np.empty(self.K, dtype=self.dtype)
        self._idx2 = np.empty(2, dtype=np.int64)
        self._idx3 = np.empty(3, dtype=np.int64)
        self._batch_tmp: Optional[np.ndarray] = None  # lazy

        # Advertise verbs if supported on caps
        if hasattr(self.caps, "ops"):
            self.caps.ops |= {
                "random", "normalize", "mutate", "neighbor", "recombine",
                "make_population", "batch_neighbors", "local_improve", "expand_position",
                "crossover",  # alias to recombine
            }

        self.caps.traits = dict(family=KeyOpsFamily.PERMUTATION, length=self.K)
        self.caps.hints = {
            "sa": {"move": "neighbor", "batch_verb": "batch_neighbors"},
            "ga": {"cx": ["recombine"], "mut": ["mutate"]},
            "beam": {"expand": "expand_position", "branch": 64},
        }

    # ----------- helpers (pure) -----------
    @staticmethod
    def _is_perm_1d(key: np.ndarray) -> bool:
        if key.ndim != 1:
            return False
        arr = np.asarray(key, dtype=np.int64).reshape(-1)
        K = arr.size
        if K == 0:
            return False
        return np.array_equal(np.sort(arr), np.arange(K, dtype=np.int64))

    @staticmethod
    def _repair_to_perm_1d(vec: np.ndarray) -> np.ndarray:
        # stable rank -> 0..K-1
        v = np.asarray(vec, dtype=np.int64).reshape(-1)
        order = np.argsort(v, kind="mergesort")
        out = np.empty_like(order, dtype=KEY_DTYPE)
        out[order] = np.arange(order.size, dtype=KEY_DTYPE)
        return out

    # ----------- required verbs -----------
    def random(self, rng) -> np.ndarray:
        # Generator has .shuffle; returns uint8 permutation
        out = self._id.copy()
        rng.shuffle(out)
        return out

    def normalize(self, key_or_batch: np.ndarray) -> np.ndarray:
        arr = np.asarray(key_or_batch)
        if arr.ndim == 1:
            if not self._is_perm_1d(arr):
                return self._repair_to_perm_1d(arr)
            return arr.astype(self.dtype, copy=False)
        if arr.ndim == 2:
            rows = [
                row if self._is_perm_1d(row) else self._repair_to_perm_1d(row)
                for row in arr
            ]
            return np.ascontiguousarray(np.stack(rows, axis=0), dtype=self.dtype)
        raise ValueError("normalize expects (K,) or (B,K) array")

    def mutate(self, key: np.ndarray, rng) -> np.ndarray:
        # 2-swap (keeps bijection)
        out = np.asarray(key, dtype=self.dtype).copy()
        if self.K > 1:
            i = int(rng.integers(0, self.K))
            j = int(rng.integers(0, self.K))
            if i == j:
                j = (j + 1) % self.K
            out[i], out[j] = out[j], out[i]
        return out.astype(self.dtype, copy=False)

    def mutate_k_swaps(self, key: np.ndarray, rng, k: int = 2) -> np.ndarray:
        """Apply up to `k` random swaps; mirrors legacy GA heuristics."""
        steps = max(1, int(k))
        out = np.asarray(key, dtype=self.dtype).copy()
        if self.K <= 1:
            return out
        for _ in range(steps):
            i = int(rng.integers(0, self.K))
            j = int(rng.integers(0, self.K - 1))
            if j >= i:
                j += 1
            out[i], out[j] = out[j], out[i]
        return out.astype(self.dtype, copy=False)

    # ----------- recommended verbs -----------
    def neighbor(self, key: np.ndarray, rng) -> np.ndarray:
        # 80% 2-swap, 20% 3-cycle
        if self.K < 3 or rng.random() < 0.8:
            return self.mutate(key, rng)
        out = np.asarray(key, dtype=self.dtype).copy()
        self._idx3[:] = rng.choice(self.K, size=3, replace=False)
        i, j, k = int(self._idx3[0]), int(self._idx3[1]), int(self._idx3[2])
        out[i], out[j], out[k] = out[k], out[i], out[j]
        return out

    def mutate_mixed(self, perm, rng, n: int = 1, acceptance=None):
        """
        Permutation-safe 'mixed' mutator for SA/GA.
        Uses only structure-preserving moves (no element resample/reset).
        """
        p = np.asarray(perm, dtype=self.dtype).copy()
        K = int(p.shape[0])
        if K <= 1:
            return p

        for _ in range(max(1, int(n))):
            r = float(rng.random())
            if r < 0.50:
                # local: adjacent swap
                i = int(rng.integers(0, K - 1))
                p[i], p[i + 1] = p[i + 1], p[i]
            elif r < 0.85:
                # global: swap two distinct positions
                i = int(rng.integers(0, K))
                j = int(rng.integers(0, K - 1))
                if j >= i:
                    j += 1
                p[i], p[j] = p[j], p[i]
            else:
                # slightly bigger step: two swaps
                i1 = int(rng.integers(0, K))
                j1 = int(rng.integers(0, K - 1))
                if j1 >= i1:
                    j1 += 1
                p[i1], p[j1] = p[j1], p[i1]

                i2 = int(rng.integers(0, K))
                j2 = int(rng.integers(0, K - 1))
                if j2 >= i2:
                    j2 += 1
                p[i2], p[j2] = p[j2], p[i2]

        return p

    @staticmethod
    def _pmx(a: np.ndarray, b: np.ndarray, rng) -> np.ndarray:
        K = a.size
        i, j = sorted(rng.choice(K, size=2, replace=False))
        child = np.full(K, 255, dtype=KEY_DTYPE)
        child[i:j+1] = a[i:j+1]
        # PMX mapping
        for k in range(i, j + 1):
            if b[k] not in child:
                pos = k
                val = b[k]
                while True:
                    idx = int(np.where(b == a[pos])[0][0])
                    if child[idx] == 255:
                        child[idx] = val
                        break
                    pos = idx
        for k in range(K):
            if child[k] == 255:
                child[k] = b[k]
        return child

    @staticmethod
    def _ox(a: np.ndarray, b: np.ndarray, rng) -> np.ndarray:
        K = a.size
        i, j = sorted(rng.choice(K, size=2, replace=False))
        child = np.full(K, 255, dtype=KEY_DTYPE)
        child[i:j+1] = a[i:j+1]
        used = set(child[i:j+1].tolist())
        cursor = (j + 1) % K
        for val in np.concatenate((b[j + 1 :], b[: j + 1])):
            if val not in used:
                child[cursor] = val
                cursor = (cursor + 1) % K
        return child

    def recombine(self, p1: np.ndarray, p2: np.ndarray, rng) -> np.ndarray:
        # Use Generator.random() (not RandomState.rand)
        child = self._pmx(p1, p2, rng) if rng.random() < 0.5 else self._ox(p1, p2, rng)
        return self.normalize(child)

    # Alias for code that expects "crossover" verb
    def crossover(self, p1: np.ndarray, p2: np.ndarray, rng) -> np.ndarray:
        return self.recombine(p1, p2, rng)

    def make_population(self, n: int, rng) -> np.ndarray:
        rows = [self.random(rng) for _ in range(int(n))]
        return np.ascontiguousarray(np.stack(rows, axis=0), dtype=self.dtype)

    def materialize(self, seed: int | None = None):
        """
        Deterministically generate a single valid permutation key from a seed,
        using the class' existing random(...) implementation.
        """
        base_seed = int(seed) if seed is not None else 0
        controller = RNGController(seed=base_seed, prefix="keyops.permutation")
        rng = controller.child("materialize")
        return self.random(rng)

    def validate(self, key) -> None:
        """
        Raise if `key` is not a true permutation of 0..K-1 (dtype uint8, shape (K,)).
        K is inferred from the key itself to avoid coupling to internal fields.
        """
        import numpy as np
        k = np.asarray(key, dtype=self.dtype)
        assert k.ndim == 1, f"Permutation key must be 1-D, got shape {k.shape}"
        K = int(k.shape[0])
        # values must be < K and a bijection
        assert np.all(k < K), "Permutation entries must be < K"
        assert len(np.unique(k)) == K, "Permutation must be a bijection of 0..K-1"

    def batch_neighbors(self, base: np.ndarray, n: int, rng, policy: Optional[str] = None) -> np.ndarray:
        B = int(n)
        if self._batch_tmp is None or self._batch_tmp.shape != (B, self.K):
            self._batch_tmp = np.empty((B, self.K), dtype=self.dtype)
        out = self._batch_tmp
        for t in range(B):
            if policy == "swap" or rng.random() < 0.7:
                out[t] = self.mutate(base, rng)
            else:
                out[t] = self.neighbor(base, rng)
        return np.ascontiguousarray(out.copy(), dtype=self.dtype)

    def batch_2swap_candidates(self, key: np.ndarray, pairs: np.ndarray) -> np.ndarray:
        """Vectorised two-swap generator used by GA local polish."""
        base = np.asarray(key, dtype=self.dtype).reshape(1, -1)
        pairs = np.asarray(pairs, dtype=np.int64)
        if pairs.ndim != 2 or pairs.shape[1] != 2:
            raise ValueError("pairs must have shape (N,2)")
        out = np.tile(base, (pairs.shape[0], 1))
        for idx, (i_raw, j_raw) in enumerate(pairs):
            i = int(i_raw) % self.K
            j = int(j_raw) % self.K
            if i == j:
                continue
            out[idx, i], out[idx, j] = out[idx, j], out[idx, i]
        return np.ascontiguousarray(out, dtype=self.dtype)

    def local_improve(self, key: np.ndarray, score: float, scorer: Any, rng, **hints: Any) -> tuple[np.ndarray, float]:
        """Permutation-aware hill climb that mirrors the Stage-1 GA polish."""
        opts = dict(hints.get("hint") or {})
        budget = max(8, int(opts.get("budget", 64)))
        batch_size = max(4, min(int(opts.get("perm_batch_size",
                                            opts.get("perm_batch_improve_size", 64))), budget))
        rounds = int(opts.get("perm_batch_rounds",
                              opts.get("perm_batch_improve_rounds", 3)))
        hill_iters = int(opts.get("perm_hill_iters", opts.get("local_improve_iters", 200)))
        hill_swaps = max(1, int(opts.get("perm_hill_swaps", opts.get("local_improve_k", 2))))

        best_k = np.ascontiguousarray(key, dtype=self.dtype).copy()
        best_s = float(score)

        def _score_batch(arr: np.ndarray) -> np.ndarray:
            res = scorer(arr)
            if isinstance(res, np.ndarray):
                return res.astype(np.float64, copy=False)
            if np.isscalar(res):
                return np.asarray([res], dtype=np.float64)
            return np.asarray(res, dtype=np.float64)

        # Batch 2-swap rounds (stop early on stagnation)
        rounds = max(1, min(rounds, max(1, budget // max(1, batch_size))))
        for _ in range(rounds):
            pairs = rng.integers(0, self.K, size=(batch_size, 2))
            try:
                cand = self.batch_2swap_candidates(best_k, pairs)
            except Exception:
                cand = self.batch_neighbors(best_k, batch_size, rng, policy="swap")
            scores = _score_batch(cand)
            idx = int(np.argmax(scores))
            if scores[idx] > best_s:
                best_s = float(scores[idx])
                best_k = cand[idx].copy()
            else:
                break

        # Random multi-swap hill climb
        if hill_iters > 0:
            cand = best_k.copy()
            for _ in range(hill_iters):
                cand[:] = best_k
                for _ in range(hill_swaps):
                    i = int(rng.integers(0, self.K))
                    j = int(rng.integers(0, self.K - 1))
                    if j >= i:
                        j += 1
                    cand[i], cand[j] = cand[j], cand[i]
                sc = float(_score_batch(cand[None, :])[0])
                if sc > best_s:
                    best_s = sc
                    best_k = cand.copy()

        return best_k, best_s

    def expand_position(self, prefix: np.ndarray, pos: int, rng) -> np.ndarray:
        if pos < 0 or pos >= self.K:
            return np.ascontiguousarray(prefix[None, :], dtype=self.dtype)
        m = max(16, min(4 * self.K, 128))
        out = np.empty((m, self.K), dtype=self.dtype)
        for t in range(m):
            cand = prefix.copy()
            j = int(rng.integers(0, self.K))  # use Generator.integers, not randint
            if j != pos:
                cand[pos], cand[j] = cand[j], cand[pos]
            out[t] = cand
        return out

# Back-compat export
PermutationKey = PermutationKeyOps

__all__ = ["PermutationKeyConfig", "PermutationKeyOps", "PermutationKey"]




