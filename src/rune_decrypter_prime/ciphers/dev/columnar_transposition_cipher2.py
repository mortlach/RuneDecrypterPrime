# rune_decrypter_prime/ciphers/columnar_transposition_cipher.py
from __future__ import annotations
import numpy as np
from rdp.keyops.permutation_ops import PermutationOps
from .pipeline import CipherPipelineMixin, ArrayU8

class ColumnarTranspositionCipher(CipherPipelineMixin):
    """
    Classical row-fill / column-read columnar transposition over Runeglish (A=29).

    Key: permutation of columns [0..K-1] indicating READ ORDER used at encryption.
         Decrypt reconstructs columns by lengths and reads row-wise.
    """
    A = 29

    def __init__(self, cfg, *, text_transposition="ltr", key_transposition="ltr"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", text_transposition),
            key_transposition=getattr(cfg, "key_transposition", key_transposition),
        )
        self.cfg = cfg

        key_len = int(getattr(cfg, "key_length", 0))
        if key_len <= 0:
            raise ValueError("Columnar requires positive key_length in cfg")
        self.keyops = PermutationOps(key_len)

        intr_exact  = getattr(cfg, "interruptors_exact", None)
        intr_legacy = getattr(cfg, "interruptors", None)
        chosen = intr_exact if intr_exact is not None else intr_legacy
        self._default_interrupt_idx = (
            np.asarray(chosen, dtype=np.intp) if chosen is not None else None
        )

    # --- batch decrypt core --- #
    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        L = int(ct_tr.size)

        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            out[b] = self._decrypt_single(ct_tr, np.asarray(keys_tr[b], dtype=np.int64))
        return out

    # --- reference encrypt (handy for tests/tutorials) --- #
    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        L = int(pt_tr.size)
        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            out[b] = self._encrypt_single(pt_tr, np.asarray(keys_tr[b], dtype=np.int64))
        return out

    # --- scalar helpers --- #
    def _decrypt_single(self, ct: np.ndarray, key_perm: np.ndarray) -> np.ndarray:
        L = int(ct.size); K = int(key_perm.size)
        rows = (L + K - 1) // K
        rem  = L % K
        col_lens = np.full(K, rows - 1, dtype=np.int64)
        if rem == 0:
            col_lens[:] = rows
        else:
            col_lens[:rem] = rows

        cols = [None] * K
        pos = 0
        for c in key_perm:
            ln = int(col_lens[c])
            cols[c] = ct[pos:pos+ln]
            pos += ln

        pt = np.empty(L, dtype=np.uint8)
        w = 0
        for r in range(rows):
            for c in range(K):
                col = cols[c]
                if r < col.size:
                    pt[w] = col[r]; w += 1
        return pt

    def _encrypt_single(self, pt: np.ndarray, key_perm: np.ndarray) -> np.ndarray:
        L = int(pt.size); K = int(key_perm.size)
        rows = (L + K - 1) // K
        rem  = L % K

        cols = [bytearray() for _ in range(K)]
        # Fill row-wise across physical columns 0..K-1
        i = 0
        for r in range(rows):
            for c in range(K):
                if i < L:
                    cols[c].append(int(pt[i])); i += 1
        # Read columns in key order
        parts = []
        for c in key_perm:
            parts.append(np.frombuffer(cols[int(c)], dtype=np.uint8))
        return np.concatenate(parts) if parts else np.empty(0, dtype=np.uint8)
