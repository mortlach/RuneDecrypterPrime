# ============================================================
# rune_decrypter_prime/ciphers/substitution_cipher.py
# Monoalphabetic substitution (permutation of N symbols; default N=29).
# ============================================================
from __future__ import annotations
import numpy as np
from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin, ArrayU8
from rune_decrypter_prime.keyops.permutation_ops import PermutationOps
from rune_decrypter_prime.ciphers.registry import register_cipher

A = 29

@register_cipher("substitution")
@register_cipher("mono")
class SubstitutionCipher(CipherPipelineMixin):
    """
    Monoalphabetic substitution (permutation of N symbols).

    Key conventions:
      - Preferred (solver path): key maps ct -> pt (inverse map), shape (N,) or (B,N).
      - Tutorial helper can use pt -> ct (forward); set key_is_fwd=True to auto-invert.
    """
    def __init__(self, cfg, *, text_transposition="fwd", key_transposition="fwd"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", "fwd"),
            key_transposition=getattr(cfg, "key_transposition", "fwd"),
        )
        self.cfg = cfg
        N = int(getattr(cfg, "key_length", 29))
        self.A = N
        self.keyops = PermutationOps(N)

    # Solver fast-path (batch): implemented in _core_decrypt_batch via the mixin.
    # Keep this for correctness if callers hit .decrypt() directly (as Problem does).
    def decrypt(self, *, ciphertext: ArrayU8, key: ArrayU8, key_is_fwd: bool = False, **kwargs) -> ArrayU8:
        """
        Decrypt:
          - If key_is_fwd=False (default): 'key' maps ct -> pt. Returns:
                pt = key[ct]            for 1-D key
                pt = key[:, ct]         for (B,N) keys (batch)
          - If key_is_fwd=True: 'key' maps pt -> ct; invert to ct->pt first.
        """
        ct = np.asarray(ciphertext, dtype=np.uint8).reshape(-1)
        k  = np.asarray(key, dtype=np.uint8)

        if not key_is_fwd:
            if k.ndim == 1:
                if k.size != self.A:  # sanity
                    raise ValueError(f"decrypt: expected key of length {self.A}, got {k.size}")
                return k[ct]
            elif k.ndim == 2:
                if k.shape[1] != self.A:
                    raise ValueError(f"decrypt: expected key shape (*,{self.A}), got {k.shape}")
                # batch fancy-indexing: (B,N) take columns at ct
                return k[:, ct]
            else:
                raise ValueError("decrypt: key must be 1-D or 2-D array")
        else:
            # key is pt->ct; build inverse(s): inv[ct]=pt
            if k.ndim == 1:
                if k.size != self.A:
                    raise ValueError(f"decrypt: expected key of length {self.A}, got {k.size}")
                inv = np.empty_like(k)
                inv[k] = np.arange(self.A, dtype=np.uint8)
                return inv[ct]
            elif k.ndim == 2:
                if k.shape[1] != self.A:
                    raise ValueError(f"decrypt: expected key shape (*,{self.A}), got {k.shape}")
                B = k.shape[0]
                inv = np.empty_like(k)
                ar = np.arange(self.A, dtype=np.uint8)
                # vectorised row-wise inverse
                for b in range(B):
                    inv[b, k[b]] = ar
                return inv[:, ct]
            else:
                raise ValueError("decrypt: key must be 1-D or 2-D array")

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """
        keys_tr: (B, N) permutation rows mapping ciphertext -> plaintext.
        Decrypt: pt = key[ct]
        """
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        return keys_tr[:, ct_tr]

    # Optional helper for tutorials (pt->ct)
    def encrypt(self, *, plaintext: ArrayU8, key: ArrayU8, **kwargs) -> ArrayU8:
        pt = np.asarray(plaintext, dtype=np.uint8).reshape(-1)
        fwd = np.asarray(key, dtype=np.uint8).reshape(-1)
        if fwd.size != A:
            raise ValueError("SubstitutionCipher.encrypt: key must be length-29 permutation.")
        return fwd[pt]
