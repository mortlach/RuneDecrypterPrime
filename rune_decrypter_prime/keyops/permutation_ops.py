# -*- coding: utf-8 -*-
# rune_decrypter_prime/keyops/permutation_ops.py
# --------------------------------------------------------------------
# Purpose: Permutation key operations
# --------------------------------------------------------------------
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional, Tuple, Any
import numpy as np
# --- existing imports at top of keyops.py ---
from dataclasses import dataclass
import numpy as np

from rune_decrypter_prime.core.keyops import KeyOps, KeyCaps

# todo move lal keyops into their own file lto to make it easy to extend
# to keyops base class and wya to pdefien particualr keyops mutation setc if you want
class PermutationOps:
    def __init__(self, K: int):
        self.K = int(K)
        self.caps = KeyCaps(kind="perm", length=self.K)

    def normalize(self, key: np.ndarray) -> np.ndarray:
        """
        If 'key' is already a proper permutation of [0..K-1] with unique values,
        return it unchanged. Otherwise, project arbitrary integers to a valid
        permutation by rank (stable), without implicitly inverting valid perms.
        """
        k = np.asarray(key, dtype=np.int64)

        # Fast-path: proper permutation → keep as-is
        if k.ndim == 1 and k.size == self.K:
            vals = k
            if (
                np.min(vals) == 0
                and np.max(vals) == self.K - 1
                and np.unique(vals).size == self.K
            ):
                return vals.astype(np.uint8, copy=False)

        # Fallback: project arbitrary vector to a permutation by rank
        vals = (k % self.K).astype(np.int64, copy=False)
        idx = np.argsort(vals, kind="stable")
        return idx.astype(np.uint8, copy=False)

     # ----- core API -----
    def random(self, rng: np.random.Generator) -> np.ndarray:
        return rng.permutation(self.K).astype(np.uint8)

    def mutate(self, key: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        # single 2-swap
        i, j = rng.integers(0, self.K, size=2)
        if i == j:
            return key.copy()
        k = key.copy()
        k[i], k[j] = k[j], k[i]
        return k

    def mutate_k_swaps(self, key: np.ndarray, rng: np.random.Generator, k: int = 2) -> np.ndarray:
        k = max(1, int(k))
        out = key.copy()
        for _ in range(k):
            i, j = rng.integers(0, self.K, size=2)
            if i == j:
                continue
            out[i], out[j] = out[j], out[i]
        return out

    def mutate_block_swap_OLD(self, key: np.ndarray, rng: np.random.Generator,
                          block_size: int = 3) -> np.ndarray:
        """Swap two adjacent blocks of given size."""
        k = key.copy()
        start = int(rng.integers(0, self.K - 2 * block_size))
        a, b = start, start + block_size
        k[a:b], k[b:b + block_size] = k[b:b + block_size].copy(), k[a:b].copy()
        return k

    def mutate_block_swap(self, key: np.ndarray, rng: np.random.Generator,
                          block_size: int = 3) -> np.ndarray:
        """
        Swap two adjacent blocks of given size, if possible.
        Falls back to a simple swap if K is too small.

        Guarantees the output is still a valid permutation.
        """
        K = self.K
        if K < 2 * block_size:
            # Not enough room for two full blocks → fall back
            return self.mutate_swap(key, rng)

        k = key.copy()
        # choose a valid starting index so both blocks fit
        start = int(rng.integers(0, K - 2 * block_size + 1))
        a, b = start, start + block_size
        k[a:b], k[b:b + block_size] = k[b:b + block_size].copy(), k[a:b].copy()
        return k


    def mutate_cycle3(self, key: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """Randomly permute 3 positions in a cycle."""
        i, j, kpos = rng.choice(self.K, size=3, replace=False)
        k = key.copy()
        k[i], k[j], k[kpos] = k[kpos], k[i], k[j]
        return k

    def mutate_rotate_subset(self, key: np.ndarray, rng: np.random.Generator,
                             size: int = 4) -> np.ndarray:
        """Rotate a small contiguous subset by one step."""
        k = key.copy()
        start = int(rng.integers(0, self.K - size + 1))
        subset = k[start:start + size].copy()
        k[start:start + size] = np.roll(subset, 1)
        return k

    def mutate_mixed(self, key: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """Randomly choose among operators (70% swap-2, 20% cycle-3, 10% block)."""
        r = rng.random()
        if r < 0.7:
            return self.mutate(key, rng)
        elif r < 0.9:
            return self.mutate_cycle3(key, rng)
        else:
            return self.mutate_block_swap(key, rng)

    def crossover(self, p1: np.ndarray, p2: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """
        Order Crossover (OX) – robust for permutations.
        """
        n = self.K
        a, b = sorted(rng.integers(0, n, size=2))
        child = -np.ones(n, dtype=np.int64)
        child[a:b] = p1[a:b]
        fill = [x for x in p2 if x not in child[a:b]]
        j = 0
        for i in range(n):
            if child[i] == -1:
                child[i] = fill[j]; j += 1
        return np.asarray(child, np.uint8)

    # ----- micro-optim helpers for GA/SA -----
    def batch_2swap_candidates(self, key: np.ndarray, pairs: np.ndarray) -> np.ndarray:
        """
        Build a batch of candidates by applying 2-swaps specified in pairs[:,2].
        pairs shape: [M,2] with indices in [0..K-1].
        Returns: [M,K] uint8
        """
        key = np.asarray(key, np.uint8)
        pairs = np.asarray(pairs, np.int64)
        M = int(pairs.shape[0])
        out = np.tile(key[None, :], (M, 1))
        for m in range(M):
            i, j = int(pairs[m,0]), int(pairs[m,1])
            if i != j:
                out[m, i], out[m, j] = out[m, j], out[m, i]
        return out.astype(np.uint8)