from __future__ import annotations

from typing import Sequence, Optional, Any

import numpy as np

from rune_decrypter_prime.core.types import KeyOpsFamily
from rune_decrypter_prime.keyops.registry import register_keyop
from .permutation_ops import PermutationKeyOps


@register_keyop(KeyOpsFamily.CRIBBED_PERMUTATION)
class CribbedPermutationKeyOps(PermutationKeyOps):
    """
    Permutation KeyOps that honours fixed (cipher_code -> plain_code) crib mappings.

    Behaviour:
        * When no crib is provided, this is identical to PermutationKeyOps.
        * When crib entries exist, the positions listed in crib_ct_codes are pinned to the
          corresponding plaintext codes. All random/mutate/repair verbs operate solely over the
          remaining free indices.
        * Optionally prioritises a subset of "active" cipher indices so mutations touch positions
          that actually influence the ciphertext being solved.
    """

    def __init__(
        self,
        *,
        K: int,
        crib_ct_codes: Optional[Sequence[int]] = None,
        crib_pt_codes: Optional[Sequence[int]] = None,
        active_ct_codes: Optional[Sequence[int]] = None,
        crib_multi: Optional[Sequence[dict]] = None,
    ):
        super().__init__(K=K)
        self.has_crib = False
        if crib_ct_codes is None or crib_pt_codes is None:
            self.crib_ct_codes = np.empty(0, dtype=np.int64)
            self.crib_pt_codes = np.empty(0, dtype=np.int64)
        else:
            ct = np.asarray(crib_ct_codes, dtype=np.int64).ravel()
            pt = np.asarray(crib_pt_codes, dtype=np.int64).ravel()
            if ct.size != pt.size:
                raise ValueError("crib_ct_codes and crib_pt_codes must have the same length")
            if ct.size:
                if (ct < 0).any() or (ct >= self.K).any():
                    raise ValueError("crib_ct_codes entries must lie within permutation domain [0, K)")
                if (pt < 0).any() or (pt >= self.K).any():
                    raise ValueError("crib_pt_codes entries must lie within permutation codomain [0, K)")
                if np.unique(ct).size != ct.size:
                    raise ValueError("crib_ct_codes contains duplicate positions")
                if np.unique(pt).size != pt.size:
                    raise ValueError("crib_pt_codes contains duplicate values")
                self.has_crib = True
            self.crib_ct_codes = ct.astype(np.int64, copy=False)
            self.crib_pt_codes = pt.astype(np.int64, copy=False)

        self._crib_multi: dict[int, np.ndarray] = {}
        self._reserved_values: set[int] = set()
        self._crib_multi_sets: dict[int, set[int]] = {}
        self._crib_multi_index: dict[int, dict[int, int]] = {}
        self._crib_multi_weights: dict[int, Optional[np.ndarray]] = {}
        if crib_multi:
            for entry in crib_multi:
                ct_code = int(entry.get("ct"))
                if not (0 <= ct_code < self.K):
                    raise ValueError("crib_multi entries must lie within permutation domain [0, K)")
                if ct_code in self._crib_multi or (
                    self.has_crib and int(ct_code) in set(self.crib_ct_codes.tolist())
                ):
                    raise ValueError(f"crib_multi specifies duplicate cipher code {ct_code}")
                pt_codes = np.asarray(entry.get("pt_codes") or [], dtype=np.int64).ravel()
                if pt_codes.size == 0:
                    raise ValueError("crib_multi entries must include at least one plaintext candidate")
                if (pt_codes < 0).any() or (pt_codes >= self.K).any():
                    raise ValueError("crib_multi plaintext codes must lie within permutation codomain [0, K)")
                self._crib_multi[ct_code] = pt_codes
                self._crib_multi_sets[ct_code] = set(int(v) for v in pt_codes.tolist())
                self._crib_multi_index[ct_code] = {int(val): idx for idx, val in enumerate(pt_codes.tolist())}
                self._reserved_values.update(self._crib_multi_sets[ct_code])
                weights = entry.get("weights")
                if weights is not None:
                    if len(weights) != pt_codes.size:
                        raise ValueError("crib_multi weights must align with pt_codes")
                    arr_w = np.asarray(weights, dtype=np.float64).reshape(-1)
                    self._crib_multi_weights[ct_code] = arr_w
                else:
                    self._crib_multi_weights[ct_code] = None
            if self._crib_multi:
                self.has_crib = True

        if self.has_crib:
            full = np.arange(self.K, dtype=np.int64)
            self.free_ct_codes = np.setdiff1d(full, self.crib_ct_codes, assume_unique=True)
            self._crib_map = dict(zip(self.crib_ct_codes.tolist(), self.crib_pt_codes.tolist()))
        else:
            self.free_ct_codes = np.arange(self.K, dtype=np.int64)
            self._crib_map = {}

        if active_ct_codes is None:
            active = np.arange(self.K, dtype=np.int64)
        else:
            active = np.asarray(active_ct_codes, dtype=np.int64).ravel()
            active = active[(active >= 0) & (active < self.K)]
            if active.size:
                active = np.unique(active)
        if self.has_crib and active.size:
            active = np.setdiff1d(active, self.crib_ct_codes, assume_unique=True)
        if active.size == 0:
            active = np.setdiff1d(np.arange(self.K, dtype=np.int64), self.crib_ct_codes, assume_unique=True)
        self.active_ct_codes = active
        self._active_mask = np.zeros(self.K, dtype=bool)
        if self.active_ct_codes.size:
            self._active_mask[self.active_ct_codes] = True
        self._active_retry = 6

    # ------------------------------------------------------------------ helpers
    def _repair_with_crib(
        self,
        perm: np.ndarray,
        rng: Optional[np.random.Generator] = None,
    ) -> np.ndarray:
        """Return a permutation that satisfies the crib constraints."""
        if not self.has_crib:
            return np.asarray(perm, dtype=self.dtype).copy()

        perm = np.asarray(perm, dtype=np.int64).reshape(-1)
        out = np.full(self.K, -1, dtype=np.int64)
        used = np.zeros(self.K, dtype=bool)

        out[self.crib_ct_codes] = self.crib_pt_codes
        used[self.crib_pt_codes] = True

        pending_general: list[int] = []
        pending_restricted: list[int] = []
        for idx in self.free_ct_codes:
            ct_idx = int(idx)
            val = int(perm[idx])
            allowed = self._crib_multi.get(ct_idx)
            if allowed is None:
                if 0 <= val < self.K and not used[val] and val not in self._reserved_values:
                    out[idx] = val
                    used[val] = True
                else:
                    pending_general.append(ct_idx)
            else:
                allowed_set = self._crib_multi_sets.get(ct_idx, set())
                if 0 <= val < self.K and not used[val] and val in allowed_set:
                    out[idx] = val
                    used[val] = True
                else:
                    pending_restricted.append(ct_idx)

        remaining = np.flatnonzero(~used)
        if rng is not None:
            rng.shuffle(remaining)

        for pos in pending_restricted:
            chosen = self._select_allowed_value(pos, used, rng)
            out[pos] = chosen
            used[chosen] = True

        remaining = [val for val in remaining if not used[val]]
        if len(remaining) < len(pending_general):
            raise ValueError("Unable to satisfy crib constraints with provided permutation")

        for pos, val in zip(pending_general, remaining):
            out[pos] = int(val)
            used[val] = True

        return out.astype(self.dtype, copy=False)

    def _select_allowed_value(
        self,
        ct_idx: int,
        used: np.ndarray,
        rng: Optional[np.random.Generator],
    ) -> int:
        allowed = self._crib_multi.get(ct_idx)
        if allowed is None:
            raise ValueError("Invalid crib_multi state: missing allowed set")
        candidates = [int(v) for v in allowed if not used[int(v)]]
        if not candidates:
            raise ValueError("Unable to satisfy crib constraints with provided permutation")
        weight_arr = self._crib_multi_weights.get(ct_idx)
        if weight_arr is not None:
            weights = []
            index_map = self._crib_multi_index.get(ct_idx, {})
            for val in candidates:
                idx = index_map.get(val)
                weights.append(max(float(weight_arr[idx]) if idx is not None else 0.0, 0.0))
            total = sum(weights)
            if total > 0.0:
                if rng is not None:
                    probs = np.asarray(weights, dtype=np.float64) / total
                    choice = int(rng.choice(len(candidates), p=probs))
                    return int(candidates[choice])
                max_idx = int(np.argmax(weights))
                return int(candidates[max_idx])
        return int(candidates[0])

    def _repair_batch(self, batch: np.ndarray, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        if not self.has_crib:
            return np.asarray(batch, dtype=self.dtype)
        rows = [self._repair_with_crib(row, rng) for row in np.asarray(batch)]
        return np.ascontiguousarray(np.stack(rows, axis=0), dtype=self.dtype)

    def _ensure_active_change(
        self,
        original: np.ndarray,
        candidate: np.ndarray,
        rng: Optional[np.random.Generator],
    ) -> np.ndarray:
        if not self._active_mask.any():
            return np.asarray(candidate, dtype=np.int64)
        orig = np.asarray(original, dtype=np.int64)
        cand = np.asarray(candidate, dtype=np.int64)
        if np.any(orig[self._active_mask] != cand[self._active_mask]):
            return cand
        if self.active_ct_codes.size == 0:
            return cand
        if rng is None:
            idx = int(self.active_ct_codes[0])
            j = (idx + 1) % self.K if self.K > 1 else idx
        else:
            idx = int(self.active_ct_codes[rng.integers(0, self.active_ct_codes.size)])
            j = int(rng.integers(0, self.K - 1))
            if j >= idx:
                j = (j + 1) % self.K
        cand[idx], cand[j] = cand[j], cand[idx]
        return cand

    # ------------------------------------------------------------------ overrides
    def random(self, rng) -> np.ndarray:
        perm = super().random(rng)
        return self._repair_with_crib(perm, rng)

    def normalize(self, key_or_batch: np.ndarray) -> np.ndarray:
        arr = super().normalize(key_or_batch)
        if not self.has_crib:
            return arr
        if arr.ndim == 1:
            return self._repair_with_crib(arr)
        return self._repair_batch(arr)

    def mutate(self, key: np.ndarray, rng) -> np.ndarray:
        base = np.asarray(key, dtype=np.int64)
        perm = super().mutate(base, rng)
        enforced = self._ensure_active_change(base, perm, rng)
        return self._repair_with_crib(enforced, rng)

    def mutate_mixed(self, perm, rng, n: int = 1, acceptance=None) -> np.ndarray:
        base = np.asarray(perm, dtype=np.int64)
        out = super().mutate_mixed(base, rng, n=n, acceptance=acceptance)
        enforced = self._ensure_active_change(base, out, rng)
        return self._repair_with_crib(enforced, rng)

    def neighbor(self, key: np.ndarray, rng) -> np.ndarray:
        base = np.asarray(key, dtype=np.int64)
        perm = super().neighbor(base, rng)
        enforced = self._ensure_active_change(base, perm, rng)
        return self._repair_with_crib(enforced, rng)

    def recombine(self, p1: np.ndarray, p2: np.ndarray, rng) -> np.ndarray:
        child = super().recombine(p1, p2, rng)
        return self._repair_with_crib(child, rng)

    def crossover(self, p1: np.ndarray, p2: np.ndarray, rng) -> np.ndarray:
        child = super().crossover(p1, p2, rng)
        return self._repair_with_crib(child, rng)

    def make_population(self, n: int, rng) -> np.ndarray:
        pop = super().make_population(n, rng)
        if not self.has_crib:
            return pop
        return self._repair_batch(pop, rng)

    def batch_neighbors(self, base: np.ndarray, n: int, rng, policy: Optional[str] = None) -> np.ndarray:
        batch = super().batch_neighbors(base, n, rng, policy=policy)
        base_arr = np.asarray(base, dtype=np.int64)
        enforced_rows = [
            self._ensure_active_change(base_arr, row, rng) for row in np.asarray(batch)
        ]
        return self._repair_batch(np.stack(enforced_rows, axis=0), rng)

    def batch_2swap_candidates(self, key: np.ndarray, pairs: np.ndarray) -> np.ndarray:
        batch = super().batch_2swap_candidates(key, pairs)
        base_arr = np.asarray(key, dtype=np.int64)
        enforced_rows = [
            self._ensure_active_change(base_arr, row, None)
            for row in np.asarray(batch)
        ]
        return self._repair_batch(np.stack(enforced_rows, axis=0))

    def local_improve(self, key: np.ndarray, score: float, scorer: Any, rng, **hints: Any) -> tuple[np.ndarray, float]:  # type: ignore[override]
        improved_key, improved_score = super().local_improve(key, score, scorer, rng, **hints)
        base = np.asarray(key, dtype=np.int64)
        enforced = self._ensure_active_change(base, improved_key, rng)
        return self._repair_with_crib(enforced, rng), float(improved_score)

    def expand_position(self, key: np.ndarray, pos: int, rng=None) -> np.ndarray:
        batch = super().expand_position(key, pos, rng=rng)
        base_arr = np.asarray(key, dtype=np.int64)
        enforced_rows = [
            self._ensure_active_change(base_arr, row, rng)
            for row in np.asarray(batch)
        ]
        return self._repair_batch(np.stack(enforced_rows, axis=0), rng)
