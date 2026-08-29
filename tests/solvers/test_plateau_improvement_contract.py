from __future__ import annotations
import pytest
from rune_decrypter_prime.solvers.solver_base import SolverBase
pytestmark = pytest.mark.tier_a

def test_is_improvement_requires_strict_gain_when_min_delta_zero():
    assert not SolverBase._is_improvement(1.0, 1.0, 0.0)
    assert SolverBase._is_improvement(1.0000001, 1.0, 0.0)

def test_is_improvement_respects_min_delta_threshold():
    assert not SolverBase._is_improvement(1.0009, 1.0, 0.001)
    assert SolverBase._is_improvement(1.0011, 1.0, 0.001)
