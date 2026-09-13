# ============================================================
# rdp/ciphers/autokey_cipher.py
# ============================================================
from __future__ import annotations

import numpy as np

from rdp.ciphers.ciphers_pipeline import CipherPipelineMixin, ArrayU8
from rdp.ciphers.base_keyed_cipher import KeyedCipherBase
from rdp.core.types import Direction, KeyOpsFamily, ensure_direction


class AutokeyCipher(CipherPipelineMixin, KeyedCipherBase):
    """
    Additive Autokey cipher over the 29-rune alphabet.

    Key model
    ---------
    Seed vector of length `seed_length`. The keystream is:
        key[i] = seed[i]                          for i < seed_length
        key[i] = plaintext[i - seed_length]       otherwise

    We only search over the seed; the rest of the keystream is derived on the fly.
    """

    keyops_family: KeyOpsFamily = KeyOpsFamily.VECTOR

    def __init__(
        self,
        cfg,
        *,
        text_transposition: Direction | str = Direction.LTR,
        key_transposition: Direction | str = Direction.LTR,
    ) -> None:
        text_dir = ensure_direction(getattr(cfg, "text_transposition", text_transposition))
        key_dir = ensure_direction(getattr(cfg, "key_transposition", key_transposition))
        super().__init__(
            text_transposition=text_dir.value,
            key_transposition=key_dir.value,
            initial_text_permutation_indices=getattr(cfg, "initial_text_permutation_indices", None),
        )
        self.cfg = cfg
        self.text_direction = text_dir
        self.key_direction = key_dir

        seed_len = getattr(cfg, "seed_length", None)
        if seed_len is None:
            seed_len = getattr(cfg, "key_length", None)
        if seed_len is None:
            extra = getattr(cfg, "extra", {}) or {}
            seed_len = extra.get("seed_length")
        if seed_len is None:
            raise ValueError("Autokey cipher requires a positive seed_length / key_length")
        seed_len = int(seed_len)
        if seed_len <= 0:
            raise ValueError("Autokey cipher seed_length must be >= 1")
        self.seed_length = seed_len
        self.key_length = seed_len

        self.alphabet_size = int(getattr(cfg, "alphabet_size", getattr(cfg, "A", 29)) or 29)
        self.keyops_hints = {"mod": self.alphabet_size}

    # ------------------------------------------------------------------ helpers
    def _require_seed(self, seed: np.ndarray) -> np.ndarray:
        if seed.size != self.seed_length:
            raise ValueError(
                f"Autokey seed must have length {self.seed_length}, got {seed.size}"
            )
        return seed.astype(np.uint8, copy=False)

    def _encrypt_single(self, pt: np.ndarray, seed: np.ndarray) -> np.ndarray:
        seed_u8 = self._require_seed(seed)
        L = int(pt.size)
        out = np.empty(L, dtype=np.uint8)
        for idx in range(L):
            if idx < self.seed_length:
                key_val = int(seed_u8[idx])
            else:
                key_val = int(pt[idx - self.seed_length])
            out[idx] = np.uint8((int(pt[idx]) + key_val) % self.alphabet_size)
        return out

    def _decrypt_single(self, ct: np.ndarray, seed: np.ndarray) -> np.ndarray:
        seed_u8 = self._require_seed(seed)
        L = int(ct.size)
        out = np.empty(L, dtype=np.uint8)
        for idx in range(L):
            if idx < self.seed_length:
                key_val = int(seed_u8[idx])
            else:
                key_val = int(out[idx - self.seed_length])
            out[idx] = np.uint8((int(ct[idx]) - key_val) % self.alphabet_size)
        return out

    # ------------------------------------------------------------------ decrypt
    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        ct = self._as_u8(ct_tr, "ct")
        if ct.ndim == 1:
            ct_rows = ct[None, :]
        else:
            ct_rows = ct
        B_text, L = ct_rows.shape

        keys = self._as_u8(keys_tr, "keys")
        if keys.ndim == 1:
            keys = keys[None, :]
        B_keys = int(keys.shape[0])

        out = np.empty((B_keys, L), dtype=np.uint8)
        for b in range(B_keys):
            ct_row = ct_rows[b % B_text]
            seed = keys[b]
            out[b] = self._decrypt_single(ct_row, seed)
        return out

    # ------------------------------------------------------------------ encrypt
    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        pt = self._as_u8(pt_tr, "pt")
        if pt.ndim == 1:
            pt_rows = pt[None, :]
        else:
            pt_rows = pt
        B_text, L = pt_rows.shape

        keys = self._as_u8(keys_tr, "keys")
        if keys.ndim == 1:
            keys = keys[None, :]
        B_keys = int(keys.shape[0])

        out = np.empty((max(B_text, B_keys), L), dtype=np.uint8)
        for b in range(out.shape[0]):
            pt_row = pt_rows[b % B_text]
            seed = keys[b % B_keys]
            out[b] = self._encrypt_single(pt_row, seed)
        return out
