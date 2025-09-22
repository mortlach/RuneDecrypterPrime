# ============================================================
# rune_decrypter_prime/ciphers/affine_cipher.py   (Affine mod 29)
# ============================================================
import numpy as np
from .pipeline import CipherPipelineMixin, ArrayU8

class AffineCipherMod29(CipherPipelineMixin):
    """
    Affine cipher over Z_29.
    Key is length-2 [a, b] with gcd(a,29)=1.
      Encrypt:  ct = (a * pt + b) mod 29
      Decrypt:  pt = a_inv * (ct - b) mod 29
    """
    A = 29

    def __init__(self, cfg, *, text_transposition="fwd", key_transposition="fwd"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", "fwd"),
            key_transposition=getattr(cfg, "key_transposition", "fwd"),
        )
        self.cfg = cfg
        # interruptors (exact/legacy)
        intr_exact  = getattr(cfg, "interruptors_exact", None)
        intr_legacy = getattr(cfg, "interruptors", None)
        chosen = intr_exact if intr_exact is not None else intr_legacy
        self._default_interrupt_idx = (
            np.asarray(chosen, dtype=np.intp) if chosen is not None else None
        )
        # Not a pure additive column cipher; keep additive debug off.

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        assert K == 2, f"Affine key must be length 2 [a,b], got {K}"
        L = int(ct_tr.size)

        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            a = int(keys_tr[b, 0]) % self.A
            c = int(keys_tr[b, 1]) % self.A  # b (offset)
            a_inv = self._modinv(a, self.A)
            if a_inv is None:
                raise ValueError(f"Non-invertible 'a' for mod {self.A}: a={a}")
            # pt = a_inv * (ct - c) mod A
            tmp = (ct_tr.astype(np.int16) - c) % self.A
            pt  = (a_inv * tmp) % self.A
            out[b] = pt.astype(np.uint8)
        return out

    @staticmethod
    def _egcd(a, b):
        if a == 0:
            return b, 0, 1
        g, y, x = AffineCipherMod29._egcd(b % a, a)
        return g, x - (b // a) * y, y

    @staticmethod
    def _modinv(a, m):
        a %= m
        g, x, _ = AffineCipherMod29._egcd(a, m)
        if g != 1:
            return None
        return x % m
