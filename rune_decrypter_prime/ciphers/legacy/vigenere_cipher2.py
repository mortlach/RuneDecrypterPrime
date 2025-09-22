# rune_decrypter_prime/ciphers/vigenere_cipher.py
from __future__ import annotations
import numpy as np

from rune_decrypter_prime.optimizers.types import ArrayU8  # if you have it; else: from .pipeline import ArrayU8
from rune_decrypter_prime.core.keyops import RepeatKeyOps
from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin

A = 29  # Gematria Primus

def _mod_add(pt: np.ndarray, key: np.ndarray) -> np.ndarray:
    # (pt + key) % 29, both u8; cast up to avoid wrap during add
    return (pt.astype(np.uint16) + key.astype(np.uint16)) % A

def _mod_sub(ct: np.ndarray, key: np.ndarray) -> np.ndarray:
    return (ct.astype(np.int16) - key.astype(np.int16)) % A

class VigenereCipher(CipherPipelineMixin):
    """
    Additive mod-29 Vigenère with repeating key of length K.
    - keyops: RepeatKeyOps(K, A=29)  -> GA/SA can mutate integer key symbols 0..28
    """

    def __init__(self, cfg, *, text_transposition="fwd", key_transposition="fwd"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", "fwd"),
            key_transposition=getattr(cfg, "key_transposition", "fwd"),
        )
        self.cfg = cfg

        K = int(getattr(cfg, "key_length", 0) or 0)
        if K <= 0:
            raise ValueError("Vigenere requires positive key_length.")
        self.keyops = RepeatKeyOps(K=K, A=A)

    # ---- Decrypt many keys against a single ciphertext (optimizer hot path)
    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """
        ct_tr:  shape (L,)
        keys_tr: shape (B, K) or (K,)
        returns: shape (B, L)
        """
        ct = np.asarray(ct_tr, dtype=np.uint8).reshape(-1)
        L = ct.size

        keys = np.asarray(keys_tr, dtype=np.uint8)
        if keys.ndim == 1:
            keys = keys[None, :]
        B, K = keys.shape

        # tile key per row to length L
        reps = (L + K - 1) // K
        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            k = np.tile(keys[b], reps)[:L]
            out[b] = _mod_sub(ct, k)
        return out

    # ---- Optional encrypt (useful for tutorials/tests)
    def encrypt(self, *, plaintext: ArrayU8, key: ArrayU8) -> ArrayU8:
        pt = np.asarray(plaintext, dtype=np.uint8).reshape(-1)
        key = np.asarray(key, dtype=np.uint8).reshape(-1)
        L, K = pt.size, key.size
        if K <= 0:
            raise ValueError("encrypt: key length must be > 0")
        k = np.tile(key, (L + K - 1) // K)[:L]
        return _mod_add(pt, k).astype(np.uint8)

    def decrypt(self, *, ciphertext: ArrayU8, key: ArrayU8) -> ArrayU8:
        # single-key convenience (used by preview or tests)
        ct = np.asarray(ciphertext, dtype=np.uint8).reshape(-1)
        key = np.asarray(key, dtype=np.uint8).reshape(-1)
        L, K = ct.size, key.size
        if K <= 0:
            raise ValueError("decrypt: key length must be > 0")
        k = np.tile(key, (L + K - 1) // K)[:L]
        return _mod_sub(ct, k).astype(np.uint8)
