"""
RNG adapters test: VectorKeyOps must accept both numpy.random.Generator
and legacy RandomState, since users may pass either.
"""

import numpy as np
import pytest
from rune_decrypter_prime.keyops.registry import create
from rune_decrypter_prime.keyops import VectorKeyOps


@pytest.mark.parametrize("rng_kind", ["generator", "randomstate"])
def test_vector_ops_accept_both_rng_kinds(rng_kind):
    K, M = (7, 29)
    ops: VectorKeyOps = create("vector", K=K, mod=M)
    if rng_kind == "generator":
        rng = np.random.default_rng(123)
    else:
        rng = np.random.RandomState(123)
    k1 = ops.random(rng)
    assert k1.shape == (K,) and k1.dtype == np.uint8
    k2 = ops.mutate(k1, rng)
    assert k2.shape == (K,) and k2.dtype == np.uint8
    pop = ops.make_population(8, rng)
    assert pop.shape == (8, K) and pop.dtype == np.uint8
    exp = ops.expand_position(k2, pos=2)
    assert exp.shape == (M, K) and exp.dtype == np.uint8


def test_vector_accepts_generator_and_randomstate():
    K, mod = (7, 23)
    ops = create("vector", K=K, mod=mod)
    gen = np.random.default_rng(123)
    rs = np.random.RandomState(123)
    k1 = ops.random(gen)
    k2 = ops.random(rs)
    assert k1.shape == (K,) and k2.shape == (K,)
    assert (k1 < mod).all() and (k2 < mod).all()
