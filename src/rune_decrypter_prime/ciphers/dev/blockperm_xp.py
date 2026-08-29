from __future__ import annotations
import numpy as np
from rune_decrypter_prime.backends.xp import select_backend

A = 29


class BlockPermutationXP:
    """
    keys_u8: shape [B, 2K] flattened [perm|shifts].
    Decrypt per key:
      1) pad ct to multiple of K
      2) undo shifts column-wise
      3) undo permutation via invperm
    """

    def __init__(self, device: str | None = None):
        dev = (device or "np").lower()
        if dev == "cuda":
            dev = "torch"
        self.dev, self.xp = select_backend(dev)

    def decrypt_batch(self, ct_u8, keys_u8):
        xp = self.xp
        ct0 = xp.asarray(ct_u8, dtype=xp.uint8)  # [N]
        keys = np.asarray(keys_u8, dtype=np.uint8)  # small admin on CPU
        B = int(keys.shape[0])
        N = int(ct0.shape[0])
        outs = []
        for b in range(B):
            key = keys[b]
            K = key.size // 2
            perm = key[:K].astype(np.int64)
            shifts = key[K:].astype(np.int64)
            # pad
            pad = (-N) % K
            if pad:
                ct = xp.empty(N + pad, dtype=xp.uint8)
                ct[:N] = ct0
                ct[N:] = xp.zeros(pad, dtype=xp.uint8)
            else:
                ct = ct0
            M = int(ct.shape[0]) // K
            blocks = ct.reshape(M, K)
            # undo shifts
            tmp = xp.mod(
                xp.astype(blocks, xp.int16) - xp.asarray(shifts, dtype=xp.int16), A
            )
            # undo permutation
            inv = np.argsort(perm).astype(np.int64)
            tmp = tmp[:, inv]
            out = tmp.reshape(-1)[:N].astype(xp.uint8)
            outs.append(out[None, :])
        return xp.astype(xp.concatenate(outs, axis=0), xp.uint8)
