# ============================================================
# rune_decrypter_prime/ciphers/generic_map_cipher.py
# Generic map/lookup cipher with CPU/Torch parity and degeneracy handling.
# ============================================================
from __future__ import annotations
from typing import Optional, Tuple
import numpy as np

from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin
from rune_decrypter_prime.ciphers.base_keyed_cipher import KeyedCipherBase
from rune_decrypter_prime.ciphers.cipher_runtime_registry import register_cipher
from rune_decrypter_prime.backends.xp import select_backend
from rune_decrypter_prime.core.types import (
    RuntimeCipherKind,
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


@register_cipher("generic_map")
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
        raw_kind = getattr(spec, "kind", getattr(cfg, "name", RuntimeCipherKind.LOOKUP.value))
        kind_key = str(raw_kind.value if isinstance(raw_kind, RuntimeCipherKind) else raw_kind).strip().lower()
        if kind_key == "generic-map":
            kind_key = RuntimeCipherKind.LOOKUP.value
        self.kind: RuntimeCipherKind = ensure_cipher_kind(kind_key)
        self.kind_value = self.kind.value
        parameters = spec.parameters
        self.A = int(parameters["alphabet_size"])
        self.N = self.A
        if self.kind is RuntimeCipherKind.USER_MAP3:
            # user_map3 key values encode (k1,k2) pairs in [0..A-1]^2
            self.keyops_hints = {"mod": int(self.A * self.A)}

        # resolve period K (required for function kinds; inferable for lookup)
        K_cfg = int(getattr(cfg, "key_length", 0) or 0)
        K = K_cfg

        A_key = self.A if self.kind is not RuntimeCipherKind.USER_MAP3 else self.A * self.A  # domain size for key value index

        # build enc/dec tables (NumPy arrays)
        enc = np.zeros((self.A, A_key), dtype=np.uint8)
        dec_len = np.zeros((A_key, self.A), dtype=np.uint16)
        dec_all = np.zeros((A_key, self.A, self.A), dtype=np.uint8)

        def _push_candidate(kv: int, ct_val: int, pt_val: int, seen: np.ndarray) -> None:
            if seen[ct_val, pt_val]:
                return
            idx = int(dec_len[kv, ct_val])
            if idx < self.A:
                dec_all[kv, ct_val, idx] = np.uint8(pt_val)
                dec_len[kv, ct_val] = np.uint16(idx + 1)
            seen[ct_val, pt_val] = True

        if self.kind in (RuntimeCipherKind.USER_MAP2, RuntimeCipherKind.USER_MAP3):
            if K <= 0:
                raise ValueError("GenericMapCipher requires cfg.key_length > 0 for user_map2/user_map3")
            from rdp.api.experimental import function_for

            f = function_for(spec)
            if not callable(f):
                raise ValueError(f"{self.kind.value} requires spec.function")
            if self.kind is RuntimeCipherKind.USER_MAP2:
                for kv in range(A_key):
                    seen = np.zeros((self.A, self.A), dtype=bool)
                    for pt in range(self.A):
                        ct = int(f(pt, kv)) % self.A
                        enc[pt, kv] = np.uint8(ct)
                        _push_candidate(kv, int(ct), int(pt), seen)
            else:  # user_map3
                for kv in range(A_key):
                    seen = np.zeros((self.A, self.A), dtype=bool)
                    k1 = kv // self.A
                    k2 = kv % self.A
                    for pt in range(self.A):
                        ct = int(f(pt, k1, k2)) % self.A
                        enc[pt, kv] = np.uint8(ct)
                        _push_candidate(kv, int(ct), int(pt), seen)

        elif self.kind is RuntimeCipherKind.LOOKUP:
            table = parameters.get("table")
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

            for kv in range(A_key):
                seen = np.zeros((self.A, self.A), dtype=bool)
                for pt in range(self.A):
                    val = T_use[pt, kv]
                    if isinstance(val, np.ndarray):
                        vals = [val.item()] if val.ndim == 0 else list(val)
                    elif isinstance(val, (list, tuple)):
                        vals = list(val)
                    else:
                        vals = [] if val is None else [val]

                    if not vals:
                        enc[pt, kv] = np.uint8(0)
                        continue

                    ct0 = int(vals[0]) % self.A
                    enc[pt, kv] = np.uint8(ct0)
                    for ct in vals:
                        ct_val = int(ct) % self.A
                        _push_candidate(kv, int(ct_val), int(pt), seen)
        else:
            raise ValueError(f"Unknown map kind '{self.kind.value}'")

        # derive first-inverse from full candidate table
        dec_first = np.zeros((A_key, self.A), dtype=np.uint8)
        for kv in range(A_key):
            for ct in range(self.A):
                if dec_len[kv, ct] > 0:
                    dec_first[kv, ct] = dec_all[kv, ct, 0]

        self._enc_np = enc
        self._dec_np = dec_first
        self._dec_all = dec_all
        self._dec_len = dec_len

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
        if LIMIT < 0:
            raise ValueError("limit must be >= 0")
        if LIMIT > self.A:
            LIMIT = int(self.A)
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

        # build short lists using candidate tables
        lens = np.zeros((B, Lq), dtype=np.uint16)
        cands = np.zeros((B, Lq, LIMIT), dtype=np.uint8)
        for b in range(B):
            for i, p in enumerate(pos):
                kl = int(kv[b, i])
                ct_sym = int(ct[p])
                n = int(self._dec_len[kl, ct_sym]) if hasattr(self, "_dec_len") else 0
                if n > 0:
                    Lm = min(n, LIMIT)
                    lens[b, i] = np.uint16(Lm)
                    cands[b, i, :Lm] = self._dec_all[kl, ct_sym, :Lm]
                    if Lm < LIMIT:
                        cands[b, i, Lm:] = cands[b, i, Lm - 1]
                else:
                    lens[b, i] = 0
                    if LIMIT:
                        cands[b, i, :] = 0
        invalid = (lens == 0)
        return cands, lens, invalid
