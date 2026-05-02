from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    explore_phasec_richer_pool_phaseb_replacement_reopen_v1 as mod,
)


def test_control_comparison_summary_is_neutral_clone() -> None:
    class DummyCase:
        artifact_path = mod.REPO_ROOT / "output/mock_case.json"
        artifact = {
            "instance_source_key_seed": 1111,
            "search_seed": 7002,
        }

    control_summary = {
        "best_match_ratio": 0.75,
        "pre_phasec_best_match": 0.734,
        "winner_lane": "anchor",
        "winner_source": "stage3_best_phaseB",
        "winner_source_rank": 1,
        "winner_candidate_hash": "winner-hash",
        "phasec_evals": 123,
        "start_identities": [
            {"candidate_hash": "winner-hash"},
            {"candidate_hash": "challenger-a"},
        ],
    }

    original_extract = mod.exact_mod.retained_mod.extract_retained_stage3_reference
    mod.exact_mod.retained_mod.extract_retained_stage3_reference = lambda artifact: {
        "match_ratio": 0.754,
        "source": "retained_stage3",
        "stage3_source": "stage3_best_phaseB",
        "candidate_hash": "winner-hash",
    }
    try:
        summary = mod._build_control_comparison_summary(
            case=DummyCase(),
            control_summary=control_summary,
        )
    finally:
        mod.exact_mod.retained_mod.extract_retained_stage3_reference = original_extract

    assert summary["candidate_best_match_ratio"] == 0.75
    assert summary["candidate_minus_control_best_match_ratio"] == 0.0
    assert summary["candidate_reordered_surface"] == 0
    assert summary["candidate_winner_candidate_hash"] == "winner-hash"


def test_annotate_vs_reorder_floor_uses_frontload_floor() -> None:
    rows = [
        {
            "policy_name": mod.CONTROL_POLICY_NAME,
            "candidate_best_match_ratio": 0.750,
        },
        {
            "policy_name": mod.REORDER_FLOOR_POLICY_NAME,
            "candidate_best_match_ratio": 0.752,
        },
        {
            "policy_name": "phaseb_topk_replace_width_1_v1",
            "candidate_best_match_ratio": 0.754,
        },
    ]

    out = mod._annotate_vs_reorder_floor(rows)
    replacement_row = next(
        row for row in out if str(row.get("policy_name")) == "phaseb_topk_replace_width_1_v1"
    )

    assert replacement_row["reorder_floor_policy_name"] == mod.REORDER_FLOOR_POLICY_NAME
    assert replacement_row["vs_reorder_floor_delta"] == pytest.approx(0.002)
    assert replacement_row["vs_reorder_floor_read"] == "positive"


def test_build_recommendation_closes_when_no_width_beats_floor() -> None:
    rows = [
        {
            "policy_name": "phaseb_topk_replace_width_1_v1",
            "policy_group": "replacement",
            "requested_width": "1",
            "vs_reorder_floor_delta": 0.0,
            "candidate_minus_control_best_match_ratio": 0.002,
            "winner_identity_changed": 0,
        },
        {
            "policy_name": "phaseb_topk_replace_width_2_v1",
            "policy_group": "replacement",
            "requested_width": "2",
            "vs_reorder_floor_delta": -0.001,
            "candidate_minus_control_best_match_ratio": -0.001,
            "winner_identity_changed": 1,
        },
    ]

    recommendation = mod.build_recommendation(rows)

    assert recommendation["recommendation"] == "close"


def test_build_recommendation_promotes_only_with_clear_winner_change() -> None:
    rows = [
        {
            "policy_name": "phaseb_topk_replace_width_2_v1",
            "policy_group": "replacement",
            "requested_width": "2",
            "vs_reorder_floor_delta": 0.004,
            "candidate_minus_control_best_match_ratio": 0.006,
            "winner_identity_changed": 1,
        }
    ]

    recommendation = mod.build_recommendation(rows)

    assert recommendation["recommendation"] == "promote"
