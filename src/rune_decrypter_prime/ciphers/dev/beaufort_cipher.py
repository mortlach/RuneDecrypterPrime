# ============================================================
# rune_decrypter_prime/ciphers/beaufort_cipher.py   (Beaufort & Variant Beaufort)
# ============================================================
import numpy as np
from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin, ArrayU8
from rdp.keyops.vector import VectorKeyOps

class BeaufortCipher(CipherPipelineMixin):
    """
    Classical Beaufort over Z_29 with repeating key.
      Encrypt: c = (k - p) mod A
      Decrypt: p = (k - c) mod A  (same transform)
    Key: [K] numeric (0..A-1), repeats across text.
    """
    A = 29

    def __init__(self, cfg, *, text_transposition="ltr", key_transposition="ltr"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", "ltr"),
            key_transposition=getattr(cfg, "key_transposition", "ltr"),
        )
        #self._additive_debug = False
        self.cfg = cfg
        # todo wow this is till about, years old, poor beaufort obviously unloved
        intr_exact  = getattr(cfg, "interruptors_exact", None)
        intr_legacy = getattr(cfg, "interruptors", None)
        chosen = intr_exact if intr_exact is not None else intr_legacy
        self._default_interrupt_idx = np.asarray(chosen, dtype=np.intp) if chosen is not None else None
        # expect a VectorKeyOps (length K, mod = A)
        key_obj = getattr(cfg, "key", None)
        if not isinstance(key_obj, VectorKeyOps):
            raise TypeError(f"{self.__class__.__name__} expects a VectorKeyOps (VectorKeyConfig(K=..., mod={self.A}))")
        self._keyops: VectorKeyOps = key_obj

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        L = int(ct_tr.size)
        out = np.empty((B, L), dtype=np.uint8)
        cols = (np.arange(L, dtype=np.int64) % K)
        for b in range(B):
            # normalize each candidate key row to [0..A) & right length
            krow = self._keyops.normalize(keys_tr[b])
            # Beaufort: p = (k - c) mod A   | Variant: p = (c + k) mod A
            # Choose arithmetic per class:
            if self.__class__.__name__.startswith("Variant"):
                pt = (ct_tr.astype(np.int16) + krow[cols].astype(np.int16)) % self.A
            else:
                pt = (krow[cols].astype(np.int16) - ct_tr.astype(np.int16)) % self.A
            out[b] = pt.astype(np.uint8)
        return out


class VariantBeaufortCipher(CipherPipelineMixin):
    """
    Variant Beaufort over Z_29 with repeating key.
      Encrypt: c = (p - k) mod A
      Decrypt: p = (c + k) mod A
    Key: [K] numeric (0..A-1), repeats across text.
    """
    A = 29

    def __init__(self, cfg, *, text_transposition="ltr", key_transposition="ltr"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", "ltr"),
            key_transposition=getattr(cfg, "key_transposition", "ltr"),
        )
        self.cfg = cfg
        #self._additive_debug = False  # additive identity holds with (+k)
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
        cols = (np.arange(L, dtype=np.int64) % K)
        for b in range(B):
            krow = keys_tr[b]
            pt = (ct_tr.astype(np.int16) + krow[cols].astype(np.int16)) % self.A
            out[b] = pt.astype(np.uint8)
        return out
