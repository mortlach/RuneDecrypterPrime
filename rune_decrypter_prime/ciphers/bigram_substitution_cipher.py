# -*- coding: utf-8 -*-
from __future__ import annotations
import numpy as np
from typing import Iterable, Optional, Sequence, Tuple, Dict, List

from rune_decrypter_prime.keyops.permutation_ops import PermutationOps
from .pipeline import CipherPipelineMixin, ArrayU8


class BigramSubstitutionCipher(CipherPipelineMixin):
    """
    Generic BIGRAM substitution over the 29-rune alphabet.

    Key space
    ---------
    A = 29 symbols → A^2 = 841 bigrams. The cipher key is a PERMUTATION of 0..840.
    We encode bigram (x,y) as b = x*A + y.

      Encrypt:   ct_bigram = P[ pt_bigram ]
      Decrypt:   pt_bigram = P^{-1}[ ct_bigram ]

    Text length
    -----------
    We operate over pairs. Odd trailing symbol (if any) is passed through unchanged.
    (That mirrors a common classical default; if you prefer padding, set cfg.pad_value.)

    Optimizers
    ----------
    self.keyops = PermutationOps(841)  # supports random/mutate/crossover etc.

    Crib seeding (optional)
    -----------------------
    Use the helper `seed_key_from_crib(ct, crib_idx)` to create a starting key
    consistent with placing the CRIB (plaintext) onto CT at some offset. You can
    pass this seed into GA via OptimizerConfig(test_key=seed.tolist()) or by
    adding it to the initial population.
    """
    A = 29

    def __init__(self, cfg, *, text_transposition: str = "fwd", key_transposition: str = "fwd"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", text_transposition),
            key_transposition=getattr(cfg, "key_transposition", key_transposition),
        )
        self.cfg = cfg

        # --- keyops for GA/SA/Beam ---
        K = self.A * self.A  # 841
        req_len = getattr(cfg, "key_length", None)
        if req_len not in (None, K):
            raise ValueError(f"BigramSubstitution requires key_length={K} (got {req_len})")
        self.keyops = PermutationOps(K)

        # Optional: if cfg.pad_value is provided, we’ll use it to pad an odd-length PT during encrypt
        self._pad_value: Optional[int] = getattr(cfg, "pad_value", None)

    # ------------------------- helpers -------------------------

    @staticmethod
    def _pairs_to_codes(x: np.ndarray, A: int) -> Tuple[np.ndarray, Optional[int]]:
        """
        Convert a 1D stream x (uint8 in [0..A-1]) into bigram codes in [0..A^2-1].
        Return (codes, trailing) where trailing is the last odd symbol (or None).
        """
        L = int(x.size)
        if L == 0:
            return np.empty(0, dtype=np.int64), None
        even = (L // 2) * 2
        x2 = x[:even].astype(np.int64, copy=False).reshape(-1, 2)
        codes = x2[:, 0] * A + x2[:, 1]
        trailing = int(x[-1]) if (L & 1) else None
        return codes, trailing

    @staticmethod
    def _codes_to_pairs(codes: np.ndarray, A: int, trailing: Optional[int]) -> np.ndarray:
        """
        Inverse of _pairs_to_codes: expand bigram codes back to a 1D stream (append trailing if any).
        """
        if codes.size == 0:
            if trailing is None:
                return np.empty(0, dtype=np.uint8)
            return np.asarray([trailing], dtype=np.uint8)

        c = codes.astype(np.int64, copy=False).reshape(-1)
        left = (c // A).astype(np.uint8, copy=False)
        right = (c % A).astype(np.uint8, copy=False)
        out = np.empty(left.size * 2 + (1 if trailing is not None else 0), dtype=np.uint8)
        out[0::2] = left
        out[1::2] = right
        if trailing is not None:
            out[-1] = np.uint8(trailing)
        return out

    # ------------------------- batch core -------------------------

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """
        pt_tr: (L,)   or (B,L)
        keys_tr: (841,) or (B,841) permutation vectors
        returns: (B,L)
        """
        x = pt_tr
        if x.ndim == 1:
            x = x[None, :]
        B_text, L = x.shape

        keys = keys_tr
        if keys.ndim == 1:
            keys = keys[None, :]
        B_keys, K = keys.shape
        if K != self.A * self.A:
            raise ValueError(f"BigramSubstitution: key length must be {self.A*self.A}, got {K}")

        B = max(B_text, B_keys)
        out = np.empty((B, L), dtype=np.uint8)

        for b in range(B):
            pt = x[b % B_text]
            key = keys[b % B_keys].astype(np.int64, copy=False)

            # If odd length and pad_value is set, pad on encrypt
            trailing_enc = None
            if (pt.size & 1) and (self._pad_value is not None):
                pt = np.concatenate([pt, np.asarray([self._pad_value], dtype=np.uint8)], axis=0)

            codes, trailing = self._pairs_to_codes(pt, self.A)
            y_codes = key[codes]  # apply permutation P
            ct = self._codes_to_pairs(y_codes, self.A, trailing)

            # If we padded, length grew by 1; fit to out row size or trim/pad
            if ct.size != L:
                # Make sure we fit the preallocated row
                if ct.size > L:
                    out[b, :] = ct[:L]
                else:
                    tmp = np.empty(L, dtype=np.uint8)
                    tmp[:ct.size] = ct
                    tmp[ct.size:] = 0
                    out[b, :] = tmp
            else:
                out[b, :] = ct

        return out

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """
        ct_tr: (L,)   or (B,L)
        keys_tr: (841,) or (B,841) permutation vectors
        returns: (B,L)
        """
        x = ct_tr
        if x.ndim == 1:
            x = x[None, :]
        B_text, L = x.shape

        keys = keys_tr
        if keys.ndim == 1:
            keys = keys[None, :]
        B_keys, K = keys.shape
        if K != self.A * self.A:
            raise ValueError(f"BigramSubstitution: key length must be {self.A*self.A}, got {K}")

        B = max(B_text, B_keys)
        out = np.empty((B, L), dtype=np.uint8)

        # Build inverse permutations in a batch-friendly way
        inv_keys = np.empty_like(keys)
        # vectorised inverse: for each row r, inv[key[r]] = arange
        ar = np.arange(self.A * self.A, dtype=np.int64)
        for r in range(keys.shape[0]):
            inv = inv_keys[r]
            k = keys[r].astype(np.int64, copy=False)
            inv[k] = ar

        for b in range(B):
            ct = x[b % B_text]
            inv = inv_keys[b % B_keys].astype(np.int64, copy=False)

            codes, trailing = self._pairs_to_codes(ct, self.A)
            y_codes = inv[codes]  # apply P^{-1}
            pt = self._codes_to_pairs(y_codes, self.A, trailing)
            # Fit
            if pt.size != L:
                if pt.size > L:
                    out[b, :] = pt[:L]
                else:
                    tmp = np.empty(L, dtype=np.uint8)
                    tmp[:pt.size] = pt
                    tmp[pt.size:] = 0
                    out[b, :] = tmp
            else:
                out[b, :] = pt

        return out

    # ------------------------- crib seeding helper -------------------------

    @classmethod
    def seed_key_from_crib(
        cls,
        ct: Sequence[int],
        crib_idx: Sequence[int],
        *,
        offset: Optional[int] = None,
        A: int = 29,
        default_random: Optional[np.random.Generator] = None,
    ) -> np.ndarray:
        """
        Build a seed permutation consistent with placing the CRIB (plaintext indices)
        onto the ciphertext at some offset (if None, we scan all possible).

        Strategy
        --------
        - Convert ct and crib into bigram codes (lengths Lc2, Lp2).
        - For each viable offset t s.t. ct2[t + i] aligns with crib2[i], we
          set mapping ct2[t+i] -> crib2[i] IN THE PERMUTATION.
        - Finally, fill any unmapped entries with a random derangement of the leftovers.

        Returns
        -------
        key: np.ndarray shape (A*A,) — a VALID permutation vector.

        Notes
        -----
        - If multiple offsets are viable, the first with the largest number of
          non-conflicting constraints is used.
        - This is a helper only; pass the result to GA's initial population
          (e.g., OptimizerConfig params: {"test_key": key.tolist()}) or add it
          into your population initializer.
        """
        rng = default_random or np.random.default_rng()
        ct_arr = np.asarray(list(ct), dtype=np.uint8).reshape(-1)
        crib_arr = np.asarray(list(crib_idx), dtype=np.uint8).reshape(-1)

        # codes
        ct_codes, _ = cls._pairs_to_codes(ct_arr, A)
        cr_codes, trailing_cr = cls._pairs_to_codes(crib_arr, A)
        if cr_codes.size == 0:
            # Degenerate crib → just random key
            return rng.permutation(A * A).astype(np.int64)

        Lc2 = ct_codes.size
        Lp2 = cr_codes.size
        if Lp2 > Lc2:
            # Crib longer than CT — fall back to random
            return rng.permutation(A * A).astype(np.int64)

        # Choose offset
        offsets: Iterable[int]
        if offset is None:
            offsets = range(0, Lc2 - Lp2 + 1)
        else:
            if not (0 <= offset <= Lc2 - Lp2):
                return rng.permutation(A * A).astype(np.int64)
            offsets = (offset,)

        best_key = None
        best_hits = -1

        for t in offsets:
            mapping: Dict[int, int] = {}
            ok = True
            hits = 0
            for i in range(Lp2):
                c = int(ct_codes[t + i])
                p = int(cr_codes[i])
                prev = mapping.get(c, None)
                if prev is None:
                    mapping[c] = p
                    hits += 1
                elif prev != p:
                    ok = False
                    break
            if not ok:
                continue

            # Build permutation consistent with `mapping`
            A2 = A * A
            key = np.full(A2, -1, dtype=np.int64)
            used_targets = np.zeros(A2, dtype=bool)
            for src, dst in mapping.items():
                key[src] = dst
                used_targets[dst] = True

            # Remaining slots: fill with a random permutation of remaining targets
            src_left = np.flatnonzero(key < 0)
            tgt_left = np.flatnonzero(~used_targets)
            rng.shuffle(tgt_left)
            key[src_left] = tgt_left
            # Sanity: permutation?
            if np.unique(key).size != A2:
                # extremely unlikely — resample
                key = rng.permutation(A2).astype(np.int64)

            if hits > best_hits:
                best_hits = hits
                best_key = key
                if offset is not None:
                    break  # fixed offset: good enough

        if best_key is None:
            return rng.permutation(A * A).astype(np.int64)
        return best_key
