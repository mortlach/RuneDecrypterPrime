# ============================================================
# rune_decrypter_prime/ciphers/generic_map_cipher.py
# Generic map/lookup cipher with CPU/Torch parity and degeneracy handling.
# ============================================================
from __future__ import annotations
from typing import Optional, Tuple
import numpy as np

from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin
from rune_decrypter_prime.ciphers.dev.base_keyed_cipher import KeyedCipherBase
from rune_decrypter_prime.ciphers.registry import register_cipher
from rune_decrypter_prime.backends.xp import select_backend
from rune_decrypter_prime.core.types import (
    CipherKind,
    Device,
    Direction,
    KeyOpsFamily,
    ensure_cipher_kind,
    ensure_device,
    ensure_direction,
)

ArrayU8 = np.ndarray

def _as_u8(value, name: str) -> np.ndarray:
    try:
        return np.asarray(value, dtype=np.uint8, order="C")
    except Exception as exc:
        raise TypeError(f"{name} must be array-like of uint8") from exc


@register_cipher("user_map2")
@register_cipher("user_map3")
@register_cipher("lookup")
@register_cipher("generic-map")
class GenericMapCipher(CipherPipelineMixin, KeyedCipherBase):
    """
    Generic map cipher that evaluates a per-position mapping:
      - function-based (user_map2: pt,k → ct) or (user_map3: pt,k1,k2 → ct)
      - lookup-based (table with shapes (A,A_key), (A,K), or (A,1))

    Key model
    ---------
    Vector key of period K. At text position i, the active key value is k[i % K].
    For user_map3, the key value index encodes a pair (k1,k2) in [0..A-1]^2.

    Inputs / Outputs
    ----------------
    _core_decrypt_batch:
      ct_tr  : [L] uint8
      keys_tr: [B,K] uint8   (key values or encoded pairs)
      returns: [B,L] uint8 plaintexts (first-inverse policy for degeneracy)

    Notes
    -----
    - Does not construct KeyOps; Problem attaches it with `keyops_family="vector"`.
    - Degeneracy in lookup tables: decoder uses the first-seen inverse deterministically.
    """
    keyops_family: KeyOpsFamily = KeyOpsFamily.VECTOR
    A: int = 29

    def __init__(self, cfg) -> None:
        text_dir = ensure_direction(getattr(cfg, "text_transposition", Direction.LTR))
        key_dir = ensure_direction(getattr(cfg, "key_transposition", Direction.LTR))
        super().__init__(
            text_transposition=text_dir.value,
            key_transposition=key_dir.value,
            initial_text_permutation_indices=getattr(cfg, "initial_text_permutation_indices", None),
        )
        self.cfg = cfg
        self.text_direction = text_dir
        self.key_direction = key_dir
        spec = getattr(cfg, "spec", None)
        if spec is None:
            raise ValueError("GenericMapCipher requires cfg.spec")
        raw_kind = getattr(spec, "kind", getattr(cfg, "name", CipherKind.LOOKUP.value))
        kind_key = str(raw_kind).strip().lower()
        if kind_key == "generic-map":
            kind_key = CipherKind.LOOKUP.value
        self.kind: CipherKind = ensure_cipher_kind(kind_key)
        self.kind_value = self.kind.value
        self.A = int(getattr(spec, "N", 29))
        self.N = self.A

        # resolve period K (required for function kinds; inferable for lookup)
        K_cfg = int(getattr(cfg, "key_length", 0) or 0)
        K = K_cfg

        A_key = self.A if self.kind is not CipherKind.USER_MAP3 else self.A * self.A  # domain size for key value index

        # build enc/dec tables (NumPy arrays)
        enc = np.empty((self.A, A_key), dtype=np.uint8)
        dec_first = np.full((A_key, self.A), 255, dtype=np.uint8)

        if self.kind in (CipherKind.USER_MAP2, CipherKind.USER_MAP3):
            if K <= 0:
                raise ValueError("GenericMapCipher requires cfg.key_length > 0 for user_map2/user_map3")
            f = getattr(spec, "function", None)
            if not callable(f):
                raise ValueError(f"{self.kind.value} requires spec.function")
            if self.kind is CipherKind.USER_MAP2:
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

        elif self.kind is CipherKind.LOOKUP:
            table = getattr(spec, "table", None)
            if table is None:
                raise ValueError("lookup requires spec.table")
            T = np.asarray(table, dtype=object)
            if T.ndim != 2 or T.shape[0] != self.A:
                raise ValueError(f"lookup table must have A rows; got shape {T.shape}, expected ({self.A}, ?)")

            # infer K if not provided
            if K <= 0:
                if T.shape[1] == 1:
                    K = 1
                elif T.shape[1] != A_key:
                    K = int(T.shape[1])  # treat non-1, non-A_key as period
                # else: table is in key-value domain; require explicit K
            if K <= 0:
                raise ValueError("GenericMapCipher requires cfg.key_length > 0 (or inferable from lookup shape)")

            # canonicalize to key-value domain
            if T.shape[1] == A_key:
                T_use = T
            elif T.shape[1] == 1:
                T_use = np.broadcast_to(T, (self.A, A_key)).copy()
            elif T.shape[1] == K:
                idx = (np.arange(A_key) % K)
                T_use = T[:, idx]
            else:
                raise ValueError(
                    f"lookup table shape {T.shape}; expected ({self.A},{A_key}) or ({self.A},{K}) or ({self.A},1)"
                )

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
            raise ValueError(f"Unknown map kind '{self.kind.value}'")

        dec_first[dec_first == 255] = 0
        self._enc_np = enc
        self._dec_np = dec_first

        # backend switch (CPU default)
        requested = ensure_device(getattr(cfg, "device", Device.CPU))
        dev_name, xp = select_backend(requested.value)
        self.device = requested
        self._xp_backend = xp.backend
        self._device_name = dev_name
        self._enc_t = self._dec_t = None
        if self._xp_backend == "torch":
            import torch
            device = torch.device(self._device_name if "cuda" in self._device_name else "cpu")
            self._enc_t = torch.as_tensor(self._enc_np, device=device, dtype=torch.uint8)
            self._dec_t = torch.as_tensor(self._dec_np, device=device, dtype=torch.uint8)

        self.key_length = int(K)  # expose K for Problem/KeyOps

    # ---- core kernels used by CipherPipelineMixin ----

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """
        Decrypt in core space using decoder table:
          p = dec_first[key_value, c]
        where key_value = keys[:, pos % K].

        Shapes:
          ct_tr  : [L]    uint8
          keys_tr: [B,K]  uint8
          return : [B,L]  uint8
        """
        ct = np.asarray(ct_tr, dtype=np.uint8).reshape(-1)
        keys  = np.asarray(keys_tr, dtype=np.uint8)
        if keys.ndim == 1:
            keys = keys[None, :]
        B, K = int(keys.shape[0]), int(keys.shape[1])
        L = int(ct.size)

        if self._xp_backend == "torch":
            import torch as t
            device = self._enc_t.device  # type: ignore
            ct_t   = t.as_tensor(ct, device=device, dtype=t.long).reshape(-1)
            keys_t = t.as_tensor(keys, device=device, dtype=t.long)
            cols   = t.arange(L, device=device, dtype=t.long) % K
            kv     = keys_t[:, cols]                                     # (B,L)
            out    = self._dec_t[kv, ct_t]                                # (B,L)
            return out.detach().cpu().numpy().astype(np.uint8, copy=False)

        cols = np.arange(L, dtype=np.int64) % K
        kv = keys[:, cols]                                                # (B,L)
        out = self._dec_np[kv, ct]                                        # (B,L)
        return out.astype(np.uint8, copy=False)

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """
        Encrypt in core space using encoder table:
          c = enc[p, key_value]
        """
        pt = _as_u8(pt_tr,"pt")
        keys = _as_u8(keys_tr,"keys")
        if keys.ndim == 1:
            keys = keys[None, :]
        B, K = int(keys.shape[0]), int(keys.shape[1])
        L = int(pt.shape[0])

        if self._xp_backend == "torch":
            import torch as t
            device = self._enc_t.device  # type: ignore
            pt_t   = t.as_tensor(pt, device=device, dtype=t.long).reshape(-1)
            keys_t = t.as_tensor(keys, device=device, dtype=t.long)
            cols   = t.arange(L, device=device, dtype=t.long) % K
            kv     = keys_t[:, cols]                                     # (B,L)
            out    = self._enc_t[pt_t, kv]                                # (B,L)
            return out.detach().cpu().numpy().astype(np.uint8, copy=False)

        cols = np.arange(L, dtype=np.int64) % K
        kv = keys[:, cols]
        out = self._enc_np[pt, kv]
        return out.astype(np.uint8, copy=False)

    # optional degeneracy API (kept for compatibility)
    def candidates_for(self, ct_tr: ArrayU8, keys_tr: ArrayU8, *, positions: Optional[np.ndarray] = None,
                       limit: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Candidates per position (first LMT plaintext indices per (key_value, ct)).
        Returns:
            cands  : (B, Lq, Lmt) uint8
            lens   : (B, Lq)      uint8
            invalid: (B, Lq)      bool
        """
        LIMIT = 4 if limit is None else int(limit)
        ct = _as_u8(ct_tr,"ct").reshape(-1)
        keys = _as_u8(keys_tr,"key")
        if keys.ndim == 1:
            keys = keys[None, :]
        B, K = int(keys.shape[0]), int(keys.shape[1])
        L = int(ct.size)
        pos = np.arange(L, dtype=np.int64) if positions is None else np.asarray(positions, dtype=np.int64).reshape(-1)
        Lq = int(pos.size)
        cols = (pos % K).astype(np.int64)
        kv = keys[:, cols]  # (B,Lq)

        # build short lists using enc/dec tables
        lens = np.zeros((B, Lq), dtype=np.uint8)
        cands = np.zeros((B, Lq, LIMIT), dtype=np.uint8)
        for b in range(B):
            for i, p in enumerate(pos):
                kl = int(kv[b, i])
                ct_sym = int(ct[p])
                pts = np.flatnonzero(self._enc_np[:, kl] == ct_sym)
                if pts.size:
                    Lm = min(int(pts.size), LIMIT)
                    lens[b, i] = Lm
                    cands[b, i, :Lm] = pts[:Lm].astype(np.uint8, copy=False)
                    if Lm < LIMIT:
                        cands[b, i, Lm:] = cands[b, i, Lm-1]
                else:
                    lens[b, i] = 0
                    if LIMIT:
                        cands[b, i, :] = 0
        invalid = (lens == 0)
        return cands, lens, invalid
