from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    verify_candidate2_top_family_reinforce_exact_replay as mod,
)


def test_family_counts_label_is_sorted_by_count_then_family() -> None:
    rows = [
        {"family_id": "f1"},
        {"family_id": "f0"},
        {"family_id": "f1"},
        {"family_id": "f2"},
        {"family_id": ""},
    ]

    label = mod._family_counts_label(rows)

    assert label == "f1:2, f0:1, f2:1"


def test_build_candidate2_exact_replay_summary_keeps_family_and_match_fields() -> None:
    case = type(
        "Case",
        (),
        {
            "artifact_path": Path(
                "output/tools/benchmarks/periodic_sub_trans/no_wli/mock/final.json"
            ),
            "run_dir": Path(
                "output/tools/benchmarks/periodic_sub_trans/no_wli/mock/run_dir"
            ),
            "artifact": {
                "instance_source_key_seed": 611,
                "search_seed": 7005,
                "best_stage": "stage3_full_refine",
                "best_match_ratio": 0.585,
            },
        },
    )()
    payload = {
        "resume_source": "saved_live_stage2_resume_rebuilt_prep",
        "stage35_enabled_effective": 0,
        "resume_best_stage": "stage3_full_refine",
        "resume_best_match_ratio": 0.612,
        "resume_best_score": 0.123,
        "stage3_flow": {
            "phaseB_family_preservation_policy": "reinforce_top_family_v1",
            "phaseB_family_view_id": "prefix_hamming_le_24",
            "phaseB_family_reserved_slots": 2,
            "phaseB_family_count_in_top_band": 3,
            "phaseB_family_preserved_count": 1,
            "phaseB_family_reservation_applied": 1,
            "phaseB_downstream_selected_count": 4,
            "phaseB_downstream_selected_unique_end_hash": 4,
            "phaseB_downstream_selected_summaries": [
                {"family_id": "f0"},
                {"family_id": "f0"},
                {"family_id": "f1"},
                {"family_id": ""},
            ],
            "phaseC_ran": 1,
            "phaseC_start_keys_used": 6,
            "phaseC_start_policy": "source_order",
        },
        "outcome": {
            "stage35_used_for_final_best": 0,
            "status": "unsolved",
        },
    }

    summary = mod.build_candidate2_exact_replay_summary(case=case, payload=payload)

    assert summary["fixture_seed"] == 611
    assert summary["search_seed"] == 7005
    assert summary["baseline_best_match_ratio"] == pytest.approx(0.585)
    assert summary["resume_best_match_ratio"] == pytest.approx(0.612)
    assert summary["match_delta_vs_baseline"] == pytest.approx(0.027)
    assert summary["phaseb_family_preservation_policy"] == "reinforce_top_family_v1"
    assert summary["phaseb_downstream_selected_family_counts"] == "f0:2, f1:1"
    assert summary["phasec_ran"] == 1
    assert summary["outcome_stage35_used_for_final_best"] == 0
