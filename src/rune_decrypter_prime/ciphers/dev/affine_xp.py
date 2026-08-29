from __future__ import annotations
import numpy as np
from rune_decrypter_prime.backends.xp import select_backend

A = 29

# Precompute inverses in Z_29
_inv = {a: pow(a, -1, A) for a in range(1, A)}  # pow(a,-1,p) works for prime p


class AffineCipherXP:
    """
    keys_u8: shape [B,2] where keys[:,0]=a, keys[:,1]=b  (scalars per key)
    decrypt: pt = a^{-1} * (ct - b) mod 29
    """

    def __init__(self, device: str | None = None):
        dev = (device or "np").lower()
        if dev == "cuda":
            dev = "torch"
        self.dev, self.xp = select_backend(dev)

    def decrypt_batch(self, ct_u8, keys_u8):
        xp = self.xp
        ct = xp.asarray(ct_u8, dtype=xp.uint8)  # [N]
        keys = np.asarray(keys_u8, dtype=np.uint8)  # small admin on CPU
        a = keys[:, 0].astype(np.int64)
        b = keys[:, 1].astype(np.int64)
        ainv = np.vectorize(lambda x: _inv[int(x)])(a).astype(np.int64)  # [B]

        B = int(keys.shape[0])
        N = int(ct.shape[0])
        ct_i = xp.astype(ct, xp.int16)[None, :]  # [1,N]
        b_i = xp.asarray(b[:, None], dtype=xp.int16)  # [B,1]
        ainv_i = xp.asarray(ainv[:, None], dtype=xp.int16)  # [B,1]
        tmp = xp.mod(ct_i - b_i, A)  # [B,N]
        pt = xp.mod(ainv_i * tmp, A)  # [B,N]
        return xp.astype(pt, xp.uint8)
