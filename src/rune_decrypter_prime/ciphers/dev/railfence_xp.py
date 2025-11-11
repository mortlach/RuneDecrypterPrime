from __future__ import annotations
import numpy as np
from rune_decrypter_prime.backends.xp import select_backend

A = 29

def _railfence_decrypt_indices(n: int, rails: int) -> np.ndarray:
    # Build the inverse traversal mapping for decryption.
    pattern = []
    r, d = 0, 1
    for i in range(n):
        pattern.append(r)
        if r == 0: d = 1
        elif r == rails - 1: d = -1
        r += d
    pattern = np.asarray(pattern, dtype=np.int64)
    counts = np.bincount(pattern, minlength=rails)
    starts = np.zeros(rails, dtype=np.int64)
    starts[1:] = np.cumsum(counts)[:-1]
    rank = np.zeros(n, dtype=np.int64)
    seen = np.zeros(rails, dtype=np.int64)
    for i in range(n):
        rr = pattern[i]
        rank[i] = seen[rr]
        seen[rr] += 1
    ct_idx = starts[pattern] + rank
    return ct_idx

class RailFenceCipherXP:
    """
    keys_u8: shape [B,1] with rails per key (int)
    Decrypt by precomputing ct->pt index map on CPU, then XP gather per key (same map).
    """
    def __init__(self, device: str | None = None):
        dev = (device or "np").lower()
        if dev == "cuda": dev = "torch"
        self.dev, self.xp = select_backend(dev)

    def decrypt_batch(self, ct_u8, keys_u8):
        xp = self.xp
        ct = xp.asarray(ct_u8, dtype=xp.uint8)      # [N]
        keys = np.asarray(keys_u8, dtype=np.uint8)  # rails per key
        N = int(ct.shape[0])
        rails = int(keys[0,0])
        idx = _railfence_decrypt_indices(N, rails)  # CPU tiny admin
        idx_x = xp.asarray(idx, dtype=xp.int64)
        pt = ct[idx_x][None, :].repeat(keys.shape[0], 0)  # same rails across batch typical
        return pt
