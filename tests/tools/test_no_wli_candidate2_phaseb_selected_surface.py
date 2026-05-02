from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_candidate2_phaseb_selected_surface_v1 as mod,
)


def test_build_phaseb_selected_surface_row_marks_unique_surface_as_non_engageable() -> None:
    panel_row = {
        "panel_job_index": "10",
        "fixture_seed": "611",
        "search_seed": "7005",
        "copied_report_dir": "50_completed_job_runs/demo_run",
    }
    best_instance = {
        "status": "unsolved",
        "best_stage": "stage3_full_refine",
        "best_match_ratio": 0.585,
        "stage3_diagnostics": {
            "phaseB_family_preservation_policy": "off",
            "phaseB_family_view_id": "prefix_hamming_le_24",
            "phaseB_family_reserved_slots": 0,
            "phaseB_family_count_in_top_band": 32,
            "phaseB_family_preserved_count": 32,
            "phaseB_family_reservation_applied": 0,
            "phaseB_selected_unique_end_hash": 32,
            "phaseB_downstream_selected_count": 32,
        },
    }

    row = mod.build_phaseb_selected_surface_row(
        panel_row=panel_row,
        best_instance=best_instance,
    )

    assert row["selected_surface_all_unique_families"] == 1
    assert row["repeated_family_row_count"] == 0
    assert row["candidate2_current_lever_can_engage"] == 0


def test_build_phaseb_selected_surface_row_marks_repeat_surface_as_engageable() -> None:
    panel_row = {
        "panel_job_index": "11",
        "fixture_seed": "1111",
        "search_seed": "7004",
        "copied_report_dir": "50_completed_job_runs/demo_run",
    }
    best_instance = {
        "status": "unsolved",
        "best_stage": "stage3_full_refine",
        "best_match_ratio": 0.406,
        "stage3_diagnostics": {
            "phaseB_family_preservation_policy": "reinforce_top_family_v1",
            "phaseB_family_view_id": "prefix_hamming_le_24",
            "phaseB_family_reserved_slots": 2,
            "phaseB_family_count_in_top_band": 28,
            "phaseB_family_preserved_count": 30,
            "phaseB_family_reservation_applied": 1,
            "phaseB_selected_unique_end_hash": 30,
            "phaseB_downstream_selected_count": 32,
        },
    }

    row = mod.build_phaseb_selected_surface_row(
        panel_row=panel_row,
        best_instance=best_instance,
    )

    assert row["selected_surface_all_unique_families"] == 0
    assert row["repeated_family_row_count"] == 2
    assert row["candidate2_current_lever_can_engage"] == 1


def test_build_phaseb_selected_surface_summary_counts_blocked_panel() -> None:
    rows = [
        {
            "fixture_seed": 611,
            "benchmark_case_role": "middle_unsolved_case",
            "repeated_family_row_count": 0,
            "selected_surface_all_unique_families": 1,
            "candidate2_current_lever_can_engage": 0,
        },
        {
            "fixture_seed": 1111,
            "benchmark_case_role": "conversion_failure_case",
            "repeated_family_row_count": 0,
            "selected_surface_all_unique_families": 1,
            "candidate2_current_lever_can_engage": 0,
        },
    ]

    summary = mod.build_phaseb_selected_surface_summary(rows)

    assert summary["run_count"] == 2
    assert summary["runs_with_repeat_families"] == 0
    assert summary["runs_where_current_candidate2_lever_can_engage"] == 0
    assert summary["current_candidate2_lever_structurally_blocked_on_panel"] == 1
