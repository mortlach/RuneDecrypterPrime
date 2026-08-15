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

    # ---- Public orientation helpers; structure remains owned by the mixin ----
    def decrypt(
        self,
        *,
        ciphertext: ArrayU8,
        key: ArrayU8,
        key_is_fwd: bool = False,
        interrupt_idx: ArrayU8 | None = None,
        interrupt_sym: ArrayU8 | None = None,
    ) -> ArrayU8:
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
        k = np.asarray(key, dtype=np.uint8)
        single = k.ndim == 1
        self._validate_substitution_key_shape(k, "decrypt")
        if key_is_fwd:
            inverse = np.empty_like(k)
            alphabet = np.arange(self.A, dtype=np.uint8)
            if single:
                inverse[k] = alphabet
            else:
                for row in range(k.shape[0]):
                    inverse[row, k[row]] = alphabet
            k = inverse

        out = super().decrypt(
            ciphertext=ciphertext,
            key=k,
            interrupt_idx=interrupt_idx,
            interrupt_sym=interrupt_sym,
        )
        return out[0] if single else out

    # ---- Optional tutorial helper (pt->ct) ----
    def encrypt(
        self,
        *,
        plaintext: ArrayU8,
        key: ArrayU8,
        interrupt_idx: ArrayU8 | None = None,
        interrupt_sym: ArrayU8 | None = None,
    ) -> ArrayU8:
        """
        Encrypt using a forward permutation key mapping pt->ct (tutorials).
        Optimizers never call this.
        """
        k = np.asarray(key, dtype=np.uint8)
        single = k.ndim == 1
        self._validate_substitution_key_shape(k, "encrypt")
        out = super().encrypt(
            plaintext=plaintext,
            key=k,
            interrupt_idx=interrupt_idx,
            interrupt_sym=interrupt_sym,
        )
        return out[0] if single else out

    def decrypt_single(
        self,
        *,
        ciphertext: ArrayU8,
        key: ArrayU8,
        interrupt_idx: ArrayU8 | None = None,
        interrupt_sym: ArrayU8 | None = None,
        key_is_fwd: bool = False,
    ) -> ArrayU8:
        """Decrypt one key while preserving the historical one-dimensional result."""
        out = self.decrypt(
            ciphertext=ciphertext,
            key=key,
            key_is_fwd=key_is_fwd,
            interrupt_idx=interrupt_idx,
            interrupt_sym=interrupt_sym,
        )
        return out[0] if out.ndim == 2 else out

    def encrypt_single(
        self,
        *,
        plaintext: ArrayU8,
        key: ArrayU8,
        interrupt_idx: ArrayU8 | None = None,
        interrupt_sym: ArrayU8 | None = None,
    ) -> ArrayU8:
        """Encrypt one key while preserving the historical one-dimensional result."""
        out = self.encrypt(
            plaintext=plaintext,
            key=key,
            interrupt_idx=interrupt_idx,
            interrupt_sym=interrupt_sym,
        )
        return out[0] if out.ndim == 2 else out

    def _validate_substitution_key_shape(self, key: np.ndarray, operation: str) -> None:
        if key.ndim == 1:
            if key.size != self.A:
                raise ValueError(f"{operation}: expected key of length {self.A}, got {key.size}")
            return
        if key.ndim == 2:
            if key.shape[1] != self.A:
                raise ValueError(f"{operation}: expected key shape (*,{self.A}), got {key.shape}")
            return
        raise ValueError(f"{operation}: key must be 1-D or 2-D array")

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """Gather inverse substitution tables in compacted/transposed core space."""
        ct = np.asarray(ct_tr, dtype=np.uint8).reshape(-1)
        keys = np.asarray(keys_tr, dtype=np.uint8)
        if keys.ndim == 1:
            keys = keys[None, :]
        self._validate_substitution_key_shape(keys, "decrypt")
        return keys[:, ct]

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """Gather forward substitution tables in compacted/transposed core space."""
        pt = np.asarray(pt_tr, dtype=np.uint8).reshape(-1)
        keys = np.asarray(keys_tr, dtype=np.uint8)
        if keys.ndim == 1:
            keys = keys[None, :]
        self._validate_substitution_key_shape(keys, "encrypt")
        return keys[:, pt]
