# ============================================================
# rune_decrypter_prime/utils/transposition.py
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
        self._text_perm = None if text_perm is None else np.asarray(text_perm, dtype=np.int64)
        self._key_perm  = None if key_perm  is None else np.asarray(key_perm,  dtype=np.int64)

    # -------- text --------
    def apply_text(self, arr: np.ndarray) -> np.ndarray:
        if self.text_mode == "ltr":
            return arr
        if self.text_mode == "rtl":
            return arr[::-1].copy()
        if self.text_mode == "perm":
            if self._text_perm is None or self._text_perm.size != arr.size:
                raise ValueError("text_perm must match text length")
            return arr[self._text_perm]
        raise ValueError(f"unknown text_mode {self.text_mode}")

    def undo_text(self, arr: np.ndarray) -> np.ndarray:
        if self.text_mode == "ltr":
            return arr
        if self.text_mode == "rtl":
            return arr[::-1].copy()
        if self.text_mode == "perm":
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
            if self._key_perm is None or self._key_perm.size != keys.shape[1]:
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
            inv = np.empty_like(self._key_perm)
            inv[self._key_perm] = np.arange(self._key_perm.size)
            return keys[:, inv]
        raise ValueError(f"unknown key_mode {self.key_mode}")

# TODO: Consider normalising `text_mode`/`key_mode` with a shared helper
#       (accept "reverse"/"rtl"/"back"/"bwd" etc.) without changing defaults.
