# -*- coding: utf-8 -*-
"""
Monoalphabetic substitution over N symbols (permutation key).
Modern pipeline: CipherPipelineMixin + PermutationOps.
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin
from rune_decrypter_prime.keyops.permutation_ops import PermutationOps


@dataclass
class MonoCipher(CipherPipelineMixin):
    """
    A one-to-one substitution: ct[i] = P[pt[i]], where P is a permutation of range(N).
    - Key: length-N permutation over [0..N-1]
    - Alphabet: N (default 29)
    """
    N: int = 29

    def __post_init__(self) -> None:
        # Key operations (GA/SA/Beam compatible) over permutations of length N.
        self._ops = PermutationOps(self.N)

    # ---- CipherPipelineMixin required surface ----

    @property
    def name(self) -> str:
        return "mono"

    @property
    def key_len(self) -> int:
        return self.N

    @property
    def key_ops(self) -> PermutationOps:
        return self._ops

    def _core_encrypt_batch(self, pt_batch: np.ndarray, key_perm: np.ndarray) -> np.ndarray:
        """
        pt_batch: (B, L) uint8/uint16 within [0..N-1]
        key_perm: (N,) permutation of 0..N-1
        return  : (B, L) mapped via key_perm
        """
        # Vectorised take is faster and avoids Python loops.
        # Ensure integer dtype for NumPy take.
        key_perm = key_perm.astype(np.int64, copy=False)
        return np.take(key_perm, pt_batch, mode="raise")

    def _core_decrypt_batch(self, ct_batch: np.ndarray, key_perm: np.ndarray) -> np.ndarray:
        """
        Inverse mapping via inverse permutation.
        """
        key_perm = key_perm.astype(np.int64, copy=False)
        inv = np.empty_like(key_perm)
        inv[key_perm] = np.arange(self.N, dtype=key_perm.dtype)
        return np.take(inv, ct_batch, mode="raise")

