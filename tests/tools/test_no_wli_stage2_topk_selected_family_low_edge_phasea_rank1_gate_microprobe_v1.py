from __future__ import annotations

import math

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1 as mod,
)


def test_phasea_gate_proxy_elapsed_seconds_uses_first_phaseb_row() -> None:
    progress_rows = [
        {"phase": "phaseA", "elapsed_seconds": 12.0, "phaseA_done": 1},
        {"phase": "phaseB", "elapsed_seconds": 53.5},
        {"phase": "phaseB", "elapsed_seconds": 75.0},
    ]
    assert math.isclose(mod._phasea_gate_proxy_elapsed_seconds(progress_rows), 53.5)


def test_build_counterfactual_row_falls_back_and_saves_time() -> None:
    row = mod.build_counterfactual_row(
        matrix_row={
            "fixture_seed": 1111,
            "search_seed": 7002,
            "output_dir": "output/example",
            "baseline_best_match_ratio": 0.754,
            "retained_stage3_reference_match_ratio": 0.752,
            "resume_best_match_ratio": 0.310,
        },
        case_row={
            "case_category": "phasea_competitiveness_below_floor",
            "phasea_rank1_init_match": 0.289,
        },
        attempt_status={"elapsed_seconds": 1330.0, "status": "completed"},
        resume_status={"flow_elapsed_seconds": 1328.0, "stop_reason": "stalled_no_improve"},
        gate_proxy_elapsed_seconds=51.0,
    )
    assert row["gate_kept"] == 0
    assert row["counterfactual_mode"] == "baseline_fallback_after_phasea"
    assert math.isclose(row["counterfactual_best_match_ratio"], 0.754)
    assert math.isclose(row["counterfactual_delta_vs_baseline"], 0.0)
    assert math.isclose(row["counterfactual_delta_vs_retained_stage3_reference"], 0.002)
    assert math.isclose(row["estimated_saved_attempt_seconds"], 1279.0)


def test_build_recommendation_advances_for_positive_and_cheap_gate() -> None:
    recommendation = mod.build_recommendation(
        {
            "counterfactual_family_mean_delta_vs_baseline": 0.0212,
            "counterfactual_family_worst_delta_vs_baseline": -0.003,
            "filtered_estimated_saved_attempt_share": 0.96,
            "filtered_run_count": 2,
        }
    )
    assert recommendation["recommendation"] == "advance"
    assert (
        recommendation["next_branch_label"]
        == "stage2_topk_selected_family_low_edge_phasea_rank1_gate_persistence_microprobe"
    )
