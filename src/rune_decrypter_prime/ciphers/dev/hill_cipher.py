# -*- coding: utf-8 -*-
# rune_decrypter_prime/ciphers/hill_cipher.py
from __future__ import annotations
import numpy as np

from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin, ArrayU8
from rune_decrypter_prime.ciphers.cipher_runtime_registry import register_cipher
# from rdp.keyops.base_keyops import KeyOpBase
from rdp.keyops.dev.matrix import MatrixKey, MatrixKeyConfig
# XP helper is optional and only used when n==2 and device is GPU/XP
try:
    from rune_decrypter_prime.ciphers.dev import hill2x2_xp as hill_xp
except Exception:
    hill_xp = None

A = 29

def _inv_mod(x: int, m: int = A) -> int:
    return pow(int(x), -1, int(m))

def _det_mod(M: np.ndarray, mod: int) -> int:
    det = round(np.linalg.det(M.astype(np.int64)))
    return int(det) % int(mod)

def _adjugate(M: np.ndarray, mod: int) -> np.ndarray:
    n = M.shape[0]
    cof = np.zeros_like(M, dtype=np.int64)
    for i in range(n):
        for j in range(n):
            minor = np.delete(np.delete(M, i, axis=0), j, axis=1)
            sign = -1 if ((i + j) % 2) else 1
            cof[i, j] = (sign * round(np.linalg.det(minor.astype(np.int64)))) % mod
    return (cof.T % mod).astype(np.int64)

def _invert_mod(M: np.ndarray, mod: int) -> np.ndarray:
    det = _det_mod(M, mod)
    if np.gcd(det, mod) != 1:
        raise ValueError("Hill: key matrix is not invertible modulo the alphabet size.")
    inv_det = _inv_mod(det, mod)
    adj = _adjugate(M, mod)
    Minv = (adj * inv_det) % mod
    return Minv.astype(np.uint8)

def _precompute_inv_map(mod: int) -> np.ndarray:
    """inv_map[x] = x^{-1} mod mod (0 for non-invertible)."""
    inv = np.zeros(mod, dtype=np.int64)
    for x in range(1, mod):
        if np.gcd(x, mod) == 1:
            inv[x] = pow(x, -1, mod)
    return inv




@register_cipher("hill")
class HillCipher(CipherPipelineMixin):
    """
    Hill cipher over Z_29 with an NxN key (square, invertible mod 29).
    Uses CPU/NumPy for general N; if N==2 and GPU/XP is selected, uses the XP path.

    Hill consumes keys as flat uint8 arrays of length n*n from the solver.
    Before decrypting, we call MatrixKey.normalize(...) to enforce square + invertible mod 29.
    This keeps solver simple (they do not import KeyOps) and guarantees decryption never
    sees a singular matrix.

    """
    A = A

    def __init__(self, cfg, *, text_transposition="ltr", key_transposition="ltr"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", text_transposition),
            key_transposition=getattr(cfg, "key_transposition", key_transposition),
        )
        self.cfg = cfg
        self.device = str(getattr(cfg, "device", "cpu")).lower()

        # --- Accept BOTH backend-key and UI-only flows ---
        # 1) If the caller provided a backend MatrixKey, use it.
        key_obj = getattr(cfg, "key", None)
        if isinstance(key_obj, MatrixKey):
            self._keyops: MatrixKey = key_obj
            n_rows, n_cols, modA = self._keyops.rows, self._keyops.cols, self._keyops.mod
            if n_rows != n_cols:
                raise ValueError("Hill requires a square matrix key")
            self._n = int(n_rows)
            self.A = int(modA)
        else:
            # 2) UI-only/wrapper path: infer matrix size from cfg.key_length
            #    - wrapper sets key_length = n*n (e.g., 4 for 2x2)
            key_len = int(getattr(cfg, "key_length", 0) or 0)
            if key_len <= 0:
                raise ValueError(
                    "HillCipher: key_length (n*n) must be provided explicitly (e.g., 4 for 2x2, 9 for 3x3).")
            n_float = int(round((key_len) ** 0.5))
            if n_float * n_float != key_len:
                raise ValueError(f"HillCipher: key_length={key_len} is not a perfect square")
            n = n_float

            self.A = int(getattr(cfg, "N", 29) or 29)
            # Construct a default MatrixKey (require invertible)
            self._keyops = MatrixKey(MatrixKeyConfig(rows=n, cols=n, mod=self.A, require_invertible=True))
            self._n = n

        # --- expose for solver/UI ---
        self.keyops = self._keyops
        self.key_length = int(self._n * self._n)

        # cache invers emap
        self._inv_map = _precompute_inv_map(self.A) if self._n == 2 else None

        # --- Optional XP helper for 2x2 on CUDA/GPU ---
        self._xp_helper = None
        if self._n == 2 and self.device.startswith("cuda"):
            try:
                from rune_decrypter_prime.ciphers.dev import hill2x2_xp as hill_xp  # fast path
                self._xp_helper = hill_xp
            except Exception:
                self._xp_helper = None  # safe fallback to CPU

    # --- core hooks (CipherPipelineMixin will call this on transposed arrays) ---
    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """
        ct_tr: [N] or [B,N] uint8 indices (transposed by the pipeline)
        keys_tr: [B, Lk] or [Lk] uint8 flattened matrices (row-major)
        returns: [B,N] uint8 plaintext indices (transposed back by the pipeline)
        """
        A = self.A
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B = int(keys_tr.shape[0])

        # Fast-path to XP only for n==2 and GPU/XP device
        if self._xp_helper is not None and self._n == 2:
            # hill_xp.decrypt_batch(self, ct_u8, keys_u8) -> xp uint8 [B,N]
            # Convert to CPU numpy at the end to match ArrayU8 contract.
            outs = []
            for b in range(B):
                key_b = keys_tr[b]
                out_b = self._decrypt_cpu(ct_tr, key_b) if self._xp_helper is None else self._decrypt_xp(ct_tr, key_b)
                outs.append(out_b[None, :])
            return np.concatenate(outs, axis=0).astype(np.uint8)


        # General CPU NxN path
        outs = []
        if self._n == 2 and self._inv_map is not None:
            # ---- Fast vectorized 2x2 decrypt on CPU ----
            ct = np.asarray(ct_tr, np.uint8).ravel()
            keys = np.asarray(keys_tr, np.uint8)
            B = int(keys.shape[0])
            A = int(self.A)

            # Split keys into a,b,c,d
            a = keys[:, 0].astype(np.int64);
            b = keys[:, 1].astype(np.int64)
            c = keys[:, 2].astype(np.int64);
            d = keys[:, 3].astype(np.int64)

            det = (a * d - b * c) % A
            inv_det = self._inv_map[det]  # 0 for non-invertible (should be rare with normalize)

            # inverse matrix [[d,-b],[-c,a]] * inv_det mod A
            m00 = (d * inv_det) % A
            m01 = ((A - b % A) * inv_det) % A
            m10 = ((A - c % A) * inv_det) % A
            m11 = (a * inv_det) % A
            Minv = np.stack([np.stack([m00, m01], axis=1),
                             np.stack([m10, m11], axis=1)], axis=1)  # (B,2,2)

            # reshape ciphertext to blocks of 2
            L = int(ct.size)
            pad = (-L) % 2
            if pad:
                w = np.empty(L + pad, dtype=np.uint8);
                w[:L] = ct;
                w[L:] = 0
            else:
                w = ct
            X = w.reshape(-1, 2).astype(np.int64)  # (T,2)

            # batch matmul: (B, T, 2) = (T,2) @ (B,2,2)^T
            # i.e., for each b: X @ Minv[b].T
            Y = (X[None, :, :] @ np.transpose(Minv, (0, 2, 1))) % A  # (B,T,2)

            out = Y.reshape(B, -1)[:, :L].astype(np.uint8, copy=False)
            return out

    def _decrypt_batch_2x2_numpy(self, ct_u8: np.ndarray, keys_2d: np.ndarray) -> np.ndarray:
        """
        Ultra-fast NumPy decrypt for Hill 2x2 (B keys).
        Shapes:
          ct_u8   : (L,) uint8   (already in core/transposed order)
          keys_2d : (B,4) uint8  (row-major [a,b,c,d])
        Returns:
          (B,L) uint8 plaintexts
        """
        A = int(self.A)
        L = int(ct_u8.size)
        B = int(keys_2d.shape[0])

        # Reshape text into pairs with padding (pad=0) but crop back to L.
        pad = (-L) % 2
        if pad:
            w = np.empty(L + pad, dtype=np.uint8);
            w[:L] = ct_u8;
            w[L:] = 0
        else:
            w = ct_u8
        X = w.reshape(-1, 2).astype(np.int64)  # (T,2)

        a = keys_2d[:, 0].astype(np.int64)
        b = keys_2d[:, 1].astype(np.int64)
        c = keys_2d[:, 2].astype(np.int64)
        d = keys_2d[:, 3].astype(np.int64)

        # Compute inverse per key (vectorised)
        det = (a * d - b * c) % A
        inv_det = np.array([pow(int(x), -1, A) for x in det], dtype=np.int64)

        ai = (d * inv_det) % A
        bi = ((-b) * inv_det) % A
        ci = ((-c) * inv_det) % A
        di = (a * inv_det) % A

        # Broadcast over T pairs
        x0 = X[:, 0][None, :]  # (1,T)
        x1 = X[:, 1][None, :]  # (1,T)

        p0 = (ai[:, None] * x0 + bi[:, None] * x1) % A  # (B,T)
        p1 = (ci[:, None] * x0 + di[:, None] * x1) % A  # (B,T)

        out = np.empty((B, X.shape[0] * 2), dtype=np.uint8)
        out[:, 0::2] = p0.astype(np.uint8)
        out[:, 1::2] = p1.astype(np.uint8)
        return out[:, :L]

    # --- helpers ---
    def _decrypt_xp(self, ct: ArrayU8, key_flat: ArrayU8) -> ArrayU8:
        """
        XP helper for 2x2 case when device is GPU/XP.
        Falls back to CPU if XP not initialised for any reason.
        """
        try:
            Mi = None  # XP path computes inverse internally per batch
            # hill2x2_xp API contracts to accept flat key(s); we wrap one at a time.
            # Build a tiny wrapper object exposing .xp if needed; current impl handles inside.
            xp_out = self._xp_helper.decrypt_batch(self, ct, key_flat[None, :])
            # Bring back to CPU numpy
            if hasattr(xp_out, "get"):
                return np.asarray(xp_out.get(), dtype=np.uint8).ravel()
            return np.asarray(xp_out, dtype=np.uint8).ravel()
        except Exception:
            return self._decrypt_cpu(ct, key_flat)

    def _decrypt_cpu(self, ct: ArrayU8, key_flat: ArrayU8) -> ArrayU8:
        A = self.A
        n = self._n
        ct_u8 = np.asarray(ct, dtype=np.uint8).ravel()
        N = int(ct_u8.size)
        pad = (-N) % n
        if pad:
            ct_work = np.empty(N + pad, dtype=np.uint8)
            ct_work[:N] = ct_u8
            ct_work[N:] = 0
        else:
            ct_work = ct_u8
        X = ct_work.reshape(-1, n).astype(np.int64)  # [M, n]
        K = np.asarray(key_flat, dtype=np.uint8).ravel().astype(np.int64)
        if K.size != n * n:
            raise ValueError(f"HillCipher: key length {K.size} does not match n*n={n*n}.")
        M = K.reshape(n, n)
        Mi = _invert_mod(M, A).astype(np.int64)
        pt = (X @ Mi.T) % A
        out = pt.reshape(-1)[:N].astype(np.uint8)
        return out

    def _det_mod_2x2(self, k_u8: np.ndarray) -> int:
        # k_u8 is flat [a,b,c,d] (row-major)
        a, b, c, d = [int(x) for x in k_u8[:4]]
        return (a * d - b * c) % self.mod

    def _is_invertible(self, key: ArrayU8) -> bool:
        if self.rows != self.cols:
            return False
        k = np.asarray(key, np.uint8).ravel()
        if self.rows == 2 and self.cols == 2:
            det = self._det_mod_2x2(k)
            return np.gcd(det, self.mod) == 1
        # --- old general path unchanged ---
        M = k.reshape(self.rows, self.cols).astype(np.int64)
        det = _det_mod(M, self.mod)
        return _gcd(det, self.mod) == 1

    def normalize(self, key: ArrayU8) -> ArrayU8:
        k = np.asarray(key, dtype=np.int64).ravel()
        self._validate_shape(k)
        k = (k % self.mod).astype(np.uint8)

        if not self.require_invertible:
            return k

        # ---- fast path for 2x2 (cheap, stays in integer arithmetic) ----
        if self.rows == 2 and self.cols == 2:
            if self._is_invertible(k):
                return k
            # Try a few tiny nudges on a single entry; keep this very cheap.
            a = k.astype(np.int64)
            for i in range(4):
                base = int(a[i])
                # small deltas are usually enough over prime modulus
                for delta in (1, 2, 3, 4, 5):
                    a[i] = (base + delta) % self.mod
                    if self._is_invertible(a.astype(np.uint8)):
                        return a.astype(np.uint8)
                a[i] = base
            # last resort (rare under prime mod): re-materialize once
            return self.materialize()

        # ---- general n×n: keep existing (old) logic unchanged ----
        if not self._is_invertible(k):
            # Try small nudges before resampling
            M = k.reshape(self.rows, self.cols).astype(np.int64)
            for i in range(self.rows * self.cols):
                base = int(M.flat[i])
                for delta in range(1, self.mod):
                    M.flat[i] = (base + delta) % self.mod
                    det = _det_mod(M, self.mod)
                    if _gcd(det, self.mod) == 1:
                        return (M % self.mod).astype(np.uint8).ravel()
                M.flat[i] = base
            return self.materialize()  # last resort
        return k
