# ============================================================
# rune_decrypter_prime/ciphers/columnar_transposition_cipher.py
# Columnar Transposition Cipher (row-fill, column-read; pipeline-integrated).
# ============================================================
from __future__ import annotations
import numpy as np

from rune_decrypter_prime.keyops.permutation_ops import PermutationOps
from .pipeline import CipherPipelineMixin, ArrayU8


class ColumnarTranspositionCipher(CipherPipelineMixin):
    name: str = "columnar"

    def __init__(self, cfg, *, text_transposition: str = "fwd", key_transposition: str = "fwd"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", text_transposition),
            key_transposition=getattr(cfg, "key_transposition", key_transposition),
        )
        self.cfg = cfg

        # Attach keyops so GA/SA/Beam know how to explore keys
        key_len = getattr(cfg, "key_length", None)
        if not key_len or key_len <= 0:
            raise ValueError("Columnar requires positive key_length in cfg")
        self.keyops = PermutationOps(key_len)

        # Interruptors (legacy preserved)
        intr_exact = getattr(cfg, "interruptors_exact", None)
        intr_legacy = getattr(cfg, "interruptors", None)
        chosen = intr_exact if intr_exact is not None else intr_legacy
        self._default_interrupt_idx = (
            np.asarray(chosen, dtype=np.intp) if chosen is not None else None
        )

    # ----------------- pipeline hooks -----------------

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """Batch decryption for [B,K] permutation keys."""
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        L = int(ct_tr.size)

        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            key_perm = np.asarray(keys_tr[b], dtype=np.int64)
            out[b] = self._decrypt_single(ct_tr, key_perm)
        return out

    def _decrypt_single(self, ct: np.ndarray, key_perm: np.ndarray) -> np.ndarray:
        """Decrypt a single ciphertext using a columnar permutation key."""
        L = int(ct.size)
        K = int(key_perm.size)
        if K <= 0:
            raise ValueError("Columnar key length must be positive")

        rows = (L + K - 1) // K  # ceil(L/K)
        rem = L % K

        # Column lengths by physical column index (0..K-1).
        col_lens = np.full(K, rows - 1, dtype=np.int64)
        if rem == 0:
            col_lens[:] = rows
        else:
            col_lens[:rem] = rows

        # Slice CT into columns in the ORDER THEY WERE READ (key_perm)
        cols = [None] * K
        pos = 0
        for c in key_perm:
            ln = int(col_lens[c])
            cols[c] = ct[pos : pos + ln]
            pos += ln

        # Reconstruct plaintext by reading row-wise
        pt = np.empty(L, dtype=np.uint8)
        write = 0
        for r in range(rows):
            for c in range(K):
                if r < cols[c].size:
                    pt[write] = cols[c][r]
                    write += 1
        return pt
