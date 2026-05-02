from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_family_representative_policy_audit_v1 as policy_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_family_representative_policy_sensitivity_v1 as sensitivity_mod,
)


pytestmark = pytest.mark.tier_a


def test_selected_family_low_edge_thresholds_are_narrow() -> None:
    family_rows = [
        {
            "row_id": "r1",
            "rank": 1,
            "score_stage2": -4.943248,
            "score_judge": -4.943248,
            "truth_match": 0.091,
        },
        {
            "row_id": "r4",
            "rank": 4,
            "score_stage2": -4.958040,
            "score_judge": -4.958040,
            "truth_match": 0.068,
        },
        {
            "row_id": "r5",
            "rank": 5,
            "score_stage2": -4.958404,
            "score_judge": -4.958404,
            "truth_match": 0.161,
        },
        {
            "row_id": "r6",
            "rank": 6,
            "score_stage2": -4.966101,
            "score_judge": -4.966101,
            "truth_match": 0.096,
        },
    ]
    selected_row = dict(family_rows[0])

    chosen_015 = policy_mod.select_selected_family_low_edge_row(
        family_rows=family_rows,
        selected_row=selected_row,
        score_band_eps=0.015,
    )
    chosen_016 = policy_mod.select_selected_family_low_edge_row(
        family_rows=family_rows,
        selected_row=selected_row,
        score_band_eps=0.016,
    )
    chosen_025 = policy_mod.select_selected_family_low_edge_row(
        family_rows=family_rows,
        selected_row=selected_row,
        score_band_eps=0.025,
    )

    assert chosen_015["row_id"] == "r4"
    assert chosen_016["row_id"] == "r5"
    assert chosen_025["row_id"] == "r6"


def test_recommendation_picks_minimal_clean_positive_window() -> None:
    summary_rows = []
    for view_id in ("exact_key", "exact_tail", "near_tail_h1", "prefix_hamming_le_24"):
        for eps in sensitivity_mod.EPS_VALUES:
            for fixture_seed in (611, 1111, 1411, 1511):
                row = {
                    "family_view_id": view_id,
                    "score_band_eps": eps,
                    "fixture_seed": fixture_seed,
                    "run_count": 5,
                    "candidate_active_run_count": 0,
                    "candidate_any_negative_truth_delta": 0,
                    "mean_candidate_truth_delta_vs_baseline": 0.0,
                }
                if view_id == "prefix_hamming_le_24" and fixture_seed == 1111:
                    if eps == 0.015:
                        row["candidate_active_run_count"] = 5
                        row["candidate_any_negative_truth_delta"] = 1
                        row["mean_candidate_truth_delta_vs_baseline"] = -0.023
                    elif eps in (0.016, 0.020):
                        row["candidate_active_run_count"] = 5
                        row["mean_candidate_truth_delta_vs_baseline"] = 0.070
                    elif eps == 0.025:
                        row["candidate_active_run_count"] = 5
                        row["mean_candidate_truth_delta_vs_baseline"] = 0.005
                summary_rows.append(row)

    recommendation = sensitivity_mod.build_recommendation(summary_rows)

    assert recommendation["recommendation"] == "advance"
    assert recommendation["candidate_policy_id"] == "selected_family_low_edge_eps_0p016_v1"
    assert recommendation["family_view_id"] == "prefix_hamming_le_24"
    assert recommendation["score_band_eps"] == 0.016
    assert (
        recommendation["next_branch_label"]
        == "stage2_topk_selected_family_low_edge_eps_0p016_microprobe"
    )
