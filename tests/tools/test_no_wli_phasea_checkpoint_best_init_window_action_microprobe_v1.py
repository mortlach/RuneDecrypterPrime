from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1 as mod,
)


def test_decider_defers_before_restart32() -> None:
    decider = mod._build_phasea_provisional_gate_action_decider(
        reference_row={
            "baseline_best_match_ratio": 0.428,
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


def test_decider_filters_at_restart32_when_below_threshold() -> None:
    decider = mod._build_phasea_provisional_gate_action_decider(
        reference_row={
            "baseline_best_match_ratio": 0.428,
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
    assert decision["trigger_source"] == "best_init_window_filter"


def test_decider_keeps_at_restart32_when_above_threshold() -> None:
    decider = mod._build_phasea_provisional_gate_action_decider(
        reference_row={
            "baseline_best_match_ratio": 0.372,
            "baseline_best_stage": "stage3_full_refine",
        },
        expected_gate_verdict="keep",
    )

    decision = decider(
        {
            "phaseA_checkpoint_restart_count": 32,
            "phaseA_best_init_match": 0.395,
        }
    )

    assert decision["gate_verdict"] == "keep"
    assert decision["action_stop_now"] == 0
    assert decision["trigger_source"] == "best_init_window_keep"
