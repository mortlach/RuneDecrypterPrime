# ============================================================
# rune_decrypter_prime/utils/interrupter.py
# Strip/reinsert interruptors (by position only) for numeric pipelines.
# Behaviour preserved; numpy-only and side-effect free.
# ============================================================

from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Tuple
import numpy as np

__all__ = ["InterruptorInfo", "InterruptorManager"]


@dataclass(slots=True)
class InterruptorInfo:
    """Holds (index → symbol) pairs stripped from ciphertext."""

    idx: (
        np.ndarray
    )  # int64, ascending, unique (position in core array after prior removals)
    sym: np.ndarray  # same dtype as ciphertext (uint8 for our numeric pipeline)


class InterruptorManager:
    """Strip/reinsert interruptors by **position only** (never by symbol)."""

    def __init__(self) -> None:
        # uint8 default for our numeric pipeline; idx empty int64
        self._EMPTY_INFO = InterruptorInfo(
            idx=np.empty(0, dtype=np.int64),
            sym=np.empty(0, dtype=np.uint8),
        )

    def empty_info(self) -> InterruptorInfo:
        return self._EMPTY_INFO

    def remove_from(
        self,
        arr: np.ndarray,
        *,
        possible_idx: Iterable[int] | None = None,
    ) -> Tuple[np.ndarray, InterruptorInfo]:
        """
        Drop arr[idx] for provided indices and return (remaining, info).

        Notes
        -----
        - If `possible_idx` is None or empty, this is a no-op.
        - The returned `info.idx` is adjusted to the *core* index:
          the k-th removed element ends up at (original_idx - k).
        """
        if possible_idx is None:
            return arr, self._EMPTY_INFO

        idx = np.fromiter(possible_idx, dtype=np.int64)
        if idx.size == 0:
            return arr, self._EMPTY_INFO

        # Sanitize indices
        idx = np.unique(idx)
        if idx[-1] >= arr.size or idx[0] < 0:
            raise IndexError("interrupt indices out of bounds")

        sym = arr[idx].astype(arr.dtype, copy=True)
        keep = np.ones(arr.size, dtype=bool)
        keep[idx] = False
        out = arr[keep]

        # After each deletion, everything to the right shifts left by 1.
        idx_core = idx - np.arange(idx.size, dtype=idx.dtype)
        return out, InterruptorInfo(idx=idx_core, sym=sym)

    def insert_into(self, arr: np.ndarray, info: InterruptorInfo) -> np.ndarray:
        """Reinsert previously removed symbols at their core indices."""
        if info.idx.size == 0:
            return arr
        # `np.insert` returns a new array (OK); dtype stays numeric because info.sym is uint8
        return np.insert(arr, info.idx, info.sym)
