# rune_decrypter_prime/ciphers/simple_substitution_cipher.py
from __future__ import annotations
import numpy as np

from rune_decrypter_prime.optimizers.types import ArrayU8
from rune_decrypter_prime.keyops.permutation_ops import PermutationOps
from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin

A = 29

class SimpleSubstitutionCipher(CipherPipelineMixin):
    """
    Monoalphabetic substitution over 29 symbols.
    Key = permutation π of [0..28] that maps plaintext symbol -> ciphertext symbol.
    Decrypt uses inverse permutation.
    keyops: PermutationOps(29)
    """

    def __init__(self, cfg, *, text_transposition="fwd", key_transposition="fwd"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", "fwd"),
            key_transposition=getattr(cfg, "key_transposition", "fwd"),
        )
        self.cfg = cfg
        self.keyops = PermutationOps(A)  # length 29 permutation

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """
        keys_tr: (B, 29) where keys_tr[b, x] = ciphertext symbol for plaintext x (i.e., forward perm).
        For decryption we need inverse: inv[ct] = pt.
        """
        ct = np.asarray(ct_tr, dtype=np.uint8).reshape(-1)
        keys = np.asarray(keys_tr, dtype=np.uint8)
        if keys.ndim == 1:
            keys = keys[None, :]
        B = keys.shape[0]
        L = ct.size

        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            forward = keys[b]
            inv = np.empty_like(forward)
            inv[forward] = np.arange(A, dtype=np.uint8)  # invert permutation
            out[b] = inv[ct]
        return out

    # Optional helpers for tutorials
    def encrypt(self, *, plaintext: ArrayU8, key: ArrayU8) -> ArrayU8:
        pt = np.asarray(plaintext, dtype=np.uint8).reshape(-1)
        fwd = np.asarray(key, dtype=np.uint8).reshape(-1)
        if fwd.size != A:
            raise ValueError("SimpleSubstitutionCipher.encrypt: key must be length 29 permutation.")
        return fwd[pt]

    def decrypt(self, *, ciphertext: ArrayU8, key: ArrayU8) -> ArrayU8:
        ct = np.asarray(ciphertext, dtype=np.uint8).reshape(-1)
        fwd = np.asarray(key, dtype=np.uint8).reshape(-1)
        inv = np.empty_like(fwd)
        inv[fwd] = np.arange(A, dtype=np.uint8)
        return inv[ct]
