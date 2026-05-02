from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_v1 as mod,
)


def test_summary_advances_when_7003_is_stable_and_7004_is_broadly_slow() -> None:
    summary = mod._build_summary(
        [
            {
                "row_id": "7003_reference_exact",
                "elapsed_seconds": 1314.4,
                "phaseb_step2112_elapsed_seconds": 150.1,
            },
            {
                "row_id": "7003_family_microbatch",
                "elapsed_seconds": 1323.0,
                "phaseb_step2112_elapsed_seconds": 149.6,
            },
            {
                "row_id": "7004_reference_anchor",
                "elapsed_seconds": 1457.4,
            },
            {
                "row_id": "7004_reference_latest",
                "elapsed_seconds": 1371.9,
                "restart64_provisional_elapsed_seconds": 1150.6,
                "phaseb_step2112_elapsed_seconds": 153.4,
            },
            {
                "row_id": "7004_family_microbatch",
                "elapsed_seconds": 2257.5,
                "restart64_provisional_elapsed_seconds": 1746.2,
                "phaseb_step2112_elapsed_seconds": 379.6,
                "first_gate_decision_restart_count": 32,
                "first_gate_decision_elapsed_share": 0.269,
                "gate_decision_event_count": 3,
            },
        ]
    )

    assert summary["recommendation"] == "advance"
    assert summary["review_ready"] == 1
    assert summary["live_runtime_reopen_recommended"] == 0


def test_summary_refines_when_control_is_not_stable() -> None:
    summary = mod._build_summary(
        [
            {
                "row_id": "7003_reference_exact",
                "elapsed_seconds": 1314.4,
                "phaseb_step2112_elapsed_seconds": 150.1,
            },
            {
                "row_id": "7003_family_microbatch",
                "elapsed_seconds": 1700.0,
                "phaseb_step2112_elapsed_seconds": 220.0,
            },
            {
                "row_id": "7004_reference_anchor",
                "elapsed_seconds": 1457.4,
            },
            {
                "row_id": "7004_reference_latest",
                "elapsed_seconds": 1371.9,
                "restart64_provisional_elapsed_seconds": 1150.6,
                "phaseb_step2112_elapsed_seconds": 153.4,
            },
            {
                "row_id": "7004_family_microbatch",
                "elapsed_seconds": 2257.5,
                "restart64_provisional_elapsed_seconds": 1746.2,
                "phaseb_step2112_elapsed_seconds": 379.6,
                "first_gate_decision_restart_count": 32,
                "first_gate_decision_elapsed_share": 0.269,
                "gate_decision_event_count": 3,
            },
        ]
    )

    assert summary["recommendation"] == "refine"
    assert summary["review_ready"] == 0
