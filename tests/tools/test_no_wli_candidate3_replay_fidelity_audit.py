from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    audit_candidate3_exact_control_replay_fidelity_1511_7004 as mod,
)


def test_ordered_phaseb_topk_saved_summaries_can_be_recovered_from_retained_stage3_topk() -> None:
    artifact = {
        "stage3_topk": [
            {"rank": 2, "source": "phaseB_topk", "end_hash": "b", "match_ratio": 0.57},
            {"rank": 1, "source": "phaseB_topk", "end_hash": "a", "match_ratio": 0.58},
            {"rank": 1, "source": "phaseA_selected", "end_hash": "ignore", "match_ratio": 0.40},
        ]
    }

    summaries = mod._ordered_phaseb_topk_saved_summaries_from_retained_artifact(artifact)

    assert [int(row["stage3_topk_rank"]) for row in summaries] == [1, 2]
    assert [str(row["candidate_hash"]) for row in summaries] == ["a", "b"]


def test_ordered_phasec_start_identities_keep_source_rank_and_hash() -> None:
    rows = [
        {"source": "stage3_best_phaseB", "source_rank": 1, "candidate_hash": "anchor", "final_match": 0.56},
        {"source": "phaseB_topk", "source_rank": 2, "candidate_hash": "topk", "final_match": 0.57},
    ]

    identities = mod._ordered_phasec_start_identities(rows)

    assert identities == [
        {
            "start_rank": 1,
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "candidate_hash": "anchor",
            "final_match": pytest.approx(0.56),
        },
        {
            "start_rank": 2,
            "source": "phaseB_topk",
            "source_rank": 2,
            "candidate_hash": "topk",
            "final_match": pytest.approx(0.57),
        },
    ]


def test_build_surface_comparison_marks_missing_surface_as_unavailable() -> None:
    row = mod._build_surface_comparison(
        surface_name="phaseB_downstream_selected_ordered_hashes",
        retained_value=None,
        replay_value=["a", "b"],
        note="missing in retained case",
    )

    assert row["status"] == "unavailable"
    assert row["surface_name"] == "phaseB_downstream_selected_ordered_hashes"


def test_ordered_phaseb_downstream_hashes_can_fallback_to_candidate_pool_rows() -> None:
    payload = {
        "phaseC_candidate_pool_rows": [
            {"source": "phaseA_selected", "source_rank": 2, "candidate_hash": "b"},
            {"source": "phaseB_topk", "source_rank": 1, "candidate_hash": "ignore"},
            {"source": "phaseA_selected", "source_rank": 1, "candidate_hash": "a"},
        ]
    }

    hashes = mod._ordered_hashes_from_phaseb_downstream_selected_summaries(payload)

    assert hashes == ["a", "b"]


def test_replay_fidelity_summary_finds_first_actual_mismatch_after_unavailable() -> None:
    retained_artifact = {
        "instance_source_key_seed": 1511,
        "search_seed": 7004,
        "stage3_topk": [
            {"rank": 1, "source": "phaseB_topk", "end_hash": "topk-a", "match_ratio": 0.57},
            {"rank": 2, "source": "phaseB_topk", "end_hash": "topk-b", "match_ratio": 0.56},
        ],
        "stage3_diagnostics": {
            "phaseB_selected_unique_end_hash": 32,
            "phaseB_downstream_selected_count": 32,
            "phaseB_topk_saved_count": 2,
            "phaseC_candidate_pool_rows": [
                {"source": "phaseA_selected", "source_rank": 1, "candidate_hash": "ret-a"},
                {"source": "phaseA_selected", "source_rank": 2, "candidate_hash": "ret-b"},
            ],
            "phaseC_candidate_pool_source_counts": {
                "stage3_best_phaseB": 1,
                "phaseB_topk": 2,
                "phaseA_selected": 32,
            },
            "phaseC_start_source_counts": {
                "stage3_best_phaseB": 1,
                "phaseB_topk": 1,
                "phaseA_selected": 1,
            },
            "phaseC_start_summaries": [
                {
                    "source": "stage3_best_phaseB",
                    "source_rank": 1,
                    "candidate_hash": "anchor",
                    "final_match": 0.56,
                },
                {
                    "source": "phaseB_topk",
                    "source_rank": 2,
                    "candidate_hash": "topk-a",
                    "final_match": 0.57,
                },
            ],
        },
    }
    replay_flow = {
        "phaseB_selected_unique_end_hash": 32,
        "phaseB_downstream_selected_count": 32,
        "phaseB_downstream_selected_summaries": [
            {"downstream_rank": 1, "end_hash": "rep-a"},
            {"downstream_rank": 2, "end_hash": "rep-b"},
        ],
        "phaseB_topk_saved_count": 1,
        "stage3_topk_payload": [
            {"rank": 1, "source": "phaseB_topk", "end_hash": "anchor", "match_ratio": 0.05},
        ],
        "phaseC_candidate_pool_source_counts": {
            "stage3_best_phaseB": 1,
            "phaseB_topk": 1,
            "phaseA_selected": 32,
        },
        "phaseC_start_source_counts": {
            "stage3_best_phaseB": 1,
            "phaseA_selected": 5,
        },
        "phaseC_start_summaries": [
            {
                "source": "stage3_best_phaseB",
                "source_rank": 1,
                "candidate_hash": "anchor-replay",
                "final_match": 0.05,
            },
            {
                "source": "phaseA_selected",
                "source_rank": 1,
                "candidate_hash": "phasea-1",
                "final_match": 0.43,
            },
        ],
    }

    summary = mod.build_replay_fidelity_summary(
        retained_artifact=retained_artifact,
        replay_flow=replay_flow,
    )

    assert summary["first_unavailable_surface"] == ""
    assert summary["first_actual_mismatch_surface"] == "phaseB_downstream_selected_ordered_hashes"
    assert int(summary["ordered_identity_contract_all_match"]) == 0
    assert [str(row["surface_name"]) for row in summary["ordered_identity_contract_rows"]] == [
        "phaseB_downstream_selected_ordered_hashes",
        "phaseB_topk_saved_ordered_hashes",
        "phaseC_start_ordered_identities",
    ]
    assert summary["retained_phaseb_topk_saved_summaries"][0]["candidate_hash"] == "topk-a"
    assert summary["replay_phaseb_topk_saved_summaries"][0]["candidate_hash"] == "anchor"


def test_ordered_identity_contract_rows_mark_exact_matches() -> None:
    surface_rows = [
        {
            "surface_name": "phaseB_downstream_selected_ordered_hashes",
            "status": "match",
            "retained_value": ["a", "b"],
            "replay_value": ["a", "b"],
            "note": "downstream",
        },
        {
            "surface_name": "phaseB_topk_saved_ordered_hashes",
            "status": "match",
            "retained_value": ["t1", "t2"],
            "replay_value": ["t1", "t2"],
            "note": "topk",
        },
        {
            "surface_name": "phaseC_start_ordered_identities",
            "status": "match",
            "retained_value": [{"candidate_hash": "x"}],
            "replay_value": [{"candidate_hash": "x"}],
            "note": "phasec",
        },
        {
            "surface_name": "phaseC_start_source_counts",
            "status": "match",
            "retained_value": {"phaseB_topk": 1},
            "replay_value": {"phaseB_topk": 1},
            "note": "not ordered identity",
        },
    ]

    rows = mod._ordered_identity_contract_rows(surface_rows)

    assert [str(row["surface_name"]) for row in rows] == [
        "phaseB_downstream_selected_ordered_hashes",
        "phaseB_topk_saved_ordered_hashes",
        "phaseC_start_ordered_identities",
    ]
    assert [int(row["exact_ordered_identity_match"]) for row in rows] == [1, 1, 1]
