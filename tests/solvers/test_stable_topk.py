from __future__ import annotations
import numpy as np
import pytest
from rune_decrypter_prime.solvers.solver_base import SolverBase
pytestmark = pytest.mark.tier_a

def test_stable_topk_prefers_lower_index_on_ties():
    scores = np.array([1.0, 1.0, 0.5, 1.0], dtype=np.float64)
    idx = SolverBase._stable_topk_indices(scores, 3)
    assert idx.tolist() == [0, 1, 3]

def test_stable_topk_handles_full_length():
    scores = np.array([0.2, 0.2, 0.1], dtype=np.float64)
    idx = SolverBase._stable_topk_indices(scores, 5)
    assert idx.tolist() == [0, 1, 2]
