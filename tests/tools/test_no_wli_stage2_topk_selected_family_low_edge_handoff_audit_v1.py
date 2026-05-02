from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_selected_family_low_edge_handoff_audit_v1 as handoff_mod,
)


pytestmark = pytest.mark.tier_a


def test_list_edit_count_counts_position_changes() -> None:
    baseline = [[1, 2], [3, 4], [5, 6]]
    candidate = [[1, 2], [7, 8]]

    assert handoff_mod._list_edit_count(baseline, candidate) == 2


def test_recommendation_advances_for_1111_only_handoff_change() -> None:
    fixture_summary_rows = [
        {
            "fixture_seed": 611,
            "run_count": 5,
            "best2_key_changed_run_count": 0,
            "init3_changed_run_count": 0,
            "mean_init3_edit_count": 0.0,
        },
        {
            "fixture_seed": 1111,
            "run_count": 5,
            "best2_key_changed_run_count": 5,
            "init3_changed_run_count": 5,
            "mean_init3_edit_count": 7.8,
        },
        {
            "fixture_seed": 1411,
            "run_count": 5,
            "best2_key_changed_run_count": 0,
            "init3_changed_run_count": 0,
            "mean_init3_edit_count": 0.0,
        },
        {
            "fixture_seed": 1511,
            "run_count": 5,
            "best2_key_changed_run_count": 0,
            "init3_changed_run_count": 0,
            "mean_init3_edit_count": 0.0,
        },
    ]

    recommendation = handoff_mod.build_recommendation(fixture_summary_rows)

    assert recommendation["recommendation"] == "advance"
    assert recommendation["candidate_policy_id"] == handoff_mod.POLICY_ID
    assert (
        recommendation["next_branch_label"]
        == "stage2_topk_selected_family_low_edge_eps_0p016_microprobe"
    )
