from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1 as mod,
)


def test_extract_readout_recommendation() -> None:
    text = "\n".join(
        [
            "Recommendation:",
            "- `hold`",
            "- next branch: `x`",
        ]
    )

    assert mod._extract_readout_recommendation(text) == "hold"


def test_build_row_check_recomputes_filtered_family_mismatch() -> None:
    row = mod._build_row_check(
        {
            "search_seed": 7002,
            "lane_role": "filtered_family",
            "observed_gate_verdict": "filter",
            "expected_gate_verdict": "filter",
            "phasea_gate_action_applied": 1,
            "baseline_best_match_ratio": 0.754,
            "reference_resume_best_match_ratio": 0.310,
            "current_resume_best_match_ratio": 0.754,
            "action_behaved_as_expected": 0,
        }
    )

    assert row["saved_action_behaved_as_expected"] == 0
    assert row["recomputed_action_behaved_as_expected"] == 1
    assert row["row_mismatch"] == 1


def test_build_summary_row_flags_summary_recommendation_split() -> None:
    summary_row = mod._build_summary_row(
        row_checks=[
            {
                "search_seed": 7002,
                "row_mismatch": 1,
            }
        ],
        summary_payload={
            "summary_row": {
                "completed_run_count": 3,
                "filtered_behaved_as_expected": 1,
                "kept_no_harm_count": 2,
                "verdict_match_count": 3,
                "filtered_saved_attempt_share": 0.570,
            }
        },
        state_payload={"recommendation": {"recommendation": "hold"}},
        final_event={"recommendation": "hold"},
        recommendation_payload={"recommendation": "advance"},
        readout_recommendation="advance",
    )

    assert summary_row["summary_recomputed_recommendation"] == "advance"
    assert summary_row["state_recommendation"] == "hold"
    assert summary_row["event_recommendation"] == "hold"
    assert summary_row["recommendation_json_recommendation"] == "advance"
    assert summary_row["readout_recommendation"] == "advance"
    assert summary_row["recommendation_values_present"] == 1
    assert summary_row["missing_recommendation_layers"] == []
    assert summary_row["recommendation_values_match"] == 0
    assert summary_row["row_mismatch_count"] == 1
    assert summary_row["mismatched_search_seeds"] == [7002]


def test_build_summary_row_flags_incomplete_bundle() -> None:
    summary_row = mod._build_summary_row(
        row_checks=[
            {
                "search_seed": 7002,
                "row_mismatch": 0,
            },
            {
                "search_seed": 7003,
                "row_mismatch": 0,
            },
        ],
        summary_payload={
            "summary_row": {
                "completed_run_count": 2,
                "filtered_behaved_as_expected": 1,
                "kept_no_harm_count": 1,
                "verdict_match_count": 2,
                "filtered_saved_attempt_share": -0.240,
            }
        },
        state_payload={
            "status": "stopped_over_budget",
            "completed_jobs": 2,
            "planned_jobs": 3,
            "recommendation": {"recommendation": "hold"},
        },
        final_event={"recommendation": "hold"},
        recommendation_payload={"recommendation": "hold"},
        readout_recommendation="hold",
    )

    assert summary_row["bundle_complete"] == 0
    assert summary_row["completed_jobs"] == 2
    assert summary_row["planned_jobs"] == 3
    assert summary_row["row_mismatch_count"] == 0
    assert summary_row["recommendation_values_match"] == 1


def test_build_summary_row_fails_missing_recommendation_layer() -> None:
    summary_row = mod._build_summary_row(
        row_checks=[
            {
                "search_seed": 7002,
                "row_mismatch": 0,
            },
        ],
        summary_payload={
            "summary_row": {
                "completed_run_count": 1,
                "filtered_behaved_as_expected": 1,
                "kept_no_harm_count": 0,
                "verdict_match_count": 1,
                "filtered_saved_attempt_share": 0.570,
            }
        },
        state_payload={
            "status": "completed",
            "completed_jobs": 1,
            "planned_jobs": 1,
            "recommendation": {"recommendation": "advance"},
        },
        final_event={"recommendation": "advance"},
        recommendation_payload={"recommendation": "advance"},
        readout_recommendation="",
    )

    assert summary_row["recommendation_values_present"] == 0
    assert summary_row["missing_recommendation_layers"] == ["readout"]
    assert summary_row["recommendation_values_match"] == 0
