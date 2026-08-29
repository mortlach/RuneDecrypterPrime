from __future__ import annotations
import numpy as np
from rune_decrypter_prime.io.rng import RNGController


def _sample(gen: np.random.Generator, n: int = 8) -> list[int]:
    return gen.integers(0, 1000000, size=n).tolist()


def test_same_seed_same_name_same_sequence():
    a = RNGController(123).child("optim.SA")
    b = RNGController(123).child("optim.SA")
    assert _sample(a) == _sample(b)


def test_same_seed_different_names_different_sequences():
    rc = RNGController(123)
    a = _sample(rc.child("optim.SA"))
    b = _sample(rc.child("optim.GA"))
    assert a != b


def test_different_seeds_same_name_different_sequences():
    a = _sample(RNGController(123).child("keyops.permutation"))
    b = _sample(RNGController(124).child("keyops.permutation"))
    assert a != b


def test_scope_equivalence_to_qualified_name():
    rc = RNGController(999)
    a = _sample(rc.child("optim.SA"))
    b = _sample(rc.scope("optim").child("SA"))
    assert a == b


def test_streams_are_independent_progress():
    rc = RNGController(42)
    g1 = rc.child("beam.width")
    g2 = rc.child("beam.width")
    _ = _sample(g1, 16)
    assert _sample(RNGController(42).child("beam.width")) == _sample(g2)
