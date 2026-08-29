"""Helpers for Hill cipher tests."""

from __future__ import annotations
import numpy as np


def hill_encrypt(pt_idx: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    arr = np.asarray(pt_idx, dtype=np.uint8)
    if arr.size % 2 == 1:
        arr = np.concatenate([arr, np.zeros(1, dtype=np.uint8)], axis=0)
    pairs = arr.reshape(-1, 2).astype(np.int64)
    out = pairs @ np.asarray(matrix, dtype=np.int64).T % 29
    return out.reshape(-1).astype(np.uint8)[: pt_idx.size]
