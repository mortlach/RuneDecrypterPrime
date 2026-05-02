from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1 as mod,
)


def test_summary_row_counts_family_behaviour() -> None:
    summary = mod._summary_row(
        [
            {
                "search_seed": 7002,
                "lane_role": "filtered_family",
                "observed_gate_verdict": "filter",
                "expected_gate_verdict": "filter",
                "phasea_gate_action_applied": 1,
                "gate_checkpoint_restart_count": 32,
                "actual_saved_attempt_seconds": 736.0,
                "actual_saved_attempt_share": 0.562,
                "action_behaved_as_expected": 1,
                "gate_checkpoint_share_of_reference_attempt": 0.43,
                "baseline_best_match_ratio": 0.754,
                "current_resume_best_match_ratio": 0.754,
                "delta_vs_baseline": 0.0,
            },
            {
                "search_seed": 7003,
                "lane_role": "kept_family",
                "observed_gate_verdict": "keep",
                "expected_gate_verdict": "keep",
                "phasea_gate_action_applied": 0,
                "action_behaved_as_expected": 1,
                "reference_resume_best_match_ratio": 0.476,
                "current_resume_best_match_ratio": 0.476,
                "delta_vs_reference_candidate": 0.0,
                "delta_vs_baseline": 0.068,
                "gate_checkpoint_share_of_reference_attempt": 0.44,
            },
            {
                "search_seed": 7004,
                "lane_role": "kept_family",
                "observed_gate_verdict": "keep",
                "expected_gate_verdict": "keep",
                "phasea_gate_action_applied": 0,
                "action_behaved_as_expected": 1,
                "reference_resume_best_match_ratio": 0.420,
                "current_resume_best_match_ratio": 0.420,
                "delta_vs_reference_candidate": 0.0,
                "delta_vs_baseline": -0.003,
                "gate_checkpoint_share_of_reference_attempt": 0.45,
            },
        ]
    )

    assert summary["completed_run_count"] == 3
    assert summary["verdict_match_count"] == 3
    assert summary["filtered_search_seed"] == 7002
    assert summary["filtered_behaved_as_expected"] == 1
    assert summary["kept_no_harm_count"] == 2
    assert summary["family_mean_delta_vs_baseline"] > 0.0


def test_recommendation_advances_on_clean_family_pass() -> None:
    recommendation = mod._build_recommendation(
        {
            "completed_run_count": 3,
            "filtered_behaved_as_expected": 1,
            "kept_no_harm_count": 2,
            "verdict_match_count": 3,
            "filtered_saved_attempt_share": 0.562,
        }
    )

    assert recommendation["recommendation"] == "advance"


def test_recommendation_holds_on_any_family_mismatch() -> None:
    recommendation = mod._build_recommendation(
        {
            "completed_run_count": 3,
            "filtered_behaved_as_expected": 1,
            "kept_no_harm_count": 1,
            "verdict_match_count": 2,
            "filtered_saved_attempt_share": 0.562,
        }
    )

    assert recommendation["recommendation"] == "hold"
