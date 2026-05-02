from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    verify_candidate3_phasec_saved_surface_1511_7004 as mod,
)


def test_build_candidate3_saved_surface_rows_swaps_first_distinct_phaseb_topk() -> None:
    rows = [
        {
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "candidate_hash": "anchor",
            "selection_bucket": "anchor",
            "final_match": 0.56,
        },
        {
            "source": "phaseB_topk",
            "source_rank": 2,
            "candidate_hash": "topk-2",
            "selection_bucket": "legacy_fill",
            "final_match": 0.57,
        },
        {
            "source": "phaseA_selected",
            "source_rank": 1,
            "candidate_hash": "phasea-1",
            "selection_bucket": "legacy_fill",
            "final_match": 0.55,
        },
    ]

    out = mod.build_candidate3_saved_surface_rows(rows)

    assert [str(row["candidate_hash"]) for row in out] == [
        "topk-2",
        "anchor",
        "phasea-1",
    ]
    assert str(out[0]["selection_bucket"]) == "phaseb_topk_anchor"
    assert int(out[0]["selected_by_phaseb_topk_anchor_policy"]) == 1
    assert str(out[1]["selection_bucket"]) == "anchor_demoted"
    assert str(out[2]["lane"]) == "challenger"


def test_build_candidate3_saved_surface_rows_is_noop_without_distinct_phaseb_topk() -> None:
    rows = [
        {
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "candidate_hash": "anchor",
            "final_match": 0.56,
        },
        {
            "source": "phaseA_selected",
            "source_rank": 1,
            "candidate_hash": "phasea-1",
            "final_match": 0.55,
        },
    ]

    out = mod.build_candidate3_saved_surface_rows(rows)

    assert out == rows


def test_build_saved_surface_summary_reports_candidate_engagement_and_delta() -> None:
    artifact = {
        "instance_source_key_seed": 1511,
        "search_seed": 7004,
        "stage3_diagnostics": {
            "phaseC_start_policy": "source_order",
            "phaseC_start_summaries": [
                {
                    "source": "stage3_best_phaseB",
                    "source_rank": 1,
                    "candidate_hash": "anchor",
                    "selection_bucket": "anchor",
                    "final_match": 0.56,
                },
                {
                    "source": "phaseB_topk",
                    "source_rank": 2,
                    "candidate_hash": "topk-2",
                    "selection_bucket": "legacy_fill",
                    "final_match": 0.57,
                },
                {
                    "source": "phaseA_selected",
                    "source_rank": 1,
                    "candidate_hash": "phasea-1",
                    "selection_bucket": "legacy_fill",
                    "final_match": 0.55,
                },
            ]
        },
    }

    summary = mod.build_saved_surface_summary(artifact)

    assert int(summary["saved_surface_can_engage"]) == 1
    assert int(summary["saved_surface_phaseb_topk_index"]) == 2
    assert float(summary["saved_surface_phaseb_topk_minus_anchor_final_match"]) == pytest.approx(
        0.01
    )
    assert str(summary["candidate_start_identities"][0]["candidate_hash"]) == "topk-2"
    assert int(
        summary["candidate_start_identities"][0]["selected_by_phaseb_topk_anchor_policy"]
    ) == 1


def test_build_phaseb_topk_frontload_two_saved_surface_rows_frontloads_two_rows() -> None:
    rows = [
        {
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "candidate_hash": "anchor",
        },
        {
            "source": "phaseB_topk",
            "source_rank": 2,
            "candidate_hash": "topk-2",
        },
        {
            "source": "phaseB_topk",
            "source_rank": 3,
            "candidate_hash": "topk-3",
        },
        {
            "source": "phaseA_selected",
            "source_rank": 1,
            "candidate_hash": "phasea-1",
        },
    ]

    out = mod.build_phaseb_topk_frontload_two_saved_surface_rows(rows)

    assert [str(row["candidate_hash"]) for row in out] == [
        "topk-2",
        "topk-3",
        "anchor",
        "phasea-1",
    ]
    assert str(out[0]["selection_bucket"]) == "phaseb_topk_frontload"
    assert str(out[1]["selection_bucket"]) == "phaseb_topk_frontload_extra"
    assert str(out[2]["selection_bucket"]) == "anchor_demoted"


def test_build_phaseb_topk_frontload_all_saved_surface_rows_frontloads_all_rows() -> None:
    rows = [
        {
            "source": "stage3_best_phaseA",
            "source_rank": 1,
            "candidate_hash": "anchor",
        },
        {
            "source": "phaseB_topk",
            "source_rank": 1,
            "candidate_hash": "topk-1",
        },
        {
            "source": "phaseA_selected",
            "source_rank": 2,
            "candidate_hash": "phasea-2",
        },
        {
            "source": "phaseB_topk",
            "source_rank": 2,
            "candidate_hash": "topk-2",
        },
    ]

    out = mod.build_phaseb_topk_frontload_all_saved_surface_rows(rows)

    assert [str(row["candidate_hash"]) for row in out] == [
        "topk-1",
        "topk-2",
        "anchor",
        "phasea-2",
    ]


def test_build_phaseb_topk_frontload_depth_saved_surface_rows_keeps_anchor_fixed() -> None:
    rows = [
        {
            "source": "stage3_best_phaseA",
            "source_rank": 1,
            "candidate_hash": "anchor",
        },
        {
            "source": "phaseA_selected",
            "source_rank": 1,
            "candidate_hash": "phasea-1",
        },
        {
            "source": "phaseB_topk",
            "source_rank": 2,
            "candidate_hash": "topk-2",
        },
        {
            "source": "phaseB_topk",
            "source_rank": 3,
            "candidate_hash": "topk-3",
        },
    ]

    out = mod.build_phaseb_topk_frontload_depth_saved_surface_rows(
        rows,
        frontload_width=2,
    )

    assert [str(row["candidate_hash"]) for row in out] == [
        "anchor",
        "topk-2",
        "topk-3",
        "phasea-1",
    ]
    assert str(out[1]["selection_bucket"]) == "phaseb_topk_frontload_depth"
    assert str(out[2]["selection_bucket"]) == "phaseb_topk_frontload_depth_extra"


def test_build_phasec_pool_replacement_saved_surface_rows_replaces_weakest_selected() -> None:
    start_rows = [
        {
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "candidate_hash": "anchor",
            "init_key_idx": [1, 2, 3],
            "init_match": 0.60,
            "init_score": 0.30,
            "selection_bucket": "anchor",
        },
        {
            "source": "phaseB_topk",
            "source_rank": 2,
            "candidate_hash": "selected-1",
            "init_key_idx": [4, 5, 6],
            "init_match": 0.55,
            "init_score": 0.20,
            "selection_bucket": "legacy_fill",
        },
        {
            "source": "phaseB_topk",
            "source_rank": 3,
            "candidate_hash": "selected-2",
            "init_key_idx": [7, 8, 9],
            "init_match": 0.40,
            "init_score": 0.10,
            "selection_bucket": "legacy_fill",
        },
        {
            "source": "phaseA_selected",
            "source_rank": 1,
            "candidate_hash": "selected-3",
            "init_key_idx": [10, 11, 12],
            "init_match": 0.45,
            "init_score": 0.11,
            "selection_bucket": "legacy_fill",
        },
    ]
    candidate_pool_rows = [
        {
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "candidate_hash": "anchor",
            "key": [1, 2, 3],
            "selected_by_phasec_start": 1,
        },
        {
            "source": "phaseB_topk",
            "source_rank": 2,
            "candidate_hash": "selected-1",
            "key": [4, 5, 6],
            "selected_by_phasec_start": 1,
        },
        {
            "source": "phaseB_topk",
            "source_rank": 3,
            "candidate_hash": "selected-2",
            "key": [7, 8, 9],
            "selected_by_phasec_start": 1,
        },
        {
            "source": "phaseA_selected",
            "source_rank": 1,
            "candidate_hash": "selected-3",
            "key": [10, 11, 12],
            "selected_by_phasec_start": 1,
        },
        {
            "source": "phaseB_topk",
            "source_rank": 4,
            "candidate_hash": "challenger-topk",
            "key": [13, 14, 15],
            "selected_by_phasec_start": 0,
        },
        {
            "source": "phaseA_selected",
            "source_rank": 2,
            "candidate_hash": "challenger-phasea",
            "key": [16, 17, 18],
            "selected_by_phasec_start": 0,
        },
    ]

    out = mod.build_phasec_pool_replace_width_one_saved_surface_rows(
        start_rows,
        candidate_pool_rows,
    )

    assert [str(row["candidate_hash"]) for row in out] == [
        "anchor",
        "selected-1",
        "challenger-topk",
        "selected-3",
    ]
    assert str(out[2]["selection_bucket"]) == "pool_replacement_challenger"
    assert int(out[2]["selected_by_pool_replacement_policy"]) == 1
    assert str(out[2]["replacement_evicted_candidate_hash"]) == "selected-2"
    assert list(out[2]["init_key_idx"]) == [13, 14, 15]


def test_build_phasec_pool_replacement_saved_surface_rows_prefers_phaseb_topk_then_phasea() -> None:
    start_rows = [
        {
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "candidate_hash": "anchor",
            "init_key_idx": [1],
            "init_match": 0.60,
            "init_score": 0.30,
        },
        {
            "source": "phaseB_topk",
            "source_rank": 2,
            "candidate_hash": "selected-1",
            "init_key_idx": [2],
            "init_match": 0.50,
            "init_score": 0.20,
        },
        {
            "source": "phaseA_selected",
            "source_rank": 1,
            "candidate_hash": "selected-2",
            "init_key_idx": [3],
            "init_match": 0.40,
            "init_score": 0.10,
        },
    ]
    candidate_pool_rows = [
        {
            "source": "phaseA_selected",
            "source_rank": 2,
            "candidate_hash": "challenger-phasea",
            "key": [4],
            "selected_by_phasec_start": 0,
        },
        {
            "source": "phaseB_topk",
            "source_rank": 5,
            "candidate_hash": "challenger-topk",
            "key": [5],
            "selected_by_phasec_start": 0,
        },
    ]

    out = mod.build_phasec_pool_replace_width_two_saved_surface_rows(
        start_rows,
        candidate_pool_rows,
    )

    assert [str(row["candidate_hash"]) for row in out] == [
        "anchor",
        "challenger-topk",
        "challenger-phasea",
    ]


def test_build_phasec_pool_replacement_saved_surface_rows_cap_all_replaces_all_non_anchor() -> None:
    start_rows = [
        {
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "candidate_hash": "anchor",
            "init_key_idx": [1],
            "init_match": 0.60,
            "init_score": 0.30,
        },
        {
            "source": "phaseB_topk",
            "source_rank": 2,
            "candidate_hash": "selected-1",
            "init_key_idx": [2],
            "init_match": 0.50,
            "init_score": 0.20,
        },
        {
            "source": "phaseA_selected",
            "source_rank": 1,
            "candidate_hash": "selected-2",
            "init_key_idx": [3],
            "init_match": 0.40,
            "init_score": 0.10,
        },
    ]
    candidate_pool_rows = [
        {
            "source": "phaseB_topk",
            "source_rank": 5,
            "candidate_hash": "challenger-1",
            "key": [4],
            "selected_by_phasec_start": 0,
        },
        {
            "source": "phaseA_selected",
            "source_rank": 2,
            "candidate_hash": "challenger-2",
            "key": [5],
            "selected_by_phasec_start": 0,
        },
    ]

    out = mod.build_phasec_pool_replace_width_cap_all_saved_surface_rows(
        start_rows,
        candidate_pool_rows,
    )

    assert [str(row["candidate_hash"]) for row in out] == [
        "anchor",
        "challenger-1",
        "challenger-2",
    ]


def test_build_phaseb_topk_quota_saved_surface_rows_adds_phaseb_mass() -> None:
    start_rows = [
        {
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "candidate_hash": "anchor",
            "init_key_idx": [1],
        },
        {
            "source": "phaseA_selected",
            "source_rank": 1,
            "candidate_hash": "selected-a",
            "init_key_idx": [2],
        },
        {
            "source": "phaseB_topk",
            "source_rank": 3,
            "candidate_hash": "selected-b",
            "init_key_idx": [3],
        },
        {
            "source": "phaseA_selected",
            "source_rank": 2,
            "candidate_hash": "selected-c",
            "init_key_idx": [4],
        },
    ]
    candidate_pool_rows = [
        {
            "source": "phaseB_topk",
            "source_rank": 2,
            "candidate_hash": "challenger-topk",
            "key": [5],
            "selected_by_phasec_start": 0,
        }
    ]

    out = mod.build_phaseb_topk_quota_saved_surface_rows(
        start_rows,
        candidate_pool_rows,
        quota_width=2,
    )

    assert [str(row["candidate_hash"]) for row in out] == [
        "anchor",
        "challenger-topk",
        "selected-b",
        "selected-a",
    ]
    assert int(
        sum(1 for row in out[1:] if str(row.get("source")) == "phaseB_topk")
    ) == 2


def test_build_phaseb_topk_quota_saved_surface_rows_is_noop_when_quota_already_met() -> None:
    start_rows = [
        {
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "candidate_hash": "anchor",
            "init_key_idx": [1],
        },
        {
            "source": "phaseB_topk",
            "source_rank": 2,
            "candidate_hash": "selected-a",
            "init_key_idx": [2],
        },
        {
            "source": "phaseB_topk",
            "source_rank": 3,
            "candidate_hash": "selected-b",
            "init_key_idx": [3],
        },
        {
            "source": "phaseA_selected",
            "source_rank": 1,
            "candidate_hash": "selected-c",
            "init_key_idx": [4],
        },
    ]

    out = mod.build_phaseb_topk_quota_saved_surface_rows(
        start_rows,
        [],
        quota_width=2,
    )

    assert out == start_rows


def test_build_phaseb_topk_only_replacement_saved_surface_rows_uses_late_rank_eviction() -> None:
    start_rows = [
        {
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "candidate_hash": "anchor",
            "init_key_idx": [1],
        },
        {
            "source": "phaseA_selected",
            "source_rank": 1,
            "candidate_hash": "selected-a",
            "init_key_idx": [2],
        },
        {
            "source": "phaseB_topk",
            "source_rank": 4,
            "candidate_hash": "selected-b",
            "init_key_idx": [3],
        },
        {
            "source": "phaseA_selected",
            "source_rank": 2,
            "candidate_hash": "selected-c",
            "init_key_idx": [4],
        },
    ]
    candidate_pool_rows = [
        {
            "source": "phaseB_topk",
            "source_rank": 2,
            "candidate_hash": "challenger-topk-1",
            "key": [5],
            "selected_by_phasec_start": 0,
        },
        {
            "source": "phaseB_topk",
            "source_rank": 3,
            "candidate_hash": "challenger-topk-2",
            "key": [6],
            "selected_by_phasec_start": 0,
        },
    ]

    out = mod.build_phaseb_topk_only_replacement_saved_surface_rows(
        start_rows,
        candidate_pool_rows,
        replace_width=2,
    )

    assert [str(row["candidate_hash"]) for row in out] == [
        "anchor",
        "selected-a",
        "challenger-topk-1",
        "challenger-topk-2",
    ]
    assert str(out[2]["replacement_evicted_candidate_hash"]) == "selected-b"
    assert str(out[3]["replacement_evicted_candidate_hash"]) == "selected-c"
