# -*- coding: utf-8 -*-
from __future__ import annotations
import numpy as np
from typing import Optional, Tuple

# todo move to own file
from rune_decrypter_prime.keyops import PermutationKeyOps, PermutationKeyConfig
from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin, ArrayU8


class PlaySquareCipher(CipherPipelineMixin):
    """
    Play-square (Playfair-style) cipher implemented as a 5×5 grid (25 symbols)
    while remaining fully compatible with the 29-rune pipeline.

    How we bridge 29 → 25
    ---------------------
    We define a deterministic REDUCTION mapping that merges four low-utility
    runes into canonical representatives. Internally we work in an alphabet
    of size 25 (index 0..24). Decrypt/encrypt return 29-space indices that
    live inside the representative subset, so scorers (A=29) remain happy.

    Reduction (example policy)
    --------------------------
      - Merge J→I (ᛂ → ᛁ)
      - Merge X→S (ᛉ → ᛋ)
      - Merge AE→A (ᚫ → ᚪ)
      - Merge IO→I (ᛡ → ᛁ)

    You can tweak these mappings if you prefer different canonical merges.

    Key
    ---
    key_length=25, a permutation of 0..24 filling the 5×5 square row-wise.

    Rules (classical Playfair)
    --------------------------
      Encrypt:
        - Pair up (digraph). If a pair has same letter, insert filler (default F=ᚠ index 0) between them.
        - Same row → shift right
        - Same col → shift down
        - Rectangle → swap columns (take corners)
      Decrypt: inverse operations (left/up/rectangle)

    Filler
    ------
    cfg.filler_idx29 (default: 0) used ONLY when we split double letters within a digraph.
    Odd trailing letter is paired with filler.

    Optimizers
    ----------
    self.keyops = PermutationOps(25)
    """
    A29 = 29
    A25 = 25
    S = 5  # grid size

    # ---- 29 -> 25 reduction (indices) ----
    # map any 29-space index to a 25-space representative
    _REDUCE_29_TO_25 = np.arange(A29, dtype=np.int64)
    # representatives: keep many as-is, remap 4 symbols into representatives
    # these positions (by index) depend on  Runeglish mapping.
    # Based on user's canonical ordering: indices (11=J), (14=X), (25=AE), (27=IO)
    _REDUCE_29_TO_25[11] = 10   # J→I
    _REDUCE_29_TO_25[14] = 15   # X→S
    _REDUCE_29_TO_25[25] = 24   # AE→A (careful: adjust to some 25-space index later)
    _REDUCE_29_TO_25[27] = 10   # IO→I

    #  build a compact 25-space relabel below (in __init__) that maps survivors
    # to 0..24 and creates a reverse projection back into 29-space.

    def __init__(self, cfg, *, text_transposition="ltr", key_transposition="ltr"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", text_transposition),
            key_transposition=getattr(cfg, "key_transposition", key_transposition),
        )
        self.cfg = cfg
        self.keyops = PermutationKeyOps(PermutationKeyConfig(K=self.A25))
        # Build the 29->25 compact relabel & 25->29 inverse projection
        # Step 1: choose canonical representatives set R ⊂ [0..28]
        rep = self._choose_representatives()
        # rep is sorted array of length 25 with unique 29-space indices
        self.rep25_in_29 = rep.astype(np.int64)         # (25,)
        inv29 = -np.ones(self.A29, dtype=np.int64)      # map 29→(0..24) or -1
        inv29[self.rep25_in_29] = np.arange(self.A25, dtype=np.int64)
        self.inv29_to_25 = inv29                        # (29,) entries in 0..24 or -1

        # filler (in 29-space) & its 25-space projection
        filler_29 = int(getattr(cfg, "filler_idx29", 0))
        if not (0 <= filler_29 < self.A29):
            filler_29 = 0
        self.filler_29 = filler_29
        # project to 25 (if non-representative, it lands on the representative bucket)
        self.filler_25 = int(self.inv29_to_25[self._reduce29(filler_29)])

        # --- keyops ---
        req_len = getattr(cfg, "key_length", None)
        if req_len not in (None, self.A25):
            raise ValueError(f"PlaySquare requires key_length={self.A25}, got {req_len}")
        self.keyops = PermutationOps(self.A25)

    # ------------------- reduction & projection -------------------

    @classmethod
    def _reduce29(cls, idx29: int) -> int:
        """Apply pre-reduction hint (coalescing), still in 29-space indices."""
        return int(cls._REDUCE_29_TO_25[idx29])

    def _to25(self, arr29: np.ndarray) -> np.ndarray:
        """Map a 29-space stream to 25-space indices (0..24)."""
        # First coalesce: 29→29 (merge)
        tmp29 = self._REDUCE_29_TO_25[arr29]
        # Then project: survivors → 0..24
        out25 = self.inv29_to_25[tmp29]
        # All entries should be valid (since inv on reps is defined)
        return out25.astype(np.int64, copy=False)

    def _to29(self, arr25: np.ndarray) -> np.ndarray:
        """Map a 25-space stream back to 29-space via representatives."""
        reps = self.rep25_in_29
        return reps[arr25.astype(np.int64, copy=False)].astype(np.uint8, copy=False)

    def _choose_representatives(self) -> np.ndarray:
        """
        Build the set of 25 representatives in 29-space deterministically.

        Policy:
        - Start with 0..28.
        - Apply the merge preferences: J→I, X→S, AE→A, IO→I by dropping (J, X, AE, IO).
        - Keep the remaining 25 symbols in order.
        """
        drops = {11, 14, 25, 27}  # J, X, AE, IO (indices in 29-space)
        keep = [i for i in range(self.A29) if i not in drops]
        if len(keep) != self.A25:
            raise RuntimeError("PlaySquare representative selection produced wrong count.")
        return np.asarray(keep, dtype=np.int64)

    # ------------------- grid helpers -------------------

    @staticmethod
    def _grid_pos(idx25: np.ndarray, S: int) -> Tuple[np.ndarray, np.ndarray]:
        """Given 25-space symbols (0..24), get rows/cols."""
        r = (idx25 // S).astype(np.int64, copy=False)
        c = (idx25 % S).astype(np.int64, copy=False)
        return r, c

    @staticmethod
    def _from_grid(r: np.ndarray, c: np.ndarray, S: int) -> np.ndarray:
        return (r * S + c).astype(np.int64, copy=False)

    # ------------------- pair builders -------------------

    def _make_pairs_encrypt(self, x25: np.ndarray) -> np.ndarray:
        """
        Build digraph pairs for ENCRYPT:
        - Split doubles by inserting filler between identical letters.
        - If odd final, append filler.
        Returns an array length 2*M.
        """
        filler = self.filler_25
        buf = np.empty(x25.size * 2 + 2, dtype=np.int64)  # generous
        w = 0
        i = 0
        L = int(x25.size)
        while i < L:
            a = int(x25[i])
            if i + 1 < L:
                b = int(x25[i + 1])
                if a == b:
                    # insert filler
                    buf[w] = a
                    buf[w + 1] = filler
                    w += 2
                    i += 1
                else:
                    buf[w] = a
                    buf[w + 1] = b
                    w += 2
                    i += 2
            else:
                buf[w] = a
                buf[w + 1] = filler
                w += 2
                i += 1
        return buf[:w]

    def _make_pairs_decrypt(self, x25: np.ndarray) -> np.ndarray:
        """For DECRYPT we just ensure even length (pad filler if odd)."""
        if (x25.size & 1) == 0:
            return x25.astype(np.int64, copy=False)
        out = np.empty(x25.size + 1, dtype=np.int64)
        out[:-1] = x25
        out[-1] = self.filler_25
        return out

    # ------------------- core transforms -------------------

    def _enc_pairs(self, pairs25: np.ndarray, key25: np.ndarray) -> np.ndarray:
        """
        Apply Playfair encrypt rules to an even-length 25-stream using key square.
        """
        S = self.S
        # build lookup: symbol (0..24) → (row,col)
        inv = np.empty(self.A25, dtype=np.int64)
        inv[key25] = np.arange(self.A25, dtype=np.int64)
        r = (inv // S).astype(np.int64)
        c = (inv % S).astype(np.int64)

        out = np.empty_like(pairs25)
        for i in range(0, pairs25.size, 2):
            a = int(pairs25[i])
            b = int(pairs25[i + 1])
            ra, ca = r[a], c[a]
            rb, cb = r[b], c[b]
            if ra == rb:
                # same row: shift right
                na = ra * S + ((ca + 1) % S)
                nb = rb * S + ((cb + 1) % S)
            elif ca == cb:
                # same column: shift down
                na = ((ra + 1) % S) * S + ca
                nb = ((rb + 1) % S) * S + cb
            else:
                # rectangle: swap columns
                na = ra * S + cb
                nb = rb * S + ca
            out[i] = key25[na]
            out[i + 1] = key25[nb]
        return out

    def _dec_pairs(self, pairs25: np.ndarray, key25: np.ndarray) -> np.ndarray:
        """
        Apply Playfair decrypt rules to an even-length 25-stream using key square.
        """
        S = self.S
        inv = np.empty(self.A25, dtype=np.int64)
        inv[key25] = np.arange(self.A25, dtype=np.int64)
        r = (inv // S).astype(np.int64)
        c = (inv % S).astype(np.int64)

        out = np.empty_like(pairs25)
        for i in range(0, pairs25.size, 2):
            a = int(pairs25[i])
            b = int(pairs25[i + 1])
            ra, ca = r[a], c[a]
            rb, cb = r[b], c[b]
            if ra == rb:
                # same row: shift LEFT
                na = ra * S + ((ca - 1) % S)
                nb = rb * S + ((cb - 1) % S)
            elif ca == cb:
                # same column: shift UP
                na = ((ra - 1) % S) * S + ca
                nb = ((rb - 1) % S) * S + cb
            else:
                # rectangle: swap columns
                na = ra * S + cb
                nb = rb * S + ca
            out[i] = key25[na]
            out[i + 1] = key25[nb]
        return out

    # ------------------- batch API -------------------

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        x = pt_tr
        if x.ndim == 1:
            x = x[None, :]
        Bx, L = x.shape

        k = keys_tr
        if k.ndim == 1:
            k = k[None, :]
        Bk, K = k.shape
        if K != self.A25:
            raise ValueError(f"PlaySquare requires key length {self.A25}")

        B = max(Bx, Bk)
        out = np.empty((B, L if (L % 2 == 0) else L + 1), dtype=np.uint8)

        for b in range(B):
            pt29 = x[b % Bx]
            key25 = self.keyops.normalize(k[b % Bk]).astype(np.int64, copy=False)
            # project to 25-space, build pairs (split doubles + pad)
            pt25 = self._to25(pt29)
            pairs = self._make_pairs_encrypt(pt25)
            enc25 = self._enc_pairs(pairs, key25)
            ct29 = self._to29(enc25)
            # fit to row
            if ct29.size != out.shape[1]:
                tmp = np.empty(out.shape[1], dtype=np.uint8)
                n = min(tmp.size, ct29.size)
                tmp[:n] = ct29[:n]
                if n < tmp.size:
                    tmp[n:] = 0
                out[b] = tmp
            else:
                out[b] = ct29
        return out

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        x = ct_tr
        if x.ndim == 1:
            x = x[None, :]
        Bx, L = x.shape

        k = keys_tr
        if k.ndim == 1:
            k = k[None, :]
        Bk, K = k.shape
        if K != self.A25:
            raise ValueError(f"PlaySquare requires key length {self.A25}")

        B = max(Bx, Bk)
        out = np.empty((B, L if (L % 2 == 0) else L + 1), dtype=np.uint8)

        for b in range(B):
            ct29 = x[b % Bx]
            key25 = self.keyops.normalize(k[b % Bk]).astype(np.int64, copy=False)
            ct25 = self._to25(ct29)
            pairs = self._make_pairs_decrypt(ct25)
            dec25 = self._dec_pairs(pairs, key25)
            pt29 = self._to29(dec25)
            # fit
            if pt29.size != out.shape[1]:
                tmp = np.empty(out.shape[1], dtype=np.uint8)
                n = min(tmp.size, pt29.size)
                tmp[:n] = pt29[:n]
                if n < tmp.size:
                    tmp[n:] = 0
                out[b] = tmp
            else:
                out[b] = pt29
        return out
