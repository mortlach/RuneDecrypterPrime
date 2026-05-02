from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    explore_phasec_saved_surface_policy_seed_sweep_v1 as mod,
)


def test_build_summary_counts_policy_rows_and_best_policies() -> None:
    rows = [
        {
            "policy_name": "phaseb_topk_anchor_swap_v1",
            "fixture_seed": 1511,
            "search_seed": 7005,
            "seed_offset": -1,
            "candidate_minus_control_best_match_ratio": 0.004,
            "candidate_best_match_ratio": 0.690,
            "candidate_effect": "positive",
        },
        {
            "policy_name": "phaseb_topk_frontload_all_v1",
            "fixture_seed": 1511,
            "search_seed": 7005,
            "seed_offset": -1,
            "candidate_minus_control_best_match_ratio": 0.008,
            "candidate_best_match_ratio": 0.694,
            "candidate_effect": "positive",
        },
        {
            "policy_name": "phaseb_topk_anchor_swap_v1",
            "fixture_seed": 1511,
            "search_seed": 7005,
            "seed_offset": 0,
            "candidate_minus_control_best_match_ratio": 0.000,
            "candidate_best_match_ratio": 0.686,
            "candidate_effect": "neutral",
        },
        {
            "policy_name": "phaseb_topk_frontload_all_v1",
            "fixture_seed": 1511,
            "search_seed": 7005,
            "seed_offset": 0,
            "candidate_minus_control_best_match_ratio": 0.009,
            "candidate_best_match_ratio": 0.695,
            "candidate_effect": "positive",
        },
    ]

    summary = mod.build_summary(rows)

    assert int(summary["case_count"]) == 1
    assert int(summary["seed_offset_count"]) == 2
    assert list(summary["policy_summary_rows"]) == [
        {
            "policy_name": "phaseb_topk_anchor_swap_v1",
            "row_count": 2,
            "positive_rows": 1,
            "neutral_rows": 1,
            "negative_rows": 0,
            "mean_delta_vs_control": 0.002,
        },
        {
            "policy_name": "phaseb_topk_frontload_all_v1",
            "row_count": 2,
            "positive_rows": 2,
            "neutral_rows": 0,
            "negative_rows": 0,
            "mean_delta_vs_control": 0.0085,
        },
    ]
    assert list(summary["best_policy_rows"]) == [
        {
            "fixture_seed": 1511,
            "search_seed": 7005,
            "seed_offset": -1,
            "best_policy_name": "phaseb_topk_frontload_all_v1",
            "best_candidate_best_match_ratio": 0.694,
            "best_candidate_minus_control": 0.008,
        },
        {
            "fixture_seed": 1511,
            "search_seed": 7005,
            "seed_offset": 0,
            "best_policy_name": "phaseb_topk_frontload_all_v1",
            "best_candidate_best_match_ratio": 0.695,
            "best_candidate_minus_control": 0.009,
        },
    ]
