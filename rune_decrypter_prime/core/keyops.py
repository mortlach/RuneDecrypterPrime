# ============================================================
# rune_decrypter_prime/core/keyops.py   (generic key operations for optimizers)
# ============================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional, Tuple, Any
import numpy as np
# --- existing imports at top of keyops.py ---
from dataclasses import dataclass
import numpy as np

ArrayU8 = np.ndarray

# ---- Capabilities describe how a key behaves (for optimizers & debug) ----
@dataclass(frozen=True)
class KeyCaps:
    kind: str                        # "additive", "perm", "matrix2x2", "scalar", "route", "mapping", ...
    length: Optional[int] = None     # fixed length if known; None if derived from cfg or key itself
    can_partial_score: bool = False  # Beam-friendly (e.g., additive column ciphers)
    can_additive_invariant: bool = False  # true only where pt+k==ct or pt==ct-k identities hold

# ---- Protocol every KeyOps must satisfy ----
class KeyOps(Protocol):
    caps: KeyCaps

    def random(self, rng: np.random.Generator) -> ArrayU8:
        """Return a valid random key (dtype uint8)."""

    def normalize(self, key: ArrayU8) -> ArrayU8:
        """Clamp/repair a candidate into a valid key (perm validity, invertibility, modulus, etc.)."""

    def mutate(self, key: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        """Small random tweak (cipher-appropriate)."""

    def crossover(self, k1: ArrayU8, k2: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        """Combine two parents into a valid child (may fall back to k1)."""

    # Optional hint: map partial key to affected absolute positions (Beam-quality)
    def partial_mask(self, L: int, depth: int) -> Optional[np.ndarray]:
        """Return absolute indices influenced by a prefix of length depth (or None if N/A)."""
        return None


# ---- Helpers for common key types -----------------------------------------

class AdditiveVectorOps:
    """
    For additive vector keys (e.g., Vigenère-like):
      - key = [k0..kK-1], repeats over text length L.
    """
    def __init__(self, K: int, A: int = 29) -> None:
        self.A = int(A)
        self.K = int(K)
        self.caps = KeyCaps(
            kind="additive",
            length=self.K,
            can_partial_score=True,
            can_additive_invariant=True,  # pipeline can do additive re-encrypt check safely
        )

    def random(self, rng: np.random.Generator) -> ArrayU8:
        return rng.integers(0, self.A, size=self.K, dtype=np.uint8)



    def normalize(self, key: ArrayU8) -> ArrayU8:
        k = np.asarray(key, dtype=np.uint8).ravel()
        if k.size != self.K:
            raise ValueError(f"AdditiveVectorOps expects length {self.K}, got {k.size}")
        return (k % self.A).astype(np.uint8)

    def mutate(self, key: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        k = self.normalize(key).copy()
        # Reset 1 (or 2 if long) columns to a random value in [0..A-1]
        n_changes = 2 if self.K >= 10 else 1
        idx = rng.choice(self.K, size=n_changes, replace=False)
        k[idx] = rng.integers(0, self.A, size=n_changes, dtype=np.uint8)
        return k

    def crossover(self, k1: ArrayU8, k2: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        a = self.normalize(k1); b = self.normalize(k2)
        cut = int(rng.integers(1, self.K)) if self.K > 1 else 1
        child = np.concatenate([a[:cut], b[cut:]], axis=0)
        return child.astype(np.uint8)

    def partial_mask(self, L: int, depth: int) -> Optional[np.ndarray]:
        if depth <= 0:
            return np.array([], dtype=np.int64)
        cols = (np.arange(L, dtype=np.int64) % self.K)
        return np.where(cols < depth)[0]




class Matrix2x2Ops:
    """
    For Hill(2x2) modulo A (e.g., A=29). Ensures invertibility by resampling on normalize.
    """
    def __init__(self, A: int = 29) -> None:
        self.A = int(A)
        self.caps = KeyCaps(kind="matrix2x2", length=4, can_partial_score=False)

    def _invertible(self, m: np.ndarray) -> bool:
        a,b,c,d = map(int, m.ravel())
        det = (a*d - b*c) % self.A
        return int(np.gcd(det, self.A)) == 1

    def random(self, rng: np.random.Generator) -> ArrayU8:
        while True:
            m = rng.integers(0, self.A, size=(2,2), dtype=np.int64)
            if self._invertible(m):
                return m.astype(np.uint8).ravel()

    def normalize(self, key: ArrayU8) -> ArrayU8:
        k = np.asarray(key, dtype=np.uint8).ravel() % self.A
        if k.size != 4:
            raise ValueError("Matrix2x2Ops expects length 4")
        m = k.reshape(2,2).astype(np.int64)
        if self._invertible(m):
            return k
        # small local nudge, try a few steps, then resample
        rng = np.random.default_rng()
        for _ in range(16):
            i = int(rng.integers(0,4))
            m.flat[i] = (m.flat[i] + int(rng.integers(1, self.A))) % self.A
            if self._invertible(m):
                return (m % self.A).astype(np.uint8).ravel()
        # fallback
        return self.random(rng)

    def mutate(self, key: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        m = self.normalize(key).reshape(2,2).astype(np.int64)
        i = int(rng.integers(0,4))
        m.flat[i] = (m.flat[i] + int(rng.integers(1, self.A))) % self.A
        if not self._invertible(m):
            return self.random(rng)
        return (m % self.A).astype(np.uint8).ravel()

    def crossover(self, k1: ArrayU8, k2: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        a = self.normalize(k1); b = self.normalize(k2)
        child = a.copy()
        # swap one entry from parent b
        i = int(rng.integers(0,4))
        child[i] = b[i]
        return self.normalize(child)


class AffineOps:
    """
    Key = [a, b] with a ∈ U(Z_A) (invertible mod A), b ∈ [0..A-1].
    Default A=29.
    """
    def __init__(self, A: int = 29):
        self.A = int(A)
        self.units = np.array([x for x in range(self.A) if np.gcd(x, self.A) == 1], dtype=np.uint8)
        self.caps = KeyCaps(kind="affine", length=2)

    def random(self, rng: np.random.Generator) -> np.ndarray:
        a = rng.choice(self.units)
        b = rng.integers(0, self.A, dtype=np.uint8)
        return np.array([a, b], dtype=np.uint8)

    def normalize(self, key: np.ndarray) -> np.ndarray:
        k = np.asarray(key, np.int64) % self.A
        a = int(k[0]); b = int(k[1])
        if np.gcd(a, self.A) != 1:
            # snap to nearest valid unit (simple fallback)
            a = int(self.units[a % self.units.size])
        return np.array([a % self.A, b % self.A], dtype=np.uint8)

    def mutate(self, key: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        k = key.copy()
        if rng.random() < 0.5:
            # change 'a' to a different unit
            choices = self.units[self.units != k[0]]
            if choices.size:
                k[0] = rng.choice(choices)
        else:
            # tweak 'b'
            k[1] = np.uint8((int(k[1]) + int(rng.integers(-3, 4))) % self.A)
        return self.normalize(k)

    def crossover(self, p1: np.ndarray, p2: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        a = p1[0] if rng.random() < 0.5 else p2[0]
        b = p2[1] if rng.random() < 0.5 else p1[1]
        return self.normalize(np.array([a, b], np.uint8))

class Mat2x2Ops:
    """
    Key = 2x2 matrix over Z_A, flattened row-major [a,b,c,d], with det != 0 mod A.
    """
    def __init__(self, A: int = 29):
        self.A = int(A)
        self.K = 4
        self.caps = KeyCaps(kind="mat2x2", length=self.K)


    @staticmethod
    def _det_mod(a, b, c, d, A):  # scalar
        return (int(a)*int(d) - int(b)*int(c)) % A

    def _invertible(self, m: np.ndarray) -> bool:
        a,b,c,d = [int(x) for x in m]
        return self._det_mod(a,b,c,d,self.A) != 0

    def random(self, rng: np.random.Generator) -> np.ndarray:
        while True:
            m = rng.integers(0, self.A, size=4, dtype=np.uint8)
            if self._invertible(m):
                return m

    def normalize(self, key: np.ndarray) -> np.ndarray:
        k = np.asarray(key, np.int64) % self.A
        if self._invertible(k):
            return np.asarray(k, np.uint8)
        # If not invertible, tweak one entry until invertible
        kk = k.copy()
        for delta in range(1, self.A):
            kk[0] = (k[0] + delta) % self.A
            if self._invertible(kk):
                return np.asarray(kk, np.uint8)
        # (Should never reach here for prime mod like 29)
        return np.asarray(self.random(np.random.default_rng()), np.uint8)

    def mutate(self, key: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        k = key.astype(np.int64).copy()
        i = int(rng.integers(0, 4))
        k[i] = (k[i] + int(rng.integers(-3, 4))) % self.A
        return self.normalize(k.astype(np.uint8))

    def crossover(self, p1: np.ndarray, p2: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        # uniform crossover on 4 elements
        mask = rng.integers(0, 2, size=4, dtype=np.int64)
        child = np.where(mask==1, p1, p2).astype(np.uint8)
        return self.normalize(child)


# class PermutationOps:
#     def __init__(self, K: int):
#         self.K = int(K)
#         self.caps = KeyCaps(kind="perm", length=self.K)  # <-- fix KeyOpsCaps -> KeyCaps
#     ...
#
# class AffineOps:
#     def __init__(self, A: int = 29):
#         self.A = int(A)
#         self.units = np.array([x for x in range(self.A) if np.gcd(x, self.A) == 1], dtype=np.uint8)
#         self.caps = KeyCaps(kind="affine", length=2)     # <-- fix KeyOpsCaps -> KeyCaps