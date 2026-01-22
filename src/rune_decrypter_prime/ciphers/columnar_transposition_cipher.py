# ============================================================
# rune_decrypter_prime/ciphers/columnar_transposition_cipher.py
# Columnar Transposition Cipher (row-fill, column-read; pipeline-integrated).
# ============================================================
from __future__ import annotations
import numpy as np

from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin, ArrayU8
from rune_decrypter_prime.ciphers.dev.base_keyed_cipher import KeyedCipherBase
from rune_decrypter_prime.ciphers.registry import register_cipher
from rune_decrypter_prime.core.types import Direction, KeyOpsFamily, ensure_direction

@register_cipher("columnar")
class ColumnarTranspositionCipher(CipherPipelineMixin, KeyedCipherBase):
    """
    Columnar transposition with a permutation key of length K.

    Key model
    ---------
    Permutation key of length K on columns [0..K-1]. Ciphertext is read column-wise
    according to the permutation order; plaintext is reconstructed by row-wise read.

    Inputs / Outputs
    ----------------
    _core_decrypt_batch:
      ct_tr  : [L] uint8  (transposed/core order)
      keys_tr: [B,K] uint8 (each row is a permutation of 0..K-1)
      returns: [B,L] uint8 plaintexts

    Notes
    -----
    - Does not normalize keys; assumes valid permutations in decrypt path.
    - Problem attaches KeyOps based on `keyops_family="perm"` and `key_length`.


    Pipeline contract:
      - The pipeline hands us text/key in transposed core space.
      - Keys are **forward permutations** of {0..K-1}; decryption reconstructs
        row-fill / column-read order.
      - Uses `_core_decrypt_batch` / `_core_encrypt_batch` only (no public override).

    KeyOps:
      - family: "perm"
      - length: K (from cfg or cipher.key_length)

    """
    name: str = "columnar"
    keyops_family: KeyOpsFamily = KeyOpsFamily.PERMUTATION
    mod_keys: bool = False

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
        key_len = getattr(cfg, "key_length", None)
        if not key_len or key_len <= 0:
            key_len = getattr(cfg, "key_len", None)
        if (not key_len or key_len <= 0) and hasattr(cfg, "extra"):
            extra = getattr(cfg, "extra", None) or {}
            key_len = extra.get("key_length") or extra.get("key_len")
        if not key_len or key_len <= 0:
            raise ValueError("Columnar requires positive key_length in cfg")
        self.key_length = int(key_len)
        if self.key_length > 255:
            raise ValueError("Columnar requires key_length <= 255 (uint8 key limit)")

        # optional legacy interruptors (kept for parity)
        intr_exact = getattr(cfg, "interruptors_exact", None)
        intr_legacy = getattr(cfg, "interruptors", None)
        chosen = intr_exact if intr_exact is not None else intr_legacy
        self._default_interrupt_idx = (
            np.asarray(chosen, dtype=np.intp) if chosen is not None else None
        )

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """
        Batch decryption for [B,K] permutation keys.

        Implementation detail:
        1) compute column lengths for a rectangle with K columns and ceil(L/K) rows;
        2) slice ciphertext into columns using the physical column indices in the order given by the key permutation;
        3) reconstruct plaintext by interleaving rows.
        """
        # AFTER
        ct = self._as_u8(ct_tr, name="ct").reshape(-1)
        keys = self._as_u8(keys_tr, name="keys")
        if keys.ndim == 1:
            keys = keys[None, :]
        B, K = keys.shape
        L = int(ct.size)
        if B == 0:
            return np.empty((0, L), dtype=np.uint8)
        # vectorized validity check
        if not (
                keys.dtype.kind in "patche_old_ui" and
                keys.min() >= 0 and keys.max() < K and
                (np.apply_along_axis(lambda r: np.unique(r).size, 1, keys) == K).all()
        ):
            bad = keys[0]  # sample
            raise ValueError(
                f"[columnar] invalid permutation key of length {K}; "
                f"min={keys.min()}, max={keys.max()}, uniq_first={np.unique(bad).size}"
            )

        # precompute column lengths
        rows = (L + K - 1) // K  # ceil(L/K)
        rem = L % K
        # lengths by physical column index (0..K-1)
        col_lens = np.full(K, rows - 1, dtype=np.int64)
        if rem == 0:
            col_lens[:] = rows
        else:
            col_lens[:rem] = rows

        # Vectorised reconstruction across the entire batch.
        # Build row/col addresses for row-wise interleave once (length L)
        row_ids = np.arange(rows, dtype=np.int64)[:, None]
        present = row_ids < col_lens[None, :]
        R, C = np.where(present)  # shapes (L,), (L,)

        # For each key row, compute offsets per read-order position, then scatter to physical columns
        keys_i64 = keys.astype(np.int64, copy=False)
        col_lens_perm = col_lens[keys_i64]  # (B, K)
        off_ro = np.concatenate(
            [np.zeros((B, 1), dtype=np.int64), np.cumsum(col_lens_perm[:, :-1], axis=1)], axis=1
        )  # (B, K)
        off_phys = np.empty_like(off_ro)
        idx_rows = np.arange(B)[:, None]
        off_phys[idx_rows, keys_i64] = off_ro  # scatter read-order offsets to physical columns

        # Gather ciphertext indices for each (row, col) destination and assemble
        take = off_phys[:, C] + R[None, :]
        out = ct.take(take)  # (B, L)
        return out.astype(np.uint8, copy=False)

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """
        Batch encryption mirrors the decrypt pipeline: arrange plaintext row-wise
        and emit ciphertext by reading columns in the permutation order.
        """
        pt = self._as_u8(pt_tr, name="pt").reshape(-1)
        keys = self._as_u8(keys_tr, name="keys")
        if keys.ndim == 1:
            keys = keys[None, :]
        B, K = keys.shape
        L = int(pt.size)

        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            perm = keys[b].astype(np.int64, copy=False)
            if (
                perm.size != K
                or perm.min() < 0
                or perm.max() >= K
                or np.unique(perm).size != K
            ):
                raise ValueError(f"[columnar] Invalid permutation key (K={K}): {perm}")

            columns = [pt[c::K].astype(np.uint8, copy=False) for c in range(K)]
            ct_parts = [columns[c] for c in perm]
            out[b] = np.concatenate(ct_parts, axis=0)[:L]
        return out

