# rune_decrypter_prime/ciphers/double_transposition_cipher.py
from __future__ import annotations
import numpy as np
from rune_decrypter_prime.keyops.permutation_ops import PermutationOps
from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin, ArrayU8


class _ConcatPermKeyOps:
    """
    Compose two permutation spaces into one flat chromosome so GA/SA can work
    without special support. Exposes a .random(rng) that returns concatenated key.
    """

    def __init__(self, k1: int, k2: int):
        if k1 <= 1 or k2 <= 1:
            raise ValueError("DoubleTransposition requires k1,k2 >= 2")
        self.k1 = k1
        self.k2 = k2
        self.ops1 = PermutationOps(k1)
        self.ops2 = PermutationOps(k2)

    def random(self, rng) -> np.ndarray:
        a = self.ops1.random(rng)
        b = self.ops2.random(rng)
        return np.concatenate([a, b]).astype(np.int64, copy=False)

    # Optional helpers (solver may call these — keep signatures simple)
    def mutate(self, rng, key: np.ndarray) -> np.ndarray:
        a, b = key[: self.k1].copy(), key[self.k1 :].copy()
        if rng.random() < 0.5:
            a = self.ops1.mutate(rng, a)
        else:
            b = self.ops2.mutate(rng, b)
        return np.concatenate([a, b])

    def crossover(self, rng, pa: np.ndarray, pb: np.ndarray) -> np.ndarray:
        a1, a2 = pa[: self.k1], pb[: self.k1]
        b1, b2 = pa[self.k1 :], pb[self.k1 :]
        ca = self.ops1.crossover(rng, a1, a2)
        cb = self.ops2.crossover(rng, b1, b2)
        return np.concatenate([ca, cb])


class DoubleTranspositionCipher(CipherPipelineMixin):
    """
    Two columnar transpositions applied sequentially (Columnar(k1) -> Columnar(k2)).
    Decrypt = inverse order of operations:
        1) inverse Columnar(k2)
        2) inverse Columnar(k1)
    """

    A = 29

    def __init__(self, cfg, *, text_transposition="ltr", key_transposition="ltr"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", text_transposition),
            key_transposition=getattr(cfg, "key_transposition", key_transposition),
        )
        self.cfg = cfg
        k1 = int(getattr(cfg, "key_len1", getattr(cfg, "k1", 0)) or 0)
        k2 = int(getattr(cfg, "key_len2", getattr(cfg, "k2", 0)) or 0)
        if k1 <= 1 or k2 <= 1:
            raise ValueError("DoubleTransposition requires key_len1, key_len2 >= 2")
        self.k1 = k1
        self.k2 = k2
        self.keyops = _ConcatPermKeyOps(k1, k2)

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B = keys_tr.shape[0]
        L = int(ct_tr.size)
        out = np.empty((B, L), dtype=np.uint8)
        for i in range(B):
            k = np.asarray(keys_tr[i], dtype=np.int64)
            k1, k2 = k[: self.k1], k[self.k1 :]
            # inverse of Columnar(k2) then inverse of Columnar(k1)
            tmp = self._col_decrypt(ct_tr, k2)
            out[i] = self._col_decrypt(tmp, k1)
        return out

    @staticmethod
    def _col_decrypt(ct: np.ndarray, key_perm: np.ndarray) -> np.ndarray:
        L = int(ct.size)
        K = int(key_perm.size)
        rows = (L + K - 1) // K
        rem = L % K
        col_lens = np.full(K, rows - 1, dtype=np.int64)
        if rem == 0:
            col_lens[:] = rows
        else:
            col_lens[:rem] = rows
        cols = [None] * K
        pos = 0
        for c in key_perm:
            ln = int(col_lens[c])
            cols[c] = ct[pos : pos + ln]
            pos += ln
        pt = np.empty(L, dtype=np.uint8)
        w = 0
        for r in range(rows):
            for c in range(K):
                col = cols[c]
                if r < col.size:
                    pt[w] = col[r]
                    w += 1
        return pt
