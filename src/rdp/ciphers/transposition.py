# ============================================================
# rdp/ciphers/transposition.py
# Text/key transposition utilities: identity, reverse, or explicit perm.
# Behaviour unchanged; defensive checks and copies where relevant.
# ============================================================

from __future__ import annotations
from typing import Optional
import numpy as np

__all__ = ["TranspositionManager"]

class TranspositionManager:
    """
    Text and key transpositions.

    Modes
    -----
    - "ltr" : identity
    - "rtl" : reverse
    - "perm": use explicit permutation arrays supplied via ctor (text_perm/key_perm)
    """

    def __init__(
        self,
        text_mode: str = "ltr",
        key_mode: str = "ltr",
        *,
        text_perm: Optional[np.ndarray] = None,
        key_perm: Optional[np.ndarray] = None,
    ) -> None:
        self.text_mode = text_mode
        self.key_mode = key_mode
        if text_perm is None:
            self._text_perm = None
        else:
            perm = np.asarray(text_perm, dtype=np.int64)
            self._validate_perm(perm, "text_perm")
            self._text_perm = perm

        if key_perm is None:
            self._key_perm = None
        else:
            perm = np.asarray(key_perm, dtype=np.int64)
            self._validate_perm(perm, "key_perm")
            self._key_perm = perm

    @staticmethod
    def _validate_perm(perm: np.ndarray, name: str) -> None:
        if perm.ndim != 1:
            raise ValueError(f"{name} must be 1-D")
        n = int(perm.size)
        if n == 0:
            return
        if (perm < 0).any() or (perm >= n).any():
            raise ValueError(f"{name} must be a permutation of 0..n-1")
        if np.unique(perm).size != n:
            raise ValueError(f"{name} must be a permutation of 0..n-1")

    # -------- text --------
    def apply_text(self, arr: np.ndarray) -> np.ndarray:
        if self.text_mode == "ltr":
            return arr
        if self.text_mode == "rtl":
            return arr[::-1].copy()
        if self.text_mode == "perm":
            if self._text_perm is None:
                raise ValueError("text_perm is required for perm text_mode")
            if self._text_perm.size != arr.size:
                raise ValueError("text_perm must match text length")
            return arr[self._text_perm]
        raise ValueError(f"unknown text_mode {self.text_mode}")

    def undo_text(self, arr: np.ndarray) -> np.ndarray:
        if self.text_mode == "ltr":
            return arr
        if self.text_mode == "rtl":
            return arr[::-1].copy()
        if self.text_mode == "perm":
            if self._text_perm is None:
                raise ValueError("text_perm is required for perm text_mode")
            inv = np.empty_like(self._text_perm)
            inv[self._text_perm] = np.arange(self._text_perm.size)
            return arr[inv]
        raise ValueError(f"unknown text_mode {self.text_mode}")

    # -------- key --------
    def apply_key(self, keys: np.ndarray) -> np.ndarray:
        """Apply the configured key transposition over a [B, K] key array."""
        if self.key_mode == "ltr":
            return keys  # must be a true no-op
        if self.key_mode == "rtl":
            return keys[:, ::-1].copy()
        if self.key_mode == "perm":
            if self._key_perm is None:
                raise ValueError("key_perm is required for perm key_mode")
            if self._key_perm.size != keys.shape[1]:
                raise ValueError("key_perm must match key length")
            return keys[:, self._key_perm]
        raise ValueError(f"unknown key_mode {self.key_mode}")

    def undo_key(self, keys: np.ndarray) -> np.ndarray:
        """Undo the configured key transposition over a [B, K] key array."""
        if self.key_mode == "ltr":
            return keys
        if self.key_mode == "rtl":
            return keys[:, ::-1].copy()
        if self.key_mode == "perm":
            if self._key_perm is None:
                raise ValueError("key_perm is required for perm key_mode")
            inv = np.empty_like(self._key_perm)
            inv[self._key_perm] = np.arange(self._key_perm.size)
            return keys[:, inv]
        raise ValueError(f"unknown key_mode {self.key_mode}")

# TODO: Consider normalising `text_mode`/`key_mode` with a shared helper
#       (accept "reverse"/"rtl"/"back"/"bwd" etc.) without changing defaults.
