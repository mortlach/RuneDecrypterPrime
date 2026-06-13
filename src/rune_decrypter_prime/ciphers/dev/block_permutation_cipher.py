import numpy as np
from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin, ArrayU8
from rune_decrypter_prime.keyops import PermutationKeyOps, PermutationKeyConfig


class BlockPermutationCipher(CipherPipelineMixin):
    """Fixed-size block transposition (perm-only) for back-compat.
    ct_block[j] = pt_block[ perm[j] ]. Short last block is truncated safely.
    """
    A = 29

    def __init__(self, cfg, *, text_transposition="ltr", key_transposition="ltr"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", "ltr"),
            key_transposition=getattr(cfg, "key_transposition", "ltr"),
        )
        self.cfg = cfg
        intr_exact  = getattr(cfg, "interruptors_exact", None)
        intr_legacy = getattr(cfg, "interruptors", None)
        chosen = intr_exact if intr_exact is not None else intr_legacy
        self._default_interrupt_idx = np.asarray(chosen, dtype=np.intp) if chosen is not None else None

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        L = int(ct_tr.size)
        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            perm = np.asarray(keys_tr[b], dtype=np.int64)
            out[b] = self._decrypt_one(ct_tr, perm)
        return out

    @staticmethod
    def _decrypt_one(ct: np.ndarray, perm: np.ndarray) -> np.ndarray:
        L = int(ct.size); K = int(perm.size)
        pt = np.empty(L, dtype=np.uint8)
        for start in range(0, L, K):
            m = min(K, L - start)
            block_ct = ct[start:start+m]
            for j in range(m):
                t = int(perm[j])
                if t < m:
                    pt[start + t] = block_ct[j]
        return pt
