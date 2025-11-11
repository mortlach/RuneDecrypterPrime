# ============================================================
# rune_decrypter_prime/ciphers/base_keyed_cipher.py
# Small base for keyed ciphers with KeyOps + pipeline alignment.
# ============================================================

from __future__ import annotations
from typing import Any
import numpy as np

ArrayU8 = np.ndarray


class KeyedCipherBase:
    """
    Minimal base for keyed ciphers to keep them uniform:

    Contract:
      - Cipher declares:
          keyops_family : {"perm","vector",...} so the Problem can build KeyOps
          key_length    : int (or property/callable) — fixed K for this instance
      - Cipher implements:
          _core_decrypt_batch(ct_tr: [L] u8, keys_tr: [B,K] u8) -> [B,L] u8
          (optionally) _core_encrypt_batch(pt_tr: [L] u8, keys_tr: [B,K] u8) -> [B,L] u8

    Notes:
      - Decrypt hot path assumes keys are already valid/normalized and shaped; KeyOps handles repair.
      - Use dtype uint8 for indices; arithmetic may upcast temporarily but returns uint8.
    """

    # To be set by subclasses
    keyops_family: str = "perm"
    key_length: int | None = None

    @staticmethod
    def _as_u8(a: Any) -> ArrayU8:
        """Coerce to contiguous uint8 array (preserve shape)."""
        return np.asarray(a, dtype=np.uint8, order="C")

    @staticmethod
    def _as_u8_1d(a: Any) -> ArrayU8:
        """Coerce to 1-D contiguous uint8 array."""
        x = np.asarray(a, dtype=np.uint8, order="C")
        return x.reshape(-1)
