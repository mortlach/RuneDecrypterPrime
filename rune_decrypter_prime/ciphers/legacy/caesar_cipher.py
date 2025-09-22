# rune_decrypter_prime/ciphers/caesar_cipher.py
from __future__ import annotations
import numpy as np

from rune_decrypter_prime.optimizers.types import ArrayU8
from rune_decrypter_prime.core.keyops import RepeatKeyOps
from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin

A = 29

class CaesarCipher(CipherPipelineMixin):
    """
    Caesar is Vigenère with key length = 1.
    keyops: single symbol (0..28) searched as RepeatKeyOps(K=1, A=29).
    """

    def __init__(self, cfg, *, text_transposition="fwd", key_transposition="fwd"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", "fwd"),
            key_transposition=getattr(cfg, "key_transposition", "fwd"),
        )
        self.cfg = cfg
        self.keyops = RepeatKeyOps(K=1, A=A)

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        ct = np.asarray(ct_tr, dtype=np.uint8).reshape(-1)
        keys = np.asarray(keys_tr, dtype=np.uint8)
        if keys.ndim == 1:
            keys = keys[None, :]
        B = keys.shape[0]
        L = ct.size

        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            k = int(keys[b, 0])
            out[b] = (ct.astype(np.int16) - k) % A
        return out
