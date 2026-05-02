from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_preflight_v1 as mod,
)


def test_preflight_row_passes_for_current_harness_summary() -> None:
    raw_summary = mod.live_mod.build_preflight_summary()
    row = mod.build_preflight_row(raw_summary)
    recommendation = mod.build_recommendation(row)

    assert row["preflight_checks_passed"] == 1
    assert row["failed_checks"] == []
    assert recommendation["recommendation"] == "advance"


def test_preflight_row_fails_missing_decision_field() -> None:
    raw_summary = mod.live_mod.build_preflight_summary()
    raw_summary["missing_decision_fields"] = ["action_decision_id"]

    row = mod.build_preflight_row(raw_summary)
    recommendation = mod.build_recommendation(row)

    assert row["decision_fields_present"] == 0
    assert row["failed_checks"] == ["decision_fields_present"]
    assert recommendation["recommendation"] == "hold"
