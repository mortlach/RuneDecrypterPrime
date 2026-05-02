from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1 as mod,
)


def test_live_canary_decider_defers_before_restart32() -> None:
    decider = mod._build_phasea_provisional_gate_action_decider(
        reference_row={
            "baseline_best_match_ratio": 0.754,
            "baseline_best_stage": "stage3_full_refine",
        },
        expected_gate_verdict="filter",
    )

    decision = decider(
        {
            "phaseA_checkpoint_restart_count": 16,
            "phaseA_best_init_match": 0.378,
        }
    )

    assert decision == {}


def test_live_canary_decider_filters_with_required_fields() -> None:
    decider = mod._build_phasea_provisional_gate_action_decider(
        reference_row={
            "baseline_best_match_ratio": 0.754,
            "baseline_best_stage": "stage3_full_refine",
        },
        expected_gate_verdict="filter",
    )

    decision = decider(
        {
            "phaseA_checkpoint_restart_count": 32,
            "phaseA_best_init_match": 0.378,
        }
    )

    assert decision["gate_verdict"] == "filter"
    assert decision["action_stop_now"] == 1
    assert decision["action_fallback_to_baseline"] == 1
    assert decision["fallback_target"] == "retained_baseline"
    assert decision["threshold"] == 0.3865
    assert decision["phaseA_best_init_match"] == 0.378
    assert not [
        field_name
        for field_name in mod.REQUIRED_DECISION_FIELDS
        if decision.get(field_name) in (None, "")
    ]


def test_live_canary_decider_keeps_at_restart32() -> None:
    decider = mod._build_phasea_provisional_gate_action_decider(
        reference_row={
            "baseline_best_match_ratio": 0.408,
            "baseline_best_stage": "stage3_full_refine",
        },
        expected_gate_verdict="keep",
    )

    decision = decider(
        {
            "phaseA_checkpoint_restart_count": 32,
            "phaseA_best_init_match": 0.490,
        }
    )

    assert decision["gate_verdict"] == "keep"
    assert decision["action_stop_now"] == 0
    assert decision["action_fallback_to_baseline"] == 0
    assert decision["fallback_target"] == ""
    assert decision["phaseA_best_init_match"] == 0.490


def test_live_canary_launch_guard_blocks_runtime() -> None:
    payload = mod.run_live_canary()

    assert payload["status"] == "launch_blocked"
    assert payload["recommendation"] == "hold"


def test_live_canary_summary_holds_when_required_field_missing() -> None:
    row = {
        field_name: "x"
        for field_name in mod.REQUIRED_ROW_FIELDS
    }
    row.update(
        {
            "search_seed": 7002,
            "lane_role": "filtered_family",
            "observed_gate_verdict": "filter",
            "expected_gate_verdict": "filter",
            "phasea_gate_action_applied": 1,
            "action_stop_now": 1,
            "action_fallback_to_baseline": 1,
            "fallback_target": "retained_baseline",
            "gate_checkpoint_restart_count": 32,
            "phaseA_best_init_match": 0.378,
            "best_init_threshold": 0.3865,
            "action_behaved_as_expected": 1,
        }
    )
    row.pop("selector_id")

    summary = mod._summary_row([row])
    recommendation = mod._build_recommendation(summary)

    assert "selector_id" in summary["missing_required_row_fields"]
    assert recommendation["recommendation"] == "hold"


def test_live_canary_summary_advances_for_clean_filtered_row() -> None:
    row = {
        field_name: "x"
        for field_name in mod.REQUIRED_ROW_FIELDS
    }
    row.update(
        {
            "search_seed": 7002,
            "lane_role": "filtered_family",
            "observed_gate_verdict": "filter",
            "expected_gate_verdict": "filter",
            "phasea_gate_action_applied": 1,
            "action_stop_now": 1,
            "action_fallback_to_baseline": 1,
            "fallback_target": "retained_baseline",
            "gate_checkpoint_restart_count": 32,
            "phaseA_best_init_match": 0.378,
            "best_init_threshold": 0.3865,
            "actual_saved_attempt_seconds": 60.0,
            "actual_saved_attempt_share": 0.25,
            "delta_vs_baseline": 0.0,
            "delta_vs_reference_candidate": 0.444,
            "action_behaved_as_expected": 1,
        }
    )

    summary = mod._summary_row([row])
    recommendation = mod._build_recommendation(summary)

    assert summary["required_row_fields_present"] == 1
    assert recommendation["recommendation"] == "advance"


def test_live_canary_summary_advances_for_clean_kept_row() -> None:
    row = {
        field_name: "x"
        for field_name in mod.REQUIRED_ROW_FIELDS
    }
    row.update(
        {
            "search_seed": 7003,
            "lane_role": "kept_family",
            "observed_gate_verdict": "keep",
            "expected_gate_verdict": "keep",
            "phasea_gate_action_applied": 0,
            "action_stop_now": 0,
            "action_fallback_to_baseline": 0,
            "fallback_target": "",
            "gate_checkpoint_restart_count": 32,
            "phaseA_best_init_match": 0.490,
            "best_init_threshold": 0.3865,
            "actual_saved_attempt_seconds": -8.5,
            "actual_saved_attempt_share": -0.006,
            "delta_vs_baseline": 0.068,
            "delta_vs_reference_candidate": 0.0,
            "action_behaved_as_expected": 1,
        }
    )

    summary = mod._summary_row([row])
    recommendation = mod._build_recommendation(summary)

    assert summary["required_row_fields_present"] == 1
    assert recommendation["recommendation"] == "advance"
