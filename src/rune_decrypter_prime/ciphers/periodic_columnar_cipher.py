# ============================================================
# rune_decrypter_prime/ciphers/periodic_columnar_cipher.py
# Periodic substitution + columnar transposition (integrated).
# ============================================================
from __future__ import annotations
import numpy as np

from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin, ArrayU8
from rune_decrypter_prime.ciphers.base_keyed_cipher import KeyedCipherBase
from rune_decrypter_prime.ciphers.registry import register_cipher
from rune_decrypter_prime.core.types import Direction, KeyOpsFamily, ensure_direction

DEFAULT_A = 29
_ORDERS = {"sub_then_col", "col_then_sub"}


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


@register_cipher("periodic_columnar")
class PeriodicColumnarCipher(CipherPipelineMixin, KeyedCipherBase):
    """
    Integrated periodic substitution + columnar transposition.
    Key layout: K = p * A + W
    """
    name: str = "periodic_columnar"
    keyops_family: KeyOpsFamily = KeyOpsFamily.MATRIX
    mod_keys: bool = False

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
        columns = _cfg_get(cfg, "columns", None)
        if period is None or columns is None:
            raise ValueError("PeriodicColumnar requires period and columns in config or keyops_hints")
        A = _cfg_get(cfg, "alphabet_size", _cfg_get(cfg, "A", _cfg_get(cfg, "N", DEFAULT_A)))

        self.period = int(period)
        self.columns = int(columns)
        self.A = int(A)
        if self.period <= 0:
            raise ValueError("period must be >= 1")
        if self.columns <= 0:
            raise ValueError("columns must be >= 1")
        if self.columns > 255:
            raise ValueError("columns must be <= 255 (uint8 column limit)")
        if self.A <= 0:
            raise ValueError("alphabet_size must be >= 1")

        order = _cfg_get(cfg, "order", "sub_then_col")
        if order not in _ORDERS:
            raise ValueError(f"order must be one of {sorted(_ORDERS)}")
        self.order = str(order)

        expected = int(self.period * self.A + self.columns)
        key_len = getattr(cfg, "key_length", None)
        if key_len is not None and int(key_len) != expected:
            raise ValueError(f"key_length must be {expected} for period={self.period}, A={self.A}, columns={self.columns}")
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

    def _columnar_undo_batch(self, ct: ArrayU8, keys: ArrayU8) -> ArrayU8:
        ct_arr = self._as_u8(ct, "ct")
        if ct_arr.ndim == 1:
            ct_arr = ct_arr[None, :]
        keys_arr = np.asarray(keys, dtype=np.int64)
        if keys_arr.ndim == 1:
            keys_arr = keys_arr[None, :]

        if ct_arr.shape[0] == 1 and keys_arr.shape[0] > 1:
            ct_arr = np.repeat(ct_arr, keys_arr.shape[0], axis=0)
        if ct_arr.shape[0] != keys_arr.shape[0]:
            raise ValueError("Batch size mismatch between ciphertext and keys")

        B, W = keys_arr.shape
        L = int(ct_arr.shape[1])
        if keys_arr.min() < 0 or keys_arr.max() >= W:
            raise ValueError("columnar key values out of range")
        if (np.apply_along_axis(lambda r: np.unique(r).size, 1, keys_arr) != W).any():
            raise ValueError("columnar key is not a permutation")

        rows = (L + W - 1) // W
        rem = L % W
        col_lens = np.full(W, rows - 1, dtype=np.int64)
        if rem == 0:
            col_lens[:] = rows
        else:
            col_lens[:rem] = rows

        row_ids = np.arange(rows, dtype=np.int64)[:, None]
        present = row_ids < col_lens[None, :]
        R, C = np.where(present)

        keys_i64 = keys_arr.astype(np.int64, copy=False)
        col_lens_perm = col_lens[keys_i64]
        off_ro = np.concatenate(
            [np.zeros((B, 1), dtype=np.int64), np.cumsum(col_lens_perm[:, :-1], axis=1)], axis=1
        )
        off_phys = np.empty_like(off_ro)
        idx_rows = np.arange(B)[:, None]
        off_phys[idx_rows, keys_i64] = off_ro

        take = off_phys[:, C] + R[None, :]
        out = np.take_along_axis(ct_arr, take, axis=1)
        return out.astype(np.uint8, copy=False)

    def _columnar_apply_batch(self, pt: ArrayU8, keys: ArrayU8) -> ArrayU8:
        pt_arr = self._as_u8(pt, "pt")
        if pt_arr.ndim == 1:
            pt_arr = pt_arr[None, :]
        keys_arr = np.asarray(keys, dtype=np.int64)
        if keys_arr.ndim == 1:
            keys_arr = keys_arr[None, :]

        if pt_arr.shape[0] == 1 and keys_arr.shape[0] > 1:
            pt_arr = np.repeat(pt_arr, keys_arr.shape[0], axis=0)
        if pt_arr.shape[0] != keys_arr.shape[0]:
            raise ValueError("Batch size mismatch between plaintext and keys")

        B, W = keys_arr.shape
        L = int(pt_arr.shape[1])
        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            perm = keys_arr[b].astype(np.int64, copy=False)
            if perm.min() < 0 or perm.max() >= W or np.unique(perm).size != W:
                raise ValueError("columnar key is not a permutation")
            columns = [pt_arr[b, c::W].astype(np.uint8, copy=False) for c in range(W)]
            ct_parts = [columns[c] for c in perm]
            out[b] = np.concatenate(ct_parts, axis=0)[:L]
        return out

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        ct = self._as_u8(ct_tr, "ct").reshape(-1)
        keys = self._as_key_dtype(keys_tr, "keys")
        if keys.ndim == 1:
            keys = keys[None, :]

        sub_len = int(self.period * self.A)
        col_len = int(self.columns)
        if keys.shape[1] != int(self.key_length):
            raise ValueError(f"Expected key length {self.key_length}, got {keys.shape[1]}")
        sub_keys = keys[:, :sub_len]
        col_keys = keys[:, sub_len : sub_len + col_len]

        if self.order == "sub_then_col":
            ct1 = self._columnar_undo_batch(ct, col_keys)
            return self._periodic_decrypt_batch(ct1, sub_keys)
        pt1 = self._periodic_decrypt_batch(ct, sub_keys)
        return self._columnar_undo_batch(pt1, col_keys)

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        pt = self._as_u8(pt_tr, "pt").reshape(-1)
        keys = self._as_key_dtype(keys_tr, "keys")
        if keys.ndim == 1:
            keys = keys[None, :]

        sub_len = int(self.period * self.A)
        col_len = int(self.columns)
        if keys.shape[1] != int(self.key_length):
            raise ValueError(f"Expected key length {self.key_length}, got {keys.shape[1]}")
        sub_keys = keys[:, :sub_len]
        col_keys = keys[:, sub_len : sub_len + col_len]

        if self.order == "sub_then_col":
            pt1 = self._periodic_encrypt_batch(pt, sub_keys)
            return self._columnar_apply_batch(pt1, col_keys)
        pt1 = self._columnar_apply_batch(pt, col_keys)
        return self._periodic_encrypt_batch(pt1, sub_keys)

