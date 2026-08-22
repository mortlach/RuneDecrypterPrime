# -*- coding: utf-8 -*-
# rune_decrypter_prime/keyops/matrix.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence
import numpy as np
from rune_decrypter_prime.keyops.base_keyops import KeyOpBase, KeyCaps, ArrayU8

def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)

def _inv_mod(x: int, m: int) -> int:
    return pow(int(x), -1, int(m))

def _det_mod(M: np.ndarray, mod: int) -> int:
    # Compute determinant modulo mod for integer matrices
    # Use int64, then reduce mod.
    det = round(np.linalg.det(M.astype(np.int64)))
    return int(det) % mod

def _adjugate(M: np.ndarray, mod: int) -> np.ndarray:
    # Cofactor/adjugate for small N (tutorial scale). For larger N, consider faster algos.
    n = M.shape[0]
    cof = np.zeros_like(M, dtype=np.int64)
    for i in range(n):
        for j in range(n):
            minor = np.delete(np.delete(M, i, axis=0), j, axis=1)
            sign = -1 if ((i + j) % 2) else 1
            cof[i, j] = (sign * round(np.linalg.det(minor.astype(np.int64)))) % mod
    # adj = cof^T
    return (cof.T % mod).astype(np.int64)

# --- GL(n, Z_mod) elementary row operations (preserve invertibility) ---
def _gl_row_swap(M: np.ndarray, i: int, j: int) -> None:
    if i == j:
        return
    M[[i, j], :] = M[[j, i], :]

def _gl_row_scale(M: np.ndarray, i: int, u: int, mod: int) -> None:
    # scale by a unit (coprime to mod)
    if np.gcd(int(u), int(mod)) != 1:
        raise ValueError("Row scale u must be a unit mod")
    M[i, :] = (M[i, :] * int(u)) % int(mod)

def _gl_row_add(M: np.ndarray, i: int, j: int, k: int, mod: int) -> None:
    # R_i <- R_i + k * R_j
    if i == j:
        return
    M[i, :] = (M[i, :] + int(k) * M[j, :]) % int(mod)


@dataclass
class MatrixKeyConfig:
    rows: int
    cols: Optional[int] = None
    mod: int = 29
    require_invertible: bool = True

class MatrixKey(KeyOpBase):
    """
    General integer matrix key with modular arithmetic.
    - If cols is None -> square (rows x rows).
    - If require_invertible=True -> must be square and det != 0 (mod).
    Genome layout is row-major flattened uint8 (values in [0, mod)).
    """
    def __init__(self, cfg: MatrixKeyConfig):
        self.rows = int(cfg.rows)
        self.cols = int(cfg.cols) if cfg.cols is not None else int(cfg.rows)
        self.mod  = int(cfg.mod)
        self.require_invertible = bool(cfg.require_invertible)
        length = self.rows * self.cols
        #self.caps = KeyCaps(kind="matrix", length=length, can_partial_score=False)
        self.caps = KeyCaps(kind="matrix", length=length, can_partial_score=(self.rows == 2 and self.cols == 2))
        if self.require_invertible and self.rows != self.cols:
            raise ValueError("MatrixKey: require_invertible=True requires a square matrix (rows==cols).")

    @property
    def name(self) -> str:
        return "matrix"

    # --- Helpers ---
    def _validate_shape(self, key: ArrayU8) -> None:
        L = int(self.rows * self.cols)
        if key.ndim != 1 or key.size != L:
            raise ValueError(f"MatrixKey: expected flat length {L} ({self.rows}x{self.cols}), got shape {key.shape}.")

    def _validate_values(self, key: ArrayU8) -> None:
        if (key < 0).any() or (key >= self.mod).any():
            raise ValueError(f"MatrixKey: entries must be in [0,{self.mod}).")

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

    # --- API ---
    def validate(self, key: ArrayU8) -> None:
        k = np.asarray(key, dtype=np.uint8).ravel()
        self._validate_shape(k); self._validate_values(k)
        if self.require_invertible and not self._is_invertible(k):
            raise ValueError("MatrixKey: matrix is not invertible modulo the given modulus.")

    def materialize(self, seed: Optional[int] = None) -> ArrayU8:
        rng = np.random.default_rng(seed)
        L = self.rows * self.cols
        for _ in range(2048):
            k = rng.integers(0, self.mod, size=L, dtype=np.uint8)
            try:
                self.validate(k)
                return k
            except Exception:
                continue
        # Fallback: force invertibility by nudging entries (rare for prime mod)
        k = rng.integers(0, self.mod, size=L, dtype=np.uint8)
        if self.require_invertible and self.rows == self.cols:
            M = k.reshape(self.rows, self.cols).astype(np.int64)
            for i in range(self.rows * self.cols):
                base = int(M.flat[i])
                for delta in range(1, self.mod):
                    M.flat[i] = (base + delta) % self.mod
                    det = _det_mod(M, self.mod)
                    if _gcd(det, self.mod) == 1:
                        return (M % self.mod).astype(np.uint8).ravel()
                M.flat[i] = base
        return k

    def mutate(self, key: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        """
        Mutation in GL(n, Z_mod) using 1–3 random elementary row ops.
        Guarantees invertibility when require_invertible=True.
        """
        k = self.normalize(key).astype(np.uint8)
        if not self.require_invertible or self.rows != self.cols:
            # fallback: tiny entry tweak (as before)
            i = int(rng.integers(0, k.size))
            delta = int(rng.integers(1, max(2, self.mod // 8)))
            k[i] = np.uint8((int(k[i]) + delta) % self.mod)
            return self.normalize(k)

        n, A = int(self.rows), int(self.mod)
        M = k.reshape(n, n).astype(np.int64, copy=True)

        # 1–3 GL ops
        n_ops = int(rng.integers(1, 4))
        for _ in range(n_ops):
            op = int(rng.integers(0, 3))
            if op == 0:  # swap rows
                i, j = int(rng.integers(0, n)), int(rng.integers(0, n))
                _gl_row_swap(M, i, j)
            elif op == 1:  # scale a row by a unit
                i = int(rng.integers(0, n))
                # pick random unit modulo A
                while True:
                    u = int(rng.integers(1, A))
                    if np.gcd(u, A) == 1:
                        break
                _gl_row_scale(M, i, u, A)
            else:  # add k * row j to row i
                i, j = int(rng.integers(0, n)), int(rng.integers(0, n))
                kcoef = int(rng.integers(1, A))
                _gl_row_add(M, i, j, kcoef, A)

        out = (M % A).astype(np.uint8).ravel()
        # normalize will validate invertibility if required
        return self.normalize(out)

    def crossover(self, parent1: ArrayU8, parent2: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        """
        GL-safe 'blend': start from parent1 and apply a few GL ops biased by differences to parent2.
        Not a true recombination, but respects the group and gives directional pressure.
        """
        p1 = self.normalize(np.asarray(parent1, np.uint8))
        p2 = self.normalize(np.asarray(parent2, np.uint8))
        if not self.require_invertible or self.rows != self.cols:
            # non-square or unconstrained: copy p1
            return p1.copy()

        n, A = int(self.rows), int(self.mod)
        M1 = p1.reshape(n, n).astype(np.int64, copy=True)
        M2 = p2.reshape(n, n).astype(np.int64, copy=False)

        # 1–3 GL ops that move M1 'towards' M2 in a crude sense
        n_ops = int(rng.integers(1, 4))
        for _ in range(n_ops):
            op = int(rng.integers(0, 3))
            if op == 0:
                # swap rows if that reduces row Hamming distance
                i = int(rng.integers(0, n))
                best_j, best_d = i, (M1[i] != M2[i]).sum()
                for j in range(n):
                    d = (M1[j] != M2[i]).sum()
                    if d < best_d:
                        best_j, best_d = j, d
                _gl_row_swap(M1, i, best_j)
            elif op == 1:
                # scale a row to match a unit pattern from M2
                i = int(rng.integers(0, n))
                # pick a unit; not trying to be exact, just introduce diversity
                tries = 0
                while True and tries < 8:
                    u = int(rng.integers(1, A))
                    if np.gcd(u, A) == 1:
                        break
                    tries += 1
                _gl_row_scale(M1, i, u, A)
            else:
                # add k * M1[j] to M1[i] to reduce difference to M2[i]
                i, j = int(rng.integers(0, n)), int(rng.integers(0, n))
                kcoef = int(rng.integers(1, A))
                _gl_row_add(M1, i, j, kcoef, A)

        out = (M1 % A).astype(np.uint8).ravel()
        return self.normalize(out)

    def inverse_matrix(self, key: ArrayU8) -> Optional[np.ndarray]:
        """
        Return modular inverse matrix (rows x cols) if invertible; else None.
        """
        if self.rows != self.cols:
            return None
        M = self.normalize(key).reshape(self.rows, self.cols).astype(np.int64)
        det = _det_mod(M, self.mod)
        if _gcd(det, self.mod) != 1:
            return None
        inv_det = _inv_mod(det, self.mod)
        adj = _adjugate(M, self.mod)
        Minv = (adj * inv_det) % self.mod
        return Minv.astype(np.uint8)

    def partial_mask(self, L: int, depth: int):
        """
        For 2x2 Hill, when one inverse row is fixed we can decrypt the first
        symbol of each 2-symbol block; with two rows we decrypt both.
        Return indices influenced by the first `depth` rows.
        """
        if self.rows == 2 and self.cols == 2:
            if depth <= 0:
                return np.array([], dtype=np.int64)
            idx0 = np.arange(0, L - (L % 2), 2, dtype=np.int64)  # even positions
            if depth == 1:
                return idx0
            # depth >= 2 → both rows
            idx1 = idx0 + 1
            if (L % 2) == 1 and (idx1.size > 0):
                idx1 = idx1[idx1 < L]
            return np.sort(np.concatenate([idx0, idx1])).astype(np.int64)
        # generic matrices: no simple row-wise partial available by default
        return np.array([], dtype=np.int64)


    def is_invertible_batch(self, keys_2d: np.ndarray) -> np.ndarray:
        """
        Vectorised invertibility check for flat keys of shape (B, rows*cols).
        Returns boolean mask of shape (B,).
        Currently specialises the fast path for 2x2 (common Hill case).
        """
        K = np.asarray(keys_2d, dtype=np.int64)
        if K.ndim != 2 or K.shape[1] != self.rows * self.cols:
            raise ValueError(f"is_invertible_batch expects (B,{self.rows * self.cols}), got {K.shape}")
        if self.rows != self.cols:
            return np.zeros((K.shape[0],), dtype=bool)

        if self.rows == 2 and self.cols == 2:
            a = K[:, 0];
            b = K[:, 1];
            c = K[:, 2];
            d = K[:, 3]
            det = (a * d - b * c) % self.mod
            from numpy import gcd
            return (gcd(det, self.mod) == 1)
        # Fallback (small B only): per-row check using existing scalar path
        out = np.zeros((K.shape[0],), dtype=bool)
        for i in range(K.shape[0]):
            out[i] = self._is_invertible((K[i] % self.mod).astype(np.uint8))
        return out

    def inverse_2x2_mod(self, key_flat_u8: np.ndarray) -> np.ndarray:
        """
        Return the modular inverse of a 2x2 matrix key (flat length 4) mod self.mod.
        Raises if not 2x2 or not invertible.
        """
        if self.rows != 2 or self.cols != 2:
            raise ValueError("inverse_2x2_mod is only defined for 2x2 keys.")
        k = self.normalize(np.asarray(key_flat_u8, np.uint8))
        a, b, c, d = map(int, k)
        A = int(self.mod)
        det = (a * d - b * c) % A
        if np.gcd(det, A) != 1:
            raise ValueError("2x2 key is not invertible modulo A.")
        inv_det = pow(det, -1, A)
        # adjugate [[d, -b], [-c, a]]
        M = np.array([d, (-b) % A, (-c) % A, a], dtype=np.int64)
        Minv = (inv_det * M) % A
        return Minv.astype(np.uint8)

    #
    # def _det_mod_2x2(self, k_u8: np.ndarray) -> int:
    #     a, b, c, d = [int(x) for x in k_u8[:4]]
    #     return (a * d - b * c) % self.mod
    #
    # def _is_invertible(self, key: ArrayU8) -> bool:
    #     if self.rows != self.cols:
    #         return False
    #     k = np.asarray(key, np.uint8).ravel()
    #     if self.rows == 2 and self.cols == 2:
    #         det = self._det_mod_2x2(k)
    #         return np.gcd(det, self.mod) == 1
    #     # fallback (rare): use current integer det path
    #     M = k.reshape(self.rows, self.cols).astype(np.int64)
    #     det = _det_mod(M, self.mod)
    #     return _gcd(det, self.mod) == 1
    #
    # def normalize(self, key: ArrayU8) -> ArrayU8:
    #     k = np.asarray(key, dtype=np.int64).ravel()
    #     self._validate_shape(k)
    #     k = (k % self.mod).astype(np.uint8)
    #     # Keep normalize cheap in the inner loop; only enforce invertible when needed.
    #     if self.require_invertible:
    #         if self.rows == 2 and self.cols == 2:
    #             if not self._is_invertible(k):
    #                 # Nudge a single entry; try a few deltas (fast integer math)
    #                 a = k.astype(np.int64)
    #                 for i in range(4):
    #                     base = int(a[i])
    #                     for delta in (1, 2, 3, 4, 5):
    #                         a[i] = (base + delta) % self.mod
    #                         if self._is_invertible(a.astype(np.uint8)):
    #                             return a.astype(np.uint8)
    #                     a[i] = base
    #                 # give up: return modded k (cipher can discard later by scoring)
    #         else:
    #             # non-2x2 fallback: keep as-is (avoid heavy nudging every call)
    #             pass
    #     return k
    #
