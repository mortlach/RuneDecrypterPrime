from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    explore_phasec_saved_surface_pool_replacement_matrix_v1 as mod,
)


def test_build_source_order_rows_synthesizes_control_policy() -> None:
    rows = mod.build_source_order_rows(
        [
            {
                "fixture_seed": 1111,
                "search_seed": 7002,
                "bundle_relpath": "output/mock_bundle",
                "source_artifact_relpath": "output/mock.json",
                "retained_stage3_reference_match_ratio": 0.752,
                "control_best_match_ratio": 0.750,
                "control_fidelity_quality": "near_stable",
                "usable_decision_gate": 1,
                "control_winner_source": "phaseB_topk",
                "control_winner_candidate_hash": "winner-a",
            }
        ]
    )

    assert rows == [
        {
            "policy_name": mod.SOURCE_ORDER_POLICY_NAME,
            "policy_group": "control",
            "replacement_width": "",
            "fixture_seed": 1111,
            "search_seed": 7002,
            "bundle_relpath": "output/mock_bundle",
            "source_artifact_relpath": "output/mock.json",
            "retained_stage3_reference_match_ratio": 0.752,
            "control_best_match_ratio": 0.75,
            "candidate_best_match_ratio": 0.75,
            "candidate_minus_control_best_match_ratio": 0.0,
            "candidate_reordered_surface": 0,
            "control_fidelity_quality": "near_stable",
            "usable_decision_gate": 1,
            "candidate_effect": "neutral",
            "decision_gate_read": "neutral",
            "control_winner_source": "phaseB_topk",
            "candidate_winner_source": "phaseB_topk",
            "candidate_winner_candidate_hash": "winner-a",
        }
    ]


def test_annotate_against_best_reorder_control_uses_best_reorder_by_case() -> None:
    rows = [
        {
            "policy_name": mod.SOURCE_ORDER_POLICY_NAME,
            "policy_group": "control",
            "fixture_seed": 611,
            "search_seed": 7003,
            "candidate_best_match_ratio": 0.466,
        },
        {
            "policy_name": mod.ANCHOR_SWAP_POLICY_NAME,
            "policy_group": "reorder_control",
            "fixture_seed": 611,
            "search_seed": 7003,
            "candidate_best_match_ratio": 0.472,
        },
        {
            "policy_name": mod.FRONTLOAD_ALL_POLICY_NAME,
            "policy_group": "reorder_control",
            "fixture_seed": 611,
            "search_seed": 7003,
            "candidate_best_match_ratio": 0.469,
        },
        {
            "policy_name": "pool_replace_width_1_v1",
            "policy_group": "replacement",
            "fixture_seed": 611,
            "search_seed": 7003,
            "candidate_best_match_ratio": 0.475,
        },
    ]

    out = mod.annotate_against_best_reorder_control(rows)

    replacement_row = next(
        row for row in out if str(row.get("policy_name")) == "pool_replace_width_1_v1"
    )
    source_order_row = next(
        row for row in out if str(row.get("policy_name")) == mod.SOURCE_ORDER_POLICY_NAME
    )
    assert str(replacement_row["best_reorder_policy_name"]) == mod.ANCHOR_SWAP_POLICY_NAME
    assert float(replacement_row["vs_best_reorder_delta"]) == pytest.approx(0.003)
    assert str(replacement_row["vs_best_reorder_read"]) == "positive"
    assert float(source_order_row["vs_best_reorder_delta"]) == pytest.approx(-0.006)


def test_build_recommendation_closes_when_replacement_does_not_beat_reorder_controls() -> None:
    recommendation = mod.build_recommendation(
        summary={
            "policy_summary_rows": [
                {
                    "policy_name": "pool_replace_width_1_v1",
                    "policy_group": "replacement",
                    "replacement_width": "1",
                    "mean_vs_best_reorder_on_gate": -0.001,
                    "better_than_best_reorder_on_gate": 1,
                    "worse_than_best_reorder_on_gate": 2,
                    "positive_on_gate": 1,
                    "negative_on_gate": 2,
                },
                {
                    "policy_name": "pool_replace_width_2_v1",
                    "policy_group": "replacement",
                    "replacement_width": "2",
                    "mean_vs_best_reorder_on_gate": 0.0,
                    "better_than_best_reorder_on_gate": 1,
                    "worse_than_best_reorder_on_gate": 1,
                    "positive_on_gate": 1,
                    "negative_on_gate": 1,
                },
            ]
        }
    )

    assert recommendation == {
        "recommendation": "close",
        "best_replacement_policy_name": "pool_replace_width_2_v1",
        "best_replacement_width": "2",
        "reason": (
            "Replacement widths do not beat the reorder-only controls on usable "
            "decision gates."
        ),
    }


def test_build_recommendation_refines_when_signal_is_mixed() -> None:
    recommendation = mod.build_recommendation(
        summary={
            "policy_summary_rows": [
                {
                    "policy_name": "pool_replace_width_2_v1",
                    "policy_group": "replacement",
                    "replacement_width": "2",
                    "mean_vs_best_reorder_on_gate": 0.002,
                    "better_than_best_reorder_on_gate": 4,
                    "worse_than_best_reorder_on_gate": 2,
                    "positive_on_gate": 4,
                    "negative_on_gate": 1,
                }
            ]
        }
    )

    assert recommendation["recommendation"] == "refine"


def test_build_recommendation_promotes_when_one_width_is_clearly_cleaner() -> None:
    recommendation = mod.build_recommendation(
        summary={
            "policy_summary_rows": [
                {
                    "policy_name": "pool_replace_width_1_v1",
                    "policy_group": "replacement",
                    "replacement_width": "1",
                    "mean_vs_best_reorder_on_gate": 0.004,
                    "better_than_best_reorder_on_gate": 5,
                    "worse_than_best_reorder_on_gate": 0,
                    "positive_on_gate": 5,
                    "negative_on_gate": 1,
                }
            ]
        }
    )

    assert recommendation["recommendation"] == "promote"
