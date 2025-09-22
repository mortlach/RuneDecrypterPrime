# ============================================================
# rune_decrypter_prime/ciphers/generic_map_cipher.py
#   Generic map/lookup cipher with CPU/Torch parity + degeneracy candidates
# ============================================================
from __future__ import annotations
from typing import Optional, Any, Tuple
import numpy as np

from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin
from rune_decrypter_prime.ciphers.registry import register_cipher
from rune_decrypter_prime.core.keyops import AdditiveVectorOps, KeyOps, KeyCaps
from rune_decrypter_prime.backends.xp import select_backend

ArrayU8 = np.ndarray


def _as_u8(a) -> np.ndarray:
    return np.asarray(a, dtype=np.uint8, order="C")


def _as_intp(a, name: str = "idx") -> np.ndarray:
    x = np.asarray(a, dtype=np.intp, order="C").reshape(-1)
    if x.ndim != 1:
        raise ValueError(f"{name} must be 1D; got shape {x.shape}")
    return x


class KeyOpsGeneric(KeyOps):
    def __init__(self, K: int, A_key: int):
        self.K = int(K)
        self.A_key = int(A_key)
        self._ops = AdditiveVectorOps(self.K, self.A_key)
        self.caps = KeyCaps(kind="mapping", length=self.K, can_partial_score=True, can_additive_invariant=False)

    def random(self, rng: np.random.Generator) -> ArrayU8:
        return self._ops.random(rng)

    def normalize(self, key: ArrayU8) -> ArrayU8:
        return self._ops.normalize(key)

    def mutate(self, key: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        return self._ops.mutate(key, rng)

    def crossover(self, k1: ArrayU8, k2: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        return self._ops.crossover(k1, k2, rng)

    def partial_mask(self, L: int, depth: int):
        return self._ops.partial_mask(L, depth)


@register_cipher("user_map2")
@register_cipher("user_map3")
@register_cipher("lookup")
@register_cipher("generic-map")
class GenericMapCipher(CipherPipelineMixin):
    """
    Generic map cipher with degeneracy-aware inverse tables.

    cfg.spec fields used:
        kind: 'user_map2'|'user_map3'|'lookup'
        N: int (alphabet size)
        function: callable for map kinds
        table: for lookup
        degeneracy: 'forbid' | 'allow'
        resolver: 'first' | 'expand_beam' | 'random' (we implement 'first' and expose candidates for expand)
        per_pos_limit: int (cap on per-position candidates; used in LUT storage)
    """
    A: int = 29

    def __init__(self, cfg) -> None:
        super().__init__(text_transposition="fwd", key_transposition="fwd")
        self.cfg = cfg
        spec = getattr(cfg, "spec", None)
        if spec is None:
            raise ValueError("GenericMapCipher requires cfg.spec")
        self.kind = str(getattr(spec, "kind", getattr(cfg, "name", "generic-map"))).lower()
        self.A = int(getattr(spec, "N", 29))
        self.N = self.A

        # K = int(getattr(cfg, "key_length", 0) or 0)
        # if K <= 0:
        #     raise ValueError("GenericMapCipher requires cfg.key_length > 0")

        # --- period / key_length handling ------------------------------------------
        K_cfg = int(getattr(cfg, "key_length", 0) or 0)
        K = K_cfg  # final period we’ll use

        # Build mapping domain size (does not depend on period)
        A_key = self.A if self.kind != "user_map3" else self.A * self.A
        self.keyops = KeyOpsGeneric(K if K > 0 else 1, A_key)  # temp '1' if we’ll infer below

        enc = np.empty((self.A, A_key), dtype=np.uint8)
        dec_first = np.full((A_key, self.A), 255, dtype=np.uint8)

        if self.kind in ("user_map2", "user_map3"):
            # For function-based kinds we *require* an explicit period
            if K <= 0:
                raise ValueError("GenericMapCipher requires cfg.key_length > 0 for user_map2/user_map3")
            f = getattr(spec, "function", None)
            if not callable(f):
                raise ValueError(f"{self.kind} requires spec.function")
            if self.kind == "user_map2":
                for pt in range(self.A):
                    for kv in range(A_key):
                        ct = int(f(pt, kv)) % self.A
                        enc[pt, kv] = np.uint8(ct)
                        if dec_first[kv, ct] == 255:
                            dec_first[kv, ct] = np.uint8(pt)
            else:  # user_map3
                for pt in range(self.A):
                    for kv in range(A_key):
                        k1 = kv // self.A
                        k2 = kv % self.A
                        ct = int(f(pt, k1, k2)) % self.A
                        enc[pt, kv] = np.uint8(ct)
                        if dec_first[kv, ct] == 255:
                            dec_first[kv, ct] = np.uint8(pt)

        elif self.kind == "lookup":
            table = getattr(spec, "table", None)
            if table is None:
                raise ValueError("lookup requires spec.table")
            T = np.asarray(table, dtype=object)
            if T.ndim != 2 or T.shape[0] != self.A:
                raise ValueError(f"lookup table must have A rows; got shape {T.shape}, expected ({self.A}, ?)")

            # --- infer period K from the table when not provided ---
            if K <= 0:
                # We support three shapes:
                #  (A, A_key): key-value domain table (can’t infer period here)
                #  (A, K):     period-indexed → infer K from the table
                #  (A, 1):     broadcast → infer K=1
                if T.shape[1] == 1:
                    K = 1
                elif T.shape[1] != A_key:
                    # Treat any non-1, non-A_key second dimension as the period
                    K = int(T.shape[1])
                # else: T is in key-value domain; require explicit cfg.key_length

            if K <= 0:
                raise ValueError(
                    "GenericMapCipher requires cfg.key_length > 0 (or inferable from lookup table shape)"
                )

            # Now that K is known, refresh keyops with the real period if we created it with 1 above
            if self.keyops.K != K:
                self.keyops = KeyOpsGeneric(K, A_key)

            # Canonicalize to a key-value domain table T_use
            if T.shape[1] == A_key:
                T_use = T
            elif T.shape[1] == 1:
                T_use = np.broadcast_to(T, (self.A, A_key)).copy()
            elif T.shape[1] == K:
                idx = (np.arange(A_key) % K)
                T_use = T[:, idx]
            else:
                raise ValueError(
                    f"lookup table has shape {T.shape}, expected ({self.A},{A_key}) or ({self.A},{K}) or ({self.A},1)"
                )

            # Fill enc/dec_first from T_use
            for pt in range(self.A):
                for kv in range(A_key):
                    val = T_use[pt, kv]
                    if isinstance(val, (list, tuple, np.ndarray)):
                        if len(val) == 0:
                            continue
                        ct0 = int(val[0]) % self.A
                        enc[pt, kv] = np.uint8(ct0)
                        if dec_first[kv, ct0] == 255:
                            dec_first[kv, ct0] = np.uint8(pt)
                    else:
                        ct = int(val) % self.A
                        enc[pt, kv] = np.uint8(ct)
                        if dec_first[kv, ct] == 255:
                            dec_first[kv, ct] = np.uint8(pt)

        else:
            raise ValueError(f"Unknown map kind '{self.kind}'")

        requested = (getattr(cfg, "device", None) or "cpu").lower()
        dev_name, xp = select_backend(requested)
        self._xp_backend = xp.backend
        self._device_name = dev_name

        # Degeneracy policy / storage cap
        self.degeneracy = str(getattr(spec, "degeneracy", "forbid")).lower()
        self.resolver = str(getattr(spec, "resolver", "first")).lower()
        self.per_pos_limit = int(getattr(spec, "per_pos_limit", 4))
        if self.per_pos_limit <= 0:
            self.per_pos_limit = 1

        # Build mapping
        A_key = self.A if self.kind != "user_map3" else self.A * self.A
        self.keyops = KeyOpsGeneric(K, A_key)
        enc = np.empty((self.A, A_key), dtype=np.uint8)
        dec_first = np.full((A_key, self.A), 255, dtype=np.uint8)

        if self.kind in ("user_map2", "user_map3"):
            f = getattr(spec, "function", None)
            if not callable(f):
                raise ValueError(f"{self.kind} requires spec.function")
            if self.kind == "user_map2":
                for pt in range(self.A):
                    for kv in range(A_key):
                        ct = int(f(pt, kv)) % self.A
                        enc[pt, kv] = np.uint8(ct)
                        if dec_first[kv, ct] == 255:
                            dec_first[kv, ct] = np.uint8(pt)
            else:
                for pt in range(self.A):
                    for kv in range(A_key):
                        k1 = kv // self.A
                        k2 = kv % self.A
                        ct = int(f(pt, k1, k2)) % self.A
                        enc[pt, kv] = np.uint8(ct)
                        if dec_first[kv, ct] == 255:
                            dec_first[kv, ct] = np.uint8(pt)
        elif self.kind == "lookup":
            table = getattr(spec, "table", None)
            if table is None:
                raise ValueError("lookup requires spec.table")

            # Table can be:
            #   (A, A_key)  → canonical (key symbol domain)
            #   (A, K)      → period-indexed; tile columns to A_key
            #   (A, 1)      → broadcast to all key values
            T = np.asarray(table, dtype=object)
            if T.ndim != 2 or T.shape[0] != self.A:
                raise ValueError(f"lookup table must have A rows; got shape {T.shape}, expected ({self.A}, ?)")

            if T.shape[1] == A_key:
                T_use = T
            elif T.shape[1] == 1:
                T_use = np.broadcast_to(T, (self.A, A_key)).copy()
            elif T.shape[1] == K:
                # tile (A, K) across A_key columns (key value domain)
                idx = (np.arange(A_key) % K)
                T_use = T[:, idx]
            else:
                raise ValueError(
                    f"lookup table has shape {T.shape}, expected ({self.A},{A_key}) or ({self.A},{K}) or ({self.A},1)")

            # Fill enc/dec_first from T_use
            for pt in range(self.A):
                for kv in range(A_key):
                    val = T_use[pt, kv]
                    # entries may be scalar or iterable (degeneracy support)
                    if isinstance(val, (list, tuple, np.ndarray)):
                        # first observed wins for dec_first; keep scalar in enc (any valid ct)
                        if len(val) == 0:
                            continue
                        ct0 = int(val[0]) % self.A
                        enc[pt, kv] = np.uint8(ct0)
                        if dec_first[kv, ct0] == 255:
                            dec_first[kv, ct0] = np.uint8(pt)
                    else:
                        ct = int(val) % self.A
                        enc[pt, kv] = np.uint8(ct)
                        if dec_first[kv, ct] == 255:
                            dec_first[kv, ct] = np.uint8(pt)
        else:
            raise ValueError(f"Unknown map kind '{self.kind}'")

        # Replace holes with zero
        dec_first[dec_first == 255] = 0
        self._enc_np = enc
        self._dec_np = dec_first

        # Build degeneracy tables (candidate lists)
        LIMIT = int(self.per_pos_limit)
        dec_len = np.zeros((A_key, self.A), dtype=np.uint8)
        dec_list = np.zeros((A_key, self.A, LIMIT), dtype=np.uint8)
        # Loop is tiny (A <= 29); prioritizes determinism over micro-optimizations
        for kv in range(A_key):
            for ct in range(self.A):
                pts = [pt for pt in range(self.A) if enc[pt, kv] == ct]
                pts.sort()
                if not pts:
                    dec_len[kv, ct] = 0
                    if LIMIT:
                        dec_list[kv, ct, :] = 0
                else:
                    Lc = min(len(pts), LIMIT)
                    dec_len[kv, ct] = Lc
                    dec_list[kv, ct, :Lc] = np.asarray(pts[:Lc], dtype=np.uint8)
                    if Lc < LIMIT:
                        dec_list[kv, ct, Lc:] = dec_list[kv, ct, Lc-1]  # pad with last for stable values

        self._dec_len_np = dec_len
        self._dec_list_np = dec_list

        # Torch tensors if requested
        self._enc_t = None
        self._dec_t = None
        self._dec_len_t = None
        self._dec_list_t = None
        if self._xp_backend == "torch":
            import torch
            device = torch.device(self._device_name if "cuda" in self._device_name else "cpu")
            self._enc_t = torch.as_tensor(self._enc_np, device=device, dtype=torch.uint8)
            self._dec_t = torch.as_tensor(self._dec_np, device=device, dtype=torch.uint8)
            self._dec_len_t = torch.as_tensor(self._dec_len_np, device=device, dtype=torch.uint8)
            self._dec_list_t = torch.as_tensor(self._dec_list_np, device=device, dtype=torch.uint8)

    def _as_u8(self, a, name: str) -> np.ndarray:
        return _as_u8(a)

    def _as_intp(self, a, name: str) -> np.ndarray:
        return _as_intp(a, name)

    # Core kernels used by CipherPipelineMixin
    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        ct = _as_u8(ct_tr)
        keys = _as_u8(keys_tr)
        if keys.ndim == 1:
            keys = keys[None, :]
        B, K = int(keys.shape[0]), int(keys.shape[1])
        L = int(ct.size)

        if self._xp_backend == "torch":
            import torch as t
            device = self._enc_t.device  # type: ignore
            ct_t   = t.as_tensor(ct, device=device, dtype=t.uint8).reshape(-1)
            keys_t = t.as_tensor(keys, device=device, dtype=t.uint8)
            cols   = t.arange(L, device=device, dtype=t.long) % K
            ks     = keys_t[:, cols]  # (B,L)
            out    = self._dec_t[ks, ct_t]  # (B,L)
            return out.detach().cpu().numpy().astype(np.uint8, copy=False)
        else:
            cols = np.arange(L, dtype=np.int64) % K
            ks = keys[:, cols]            # (B,L)
            out = self._dec_np[ks, ct]    # (B,L)
            return out.astype(np.uint8, copy=False)

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        pt = _as_u8(pt_tr).reshape(-1) if getattr(pt_tr, "ndim", 1) == 1 else _as_u8(pt_tr)
        keys = _as_u8(keys_tr)
        if getattr(pt, "ndim", 1) == 1:
            pt = pt[None, :]
        if keys.ndim == 1:
            keys = keys[None, :]
        B, L = int(pt.shape[0]), int(pt.shape[1])
        K = int(keys.shape[1])

        if self._xp_backend == "torch":
            import torch as t
            device = self._enc_t.device  # type: ignore
            pt_t   = t.as_tensor(pt, device=device, dtype=t.uint8)
            keys_t = t.as_tensor(keys, device=device, dtype=t.uint8)
            cols   = t.arange(L, device=device, dtype=t.long) % K
            ks     = keys_t[:, cols]  # (B,L)
            out    = self._enc_t[pt_t, ks]  # (B,L)
            return out.detach().cpu().numpy().astype(np.uint8, copy=False)
        else:
            cols = np.arange(L, dtype=np.int64) % K
            ks = keys[:, cols]            # (B,L)
            if pt.ndim == 2 and pt.shape[0] == 1:
                pt = np.broadcast_to(pt, (ks.shape[0], pt.shape[1]))
            out = self._enc_np[pt, ks]    # (B,L)
            return out.astype(np.uint8, copy=False)

    # -------- Degeneracy API (used by optimizers or problem) --------
    def candidates_for(self, ct_tr: ArrayU8, keys_tr: ArrayU8, *, positions: Optional[np.ndarray] = None,
                       limit: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Return candidate plaintexts for each (batch,key,pos):
            cands: (B, Lq, Lmt) uint8
            lens:  (B, Lq)      uint8   (# of valid candidates per pos)
            invalid: (B, Lq)    bool
        positions: optional 1D indices into text; defaults to all positions [0..L-1]
        limit: optional cap <= self.per_pos_limit
        """
        ct = _as_u8(ct_tr).reshape(-1)
        keys = _as_u8(keys_tr)
        if keys.ndim == 1:
            keys = keys[None, :]
        B, K = int(keys.shape[0]), int(keys.shape[1])
        L = int(ct.size)
        if positions is None:
            pos = np.arange(L, dtype=np.int64)
        else:
            pos = _as_intp(positions, "positions")

        Lq = int(pos.size)
        Lmt = int(self.per_pos_limit if limit is None else min(int(limit), int(self.per_pos_limit)))

        # Gather kv = keys[:, pos%K]
        cols = (pos % K).astype(np.int64)
        kv = keys[:, cols]                       # (B,Lq)
        cts = ct[pos]                            # (Lq,)

        if self._xp_backend == "torch":
            import torch as t
            device = self._dec_len_t.device  # type: ignore
            kv_t  = t.as_tensor(kv, device=device, dtype=t.long)
            ct_t  = t.as_tensor(cts, device=device, dtype=t.long)
            lens  = self._dec_len_t[kv_t, ct_t]       # (B,Lq)
            lists = self._dec_list_t[kv_t, ct_t]      # (B,Lq,LIMIT)
            if Lmt < self.per_pos_limit:
                lists = lists[..., :Lmt]
            cands = lists.detach().cpu().numpy().astype(np.uint8, copy=False)
            lens  = lens.detach().cpu().numpy().astype(np.uint8, copy=False)
        else:
            lens  = self._dec_len_np[kv, cts]         # (B,Lq)
            lists = self._dec_list_np[kv, cts]        # (B,Lq,LIMIT)
            if Lmt < self.per_pos_limit:
                lists = lists[..., :Lmt]
            cands = lists.astype(np.uint8, copy=False)

        invalid = (lens == 0)
        return cands, lens, invalid
