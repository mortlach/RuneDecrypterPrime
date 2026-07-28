from __future__ import annotations

import numpy as np
import pytest

from cipher_development.interruptor_position_search.fixed_core_position_search import (
    search_fixed_core_positions,
)


def _hidden_subset_evaluator(hidden):
    hidden_set = set(hidden)

    def evaluate(subsets):
        rows = []
        for subset in subsets:
            chosen = set(subset)
            tp = len(chosen & hidden_set)
            fp = len(chosen - hidden_set)
            fn = len(hidden_set - chosen)
            rows.append(10.0 * tp - 4.0 * fp - 6.0 * fn)
        return np.asarray(rows, dtype=np.float64)

    return evaluate


def test_recovers_hidden_subset_without_truth_callback():
    hidden = (1, 4, 7, 10)
    outcome = search_fixed_core_positions(
        pool=tuple(range(12)),
        min_count=0,
        max_count=6,
        evaluate_subsets=_hidden_subset_evaluator(hidden),
        beam_width=128,
        maximum_rounds=16,
        plateau_rounds=4,
        evaluation_batch_size=31,
    )
    assert outcome.best.positions == hidden


def test_deterministic_across_batch_sizes():
    kwargs = dict(
        pool=tuple(range(10)),
        min_count=0,
        max_count=5,
        evaluate_subsets=_hidden_subset_evaluator((2, 5, 8)),
        beam_width=96,
        maximum_rounds=14,
        plateau_rounds=4,
    )
    first = search_fixed_core_positions(**kwargs, evaluation_batch_size=1)
    second = search_fixed_core_positions(**kwargs, evaluation_batch_size=128)
    assert first.best == second.best
    assert first.beam == second.beam
    assert first.rounds == second.rounds
    assert first.evaluations == second.evaluations


@pytest.mark.parametrize("pool", [(1, 2, 2), ()])
def test_invalid_pool_is_rejected(pool):
    with pytest.raises(ValueError):
        search_fixed_core_positions(
            pool=pool,
            min_count=0,
            max_count=2,
            evaluate_subsets=lambda subsets: np.zeros(len(subsets)),
        )


def test_non_finite_scores_fail():
    with pytest.raises(ValueError, match="non-finite"):
        search_fixed_core_positions(
            pool=(0, 1, 2),
            min_count=0,
            max_count=2,
            evaluate_subsets=lambda subsets: np.full(len(subsets), np.nan),
        )


def test_all_counts_are_represented_before_plateau():
    seen_counts = set()

    def evaluator(subsets):
        seen_counts.update(len(item) for item in subsets)
        return np.asarray([-len(item) for item in subsets], dtype=np.float64)

    search_fixed_core_positions(
        pool=tuple(range(8)),
        min_count=0,
        max_count=6,
        evaluate_subsets=evaluator,
        beam_width=32,
        maximum_rounds=6,
        plateau_rounds=1,
    )
    assert seen_counts == set(range(7))
