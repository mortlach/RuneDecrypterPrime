# ============================================================
# rune_decrypter_prime/ciphers/playfair_cipher.py
# ============================================================
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin, ArrayU8
from rune_decrypter_prime.ciphers.dev.base_keyed_cipher import KeyedCipherBase
from rune_decrypter_prime.ciphers.registry import register_cipher
from rune_decrypter_prime.core.types import Direction, KeyOpsFamily, ensure_direction
from rune_decrypter_prime.keyops.permutation_ops import PermutationKeyOps, PermutationKeyConfig


@register_cipher("playfair29")
class Playfair29Cipher(CipherPipelineMixin, KeyedCipherBase):
    """
    Playfair-style cipher that works on the 29-rune alphabet by reducing to
    a 25-symbol square internally and projecting results back into 29-space.
    """

    alphabet_size: int = 29
    reduced_size: int = 25
    grid_width: int = 5
    keyops_family: KeyOpsFamily = KeyOpsFamily.PERMUTATION

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
        self.key_length = self.reduced_size

        self._keyops = PermutationKeyOps(PermutationKeyConfig(K=self.reduced_size))

        base_reduce = np.arange(self.alphabet_size, dtype=np.int64)
        cfg_reduce = getattr(cfg, "reduction_map", getattr(cfg, "REDUCE_29_TO_25", None))
        if cfg_reduce is None:
            custom_reduce = base_reduce
        else:
            custom_reduce = np.asarray(cfg_reduce, dtype=np.int64)
        if custom_reduce.shape != base_reduce.shape:
            raise ValueError("reduction_map must be length 29")
        self.reduce_map = np.clip(custom_reduce, 0, self.alphabet_size - 1)

        reps = self._choose_representatives()
        inv29 = np.full(self.alphabet_size, -1, dtype=np.int64)
        inv29[reps] = np.arange(self.reduced_size, dtype=np.int64)
        self.rep25_in_29 = reps
        self.inv29_to_25 = inv29

        filler_29 = int(getattr(cfg, "filler_idx29", 0))
        if filler_29 < 0 or filler_29 >= self.alphabet_size:
            filler_29 = 0
        filler_reduced = int(self.inv29_to_25[self._reduce_to_representative(filler_29)])
        if filler_reduced < 0:
            filler_reduced = 0
        self.filler_29 = filler_29
        self.filler_25 = filler_reduced

    # ------------------------------------------------------------------ helpers
    def _choose_representatives(self) -> np.ndarray:
        seen = set()
        reps: list[int] = []
        for idx in range(self.alphabet_size):
            reduced = int(self.reduce_map[idx])
            if reduced not in seen:
                seen.add(reduced)
                reps.append(idx)
            if len(reps) == self.reduced_size:
                break
        if len(reps) != self.reduced_size:
            raise ValueError("Unable to derive 25 representatives from reduction_map")
        reps_arr = np.array(reps, dtype=np.int64)
        inv = np.full(self.alphabet_size, -1, dtype=np.int64)
        inv[reps_arr] = np.arange(self.reduced_size, dtype=np.int64)
        self.inv29_to_25 = inv
        return reps_arr

    def _reduce_to_representative(self, idx29: int) -> int:
        return int(self.reduce_map[idx29])

    def _pt_to_25(self, arr29: np.ndarray) -> np.ndarray:
        reduced = self.reduce_map[arr29]
        mapped = self.inv29_to_25[reduced]
        return mapped.astype(np.int64, copy=False)

    def _to_29(self, arr25: np.ndarray) -> np.ndarray:
        rev = self.rep25_in_29
        return rev[arr25].astype(np.uint8, copy=False)

    def _make_pairs_encrypt(self, arr25: np.ndarray) -> np.ndarray:
        output = []
        i = 0
        filler = self.filler_25
        while i < arr25.size:
            a = int(arr25[i])
            if i + 1 < arr25.size:
                b = int(arr25[i + 1])
                if a == b:
                    output.extend([a, filler])
                    i += 1
                else:
                    output.extend([a, b])
                    i += 2
            else:
                output.extend([a, filler])
                i += 1
        return np.asarray(output, dtype=np.int64)

    def _make_pairs_decrypt(self, arr25: np.ndarray) -> np.ndarray:
        if arr25.size % 2:
            arr25 = np.concatenate([arr25, np.asarray([self.filler_25], dtype=np.int64)], axis=0)
        return arr25.astype(np.int64, copy=False)

    def _encrypt_pairs(self, pairs25: np.ndarray, key25: np.ndarray) -> np.ndarray:
        out = np.empty_like(pairs25)
        inv = np.empty(self.reduced_size, dtype=np.int64)
        inv[key25] = np.arange(self.reduced_size, dtype=np.int64)
        rows = (inv // self.grid_width).astype(np.int64)
        cols = (inv % self.grid_width).astype(np.int64)
        for i in range(0, pairs25.size, 2):
            a = int(pairs25[i])
            b = int(pairs25[i + 1])
            ra, ca = rows[a], cols[a]
            rb, cb = rows[b], cols[b]
            if ra == rb:
                na = ra * self.grid_width + ((ca + 1) % self.grid_width)
                nb = rb * self.grid_width + ((cb + 1) % self.grid_width)
            elif ca == cb:
                na = ((ra + 1) % self.grid_width) * self.grid_width + ca
                nb = ((rb + 1) % self.grid_width) * self.grid_width + cb
            else:
                na = ra * self.grid_width + cb
                nb = rb * self.grid_width + ca
            out[i] = key25[na]
            out[i + 1] = key25[nb]
        return out

    def _decrypt_pairs(self, pairs25: np.ndarray, key25: np.ndarray) -> np.ndarray:
        out = np.empty_like(pairs25)
        inv = np.empty(self.reduced_size, dtype=np.int64)
        inv[key25] = np.arange(self.reduced_size, dtype=np.int64)
        rows = (inv // self.grid_width).astype(np.int64)
        cols = (inv % self.grid_width).astype(np.int64)
        for i in range(0, pairs25.size, 2):
            a = int(pairs25[i])
            b = int(pairs25[i + 1])
            ra, ca = rows[a], cols[a]
            rb, cb = rows[b], cols[b]
            if ra == rb:
                na = ra * self.grid_width + ((ca - 1) % self.grid_width)
                nb = rb * self.grid_width + ((cb - 1) % self.grid_width)
            elif ca == cb:
                na = ((ra - 1) % self.grid_width) * self.grid_width + ca
                nb = ((rb - 1) % self.grid_width) * self.grid_width + cb
            else:
                na = ra * self.grid_width + cb
                nb = rb * self.grid_width + ca
            out[i] = key25[na]
            out[i + 1] = key25[nb]
        return out

    # ------------------------------------------------------------------ encrypt/decrypt
    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        pt = self._as_u8(pt_tr, "pt")
        if pt.ndim == 1:
            pt = pt[None, :]
        B_text, L = pt.shape

        keys = self._as_u8(keys_tr, "keys")
        if keys.ndim == 1:
            keys = keys[None, :]
        B_keys, K = keys.shape
        if K != self.reduced_size:
            raise ValueError(f"playfair29 requires key length {self.reduced_size}")

        out = np.empty((max(B_text, B_keys), L if L % 2 == 0 else L + 1), dtype=np.uint8)
        for b in range(out.shape[0]):
            pt_row = pt[b % B_text]
            key_row = self._keyops.normalize(keys[b % B_keys])
            pt25 = self._pt_to_25(pt_row)
            pairs = self._make_pairs_encrypt(pt25)
            enc25 = self._encrypt_pairs(pairs, key_row.astype(np.int64, copy=False))
            ct29 = self._to_29(enc25)
            out[b] = self._fit_to_row(ct29, out.shape[1])
        return out

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        ct = self._as_u8(ct_tr, "ct")
        if ct.ndim == 1:
            ct = ct[None, :]
        B_text, L = ct.shape

        keys = self._as_u8(keys_tr, "keys")
        if keys.ndim == 1:
            keys = keys[None, :]
        B_keys, K = keys.shape
        if K != self.reduced_size:
            raise ValueError(f"playfair29 requires key length {self.reduced_size}")

        out = np.empty((max(B_text, B_keys), L if L % 2 == 0 else L + 1), dtype=np.uint8)
        for b in range(out.shape[0]):
            ct_row = ct[b % B_text]
            key_row = self._keyops.normalize(keys[b % B_keys])
            ct25 = self._pt_to_25(ct_row)
            pairs = self._make_pairs_decrypt(ct25)
            dec25 = self._decrypt_pairs(pairs, key_row.astype(np.int64, copy=False))
            pt29 = self._to_29(dec25)
            out[b] = self._fit_to_row(pt29, out.shape[1])
        return out

    def _fit_to_row(self, arr: np.ndarray, width: int) -> np.ndarray:
        if arr.size == width:
            return arr
        out = np.zeros(width, dtype=np.uint8)
        n = min(width, arr.size)
        out[:n] = arr[:n]
        return out
