from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    verify_candidate2_top_family_reinforce_shadow as mod,
)


def test_annotate_candidate_pool_rows_with_families_keeps_exact_key_groups() -> None:
    rows = [
        {
            "candidate_hash": "a1",
            "key_idx": [1, 2, 3],
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "selected_by_phasec_start": 1,
        },
        {
            "candidate_hash": "a2",
            "key_idx": [1, 2, 3],
            "source": "phaseB_topk",
            "source_rank": 2,
            "selected_by_phasec_start": 0,
        },
        {
            "candidate_hash": "b1",
            "key_idx": [9, 9, 9],
            "source": "phaseA_selected",
            "source_rank": 1,
            "selected_by_phasec_start": 0,
        },
    ]

    annotated = mod.annotate_candidate_pool_rows_with_families(
        rows,
        columns=1,
        family_view_id="exact_key",
    )

    assert len(annotated) == 3
    assert annotated[0]["family_id"] == annotated[1]["family_id"]
    assert annotated[0]["family_id"] != annotated[2]["family_id"]
    assert annotated[0]["row_id"] == "pool:1"
    assert annotated[1]["row_id"] == "pool:2"


def test_shadow_summary_marks_saved_room_when_anchor_family_has_extra_saved_rows() -> None:
    annotated_rows = [
        {
            "candidate_hash": "anchor-a",
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "family_id": "f0",
            "selected_by_phasec_start": 1,
        },
        {
            "candidate_hash": "anchor-a",
            "source": "phaseA_selected",
            "source_rank": 1,
            "family_id": "f0",
            "selected_by_phasec_start": 1,
        },
        {
            "candidate_hash": "anchor-b",
            "source": "phaseB_topk",
            "source_rank": 2,
            "family_id": "f0",
            "selected_by_phasec_start": 0,
        },
        {
            "candidate_hash": "other-c",
            "source": "phaseA_selected",
            "source_rank": 2,
            "family_id": "f1",
            "selected_by_phasec_start": 0,
        },
    ]

    summary = mod.summarize_candidate2_shadow_from_annotated_rows(
        fixture_seed=611,
        search_seed=7005,
        best_stage="stage3_full_refine",
        best_match_ratio=0.585,
        phaseb_downstream_selected_count=2,
        phasec_start_keys_used=2,
        annotated_rows=annotated_rows,
        reserved_slots=1,
        source_artifact_relpath="output/mock/case.json",
    )

    assert summary["anchor_family_id"] == "f0"
    assert summary["room_label"] == "saved_room_available"
    assert summary["anchor_family_extra_saved_unique_hash_count"] == 1
    assert summary["shadow_materializable_extra_anchor_rows"] == 1
    assert summary["baseline_anchor_family_share"] == pytest.approx(0.5)
    assert summary["shadow_anchor_family_share_after"] == pytest.approx(1.0)


def test_shadow_summary_marks_no_saved_room_when_anchor_family_is_already_fully_selected() -> None:
    annotated_rows = [
        {
            "candidate_hash": "anchor-a",
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "family_id": "f0",
            "selected_by_phasec_start": 1,
        },
        {
            "candidate_hash": "anchor-a",
            "source": "phaseA_selected",
            "source_rank": 1,
            "family_id": "f0",
            "selected_by_phasec_start": 1,
        },
        {
            "candidate_hash": "other-b",
            "source": "phaseA_selected",
            "source_rank": 2,
            "family_id": "f1",
            "selected_by_phasec_start": 0,
        },
        {
            "candidate_hash": "other-b",
            "source": "phaseB_topk",
            "source_rank": 2,
            "family_id": "f1",
            "selected_by_phasec_start": 0,
        },
    ]

    summary = mod.summarize_candidate2_shadow_from_annotated_rows(
        fixture_seed=1111,
        search_seed=7004,
        best_stage="stage35_substitution_only",
        best_match_ratio=0.423,
        phaseb_downstream_selected_count=2,
        phasec_start_keys_used=2,
        annotated_rows=annotated_rows,
        reserved_slots=2,
    )

    assert summary["anchor_family_id"] == "f0"
    assert summary["room_label"] == "no_saved_room"
    assert summary["anchor_family_extra_saved_unique_hash_count"] == 0
    assert summary["shadow_materializable_extra_anchor_rows"] == 0
    assert summary["baseline_anchor_family_share"] == pytest.approx(0.5)
    assert summary["shadow_anchor_family_share_after"] == pytest.approx(0.5)
