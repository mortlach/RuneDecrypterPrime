from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_both_action_microprobe_v1 as mod,
)


def test_build_phasea_provisional_gate_action_decider_filters_to_baseline_stop() -> None:
    decider = mod._build_phasea_provisional_gate_action_decider(
        reference_row={
            "baseline_best_match_ratio": 0.675,
            "baseline_best_stage": "stage3_full_refine",
        },
        expected_gate_verdict="filter",
    )

    decision = decider(
        {
            "phaseA_rank1_init_match": 0.243,
            "phaseA_best_init_match": 0.378,
        }
    )

    assert decision["gate_verdict"] == "filter"
    assert decision["trigger_source"] == "filter"
    assert decision["action_stop_now"] == 1
    assert decision["action_fallback_to_baseline"] == 1
    assert decision["resume_best_stage"] == "stage3_full_refine"
    assert decision["resume_best_match_ratio"] == 0.675


def test_build_phasea_provisional_gate_action_decider_keeps_via_high_best_rescue() -> None:
    decider = mod._build_phasea_provisional_gate_action_decider(
        reference_row={
            "baseline_best_match_ratio": 0.408,
            "baseline_best_stage": "stage3_full_refine",
        },
        expected_gate_verdict="keep",
    )

    decision = decider(
        {
            "phaseA_rank1_init_match": 0.243,
            "phaseA_best_init_match": 0.490,
        }
    )

    assert decision["gate_verdict"] == "keep"
    assert decision["trigger_source"] == "high_best_rescue"
    assert decision["action_stop_now"] == 0
    assert decision["action_fallback_to_baseline"] == 0
    assert decision["action_reason"] == "refined_gate_keep_high_best_rescue"


def test_build_recommendation_advances_when_filtered_saves_time_and_kept_is_clean() -> None:
    recommendation = mod._build_recommendation(
        {
            "filtered_canary_behaved_as_expected": 1,
            "kept_canary_behaved_as_expected": 1,
            "filtered_canary_saved_attempt_share": 0.64,
        }
    )

    assert recommendation["recommendation"] == "advance"
    assert (
        recommendation["next_branch_label"]
        == "stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_family_microbatch"
    )


def test_build_recommendation_holds_when_kept_canary_fails() -> None:
    recommendation = mod._build_recommendation(
        {
            "filtered_canary_behaved_as_expected": 1,
            "kept_canary_behaved_as_expected": 0,
            "filtered_canary_saved_attempt_share": 0.64,
        }
    )

    assert recommendation["recommendation"] == "hold"


def test_filtered_family_role_uses_filtered_action_contract() -> None:
    behaved = mod._action_behaved_as_expected_for_role(
        lane_role="filtered_family",
        observed_gate_verdict="filter",
        expected_gate_verdict="filter",
        action_applied=1,
        current_resume_best_match_ratio=0.754,
        baseline_best_match_ratio=0.754,
        reference_resume_best_match_ratio=0.310,
    )

    assert behaved == 1


def test_filtered_family_role_rejects_keep_style_no_action() -> None:
    behaved = mod._action_behaved_as_expected_for_role(
        lane_role="filtered_family",
        observed_gate_verdict="filter",
        expected_gate_verdict="filter",
        action_applied=0,
        current_resume_best_match_ratio=0.310,
        baseline_best_match_ratio=0.754,
        reference_resume_best_match_ratio=0.310,
    )

    assert behaved == 0


def test_kept_family_role_uses_kept_no_harm_contract() -> None:
    behaved = mod._action_behaved_as_expected_for_role(
        lane_role="kept_family",
        observed_gate_verdict="keep",
        expected_gate_verdict="keep",
        action_applied=0,
        current_resume_best_match_ratio=0.420,
        baseline_best_match_ratio=0.423,
        reference_resume_best_match_ratio=0.420,
    )

    assert behaved == 1


def test_unknown_lane_role_is_not_silently_treated_as_kept() -> None:
    with pytest.raises(ValueError):
        mod._action_behaved_as_expected_for_role(
            lane_role="filtered_other_name",
            observed_gate_verdict="filter",
            expected_gate_verdict="filter",
            action_applied=1,
            current_resume_best_match_ratio=0.754,
            baseline_best_match_ratio=0.754,
            reference_resume_best_match_ratio=0.310,
        )
