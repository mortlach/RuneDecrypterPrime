from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    sweep_stage35_replay_configs as sweep_mod,
)


def test_stage35_sweep_variants_follow_expected_order() -> None:
    variant_ids = [row["variant_id"] for row in sweep_mod.STAGE35_SWEEP_VARIANTS]

    assert variant_ids == [
        "baseline",
        "top_symbols_8",
        "top_symbols_6",
        "beam_width_2",
        "beam_width_1",
        "final_keep_1",
        "archive_keep_8",
    ]


def test_build_variant_summary_reports_acceptance_split_and_baseline_ratios() -> None:
    summary = sweep_mod.build_variant_summary(
        {
            "variant_id": "beam_width_2",
            "knob": "beam_width",
            "cfg": {"beam_width": 2},
        },
        [
            {
                "selector": "legacy",
                "wallclock_seconds": 6.0,
                "evals": 2000,
                "telemetry_mini_search_proposals_generated": 1200,
                "telemetry_average_proposals_generated_per_mini": 100.0,
                "telemetry_row_scoring_seconds": 3.0,
                "telemetry_batch_score_seconds": 2.5,
                "telemetry_mini_search_total_seconds": 4.5,
                "accept_reason": "search_score_drop_guard_failed",
                "accept_passed": 0,
                "resume_best_truth_match": 0.038,
                "resume_best_score": 0.19,
            },
            {
                "selector": "score_plus_novelty",
                "wallclock_seconds": 12.0,
                "evals": 7000,
                "telemetry_mini_search_proposals_generated": 4200,
                "telemetry_average_proposals_generated_per_mini": 350.0,
                "telemetry_row_scoring_seconds": 9.0,
                "telemetry_batch_score_seconds": 7.0,
                "telemetry_mini_search_total_seconds": 11.0,
                "accept_reason": "accepted",
                "accept_passed": 1,
                "resume_best_truth_match": 0.48,
                "resume_best_score": 0.18,
            },
        ],
        baseline_candidate_row={
            "wallclock_seconds": 15.0,
            "telemetry_mini_search_proposals_generated": 6000,
            "telemetry_row_scoring_seconds": 12.0,
        },
    )

    assert summary["variant_id"] == "beam_width_2"
    assert summary["acceptance_split_preserved"] == 1
    assert summary["candidate_proposals_generated"] == 4200
    assert summary["candidate_runtime_vs_baseline_ratio"] == 12.0 / 15.0
    assert summary["candidate_proposals_vs_baseline_ratio"] == 4200.0 / 6000.0
    assert summary["candidate_row_scoring_vs_baseline_ratio"] == 9.0 / 12.0
