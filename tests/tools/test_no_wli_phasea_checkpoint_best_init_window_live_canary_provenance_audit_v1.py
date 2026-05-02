from __future__ import annotations

from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1 as mod,
)


def _clean_summary_payload() -> dict[str, object]:
    return {
        "summary_row": {
            "completed_run_count": 1,
            "observed_gate_verdict": "filter",
            "expected_gate_verdict": "filter",
            "phasea_gate_action_applied": 1,
            "action_stop_now": 1,
            "action_fallback_to_baseline": 1,
            "fallback_target": "retained_baseline",
            "gate_checkpoint_restart_count": 32,
            "phaseA_best_init_match": 0.378,
            "action_behaved_as_expected": 1,
            "missing_required_row_fields": [],
        }
    }


def test_live_canary_audit_row_check_passes_clean_filtered_row() -> None:
    row = {
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
        "baseline_best_match_ratio": 0.754,
        "reference_resume_best_match_ratio": 0.310,
        "current_resume_best_match_ratio": 0.754,
        "action_behaved_as_expected": 1,
    }
    row.update({field_name: row.get(field_name, "x") for field_name in mod.live_mod.REQUIRED_ROW_FIELDS})

    check = mod._build_row_check(row)

    assert check["recomputed_action_behaved_as_expected"] == 1
    assert check["action_contract_ok"] == 1
    assert check["row_mismatch"] == 0


def test_live_canary_audit_row_check_passes_clean_kept_row() -> None:
    row = {
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
        "baseline_best_match_ratio": 0.408,
        "reference_resume_best_match_ratio": 0.476,
        "current_resume_best_match_ratio": 0.476,
        "action_behaved_as_expected": 1,
    }
    row.update({field_name: row.get(field_name, "x") for field_name in mod.live_mod.REQUIRED_ROW_FIELDS})

    check = mod._build_row_check(row)

    assert check["recomputed_action_behaved_as_expected"] == 1
    assert check["action_contract_ok"] == 1
    assert check["row_mismatch"] == 0


def test_live_canary_audit_fails_missing_recommendation_layer() -> None:
    summary_row = mod._build_summary_row(
        row_checks=[
            {
                "search_seed": 7002,
                "row_mismatch": 0,
            }
        ],
        summary_payload=_clean_summary_payload(),
        state_payload={
            "status": "completed",
            "completed_jobs": 1,
            "planned_jobs": 1,
            "recommendation": {"recommendation": "advance"},
        },
        final_event={"recommendation": "advance"},
        recommendation_payload={"recommendation": "advance"},
        readout_recommendation="",
        source_bundle_dir=Path("output/source"),
    )
    recommendation = mod._build_recommendation(summary_row)

    assert summary_row["recommendation_values_present"] == 0
    assert summary_row["missing_recommendation_layers"] == ["readout"]
    assert summary_row["recommendation_values_match"] == 0
    assert recommendation["recommendation"] == "hold"


def test_live_canary_audit_advances_clean_bundle_summary() -> None:
    summary_row = mod._build_summary_row(
        row_checks=[
            {
                "search_seed": 7002,
                "row_mismatch": 0,
            }
        ],
        summary_payload=_clean_summary_payload(),
        state_payload={
            "status": "completed",
            "completed_jobs": 1,
            "planned_jobs": 1,
            "recommendation": {"recommendation": "advance"},
        },
        final_event={"recommendation": "advance"},
        recommendation_payload={"recommendation": "advance"},
        readout_recommendation="advance",
        source_bundle_dir=Path("output/source"),
    )
    recommendation = mod._build_recommendation(summary_row)

    assert summary_row["recommendation_values_present"] == 1
    assert summary_row["recommendation_values_match"] == 1
    assert summary_row["row_mismatch_count"] == 0
    assert recommendation["recommendation"] == "advance"
