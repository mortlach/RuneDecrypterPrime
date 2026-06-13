# ============================================================
# rune_decrypter_prime/ciphers/substitution_cipher.py
# Monoalphabetic substitution (permutation of N symbols; default N=29).
# ============================================================
from __future__ import annotations
import numpy as np
from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin, ArrayU8
from rune_decrypter_prime.ciphers.registry import register_cipher
from rune_decrypter_prime.core.types import Direction, KeyOpsFamily, ensure_direction

DEFAULT_N = 29

@register_cipher("substitution")
@register_cipher("mono")
class SubstitutionCipher(CipherPipelineMixin):
    """
    Monoalphabetic substitution (permutation of N symbols).

    **Key orientation (critical):**
      - This cipher expects the key as an **inverse table**: ct -> pt.
        Decrypt is a direct gather: `pt = key[ct]`.
      - Keys may be shape (A,) or (B, A) for batched evaluation.

    **Transpositions:**
      - Text transposition: allowed (default "ltr").
      - Key transposition: must be "ltr" (identity). Reordering the table changes
        its semantics; do NOT transpose keys for mono.

    **KeyOps:**
      - family: "permutation" (alias "perm" also supported in the Problem).
      - length: K = A (alphabet size).

    **Tutorial convenience:**
      - If `key_is_fwd=True` is passed, the provided key maps pt->ct; we invert it
        once to ct->pt before gathering. Optimisers do not use this flag.
    """

    # ---- Tell the Problem which KeyOps to build ----
    keyops_family: KeyOpsFamily = KeyOpsFamily.PERMUTATION  # <- Problem will attach PermutationKeyOps(length=N)

    def __init__(self, cfg, *, text_transposition: Direction | str = Direction.LTR, key_transposition: Direction | str = Direction.LTR):
        text_dir = ensure_direction(getattr(cfg, "text_transposition", text_transposition))
        key_dir = ensure_direction(getattr(cfg, "key_transposition", key_transposition))
        super().__init__(
            text_transposition=text_dir.value,
            key_transposition=key_dir.value,
            initial_text_permutation_indices=getattr(cfg, "initial_text_permutation_indices", None),
        )
        self.cfg = cfg
        self.text_direction = text_dir
        self.key_direction = key_dir
        # Alphabet / key size
        N = int(getattr(cfg, "key_length", getattr(cfg, "alphabet_size", DEFAULT_N)))
        self.A = N
        # Optional: expose key_length for the Problem's K resolution
        self.key_length = N

    # ---- Decrypt (vectorized, batch-aware) ----
    def decrypt(self, *, ciphertext: ArrayU8, key: ArrayU8, key_is_fwd: bool = False, **kwargs) -> ArrayU8:
        """
        Decrypt ciphertext with a permutation key.

        Parameters
        ----------
        ciphertext : [L] uint8
            Cipher indices 0..A-1.
        key : [N] or [B,N] uint8
            Permutation(s).
            - When key_is_fwd=False (default): key maps ct->pt (inverse map). We index key with ct.
            - When key_is_fwd=True:  key maps pt->ct. We invert first to ct->pt, then index.

        Returns
        -------
        ArrayU8
            If key is 1-D: [L] plaintext indices.
            If key is 2-D: [B,L] plaintext indices (row per key).
        """
        ct = np.asarray(ciphertext, dtype=np.uint8).reshape(-1)
        k  = np.asarray(key, dtype=np.uint8)

        if k.ndim == 1:
            if k.size != self.A:
                raise ValueError(f"decrypt: expected key of length {self.A}, got {k.size}")
            if key_is_fwd:
                inv = np.empty_like(k)            # inv[ct] = pt
                inv[k] = np.arange(self.A, dtype=np.uint8)
                return inv[ct]
            else:
                return k[ct]

        elif k.ndim == 2:
            if k.shape[1] != self.A:
                raise ValueError(f"decrypt: expected key shape (*,{self.A}), got {k.shape}")
            B = k.shape[0]
            if key_is_fwd:
                inv = np.empty_like(k)
                ar = np.arange(self.A, dtype=np.uint8)
                # vectorized row-wise inverse
                for b in range(B):
                    inv[b, k[b]] = ar
                return inv[:, ct]  # [B,L]
            else:
                return k[:, ct]    # [B,L]

        else:
            raise ValueError("decrypt: key must be 1-D or 2-D array")

    # ---- Optional tutorial helper (pt->ct) ----
    def encrypt(self, *, plaintext: ArrayU8, key: ArrayU8, **kwargs) -> ArrayU8:
        """
        Encrypt using a forward permutation key mapping pt->ct (tutorials).
        Optimizers never call this.
        """
        pt = np.asarray(plaintext, dtype=np.uint8).reshape(-1)
        k  = np.asarray(key, dtype=np.uint8).reshape(-1)
        if k.size != self.A:
            raise ValueError(f"encrypt: expected key of length {self.A}, got {k.size}")
        return k[pt]
