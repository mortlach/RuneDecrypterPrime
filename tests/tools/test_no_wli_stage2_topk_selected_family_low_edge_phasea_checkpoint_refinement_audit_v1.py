from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1 as mod,
)


pytestmark = pytest.mark.tier_a


def test_gate_verdict_uses_rank1_floor_then_high_best_override() -> None:
    assert (
        mod._gate_verdict(
            rank1_init_match=0.31,
            best_init_match=0.31,
            rank1_threshold=0.30,
            best_threshold=0.44,
        )
        == "keep"
    )
    assert (
        mod._gate_verdict(
            rank1_init_match=0.24,
            best_init_match=0.49,
            rank1_threshold=0.30,
            best_threshold=0.44,
        )
        == "keep"
    )
    assert (
        mod._gate_verdict(
            rank1_init_match=0.24,
            best_init_match=0.33,
            rank1_threshold=0.30,
            best_threshold=0.44,
        )
        == "filter"
    )


def test_collect_interval_bounds_uses_filtered_max_and_rescued_keep_min() -> None:
    late_rows = [
        {
            "expected_gate_verdict": "filter",
            "phasea_best_init_match": 0.378,
        },
        {
            "expected_gate_verdict": "keep",
            "phasea_best_init_match": 0.395,
        },
    ]
    provisional_rows = [
        {
            "expected_gate_verdict": "filter",
            "phasea_rank1_init_match": 0.243,
            "phasea_best_init_match": 0.329,
        },
        {
            "expected_gate_verdict": "keep",
            "phasea_rank1_init_match": 0.243,
            "phasea_best_init_match": 0.490,
        },
    ]

    out = mod._collect_interval_bounds(
        late_family_rows=late_rows,
        provisional_rows=provisional_rows,
        rank1_threshold=0.30,
    )

    assert out["filtered_best_max"] == pytest.approx(0.378)
    assert out["rescued_keep_best_min"] == pytest.approx(0.49)
    assert out["safe_interval_midpoint"] == pytest.approx((0.378 + 0.49) / 2.0)


def test_build_summary_advances_when_refined_rule_exists() -> None:
    candidate_rows = [
        {
            "rule_id": "rule_a",
            "best_threshold": 0.40,
            "late_family_all_match": 1,
            "late_override_count": 0,
            "shared_checkpoint_count": 1,
            "earliest_shared_checkpoint_restart_count": 16,
            "earliest_shared_checkpoint_elapsed_share": 0.21,
            "earliest_shared_checkpoint_share_improvement_vs_late_gate": 0.67,
        },
        {
            "rule_id": "rule_b",
            "best_threshold": 0.49,
            "late_family_all_match": 0,
            "late_override_count": 0,
            "shared_checkpoint_count": 1,
            "earliest_shared_checkpoint_restart_count": 16,
            "earliest_shared_checkpoint_elapsed_share": 0.21,
            "earliest_shared_checkpoint_share_improvement_vs_late_gate": 0.67,
        },
    ]
    interval_bounds = {
        "filtered_best_max": 0.378,
        "rescued_keep_best_min": 0.49,
        "safe_interval_midpoint": 0.434,
    }

    out = mod._build_summary(
        candidate_rows=candidate_rows,
        interval_bounds=interval_bounds,
    )

    assert out["recommendation"] == "advance"
    assert out["selected_rule_id"] == "rule_a"
    assert out["selected_earliest_shared_checkpoint_restart_count"] == 16
