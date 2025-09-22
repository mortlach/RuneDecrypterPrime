# rune_decrypter_prime/ciphers/route_cipher.py
from __future__ import annotations
from rune_decrypter_prime.keyops.permutation_ops import PermutationOps
from .pipeline import CipherPipelineMixin, ArrayU8

class RouteCipher(CipherPipelineMixin):
    """
    Route cipher variant:
      • Encrypt: fill K columns row-wise; read columns in key order.
      • Decrypt: reconstruct columns per lengths; place them by key order; read row-wise.

    This is effectively the same geometry as 'ColumnarTranspositionCipher' with a different name;
    kept separate for UI/UX clarity.
    """
    A = 29

    def __init__(self, cfg, *, text_transposition="fwd", key_transposition="fwd"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", text_transposition),
            key_transposition=getattr(cfg, "key_transposition", key_transposition),
        )
        self.cfg = cfg
        K = int(getattr(cfg, "key_length", 0))
        if K <= 1:
            raise ValueError("Route cipher requires key_length K >= 2")
        self.keyops = PermutationOps(K)

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        # identical to Columnar implementation
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        L = int(ct_tr.size)
        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            key_perm = np.asarray(keys_tr[b], dtype=np.int64)
            out[b] = self._decrypt_single(ct_tr, key_perm)
        return out

    @staticmethod
    def _decrypt_single(ct: np.ndarray, key_perm: np.ndarray) -> np.ndarray:
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
