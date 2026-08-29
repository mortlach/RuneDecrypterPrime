from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.solvers.two_period_cribs import (
    _coordinate_search_with_status,
    coordinate_search,
)

pytestmark = pytest.mark.tier_a


def _quadratic(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    return -np.sum(arr * arr, axis=1)


def test_coordinate_search_compatibility_return_is_unchanged() -> None:
    rng = np.random.default_rng(7)
    variables, score, evaluations = coordinate_search(
        _quadratic, rng, np.array([3, 2], dtype=np.uint8), 2, modulus=5
    )
    assert isinstance(variables, np.ndarray)
    assert isinstance(score, float)
    assert isinstance(evaluations, int)


def test_zero_dimension_stage_reports_exact_constraint_resolution() -> None:
    result = _coordinate_search_with_status(
        _quadratic, np.random.default_rng(1), np.array([], dtype=np.uint8), 5, modulus=5
    )
    assert (
        result.stop_reason is api.advanced.StopReason.CONSTRAINT_SPACE_RESOLVED_EXACTLY
    )
    assert result.evaluations == 1


def test_no_improvement_and_sweep_limit_are_distinct() -> None:
    flat = lambda values: np.zeros((len(values),), dtype=np.float64)
    plateau = _coordinate_search_with_status(
        flat, np.random.default_rng(1), np.array([0], dtype=np.uint8), 3, modulus=5
    )
    assert plateau.stop_reason is api.advanced.StopReason.NO_IMPROVEMENT_BUDGET_REACHED

    def always_prefers_next(values: np.ndarray) -> np.ndarray:
        return np.asarray(values[:, 0], dtype=np.float64)

    limited = _coordinate_search_with_status(
        always_prefers_next,
        np.random.default_rng(2),
        np.array([0], dtype=np.uint8),
        1,
        modulus=5,
    )
    assert limited.stop_reason is api.advanced.StopReason.MAX_SWEEPS_REACHED
