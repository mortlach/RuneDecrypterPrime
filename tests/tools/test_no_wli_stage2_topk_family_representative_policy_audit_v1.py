from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_family_representative_policy_audit_v1 as audit_mod,
)


pytestmark = pytest.mark.tier_a


def test_selected_family_low_edge_row_chooses_band_edge() -> None:
    family_rows = [
        {
            "row_id": "r1",
            "rank": 1,
            "score_stage2": -4.943,
            "score_judge": -4.943,
            "truth_match": 0.091,
        },
        {
            "row_id": "r2",
            "rank": 2,
            "score_stage2": -4.957,
            "score_judge": -4.957,
            "truth_match": 0.099,
        },
        {
            "row_id": "r5",
            "rank": 5,
            "score_stage2": -4.9582,
            "score_judge": -4.9582,
            "truth_match": 0.161,
        },
        {
            "row_id": "r6",
            "rank": 6,
            "score_stage2": -4.970,
            "score_judge": -4.970,
            "truth_match": 0.096,
        },
    ]
    selected_row = dict(family_rows[0])

    chosen = audit_mod.select_selected_family_low_edge_row(
        family_rows=family_rows,
        selected_row=selected_row,
        score_band_eps=0.020,
    )

    assert chosen["row_id"] == "r5"


def test_recommendation_advances_for_1111_only_activation() -> None:
    fixture_summary_rows = [
        {
            "fixture_seed": 611,
            "run_count": 5,
            "candidate_active_run_count": 0,
            "candidate_any_negative_truth_delta": 0,
            "mean_candidate_truth_delta_vs_baseline": 0.0,
        },
        {
            "fixture_seed": 1111,
            "run_count": 5,
            "candidate_active_run_count": 5,
            "candidate_any_negative_truth_delta": 0,
            "mean_candidate_truth_delta_vs_baseline": 0.07,
        },
        {
            "fixture_seed": 1411,
            "run_count": 5,
            "candidate_active_run_count": 0,
            "candidate_any_negative_truth_delta": 0,
            "mean_candidate_truth_delta_vs_baseline": 0.0,
        },
        {
            "fixture_seed": 1511,
            "run_count": 5,
            "candidate_active_run_count": 0,
            "candidate_any_negative_truth_delta": 0,
            "mean_candidate_truth_delta_vs_baseline": 0.0,
        },
    ]

    recommendation = audit_mod.build_recommendation(fixture_summary_rows)

    assert recommendation["recommendation"] == "advance"
    assert recommendation["candidate_policy_id"] == audit_mod.POLICY_ID
    assert (
        recommendation["next_branch_label"]
        == "stage2_topk_selected_family_low_edge_microprobe"
    )
