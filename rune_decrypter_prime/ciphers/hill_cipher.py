# ============================================================
# rune_decrypter_prime/ciphers/hill_cipher.py   (Hill 2×2 mod 29)
# ============================================================
import numpy as np
from .pipeline import CipherPipelineMixin, ArrayU8

class HillCipherMod29(CipherPipelineMixin):
    """
    2×2 Hill cipher over Z_29.
    Key is [a,b,c,d] as uint8, representing matrix [[a,b],[c,d]] mod 29.
    Key length is fixed to 4. Inverse must exist mod 29.
    """

    A = 29

    def __init__(self, cfg, *, text_transposition="fwd", key_transposition="fwd"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", "fwd"),
            key_transposition=getattr(cfg, "key_transposition", "fwd"),
        )
        self.cfg = cfg
        intr_exact  = getattr(cfg, "interruptors_exact", None)
        intr_legacy = getattr(cfg, "interruptors", None)
        chosen = intr_exact if intr_exact is not None else intr_legacy
        self._default_interrupt_idx = (
            np.asarray(chosen, dtype=np.intp) if chosen is not None else None
        )
        self._additive_debug = False  # not an additive cipher

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[Non]()
