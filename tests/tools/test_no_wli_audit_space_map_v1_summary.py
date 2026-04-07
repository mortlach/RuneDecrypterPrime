from __future__ import annotations

import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    audit_space_map_v1_summary as audit_mod,
)


def test_space_map_rows_for_artifact_extracts_pool_summary_rows(tmp_path: Path) -> None:
    artifact_path = tmp_path / "final_instance.json"
    artifact_path.write_text(
        json.dumps(
            {
                "period": 9,
                "columns": 3,
                "key_seed": 411,
                "best_stage": "stage35_substitution_only",
                "best_match_ratio": 0.487,
                "stage3_diagnostics": {
                    "stage35_baseline_selector": "score_plus_novelty",
                    "stage35_accept_passed": 1,
                    "stage35_accept_reason": "accepted",
                    "stage35_best_candidate_hash": "best_hash",
                    "stage35_best_match": 0.487,
                    "space_map_v1": {
                        "pool_summaries": [
                            {
                                "stage_boundary": "stage35_seed",
                                "pool_id": "stage35_seed",
                                "pool_status": "available",
                                "selection_policy": "score_plus_novelty",
                                "family_view_id": "prefix_hamming_le_24",
                                "row_count": 2,
                                "eligible_row_count": 2,
                                "selected_row_count": 1,
                                "review_primary_row_count": 2,
                                "review_primary_row_count_kind": "next_stage_started_count",
                                "review_primary_relation": "started_vs_available",
                                "family_count": 2,
                                "largest_family_share": 0.5,
                                "unique_candidate_hash_count": 2,
                                "unique_end_hash_count": 2,
                                "anchor_candidate_hash": "anchor_hash",
                                "selected_pairwise_distance_min": 0.25,
                                "selected_pairwise_distance_mean": 0.25,
                                "next_stage_started_count": 2,
                                "next_stage_admitted_count": 1,
                                "next_stage_rejected_count": 1,
                                "best_continued_candidate_hash": "best_hash",
                                "best_continued_match": 0.487,
                            }
                        ]
                    },
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    rows = audit_mod._space_map_rows_for_artifact(artifact_path)

    assert rows == [
        {
            "artifact_path": str(artifact_path).replace("\\", "/"),
            "period": 9,
            "columns": 3,
            "key_seed": 411,
            "best_stage": "stage35_substitution_only",
            "best_match_ratio": 0.487,
            "stage35_baseline_selector": "score_plus_novelty",
            "stage35_accept_passed": 1,
            "stage35_accept_reason": "accepted",
            "stage35_best_candidate_hash": "best_hash",
            "stage35_best_match": 0.487,
            "stage_boundary": "stage35_seed",
            "pool_id": "stage35_seed",
            "pool_status": "available",
            "selection_policy": "score_plus_novelty",
            "family_view_id": "prefix_hamming_le_24",
            "row_count": 2,
            "eligible_row_count": 2,
            "selected_row_count": 1,
            "review_primary_row_count": 2,
            "review_primary_row_count_kind": "next_stage_started_count",
            "review_primary_relation": "started_vs_available",
            "family_count": 2,
            "largest_family_share": 0.5,
            "unique_candidate_hash_count": 2,
            "unique_end_hash_count": 2,
            "anchor_candidate_hash": "anchor_hash",
            "selected_pairwise_distance_min": 0.25,
            "selected_pairwise_distance_mean": 0.25,
            "next_stage_started_count": 2,
            "next_stage_admitted_count": 1,
            "next_stage_rejected_count": 1,
            "best_continued_candidate_hash": "best_hash",
            "best_continued_match": 0.487,
        }
    ]


def test_write_csv_handles_no_rows(tmp_path: Path) -> None:
    output_path = tmp_path / "pool_summaries.csv"

    audit_mod._write_csv(output_path, [])

    assert output_path.read_text(encoding="utf-8") == "artifact_path\n"
