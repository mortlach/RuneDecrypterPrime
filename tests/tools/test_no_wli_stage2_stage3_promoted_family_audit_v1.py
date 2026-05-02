from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_stage3_promoted_family_audit_v1 as audit_mod,
)


pytestmark = pytest.mark.tier_a


def test_recommendation_advances_on_persistent_1111_within_family_signature() -> None:
    fixture_summary_rows = [
        {
            "fixture_seed": 611,
            "mean_stage2_promoted_within_family_gap": 0.0,
            "mean_stage2_promoted_between_family_gap": 0.01,
            "mean_stage2_topk_within_family_gap": 0.0,
            "promoted_within_family_signal_run_count": 0,
            "run_count": 5,
            "dominant_upstream_pattern": "no_clear_upstream_gap",
        },
        {
            "fixture_seed": 1111,
            "mean_stage2_promoted_within_family_gap": 0.07,
            "mean_stage2_promoted_between_family_gap": 0.014,
            "mean_stage2_topk_within_family_gap": 0.07,
            "promoted_within_family_signal_run_count": 5,
            "run_count": 5,
            "dominant_upstream_pattern": "persistent_within_family_representative_gap",
        },
        {
            "fixture_seed": 1511,
            "mean_stage2_promoted_within_family_gap": 0.0,
            "mean_stage2_promoted_between_family_gap": 0.01,
            "mean_stage2_topk_within_family_gap": 0.0,
            "promoted_within_family_signal_run_count": 0,
            "run_count": 5,
            "dominant_upstream_pattern": "no_clear_upstream_gap",
        },
    ]

    recommendation = audit_mod.build_recommendation(fixture_summary_rows)

    assert recommendation["recommendation"] == "advance"
    assert recommendation["mechanism_layer"] == "selection"
    assert (
        recommendation["next_branch_label"]
        == "stage2_stage3_within_family_representative_selection_microprobe"
    )


def test_fixture_summary_labels_persistent_within_family_pattern() -> None:
    case_rows = []
    for search_seed in (7001, 7002, 7003, 7004, 7005):
        case_rows.append(
            {
                "fixture_seed": 1111,
                "search_seed": search_seed,
                "benchmark_case_role": "conversion_failure_case",
                "final_best_match_ratio": 0.4,
                "stage2_topk_within_family_gap": 0.07,
                "stage2_topk_between_family_gap": 0.01,
                "stage2_promoted_within_family_gap": 0.07,
                "stage2_promoted_between_family_gap": 0.014,
                "selected_family_init3_share": 0.094,
                "best_truth_family_init3_share": 0.047,
                "init3_selected_minus_best_truth_family_share": 0.047,
            }
        )

    summary_rows = audit_mod._build_fixture_summary_rows(case_rows)

    assert len(summary_rows) == 1
    summary = summary_rows[0]
    assert summary["fixture_seed"] == 1111
    assert summary["dominant_upstream_pattern"] == "persistent_within_family_representative_gap"
    assert summary["promoted_within_family_signal_run_count"] == 5
    assert summary["mean_stage2_promoted_within_family_gap"] == pytest.approx(0.07)
