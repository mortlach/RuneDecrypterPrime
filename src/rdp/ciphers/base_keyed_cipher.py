# ============================================================
# rdp/ciphers/base_keyed_cipher.py
# Small base for keyed ciphers with KeyOps + pipeline alignment.
# ============================================================

from __future__ import annotations
from typing import Any
import numpy as np
from rdp.backends.xp import to_numpy

from rdp.core.types import KeyOpsFamily, ensure_keyops_family

ArrayU8 = np.ndarray


class KeyedCipherBase:
    """
    Minimal base for keyed ciphers to keep them uniform:

    Contract:
      - Cipher declares:
          keyops_family : KeyOpsFamily so the Problem can build KeyOps
          key_length    : int (or property/callable) — fixed K for this instance
      - Cipher implements:
          _core_decrypt_batch(ct_tr: [L] u8, keys_tr: [B,K] u8) -> [B,L] u8
          (optionally) _core_encrypt_batch(pt_tr: [L] u8, keys_tr: [B,K] u8) -> [B,L] u8

    Notes:
      - Decrypt hot path assumes keys are already valid/normalized and shaped; KeyOps handles repair.
      - Use dtype uint8 for indices; arithmetic may upcast temporarily but returns uint8.
    """

    # To be set by subclasses
    keyops_family: KeyOpsFamily = KeyOpsFamily.PERMUTATION
    key_length: int | None = None
    @property
    def keyops_family_enum(self) -> KeyOpsFamily:
        """Return the canonical KeyOpsFamily for this cipher."""
        return ensure_keyops_family(self.keyops_family)


    @staticmethod
    def _as_u8(a: Any) -> ArrayU8:
        """Coerce to contiguous uint8 array (preserve shape)."""
        return np.asarray(to_numpy(a), dtype=np.uint8, order="C")

    @staticmethod
    def _as_u8_1d(a: Any) -> ArrayU8:
        """Coerce to 1-D contiguous uint8 array."""
        x = np.asarray(to_numpy(a), dtype=np.uint8, order="C")
        return x.reshape(-1)
