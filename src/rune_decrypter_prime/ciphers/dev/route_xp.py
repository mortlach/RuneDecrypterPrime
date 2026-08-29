from __future__ import annotations
import numpy as np
from rune_decrypter_prime.backends.xp import select_backend

A = 29


def _route_decrypt_indices(n: int, cols: int, mode: str = "row-major") -> np.ndarray:
    rows = (n + cols - 1) // cols
    pad = rows * cols - n
    grid_idx = np.arange(rows * cols, dtype=np.int64).reshape(rows, cols)
    if mode == "col-major":
        ct_order = grid_idx.T.ravel()
    else:
        ct_order = grid_idx.ravel()
    ct_order = ct_order[ct_order < n]
    inv = np.empty(n, dtype=np.int64)
    for rank, pos in enumerate(ct_order):
        inv[pos] = rank
    return inv


class RouteTranspositionXP:
    """
    keys_u8: shape [B,2] like [cols, mode_id] with mode_id: 0=row-major,1=col-major (example)
    Decrypt by building index map on CPU, then XP gather. Adapt mode mapping as needed.
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
        cols = int(keys[0, 0])
        mode = "col-major" if int(keys[0, 1]) == 1 else "row-major"
        idx = _route_decrypt_indices(N, cols, mode=mode)
        idx_x = xp.asarray(idx, dtype=xp.int64)
        pt1 = ct[idx_x]
        return pt1[None, :].repeat(keys.shape[0], 0)
