# ============================================================
# rune_decrypter_prime/ciphers/railfence_cipher.py
# ============================================================
from __future__ import annotations

import numpy as np

from rune_decrypter_prime.ciphers.base_keyed_cipher import (
    ArrayU8,
    KeyedCipherBase,
)
from rune_decrypter_prime.ciphers.cipher_runtime_registry import register_cipher
from rune_decrypter_prime.core.types import KeyOpsFamily


@register_cipher("rail_fence")
class RailFenceCipher(KeyedCipherBase):
    """
    Railfence (zig-zag) transposition cipher.

    Key model
    ---------
    - Vector (length 1) representing the number of rails.
    - Values are interpreted in the inclusive range [min_rails, max_rails].
    - When `rails_fixed` is provided by the config the range collapses to that
      constant and the optimiser effectively sees a single-valued key space.

    Implementation notes
    --------------------
    - The cipher never mutates global state; all helpers are pure numpy ops.
    - Batch decrypt/encrypt accept keys shaped [B, 1] (or [1]) and always
      return uint8 outputs (shape [B, L] or [L]).
    - KeyOps hints advertise the modulus so `KeyOpsFamily.VECTOR` can normalise
      candidate keys into the legal rail interval.
    """

    keyops_family: KeyOpsFamily = KeyOpsFamily.VECTOR
    key_length: int = 1

    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self.A = int(getattr(cfg, "alphabet_size", 29) or 29)

        min_rails = getattr(cfg, "min_rails", None)
        max_rails = getattr(cfg, "max_rails", None)
        rails_fixed = getattr(cfg, "rails_fixed", getattr(cfg, "rails", None))

        self._min_rails = max(2, int(min_rails) if min_rails is not None else 2)
        max_hint = int(max_rails) if max_rails is not None else max(self._min_rails, 8)
        self._max_rails = max(self._min_rails, max_hint)

        if rails_fixed is not None:
            fixed = int(rails_fixed)
            if fixed < 2:
                raise ValueError("railfence: rails must be >= 2")
            if not (self._min_rails <= fixed <= self._max_rails):
                raise ValueError(
                    f"railfence: rails={fixed} outside [{self._min_rails}, {self._max_rails}]"
                )
            self._fixed_rails = fixed
            self._min_rails = fixed
            self._max_rails = fixed
        else:
            self._fixed_rails = None

        self._key_mod = self._max_rails - self._min_rails + 1
        self.keyops_hints = {"mod": self._key_mod}

    # ------------------------------------------------------------------ utils
    def _keys_to_rails(self, keys: ArrayU8) -> np.ndarray:
        if keys.ndim == 1:
            keys = keys.reshape(1, -1)
        if keys.shape[1] != 1:
            raise ValueError(f"railfence expects key length 1, got {keys.shape[1]}")

        if self._fixed_rails is not None:
            return np.full(keys.shape[0], self._fixed_rails, dtype=np.int64)

        raw = keys[:, 0].astype(np.int64, copy=False)
        rails = self._min_rails + (raw % self._key_mod)
        # Guard against stray values from legacy callers
        np.clip(rails, self._min_rails, self._max_rails, out=rails)
        return rails

    @staticmethod
    def _zigzag_order(L: int, rails: int) -> np.ndarray:
        if rails <= 1 or rails >= L:
            return np.arange(L, dtype=np.int64)

        lines = [[] for _ in range(rails)]
        rail = 0
        step = 1
        for idx in range(L):
            lines[rail].append(idx)
            rail += step
            if rail == 0 or rail == rails - 1:
                step *= -1

        return np.array([pos for line in lines for pos in line], dtype=np.int64)

    @classmethod
    def _decrypt_single(cls, ct: ArrayU8, rails: int) -> ArrayU8:
        ct = np.asarray(ct, dtype=np.uint8).reshape(-1)
        L = int(ct.size)
        order = cls._zigzag_order(L, rails)
        pt = np.empty_like(ct)
        pt[order] = ct
        return pt

    @classmethod
    def _encrypt_single(cls, pt: ArrayU8, rails: int) -> ArrayU8:
        pt = np.asarray(pt, dtype=np.uint8).reshape(-1)
        order = cls._zigzag_order(int(pt.size), rails)
        return pt[order]

    # ---------------------------------------------------------------- decrypt
    def decrypt(self, *, ciphertext: ArrayU8, key: ArrayU8, **_) -> ArrayU8:
        ct = self._as_u8(ciphertext).reshape(-1)
        k = self._as_u8(key)
        if k.ndim == 1:
            rails = self._keys_to_rails(k)[0]
            return self._decrypt_single(ct, int(rails))

        rails = self._keys_to_rails(k)
        out = np.empty((rails.size, ct.size), dtype=np.uint8)
        for idx, r in enumerate(rails):
            out[idx] = self._decrypt_single(ct, int(r))
        return out

    # ---------------------------------------------------------------- encrypt
    def encrypt(self, *, plaintext: ArrayU8, key: ArrayU8, **_) -> ArrayU8:
        pt = self._as_u8(plaintext).reshape(-1)
        k = self._as_u8(key)
        if k.ndim == 1:
            rails = self._keys_to_rails(k)[0]
            return self._encrypt_single(pt, int(rails))

        rails = self._keys_to_rails(k)
        out = np.empty((rails.size, pt.size), dtype=np.uint8)
        for idx, r in enumerate(rails):
            out[idx] = self._encrypt_single(pt, int(r))
        return out

