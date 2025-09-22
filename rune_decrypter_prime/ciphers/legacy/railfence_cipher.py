# ============================================================
# rune_decrypter_prime/ciphers/railfence_cipher.py   (Rail Fence)
# ============================================================
import numpy as np
from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin, ArrayU8

class RailFenceCipher(CipherPipelineMixin):
    """
    Rail fence (zigzag) transposition.
    Key is [R] rails (integer >= 2). For R=1, plaintext == ciphertext.
    Encrypt (reference): write chars in zigzag across R rails, then read by rails 0..R-1.
    Decrypt (implemented): reconstruct rail counts from pattern, split CT, then read zigzag.
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

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        assert K == 1, f"RailFence key must be [R], got length {K}"
        L = int(ct_tr.size)

        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            R = int(keys_tr[b, 0])
            out[b] = self._decrypt_single(ct_tr, R)
        return out

    def _decrypt_single(self, ct: np.ndarray, R: int) -> np.ndarray:
        L = int(ct.size)
        if R <= 1 or L <= 2:
            return ct.copy()
        pattern = self._rail_pattern(L, R)  # rail index for each position 0..L-1
        # count how many chars per rail
        counts = np.bincount(pattern, minlength=R)
        # slice CT into rails in order 0..R-1
        rails = []
        pos = 0
        for r in range(R):
            ln = int(counts[r])
            rails.append(ct[pos:pos+ln])
            pos += ln
        # reconstruct plaintext by walking zigzag and taking from rails
        idx_in_rail = np.zeros(R, dtype=np.int64)
        pt = np.empty(L, dtype=np.uint8)
        for i, r in enumerate(pattern):
            j = idx_in_rail[r]
            pt[i] = rails[r][j]
            idx_in_rail[r] += 1
        return pt

    @staticmethod
    def _rail_pattern(L: int, R: int) -> np.ndarray:
        # produce rail index per position using zigzag 0..R-1..0..
        pat = np.empty(L, dtype=np.int64)
        rail = 0
        step = 1
        for i in range(L):
            pat[i] = rail
            rail += step
            if rail == 0 or rail == R - 1:
                step *= -1
        return pat
