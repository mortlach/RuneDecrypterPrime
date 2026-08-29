from __future__ import annotations
import numpy as np
from rune_decrypter_prime.backends.xp import select_backend

A = 29


def _columnar_decrypt_indices(n: int, perm: np.ndarray) -> np.ndarray:
    K = int(perm.size)
    rows = (n + K - 1) // K
    lens = np.full(K, rows, dtype=np.int64)
    extra = rows * K - n
    if extra > 0:
        for c in range(K - 1, K - 1 - extra, -1):
            lens[c] -= 1
    starts = np.zeros(K, dtype=np.int64)
    # starts in order of perm
    for i in range(1, K):
        starts[i] = starts[i - 1] + lens[perm[i - 1]]
    pos_in_ct = np.zeros(n, dtype=np.int64)
    for i, c in enumerate(perm):
        Lc = lens[c]
        for r in range(Lc):
            pt_pos = r * K + c
            pos_in_ct[pt_pos] = starts[i] + r
    ct_idx = pos_in_ct
    return ct_idx


class ColumnarTranspositionXP:
    """
    keys_u8: shape [B,K] with permutation of 0..K-1 (read order during encryption)
    Decrypt by precomputing pt_pos -> ct_pos index map on CPU, then XP gather.
    """

    def __init__(self, device: str | None = None):
        dev = (device or "np").lower()
        if dev == "cuda":
            dev = "torch"
        self.dev, self.xp = select_backend(dev)

    def decrypt_batch(self, ct_u8, keys_u8):
        xp = self.xp
        ct = xp.asarray(ct_u8, dtype=xp.uint8)
        keys = np.asarray(keys_u8, dtype=np.uint8)
        N = int(ct.shape[0])
        idx = _columnar_decrypt_indices(N, keys[0].astype(np.int64))
        idx_x = xp.asarray(idx, dtype=xp.int64)
        pt1 = ct[idx_x]  # [N]
        return pt1[None, :].repeat(keys.shape[0], 0)
