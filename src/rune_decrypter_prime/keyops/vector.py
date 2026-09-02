# rune_decrypter_prime/keyops/vector.py
from __future__ import annotations

from dataclasses import dataclass, is_dataclass
from typing import Optional, Set, Dict, Any

import numpy as np

from rdp.core.types import KeyOpsFamily
from rdp.io.rng import RNGController
from .base_keyops import KeyOpBase, KeyCaps
from .registry import register_keyop

# --- Helper RNG adapters (support both Generator and RandomState gracefully) --
def _rng_integers(rng, low: int, high: int, size=None):
    if hasattr(rng, "integers"):  # Generator
        return rng.integers(low, high, size=size, endpoint=False)
    # RandomState fallback
    return rng.randint(low, high, size=size)  # high is exclusive in RandomState

def _rng_choice(rng, a: int, size=None):
    if hasattr(rng, "choice"):
        return rng.choice(a, size=size, replace=True)
    raise TypeError("RNG must support .choice (Generator/RandomState).")
# -----------------------------------------------------------------------------

@dataclass
class VectorKeyConfig:
    K: int
    mod: int = 29  # default runic alphabet
    minimum: int = 0
    # future traits can go here (e.g., per-position step); keep simple for now

@register_keyop(KeyOpsFamily.VECTOR)
class VectorKeyOps(KeyOpBase):
    """
    Additive vector key over Z_mod of fixed length K.
    - normalize: clamps/wraps to [0, mod)
    - random: uniform in [0, mod)
    - mutate: tweak one position by +/- 1 (wrapped), optionally random step
    - recombine: single-point crossover
    - make_population: fast uniform sampler
    - batch_neighbors: N independent mutate() calls
    - expand_position: (mod, K) batch varying only one index (for Beam)
    """
    def __init__(self, cfg_or_K: Optional[Any] = None, **kwargs: Any):
        # Accept dataclass, positional K, or kwargs {K=..., mod=...}
        if is_dataclass(cfg_or_K):
            cfg = cfg_or_K  # already a VectorKeyConfig
        elif isinstance(cfg_or_K, (int, np.integer)) or cfg_or_K is None:
            K = int(cfg_or_K) if cfg_or_K is not None else int(kwargs.get("K"))
            mod = int(kwargs.get("mod", 29))
            cfg = VectorKeyConfig(K=K, mod=mod, minimum=int(kwargs.get("minimum", 0)))
        else:
            # kwargs-only path (e.g., create("vector", K=.., mod=..))
            K = int(kwargs.get("K"))
            mod = int(kwargs.get("mod", 29))
            cfg = VectorKeyConfig(K=K, mod=mod, minimum=int(kwargs.get("minimum", 0)))

        self.K: int = int(cfg.K)
        self.mod: int = int(cfg.mod)
        self.minimum: int = int(cfg.minimum)

        traits: Dict[str, Any] = {
            "family": KeyOpsFamily.VECTOR,
            "mod": self.mod,
            "minimum": self.minimum,
        }
        ops: Set[str] = {
            "random",
            "normalize",
            "mutate",
            "recombine",
            "make_population",
            "batch_neighbors",
            "expand_position",
        }
        self.caps = KeyCaps(length=self.K, prefers_batch=True, traits=traits, ops=ops)
        super().__init__(self.caps)

    # --------------------------- Core verbs -----------------------------------
    def normalize(self, key: np.ndarray) -> np.ndarray:
        k = np.asarray(key, dtype=np.int64).reshape(-1)  # tolerate list/np types
        if k.size != self.K:
            raise ValueError(f"VectorKeyOps.normalize: expected length {self.K}, got {k.size}")
        k = self.minimum + np.mod(k - self.minimum, self.mod, dtype=np.int64)
        return k.astype(np.uint8, copy=False)

    def random(self, rng) -> np.ndarray:
        k = _rng_integers(rng, self.minimum, self.minimum + self.mod, size=self.K)
        return np.asarray(k, dtype=np.uint8)

    def mutate(self, key: np.ndarray, rng) -> np.ndarray:
        k = self.normalize(key).copy()
        idx = int(_rng_integers(rng, 0, self.K))
        # +/- 1 step (wrapped). If you ever want bigger steps, make it a param.
        step = 1 if _rng_integers(rng, 0, 2) == 0 else -1
        k[idx] = np.uint8(
            self.minimum + ((int(k[idx]) - self.minimum + step) % self.mod)
        )
        return k

    def recombine(self, p1: np.ndarray, p2: np.ndarray, rng) -> np.ndarray:
        a = self.normalize(p1)
        b = self.normalize(p2)
        if self.K <= 1:
            return a.copy()
        cut = int(_rng_integers(rng, 1, self.K))  # [1..K-1]
        child = np.concatenate([a[:cut], b[cut:]], axis=0)
        # child already in range because parents are; ensure dtype:
        return child.astype(np.uint8, copy=False)

    def materialize(self, seed: int | None = None):
        """
        Deterministically generate a single valid vector key from a seed,
        using the class' existing random(...) implementation.
        """
        base_seed = int(seed) if seed is not None else 0
        controller = RNGController(seed=base_seed, prefix="keyops.vector")
        rng = controller.child("materialize")
        return self.random(rng)

    def validate(self, key) -> None:
        """
        Raise if key is not uint8, length K, and within [0, mod).
        """
        import numpy as np
        k = np.asarray(key, dtype=np.uint8)
        assert k.ndim == 1, f"Vector key must be 1-D, got shape {k.shape}"
        assert k.size > 0, "Vector key must be non-empty"
        assert np.all(k >= self.minimum), (
            f"Vector key entries must be >= minimum ({self.minimum})"
        )
        assert np.all(k < self.minimum + self.mod), (
            f"Vector key entries must be < {self.minimum + self.mod}"
        )

    def partial_mask(self, L: int, depth: int):
        """
        Return the **indices** in [0, L) that are constrained by the first `depth`
        columns of a length-K repeating key.

        A position i is constrained iff (i % K) < depth.

        Parameters
        ----------
        L : int
            Total token length (plaintext/ciphertext).
        depth : int
            Number of leading key columns to include (0..K).

        Returns
        -------
        numpy.ndarray[int32]
            1-D array of indices, sorted ascending.
            Example (K=3, L=8):
              depth=0 -> []
              depth=1 -> [0, 3, 6]
              depth=2 -> [0, 1, 3, 4, 6, 7]
              depth=3 -> [0, 1, 2, 3, 4, 5, 6, 7]
        """
        import numpy as np

        # robustly get K without touching private attrs:
        K = getattr(self, "K", None)
        if K is None and hasattr(self, "caps") and hasattr(self.caps, "length"):
            K = self.caps.length
        if K is None:
            # last resort—ask the class for a sample key to infer K
            K = int(self.random(np.random.default_rng(0)).shape[0])
        else:
            K = int(K)

        if not (0 <= depth <= K):
            raise ValueError(f"depth must be within [0, K], got {depth} for K={K}")

        idx = np.arange(int(L), dtype=np.int32)
        return idx[(idx % K) < depth]

    # --------------------------- Batch helpers --------------------------------
    def make_population(self, n: int, rng) -> np.ndarray:
        pop = _rng_integers(
            rng,
            self.minimum,
            self.minimum + self.mod,
            size=(int(n), self.K),
        )
        return np.asarray(pop, dtype=np.uint8, order="C")

    def batch_neighbors(self, key: np.ndarray, n: int, rng) -> np.ndarray:
        n = int(n)
        base = self.normalize(key)
        out = np.empty((n, self.K), dtype=np.uint8)
        # independent single-position tweaks
        for i in range(n):
            out[i] = self.mutate(base, rng)
        return out

    def expand_position(self, key: np.ndarray, pos: int, rng=None) -> np.ndarray:
        """
        Exhaustive expansion at a single index for Beam:
          returns (mod, K) where only column 'pos' varies over [0..mod-1].
        """
        base = self.normalize(key)
        p = int(pos)
        if not (0 <= p < self.K):
            raise IndexError(f"expand_position: pos={p} out of range [0,{self.K})")
        out = np.tile(base, (self.mod, 1)).astype(np.uint8, copy=False)
        out[:, p] = np.arange(
            self.minimum,
            self.minimum + self.mod,
            dtype=np.uint8,
        )
        return out
