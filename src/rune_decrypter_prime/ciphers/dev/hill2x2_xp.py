from __future__ import annotations
import numpy as np
from rdp.backends.xp import select_backend

A = 29

def _inv_mod(x: int, m: int = A) -> int:
    return pow(int(x), -1, m)

def _invert_2x2_mod29(M: np.ndarray) -> np.ndarray:
    a,b,c,d = map(int, M.ravel())
    det = (a*d - b*c) % A
    invdet = _inv_mod(det, A)
    Mi = np.array([[d, -b], [-c, a]], dtype=np.int64) % A
    Mi = (Mi * invdet) % A
    return Mi.astype(np.uint8)

class Hill2x2CipherXP:
    """
    keys_u8: shape [B,4] representing 2x2 matrices row-major.
    Decrypt in blocks of 2: pt_vec = inv(M) @ ct_vec (mod 29).
    Pads odd length with zero then truncates.
    """
    def __init__(self, device: str | None = None):
        dev = (device or "np").lower()
        if dev == "cuda": dev = "torch"
        self.dev, self.xp = select_backend(dev)

    def decrypt_batch(self, ct_u8, keys_u8):
        xp = self.xp
        ct0 = xp.asarray(ct_u8, dtype=xp.uint8)    # [N]
        keys = np.asarray(keys_u8, dtype=np.uint8) # CPU small admin
        B = keys.shape[0]; N = int(ct0.shape[0])
        pad = N % 2
        if pad:
            ct = xp.empty(N+1, dtype=xp.uint8); ct[:N]=ct0; ct[N]=xp.asarray(0, dtype=xp.uint8)
        else:
            ct = ct0
        M = int(ct.shape[0]//2)
        ct_pairs = ct.reshape(M, 2).astype(xp.int16)  # [M,2]

        outs = []
        for b in range(B):
            K = keys[b].reshape(2,2)
            Mi = _invert_2x2_mod29(K)   # CPU tiny admin
            Mi_x = xp.asarray(Mi.astype(np.int16))   # [2,2]
            pt = (ct_pairs @ Mi_x.T) % A   # [M,2]
            out = pt.reshape(-1)[:N].astype(xp.uint8)
            outs.append(out[None,:])
        return xp.astype(xp.concatenate(outs, axis=0), xp.uint8)
