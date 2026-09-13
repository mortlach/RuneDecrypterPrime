import numpy as np
from rdp.keyops.permutation_ops import PermutationKeyConfig, PermutationKeyOps
import pytest
pytestmark = [pytest.mark.tier_a]

def test_materialize_and_validate():
    keyop = PermutationKeyOps(PermutationKeyConfig(K=10))
    k = keyop.materialize(seed=123)
    keyop.validate(k)

def test_normalize_projects_to_perm():
    keyop = PermutationKeyOps(PermutationKeyConfig(K=7))
    v = np.array([10, 11, 12, 13, 14, 15, 16], dtype=np.uint8)
    p = keyop.normalize(v)
    keyop.validate(p)
    assert set(p.tolist()) == set(range(7))
