import numpy as np
from rdp.keyops.vector import VectorKeyConfig, VectorKeyOps
import pytest
pytestmark = [pytest.mark.tier_a]

def test_vector_partial_mask():
    keyop = VectorKeyOps(VectorKeyConfig(K=3, mod=29))
    mask = keyop.partial_mask(L=8, depth=2).tolist()
    assert mask == [0, 1, 3, 4, 6, 7]

def test_vector_materialize_validate_normalize():
    keyop = VectorKeyOps(VectorKeyConfig(K=7, mod=29))
    k = keyop.materialize(seed=123)
    keyop.validate(k)
    bad = np.array([100] * 7, dtype=np.uint8)
    fixed = keyop.normalize(bad)
    keyop.validate(fixed)
    assert fixed.max() < 29
