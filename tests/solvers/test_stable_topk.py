from __future__ import annotations
import numpy as np
import pytest
from rdp.solvers.solver_base import SolverBase
pytestmark = pytest.mark.tier_a

def test_stable_topk_prefers_lower_index_on_ties():
    scores = np.array([1.0, 1.0, 0.5, 1.0], dtype=np.float64)
    idx = SolverBase._stable_topk_indices(scores, 3)
    assert idx.tolist() == [0, 1, 3]

def test_stable_topk_handles_full_length():
    scores = np.array([0.2, 0.2, 0.1], dtype=np.float64)
    idx = SolverBase._stable_topk_indices(scores, 5)
    assert idx.tolist() == [0, 1, 2]


def test_stable_topk_prefers_lowest_indices_when_all_values_tie_below_full_length():
    scores = np.ones(10, dtype=np.float64)

    idx = SolverBase._stable_topk_indices(scores, 3)

    assert idx.tolist() == [0, 1, 2]


def test_stable_topk_prefers_lowest_indices_at_cutoff_tie():
    scores = np.array([5.0, 4.0, 4.0, 4.0, 3.0], dtype=np.float64)

    idx = SolverBase._stable_topk_indices(scores, 3)

    assert idx.tolist() == [0, 1, 2]


def test_stable_topk_orders_ties_above_and_below_cutoff():
    scores = np.array([5.0, 5.0, 4.0, 4.0, 3.0, 3.0], dtype=np.float64)

    idx = SolverBase._stable_topk_indices(scores, 4)

    assert idx.tolist() == [0, 1, 2, 3]


def test_stable_topk_handles_single_item_selection():
    scores = np.ones(5, dtype=np.float64)

    idx = SolverBase._stable_topk_indices(scores, 1)

    assert idx.tolist() == [0]


@pytest.mark.parametrize("k", [0, -1])
def test_stable_topk_returns_empty_for_nonpositive_k(k):
    scores = np.array([3.0, 2.0, 1.0], dtype=np.float64)

    idx = SolverBase._stable_topk_indices(scores, k)

    assert idx.dtype == np.int64
    assert idx.tolist() == []
