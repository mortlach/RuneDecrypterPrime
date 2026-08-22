"""KeyOps registry extensibility tests."""
from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.core.types import KeyOpsFamily
from rune_decrypter_prime.keyops.base_keyops import KeyCaps, KeyOpBase
from rune_decrypter_prime.keyops.registry import create, register_keyop, get
from rune_decrypter_prime.keyops.vector import VectorKeyOps

pytestmark = pytest.mark.tier_a


def test_keyops_registration_can_be_overridden_and_restored():
    """Developers can swap in custom KeyOps implementations and revert safely."""
    original_factory = get(KeyOpsFamily.VECTOR)

    @register_keyop(KeyOpsFamily.VECTOR, replace=True)
    class UnitTestVector(KeyOpBase):
        def __init__(self, K: int = 4, mod: int = 29):
            self.K = int(K)
            self.mod = int(mod)
            caps = KeyCaps(length=self.K)
            super().__init__(caps)

        def random(self, rng):
            return rng.integers(0, self.mod, size=self.K, dtype=np.uint8)

        def normalize(self, key):
            arr = np.asarray(key, dtype=np.uint8).reshape(-1, self.K)
            return arr[0]

        def mutate(self, key, rng):
            out = np.array(key, dtype=np.uint8, copy=True)
            idx = int(rng.integers(0, self.K))
            out[idx] = np.uint8((int(out[idx]) + 1) % self.mod)
            return out

    try:
        ops = create(KeyOpsFamily.VECTOR, K=5, mod=31)
        rng = np.random.default_rng(0)
        sample = ops.random(rng)
        assert sample.shape == (5,)
        mutated = ops.mutate(sample, rng)
        assert mutated.shape == (5,)
        assert ops.normalize(mutated).shape == (5,)
    finally:
        register_keyop(KeyOpsFamily.VECTOR, replace=True)(original_factory)
