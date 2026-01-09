"""
Contract: the public keyops registry advertises available families and
`create()` resolves common aliases without importing private modules.
"""

import numpy as np
import pytest

from rune_decrypter_prime.core.types import KeyOpsFamily
from rune_decrypter_prime.keyops.registry import create, available
from rune_decrypter_prime.keyops import PermutationKeyOps, VectorKeyOps


def test_available_lists_core_families():
    fams = set(available())
    assert KeyOpsFamily.PERMUTATION in fams
    assert KeyOpsFamily.VECTOR in fams
    assert KeyOpsFamily.COMPOSITE in fams


def test_alias_perm_resolves_to_permutation_family():
    ops = create("perm", K=8)  # alias
    assert isinstance(ops, PermutationKeyOps)
    assert ops.caps.length == 8


def test_vector_family_constructs_with_mod_and_K():
    ops = create("vector", K=6, mod=29)
    assert isinstance(ops, VectorKeyOps)
    # Basic random key is in correct bounds and shape
    rng = np.random.default_rng(123)
    key = ops.random(rng)
    assert key.shape == (6,)
    assert key.dtype == np.uint8
    assert int(key.max()) < 29


@pytest.mark.parametrize("name_alias", [("perm", "permutation"), ("vector", "vector")])
def test_registry_alias_resolution(name_alias):
    a, b = name_alias
    if a == b:
        # self-equality sanity
        k1 = create(a, K=7, mod=29) if a == "vector" else create(a, K=7)
        k2 = create(b, K=7, mod=29) if b == "vector" else create(b, K=7)
    else:
        k1 = create(a, K=7)
        k2 = create(b, K=7)
    assert type(k1) is type(k2), f"Alias {a} should resolve to same class as {b}"
