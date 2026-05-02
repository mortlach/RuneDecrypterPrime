from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    explore_phasec_saved_surface_policy_variants_v1 as mod,
)


def test_annotate_against_anchor_swap_computes_policy_deltas() -> None:
    rows = [
        {
            "policy_name": mod.ANCHOR_SWAP_POLICY_NAME,
            "fixture_seed": 1111,
            "search_seed": 7002,
            "candidate_best_match_ratio": 0.754,
        },
        {
            "policy_name": "phaseb_topk_frontload_two_v1",
            "fixture_seed": 1111,
            "search_seed": 7002,
            "candidate_best_match_ratio": 0.756,
        },
        {
            "policy_name": "phaseb_topk_frontload_all_v1",
            "fixture_seed": 1111,
            "search_seed": 7002,
            "candidate_best_match_ratio": 0.7535,
        },
    ]

    out = mod.annotate_against_anchor_swap(rows)

    frontload_two = next(
        row for row in out if str(row.get("policy_name")) == "phaseb_topk_frontload_two_v1"
    )
    frontload_all = next(
        row for row in out if str(row.get("policy_name")) == "phaseb_topk_frontload_all_v1"
    )
    assert float(frontload_two["vs_anchor_swap_delta"]) == pytest.approx(0.002)
    assert str(frontload_two["vs_anchor_swap_read"]) == "positive"
    assert float(frontload_all["vs_anchor_swap_delta"]) == pytest.approx(-0.0005)
    assert str(frontload_all["vs_anchor_swap_read"]) == "neutral"


def test_build_summary_counts_policy_rows_and_best_policy_by_case() -> None:
    rows = [
        {
            "policy_name": mod.ANCHOR_SWAP_POLICY_NAME,
            "fixture_seed": 611,
            "search_seed": 7003,
            "usable_decision_gate": 1,
            "candidate_effect": "positive",
            "candidate_minus_control_best_match_ratio": 0.006,
            "candidate_best_match_ratio": 0.472,
            "vs_anchor_swap_read": "neutral",
        },
        {
            "policy_name": "phaseb_topk_frontload_two_v1",
            "fixture_seed": 611,
            "search_seed": 7003,
            "usable_decision_gate": 1,
            "candidate_effect": "positive",
            "candidate_minus_control_best_match_ratio": 0.008,
            "candidate_best_match_ratio": 0.474,
            "vs_anchor_swap_read": "positive",
        },
        {
            "policy_name": "phaseb_topk_frontload_all_v1",
            "fixture_seed": 611,
            "search_seed": 7003,
            "usable_decision_gate": 1,
            "candidate_effect": "neutral",
            "candidate_minus_control_best_match_ratio": 0.001,
            "candidate_best_match_ratio": 0.467,
            "vs_anchor_swap_read": "negative",
        },
    ]

    summary = mod.build_summary(rows)

    assert int(summary["case_count"]) == 1
    policy_rows = list(summary["policy_summary_rows"])
    assert policy_rows == [
        {
            "policy_name": mod.ANCHOR_SWAP_POLICY_NAME,
            "case_count": 1,
            "usable_decision_gate_cases": 1,
            "positive_on_gate": 1,
            "neutral_on_gate": 0,
            "negative_on_gate": 0,
            "mean_delta_on_gate": 0.006,
            "better_than_anchor_swap_on_gate": 0,
            "equal_to_anchor_swap_on_gate": 1,
            "worse_than_anchor_swap_on_gate": 0,
        },
        {
            "policy_name": "phaseb_topk_frontload_all_v1",
            "case_count": 1,
            "usable_decision_gate_cases": 1,
            "positive_on_gate": 0,
            "neutral_on_gate": 1,
            "negative_on_gate": 0,
            "mean_delta_on_gate": 0.001,
            "better_than_anchor_swap_on_gate": 0,
            "equal_to_anchor_swap_on_gate": 0,
            "worse_than_anchor_swap_on_gate": 1,
        },
        {
            "policy_name": "phaseb_topk_frontload_two_v1",
            "case_count": 1,
            "usable_decision_gate_cases": 1,
            "positive_on_gate": 1,
            "neutral_on_gate": 0,
            "negative_on_gate": 0,
            "mean_delta_on_gate": 0.008,
            "better_than_anchor_swap_on_gate": 1,
            "equal_to_anchor_swap_on_gate": 0,
            "worse_than_anchor_swap_on_gate": 0,
        },
    ]
    assert list(summary["best_policy_by_case_rows"]) == [
        {
            "fixture_seed": 611,
            "search_seed": 7003,
            "best_policy_name": "phaseb_topk_frontload_two_v1",
            "best_candidate_best_match_ratio": 0.474,
            "best_candidate_minus_control": 0.008,
        }
    ]
