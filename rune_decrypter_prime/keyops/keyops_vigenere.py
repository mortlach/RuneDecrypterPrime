# # ============================================================
# # rune_decrypter_prime/ciphers/keyops_vigenere.py
# # ============================================================
from __future__ import annotations
import numpy as np
from typing import Optional
from rune_decrypter_prime.core.keyops import AdditiveVectorOps, KeyCaps, KeyOps

ArrayU8 = np.ndarray

class KeyOpsVigenere(KeyOps):
    """
    KeyOps for additive Vigenère (mod A) over K-length uint8 keys.

    Contract:
      - random(rng) -> [K] uint8 in [0..A-1]
      - normalize(key) -> [K] uint8, fixed length, mod A
      - mutate(key, rng) -> small tweak valid key
      - crossover(k1, k2, rng) -> child valid key (optional but provided)
      - partial_mask(L, depth) -> indices influenced by first `depth` columns (for Beam)
    """
    def __init__(self, K: int, A: int = 29):
        self._ops = AdditiveVectorOps(K, A)
        self.caps = KeyCaps(
            kind="additive",
            length=K,
            can_partial_score=True,
            can_additive_invariant=True,
        )

    def random(self, rng: np.random.Generator) -> ArrayU8:
        return self._ops.random(rng)

    def normalize(self, key: ArrayU8) -> ArrayU8:
        return self._ops.normalize(key)

    def mutate(self, key: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        return self._ops.mutate(key, rng)

    def crossover(self, k1: ArrayU8, k2: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        return self._ops.crossover(k1, k2, rng)

    def partial_mask(self, L: int, depth: int):
        return self._ops.partial_mask(L, depth)

