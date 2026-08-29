from __future__ import annotations
import numpy as np
from rune_decrypter_prime.backends.xp import select_backend

A = 29

class SubstitutionCipherXP:
    """
    keys_u8: shape [B,A] where each row is a permutation mapping PT->CT.
    Decrypt by inverting each row (CT->PT), then gather.
    """
    def __init__(self, device: str | None = None):
        dev = (device or "np").lower()
        if dev == "cuda": dev = "torch"
        self.dev, self.xp = select_backend(dev)

    def decrypt_batch(self, ct_u8, keys_u8):
        xp = self.xp
        ct = xp.asarray(ct_u8, dtype=xp.uint8)           # [N]
        keys = np.asarray(keys_u8, dtype=np.uint8)       # [B,A] small admin on CPU
        B = keys.shape[0]
        # invert permutations on CPU
        inv = np.empty_like(keys)
        for i in range(B):
            inv[i, keys[i]] = np.arange(A, dtype=np.uint8)
        # push to XP and gather
        inv_x = xp.asarray(inv, dtype=xp.uint8)          # [B,A]
        pt = inv_x[:, ct]                                # broadcasting take -> [B,N]
        return pt
