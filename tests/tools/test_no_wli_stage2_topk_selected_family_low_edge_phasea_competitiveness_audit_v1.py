from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1 as audit_mod,
)


pytestmark = pytest.mark.tier_a


def test_classify_case_category_recognizes_local_collapse() -> None:
    case_row = {
        "match_delta_vs_baseline": -0.267,
        "match_delta_vs_retained_stage3_reference": -0.259,
        "baseline_best_match_ratio": 0.428,
        "resume_best_match_ratio": 0.161,
        "stage3_best_match_ratio": 0.033,
        "phasea_best_init_match": 0.26,
    }

    assert (
        audit_mod.classify_case_category(case_row)
        == "local_search_collapse_after_phasea"
    )


def test_recommendation_advances_for_clean_phasea_gate() -> None:
    threshold_summary_rows = [
        {
            "gate_id": "rank1_init_ge_0p30",
            "metric_name": "phasea_rank1_init_match",
            "threshold": 0.30,
            "filters_all_hard_collapses": 1,
            "keeps_all_noncatastrophic": 1,
            "counterfactual_family_mean_delta_vs_baseline": 0.0212,
            "counterfactual_family_worst_delta_vs_baseline": -0.003,
        },
        {
            "gate_id": "rank1_init_ge_0p42",
            "metric_name": "phasea_rank1_init_match",
            "threshold": 0.42,
            "filters_all_hard_collapses": 0,
            "keeps_all_noncatastrophic": 0,
            "counterfactual_family_mean_delta_vs_baseline": 0.0136,
            "counterfactual_family_worst_delta_vs_baseline": 0.0,
        },
    ]

    recommendation = audit_mod.build_recommendation(threshold_summary_rows)

    assert recommendation["recommendation"] == "advance"
    assert recommendation["best_gate_id"] == "rank1_init_ge_0p30"
    assert (
        recommendation["next_branch_label"]
        == "stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe"
    )
