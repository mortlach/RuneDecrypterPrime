from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1 as matrix_mod,
)


pytestmark = pytest.mark.tier_a


def test_build_matrix_recommendation_closes_on_all_negative_rows() -> None:
    recommendation = matrix_mod.build_matrix_recommendation(
        [
            {
                "search_seed": 7001,
                "match_delta_vs_baseline": -0.002,
                "match_delta_vs_retained_stage3_reference": -0.010,
            },
            {
                "search_seed": 7004,
                "match_delta_vs_baseline": -0.003,
                "match_delta_vs_retained_stage3_reference": -0.012,
            },
        ]
    )

    assert recommendation["recommendation"] == "close"
    assert recommendation["clean_win_count"] == 0
    assert recommendation["baseline_win_count"] == 0


def test_build_matrix_recommendation_advances_on_multiple_clean_wins() -> None:
    recommendation = matrix_mod.build_matrix_recommendation(
        [
            {
                "search_seed": 7001,
                "match_delta_vs_baseline": 0.004,
                "match_delta_vs_retained_stage3_reference": 0.002,
            },
            {
                "search_seed": 7002,
                "match_delta_vs_baseline": 0.006,
                "match_delta_vs_retained_stage3_reference": 0.001,
            },
            {
                "search_seed": 7004,
                "match_delta_vs_baseline": -0.001,
                "match_delta_vs_retained_stage3_reference": -0.003,
            },
        ]
    )

    assert recommendation["recommendation"] == "advance"
    assert recommendation["clean_win_count"] == 2
