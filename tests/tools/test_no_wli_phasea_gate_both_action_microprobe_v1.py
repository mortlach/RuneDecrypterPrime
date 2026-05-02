from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1 as mod,
)


def test_build_phasea_gate_action_decider_filters_to_baseline_stop() -> None:
    decider = mod._build_phasea_gate_action_decider(
        reference_row={
            "baseline_best_match_ratio": 0.754,
            "baseline_best_stage": "stage3_full_refine",
        },
        expected_gate_verdict="filter",
    )

    decision = decider({"phaseA_rank1_init_match": 0.289})

    assert decision["gate_verdict"] == "filter"
    assert decision["action_stop_now"] == 1
    assert decision["action_fallback_to_baseline"] == 1
    assert decision["resume_best_stage"] == "stage3_full_refine"
    assert decision["resume_best_match_ratio"] == 0.754


def test_build_phasea_gate_action_decider_keeps_lane_without_stop() -> None:
    decider = mod._build_phasea_gate_action_decider(
        reference_row={
            "baseline_best_match_ratio": 0.408,
            "baseline_best_stage": "stage3_full_refine",
        },
        expected_gate_verdict="keep",
    )

    decision = decider({"phaseA_rank1_init_match": 0.490})

    assert decision["gate_verdict"] == "keep"
    assert decision["action_stop_now"] == 0
    assert decision["action_fallback_to_baseline"] == 0
    assert decision["action_reason"] == "gate_keep_meets_threshold"


def test_build_recommendation_refines_when_correct_but_late() -> None:
    recommendation = mod._build_recommendation(
        {
            "filtered_canary_behaved_as_expected": 1,
            "kept_canary_behaved_as_expected": 1,
            "filtered_canary_saved_attempt_share": 0.12,
        }
    )

    assert recommendation["recommendation"] == "refine"
    assert (
        recommendation["next_branch_label"]
        == "stage2_topk_selected_family_low_edge_phasea_gate_earlier_emission_microprobe"
    )


def test_build_recommendation_holds_when_filtered_canary_fails() -> None:
    recommendation = mod._build_recommendation(
        {
            "filtered_canary_behaved_as_expected": 0,
            "kept_canary_behaved_as_expected": 1,
            "filtered_canary_saved_attempt_share": 0.40,
        }
    )

    assert recommendation["recommendation"] == "hold"
