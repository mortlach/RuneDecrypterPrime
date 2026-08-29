# rune_decrypter_prime/ciphers/block_permutation_cipher.py
from __future__ import annotations
import numpy as np
from rune_decrypter_prime.keyops.permutation_ops import PermutationOps
from .pipeline import CipherPipelineMixin, ArrayU8

class BlockPermutationCipher(CipherPipelineMixin):
    """
    Fixed-size block permutation. Values unchanged; only positions permuted
    inside each block of size K. The tail (len % K) is left unpermuted.

    Key: permutation of [0..K-1] applied identically to every full block.
    """
    A = 29

    def __init__(self, cfg, *, text_transposition="ltr", key_transposition="ltr"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", text_transposition),
            key_transposition=getattr(cfg, "key_transposition", key_transposition),
        )
        self.cfg = cfg
        K = int(getattr(cfg, "key_length", 0))
        if K <= 1:
            raise ValueError("BlockPermutation requires key_length K >= 2")
        self.keyops = PermutationOps(K)

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        # For a pure permutation cipher, decrypt == encrypt with the inverse perm.
        # But GA/SA supply the "encryption-order" permutation by convention.
        # We'll compute inverse and apply block-wise.
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        L = int(ct_tr.size)
        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            key = np.asarray(keys_tr[b], dtype=np.int64)
            inv = np.empty(K, dtype=np.int64)
            inv[key] = np.arange(K, dtype=np.int64)
            out[b] = self._apply_block_perm(ct_tr, inv)
        return out

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        L = int(pt_tr.size)
        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            key = np.asarray(keys_tr[b], dtype=np.int64)
            out[b] = self._apply_block_perm(pt_tr, key)
        return out

    @staticmethod
    def _apply_block_perm(x: np.ndarray, perm: np.ndarray) -> np.ndarray:
        L = int(x.size); K = int(perm.size)
        y = np.empty(L, dtype=np.uint8)
        nb = L // K
        for bi in range(nb):
            s = bi * K
            y[s:s+K] = x[s:s+K][perm]
        # tail untouched
        if nb * K < L:
            y[nb*K:] = x[nb*K:]
        return y
