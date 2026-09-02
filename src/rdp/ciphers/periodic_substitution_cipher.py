# ============================================================
# rdp/ciphers/periodic_substitution_cipher.py
# Periodic mixed-alphabet substitution (p tables of size A).
# ============================================================
from __future__ import annotations
import numpy as np

from rdp.ciphers.ciphers_pipeline import CipherPipelineMixin, ArrayU8
from rdp.ciphers.base_keyed_cipher import KeyedCipherBase
from rdp.core.types import Direction, KeyOpsFamily, ensure_direction

DEFAULT_A = 29


def _cfg_get(cfg, name: str, default=None):
    val = getattr(cfg, name, None)
    if val is not None:
        return val
    extra = getattr(cfg, "extra", None)
    if isinstance(extra, dict) and name in extra:
        return extra.get(name)
    hints = getattr(cfg, "keyops_hints", None)
    if isinstance(hints, dict) and name in hints:
        return hints.get(name)
    return default


def _validate_key_blocks(keys_arr: np.ndarray, period: int, A: int) -> None:
    if keys_arr.ndim != 2:
        raise ValueError("keys must be 2-D [B, K]")
    expected = int(period * A)
    if keys_arr.shape[1] != expected:
        raise ValueError(f"Expected key length {expected}, got {keys_arr.shape[1]}")
    B = int(keys_arr.shape[0])
    for b in range(B):
        for r in range(int(period)):
            start = r * int(A)
            end = start + int(A)
            block = keys_arr[b, start:end].astype(np.int64, copy=False)
            if (block < 0).any() or (block >= int(A)).any():
                raise ValueError("periodic_substitution key blocks must be in [0, A)")
            if np.unique(block).size != int(A):
                raise ValueError("periodic_substitution key blocks must be permutations of 0..A-1")


class PeriodicSubstitutionCipher(CipherPipelineMixin, KeyedCipherBase):
    """
    Periodic substitution with p independent inverse tables (ct->pt).
    Key layout: K = p * A, flattened by block.
    """
    name: str = "periodic_substitution"
    keyops_family: KeyOpsFamily = KeyOpsFamily.MATRIX

    def __init__(self, cfg, *, text_transposition: Direction | str = Direction.LTR, key_transposition: Direction | str = Direction.LTR):
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

        period = _cfg_get(cfg, "period", None)
        if period is None:
            raise ValueError("PeriodicSubstitution requires period in cfg.period or cfg.keyops_hints['period']")
        A = _cfg_get(cfg, "alphabet_size", _cfg_get(cfg, "A", _cfg_get(cfg, "N", DEFAULT_A)))
        self.period = int(period)
        self.A = int(A)
        if self.period <= 0:
            raise ValueError("period must be >= 1")
        if self.A <= 0:
            raise ValueError("alphabet_size must be >= 1")

        expected = int(self.period * self.A)
        key_len = getattr(cfg, "key_length", None)
        if key_len is not None and int(key_len) != expected:
            raise ValueError(f"key_length must be {expected} for period={self.period}, A={self.A}")
        self.key_length = expected

    def _periodic_decrypt_batch(self, ct: ArrayU8, keys: ArrayU8) -> ArrayU8:
        ct_arr = self._as_u8(ct, "ct")
        if ct_arr.ndim == 1:
            ct_arr = ct_arr[None, :]
        keys_arr = self._as_key_dtype(keys, "keys")
        if keys_arr.ndim == 1:
            keys_arr = keys_arr[None, :]

        if ct_arr.shape[0] == 1 and keys_arr.shape[0] > 1:
            ct_arr = np.repeat(ct_arr, keys_arr.shape[0], axis=0)
        if ct_arr.shape[0] != keys_arr.shape[0]:
            raise ValueError("Batch size mismatch between ciphertext and keys")

        _validate_key_blocks(keys_arr, self.period, self.A)

        L = int(ct_arr.shape[1])
        phase = np.arange(L, dtype=np.int64) % int(self.period)
        idx = phase[None, :] * int(self.A) + ct_arr.astype(np.int64)
        out = np.take_along_axis(keys_arr, idx, axis=1)
        return out.astype(np.uint8, copy=False)

    def _periodic_encrypt_batch(self, pt: ArrayU8, keys: ArrayU8) -> ArrayU8:
        pt_arr = self._as_u8(pt, "pt")
        if pt_arr.ndim == 1:
            pt_arr = pt_arr[None, :]
        keys_arr = self._as_key_dtype(keys, "keys")
        if keys_arr.ndim == 1:
            keys_arr = keys_arr[None, :]

        if pt_arr.shape[0] == 1 and keys_arr.shape[0] > 1:
            pt_arr = np.repeat(pt_arr, keys_arr.shape[0], axis=0)
        if pt_arr.shape[0] != keys_arr.shape[0]:
            raise ValueError("Batch size mismatch between plaintext and keys")

        _validate_key_blocks(keys_arr, self.period, self.A)

        B, L = int(keys_arr.shape[0]), int(pt_arr.shape[1])
        inv = np.empty((B, int(self.period), int(self.A)), dtype=np.int64)
        for b in range(B):
            for r in range(int(self.period)):
                start = r * int(self.A)
                end = start + int(self.A)
                block = keys_arr[b, start:end].astype(np.int64, copy=False)
                inv_block = np.empty(int(self.A), dtype=np.int64)
                inv_block[block] = np.arange(int(self.A), dtype=np.int64)
                inv[b, r] = inv_block

        phase = np.arange(L, dtype=np.int64) % int(self.period)
        phase_idx = np.tile(phase, (B, 1))
        row_idx = np.arange(B, dtype=np.int64)[:, None]
        out = inv[row_idx, phase_idx, pt_arr.astype(np.int64)]
        return out.astype(np.uint8, copy=False)

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        ct = self._as_u8(ct_tr, "ct").reshape(-1)
        keys = self._as_key_dtype(keys_tr, "keys")
        if keys.ndim == 1:
            keys = keys[None, :]
        if keys.shape[1] != int(self.key_length):
            raise ValueError(f"Expected key length {self.key_length}, got {keys.shape[1]}")
        return self._periodic_decrypt_batch(ct, keys)

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        pt = self._as_u8(pt_tr, "pt").reshape(-1)
        keys = self._as_key_dtype(keys_tr, "keys")
        if keys.ndim == 1:
            keys = keys[None, :]
        if keys.shape[1] != int(self.key_length):
            raise ValueError(f"Expected key length {self.key_length}, got {keys.shape[1]}")
        return self._periodic_encrypt_batch(pt, keys)

