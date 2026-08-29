# ============================================================
# rune_decrypter_prime/ciphers/base_keyops.py
# ============================================================
# -*- coding: utf-8 -*-
"""
base_keyops.py — KeyOps base class and capability surface.

Optimisers must not special-case key types. They call generic verbs exposed by
KeyOps. Concrete KeyOps classes implement those verbs appropriately.

Required:
    - random(rng) -> (K,) uint8
    - normalize(key_or_batch) -> same shape, uint8
    - mutate(key, rng) -> (K,) uint8
    - caps.length: int

Recommended (optimisers will use if present):
    - neighbor(key, rng) -> (K,) uint8
    - recombine(p1, p2, rng) -> (K,) uint8
    - make_population(n, rng) -> (n,K) uint8
    - batch_neighbors(base, n, rng, policy: str|None=None) -> (n,K) uint8
    - local_improve(key, score, scorer, rng, **hints) -> (key, score)
    - expand_position(prefix, pos, rng) -> (M,K) uint8  # for Beam-like growth

Each concrete KeyOps should set self.caps.ops to the verbs it implements.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
import numpy as np

from rune_decrypter_prime.core.types import KEY_DTYPE

ArrayU8 = np.ndarray


def _rng_integers(rng, low: int, high: int):
    if hasattr(rng, "integers"):  # Generator
        return int(rng.integers(low, high, endpoint=False))
    return int(rng.randint(low, high))


@dataclass
class KeyCaps:
    length: int
    # Optional hints/capabilities:
    ops: set = field(default_factory=set)               # e.g., {"mutate","recombine","neighbor",...}
    prefers_batch: bool = False
    alphabet_size: Optional[int] = None
    traits: Dict[str, Any] = field(default_factory=dict)
    notes: Dict[str, Any] = field(default_factory=dict)


class KeyOpBase:
    """
    Base class: concrete KeyOps MUST implement:
        - random(rng)
        - normalize(key_or_batch)
        - mutate(key, rng)
        - caps.length (int)
    Other verbs are optional; declare them by adding their names to caps.ops.

    This base also exposes a lightweight "ops" registry to make verb lookups explicit.
    """

    def __init__(self, caps: KeyCaps):
        self.caps = caps
        self.dtype = getattr(self, "dtype", KEY_DTYPE)
        # Registry of verb -> callable (filled by derived classes or here if default)
        self.ops: Dict[str, Callable] = {}
        # Required verbs must be provided by concrete class
        for req in ("random", "normalize", "mutate"):
            if not hasattr(self, req):
                raise TypeError(f"{self.__class__.__name__} missing required method: {req}")

        # Auto-register present verbs
        for name in (
            "random", "normalize", "mutate",
            "neighbor", "recombine",
            "make_population", "batch_neighbors",
            "local_improve", "expand_position",
            "crossover",
        ):
            fn = getattr(self, name, None)
            if callable(fn):
                self.ops[name] = fn
                self.caps.ops.add(name)

    def supports(self, verb: str) -> bool:
        return verb in self.ops

    def op(self, verb: str):
        """Return a bound callable for the verb, or raise KeyError."""
        return self.ops[verb]

    def apply(self, verb: str, *args, **kwargs):
        return self.op(verb)(*args, **kwargs)

    def suggest(self, stage: str) -> dict:
        """Stage-specific hints: 'sa', 'ga', 'beam', etc."""
        return getattr(self.caps, "hints", {}).get(stage, {})

    def normalize(self, keys):
        """Base hook: subclasses override to enforce invariants."""
        raise NotImplementedError

    # ----------------- Required surface (abstract by convention) -----------------

    def random(self, rng: np.random.RandomState) -> np.ndarray:
        raise NotImplementedError

    def normalize(self, key_or_batch: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def mutate(self, key: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
        raise NotImplementedError

    # ----------------- Optional helpers (safe defaults) -----------------

    def neighbor(self, key: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
        """Default neighbour = mutate; override for richer local moves."""
        return self.mutate(key, rng)

    def recombine(self, p1: np.ndarray, p2: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
        """Default recombine = copy-parent with splice; override in families that support crossover."""
        K = int(self.caps.length)
        k = _rng_integers(rng, 1, K) if K > 1 else 1
        child = np.concatenate([p1[:k], p2[k:]]).astype(self.dtype, copy=False)
        return self.normalize(child)

    def make_population(self, n: int, rng: np.random.RandomState) -> np.ndarray:
        """Vectorised seeding if desired; default = loop random+normalize."""
        rows = [self.normalize(self.random(rng)) for _ in range(int(n))]
        return np.ascontiguousarray(np.stack(rows, axis=0), dtype=self.dtype)

    def batch_neighbors(
        self,
        base: np.ndarray,
        n: int,
        rng: np.random.RandomState,
        policy: Optional[str] = None,
    ) -> np.ndarray:
        """Default = n independent neighbours via neighbor()."""
        rows = [self.normalize(self.neighbor(base, rng)) for _ in range(int(n))]
        return np.ascontiguousarray(np.stack(rows, axis=0), dtype=self.dtype)

    def local_improve(
        self,
        key: np.ndarray,
        score: float,
        scorer: Any,
        rng: np.random.RandomState,
        **hints: Any,
    ) -> tuple[np.ndarray, float]:
        """
        Optional: improve (key, score) locally using scorer. Default = no-op.
        Return (maybe_new_key, maybe_new_score).
        """
        return key, float(score)

    def expand_position(
        self,
        prefix: np.ndarray,
        pos: int,
        rng: np.random.RandomState,
    ) -> np.ndarray:
        """
        Optional: expand a prefix at position pos into a small candidate set.
        Default: produce a small stochastic set via batch_neighbors.
        """
        m = max(16, 4)  # small default
        return self.batch_neighbors(prefix, m, rng, policy=None)
