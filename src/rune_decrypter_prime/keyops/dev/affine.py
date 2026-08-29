# -*- coding: utf-8 -*-
# rune_decrypter_prime/keyops/affine.py
# --------------------------------------------------------------------
# Purpose: Affine key (a,b) with a ∈ U(Z_mod), b ∈ [0..mod-1], registered keyops
# --------------------------------------------------------------------
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from rune_decrypter_prime.core.types import KeyOpsFamily
from rune_decrypter_prime.keyops.base_keyops import KeyOpBase, KeyCaps
from rune_decrypter_prime.keyops.registry import register_keyop

ArrayU8 = np.ndarray

@dataclass
class AffineKeyConfig:
    mod: int = 29  # alphabet size

@register_keyop(KeyOpsFamily.AFFINE)
class AffineKey(KeyOpBase):
    """
    Affine keyops: key = [a, b], with gcd(a, mod) == 1, b in [0..mod-1].
    Genome: length 2 (uint8).
    """
    def __init__(self, cfg_or_mod=None, **kwargs):
        mod = self._unpack(cfg_or_mod, kwargs)
        # For affine monoalphabetic, key "length" is 2 parameters (a,b),
        # but caps.length should reflect the size of the key vector you store.
        # If you represent it as length-2 vector, use 2. If you store as scalar pair, use 2.
        K_effective = 2
        self.caps = KeyCaps(length=K_effective, prefers_batch=False,
                            traits={"family": KeyOpsFamily.AFFINE, "mod": int(mod)})
        super().__init__(self.caps)
        self.mod = int(mod)


    @staticmethod
    def _unpack(cfg_or_mod, kwargs):
        if isinstance(cfg_or_mod, AffineKeyConfig) and type(cfg_or_mod).__name__ == "AffineKeyConfig":
            return int(cfg_or_mod.mod)
        if isinstance(cfg_or_mod, (int, np.integer)):
            return int(cfg_or_mod)
        if "mod" in kwargs:
            return int(kwargs["mod"])
        raise TypeError("AffineKeyOps expects AffineKeyConfig or mod=int")

    @property
    def name(self) -> str:
        return KeyOpsFamily.AFFINE.value

    def validate(self, key: ArrayU8) -> None:
        k = np.asarray(key, dtype=np.int64).ravel()
        if k.size != 2:
            raise ValueError("AffineKey: expected length 2 [a,b]")
        a = int(k[0]) % self.mod
        b = int(k[1]) % self.mod
        if np.gcd(a, self.mod) != 1:
            raise ValueError("AffineKey: 'a' must be invertible modulo mod")
        if not (0 <= b < self.mod):
            raise ValueError(f"AffineKey: 'b' must be in [0,{self.mod})")

    def materialize(self, seed: int | None = None) -> ArrayU8:
        rng = np.random.default_rng(seed)
        a = rng.choice(self.units).astype(np.uint8)
        b = rng.integers(0, self.mod, dtype=np.uint8)
        return np.array([a, b], dtype=np.uint8)

    def normalize(self, key: ArrayU8) -> ArrayU8:
        k = np.asarray(key, dtype=np.int64).ravel()
        if k.size != 2:
            raise ValueError("AffineKey: expected length 2 [a,b]")
        a = int(k[0]) % self.mod
        b = int(k[1]) % self.mod
        if np.gcd(a, self.mod) != 1:
            # snap a to nearest valid unit (cheap fallback)
            a = int(self.units[a % self.units.size])
        return np.array([a, b], dtype=np.uint8)

    def mutate(self, key: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        k = self.normalize(key).copy()
        if float(rng.random()) < 0.5:
            # change 'a' to a different unit
            choices = self.units[self.units != k[0]]
            if choices.size:
                k[0] = rng.choice(choices)
        else:
            # tweak 'b'
            k[1] = np.uint8((int(k[1]) + int(rng.integers(-3, 4))) % self.mod)
        return self.normalize(k)

    def crossover(self, p1: ArrayU8, p2: ArrayU8, rng: np.random.Generator) -> ArrayU8:
        a = p1[0] if float(rng.random()) < 0.5 else p2[0]
        b = p2[1] if float(rng.random()) < 0.5 else p1[1]
        return self.normalize(np.array([a, b], np.uint8))
