from __future__ import annotations

import numpy as np
import pytest

from cipher_development.interruptor_position_search.benchmark import build_benchmark
from cipher_development.interruptor_position_search.fixed_core_position_evaluator import (
    build_fixed_core_position_evaluator,
)


def test_real_evaluator_uses_canonical_encoder_and_fixed_prefix():
    benchmark = build_benchmark()
    evaluator = build_fixed_core_position_evaluator(benchmark)
    subsets = ((), tuple(benchmark.pool[:3]), tuple(benchmark.pool[:6]))
    encoded = evaluator.encode_subsets(subsets)
    assert encoded.shape == (3, len(benchmark.key) + 6)
    expected = np.tile(np.asarray(benchmark.key), (3, 1))
    assert np.array_equal(encoded[:, : len(benchmark.key)], expected)
    assert evaluator.context()["canonical_encoder_identity"].endswith(
        "CompositeKeyOps.normalize"
    )
    assert evaluator.context()["position_control_used_test_key"] is False
    assert evaluator.context()["position_control_used_true_positions"] is False


def test_real_evaluator_scalar_and_batch_scores_match_and_are_finite():
    benchmark = build_benchmark()
    evaluator = build_fixed_core_position_evaluator(benchmark)
    subsets = ((), tuple(benchmark.pool[:2]), tuple(benchmark.pool[-4:]))
    batch = evaluator.score_subsets(subsets)
    scalar = np.asarray(
        [evaluator.score_subsets((subset,))[0] for subset in subsets],
        dtype=np.float64,
    )
    assert np.all(np.isfinite(batch))
    assert np.array_equal(batch, scalar)


@pytest.mark.parametrize(
    "subset",
    [
        (54, 40),
        (40, 40),
        (999999,),
    ],
)
def test_invalid_subsets_fail_before_problem_evaluation(subset):
    benchmark = build_benchmark()
    evaluator = build_fixed_core_position_evaluator(benchmark)
    before = int(evaluator.problem.telemetry["evaluate_keys_calls"])
    with pytest.raises(ValueError):
        evaluator.score_subsets((subset,))
    assert int(evaluator.problem.telemetry["evaluate_keys_calls"]) == before
