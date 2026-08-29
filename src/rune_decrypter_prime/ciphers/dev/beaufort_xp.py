from __future__ import annotations
from rune_decrypter_prime.backends.xp import select_backend

A = 29


class BeaufortCipherXP:
    """
    Classic Beaufort: enc = key[i]-pt mod A  =>  dec = key[i]-ct mod A
    keys_u8: [B,K]; ct: [N]; output: [B,N]
    """

    def __init__(self, device: str | None = None):
        dev = (device or "np").lower()
        if dev == "cuda":
            dev = "torch"
        self.dev, self.xp = select_backend(dev)

    def decrypt_batch(self, ct_u8, keys_u8):
        xp = self.xp
        ct = xp.asarray(ct_u8, dtype=xp.uint8)  # [N]
        keys = xp.asarray(keys_u8, dtype=xp.uint8)  # [B,K]
        B, K = int(keys.shape[0]), int(keys.shape[1])
        N = int(ct.shape[0])
        cols = xp.mod(xp.arange(N, dtype=xp.int64), K)
        ks = keys[:, cols]  # [B,N]
        pt = xp.mod(xp.astype(ks, xp.int16) - xp.astype(ct, xp.int16)[None, :], A)
        return xp.astype(pt, xp.uint8)
