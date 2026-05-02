from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    explore_phasec_saved_surface_phaseb_mass_and_frontload_matrix_v1 as mod,
)


def test_build_surface_diagnostics_classifies_active_flat_surface_change() -> None:
    control_summary = {
        "start_identities": [
            {"candidate_hash": "anchor", "source": "stage3_best_phaseA"},
            {"candidate_hash": "a", "source": "phaseA_selected"},
            {"candidate_hash": "b", "source": "phaseB_topk"},
        ],
        "winner_lane": "challenger",
        "winner_source": "phaseB_topk",
        "winner_source_rank": 2,
        "winner_candidate_hash": "b",
    }
    candidate_summary = {
        "start_identities": [
            {"candidate_hash": "anchor", "source": "stage3_best_phaseA"},
            {
                "candidate_hash": "b",
                "source": "phaseB_topk",
                "selection_bucket": "phaseb_topk_frontload_depth",
            },
            {"candidate_hash": "a", "source": "phaseA_selected"},
        ],
        "winner_lane": "challenger",
        "winner_source": "phaseB_topk",
        "winner_source_rank": 2,
        "winner_candidate_hash": "b",
    }
    comparison_summary = {
        "candidate_reordered_surface": 1,
        "candidate_minus_control_best_match_ratio": 0.0,
        "control_winner_lane": "challenger",
        "control_winner_source": "phaseB_topk",
        "control_winner_source_rank": 2,
        "control_winner_candidate_hash": "b",
        "candidate_winner_lane": "challenger",
        "candidate_winner_source": "phaseB_topk",
        "candidate_winner_source_rank": 2,
        "candidate_winner_candidate_hash": "b",
    }

    diagnostics = mod.build_surface_diagnostics(
        control_summary=control_summary,
        candidate_summary=candidate_summary,
        comparison_summary=comparison_summary,
        candidate_rows=None,
        policy_group=mod.FRONTLOAD_DEPTH_POLICY_GROUP,
    )

    assert diagnostics["selected_surface_changed"] == 1
    assert diagnostics["selected_surface_membership_changed"] == 0
    assert diagnostics["winner_identity_changed"] == 0
    assert diagnostics["flat_delta_case_class"] == "active_surface_change_same_winner_flat"


def test_build_recommendation_closes_when_no_family_beats_controls() -> None:
    recommendation = mod.build_recommendation(
        summary={
            "policy_family_summary_rows": [
                {
                    "policy_family": mod.FRONTLOAD_DEPTH_POLICY_GROUP,
                    "best_policy_name": "phaseb_topk_frontload_2_v1",
                    "best_requested_width": "2",
                    "best_mean_vs_best_reorder_on_gate": -0.001,
                    "best_better_than_best_reorder_on_gate": 1,
                    "best_worse_than_best_reorder_on_gate": 2,
                    "best_negative_on_gate": 2,
                    "best_positive_on_gate": 1,
                    "best_active_surface_change_same_winner_flat_cases": 0,
                }
            ]
        }
    )

    assert recommendation["recommendation"] == "close"


def test_build_recommendation_refines_when_hidden_signal_exists() -> None:
    recommendation = mod.build_recommendation(
        summary={
            "policy_family_summary_rows": [
                {
                    "policy_family": mod.PHASEB_TOPK_QUOTA_POLICY_GROUP,
                    "best_policy_name": "phaseb_topk_quota_3_v1",
                    "best_requested_width": "3",
                    "best_mean_vs_best_reorder_on_gate": -0.0005,
                    "best_better_than_best_reorder_on_gate": 1,
                    "best_worse_than_best_reorder_on_gate": 1,
                    "best_negative_on_gate": 1,
                    "best_positive_on_gate": 1,
                    "best_active_surface_change_same_winner_flat_cases": 5,
                }
            ]
        }
    )

    assert recommendation["recommendation"] == "refine"


def test_build_recommendation_promotes_when_family_is_cleanly_stronger() -> None:
    recommendation = mod.build_recommendation(
        summary={
            "policy_family_summary_rows": [
                {
                    "policy_family": mod.PHASEB_TOPK_ONLY_REPLACEMENT_POLICY_GROUP,
                    "best_policy_name": "phaseb_topk_replace_width_2_v1",
                    "best_requested_width": "2",
                    "best_mean_vs_best_reorder_on_gate": 0.004,
                    "best_better_than_best_reorder_on_gate": 5,
                    "best_worse_than_best_reorder_on_gate": 0,
                    "best_negative_on_gate": 1,
                    "best_positive_on_gate": 5,
                    "best_active_surface_change_same_winner_flat_cases": 1,
                }
            ]
        }
    )

    assert recommendation["recommendation"] == "promote"
