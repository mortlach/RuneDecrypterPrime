import numpy as np
import pytest
from rune_decrypter_prime.keyops.base_keyops import KeyOpBase, KeyCaps
from rune_decrypter_prime.keyops.vector import VectorKeyOps

pytestmark = pytest.mark.tier_a


class _DummyKeyOps(KeyOpBase):
    def __init__(self):
        super().__init__(KeyCaps(length=3))

    def random(self, rng):
        return np.array([0, 1, 2], dtype=np.uint8)

    def normalize(self, key):
        return np.asarray(key, dtype=np.uint8).reshape(-1)

    def mutate(self, key, rng):
        return np.asarray(key, dtype=np.uint8).reshape(-1)


def test_keyops_op_returns_callable():
    keyops = VectorKeyOps(K=3, mod=29)
    fn = keyops.op("mutate")
    assert callable(fn)
    out = fn(np.array([0, 1, 2], dtype=np.uint8), np.random.default_rng(0))
    assert out.shape == (3,)


def test_base_recombine_accepts_generator():
    keyops = _DummyKeyOps()
    rng = np.random.default_rng(0)
    p1 = np.array([0, 1, 2], dtype=np.uint8)
    p2 = np.array([2, 1, 0], dtype=np.uint8)
    child = keyops.recombine(p1, p2, rng)
    assert child.shape == (3,)
