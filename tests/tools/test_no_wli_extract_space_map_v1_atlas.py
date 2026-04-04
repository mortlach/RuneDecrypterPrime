from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    extract_space_map_v1_atlas as atlas_mod,
)


def _write_artifact(path: Path) -> None:
    payload = {
        "period": 9,
        "columns": 3,
        "key_seed": 411,
        "best_stage": "stage35_substitution_only",
        "best_match_ratio": 0.487,
        "stage3_diagnostics": {
            "stage35_baseline_selector": "score_plus_novelty",
            "stage35_baseline_candidate_hash": "seed_hash",
            "stage35_accept_passed": 1,
            "stage35_accept_reason": "accepted",
            "stage35_best_match": 0.487,
            "stage35_outcome_status": "completed",
            "stage35_runtime_seconds": 12.5,
            "stage35_progress_jsonl_name": "stage35_progress.jsonl",
            "stage35_partial_state_name": "stage35_partial_state.json",
            "phaseC_candidate_pool_count": 3,
            "space_map_v1": {
                "run_id": "run_abc",
                "partial_state_rows": [
                    {
                        "stage_boundary": "phaseC_start",
                        "candidate_hash": "seed_hash",
                        "parent_candidate_hash": "",
                        "family_id": "seed_family",
                        "source": "phaseA_selected",
                        "lane": "challenger",
                        "selected": 1,
                        "eligible": 1,
                        "admitted_by_next_stage": 1,
                        "final_match": 0.42,
                        "match_gain": 0.01,
                        "final_score": 0.18,
                        "score_gain": 0.01,
                        "distance_to_anchor": 0.25,
                        "continued_best_candidate_hash": "best_hash",
                        "continued_best_match": 0.487,
                        "reject_reason": "",
                    },
                    {
                        "stage_boundary": "stage35_archive",
                        "candidate_hash": "best_hash",
                        "parent_candidate_hash": "seed_hash",
                        "family_id": "best_family",
                        "source": "stage35_local_search",
                        "lane": "challenger",
                        "selected": 1,
                        "eligible": 1,
                        "admitted_by_next_stage": 1,
                        "final_match": 0.487,
                        "match_gain": 0.067,
                        "final_score": 0.1813,
                        "score_gain": 0.0013,
                        "distance_to_anchor": 0.31,
                        "continued_best_candidate_hash": "",
                        "continued_best_match": float("nan"),
                        "reject_reason": "",
                    },
                ],
                "pool_summaries": [
                    {
                        "stage_boundary": "phaseC_start",
                        "pool_id": "phaseC_start",
                        "pool_status": "available",
                        "selection_policy": "source_order",
                        "row_count": 1,
                        "eligible_row_count": 1,
                        "selected_row_count": 1,
                        "family_count": 1,
                        "largest_family_share": 1.0,
                        "unique_candidate_hash_count": 1,
                        "anchor_candidate_hash": "seed_hash",
                        "selected_pairwise_distance_mean": float("nan"),
                        "next_stage_started_count": 1,
                        "next_stage_admitted_count": 1,
                        "next_stage_rejected_count": 0,
                    },
                    {
                        "stage_boundary": "stage35_archive",
                        "pool_id": "stage35_archive",
                        "pool_status": "available",
                        "selection_policy": "stage35_archive_rank",
                        "row_count": 1,
                        "eligible_row_count": 1,
                        "selected_row_count": 1,
                        "family_count": 1,
                        "largest_family_share": 1.0,
                        "unique_candidate_hash_count": 1,
                        "anchor_candidate_hash": "seed_hash",
                        "selected_pairwise_distance_mean": float("nan"),
                        "next_stage_started_count": 0,
                        "next_stage_admitted_count": 0,
                        "next_stage_rejected_count": 0,
                    },
                ],
            },
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, allow_nan=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_classifier_labels_repair_and_pool_and_run_types() -> None:
    assert (
        atlas_mod.classify_row_type(
            {
                "selected": 1,
                "admitted_by_next_stage": 1,
                "final_match": 0.42,
                "continued_best_match": 0.49,
            }
        )
        == "repair_candidate"
    )
    assert (
        atlas_mod.classify_pool_type(
            {"pool_status": "not_run", "row_count": 0, "family_count": 0}
        )
        == "not_run_pool"
    )
    assert (
        atlas_mod.classify_run_type(
            {
                "best_stage": "stage35_substitution_only",
                "best_match_ratio": 0.487,
                "stage3_diagnostics": {
                    "stage35_accept_passed": 1,
                    "stage35_accept_reason": "accepted",
                    "stage35_outcome_status": "completed",
                },
            }
        )
        == "stage35_live_win"
    )


def test_extract_rows_for_artifact_emits_row_pool_transition_and_run_tables(
    tmp_path: Path,
) -> None:
    artifact_path = (
        tmp_path
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "run_a"
        / "final_instances"
        / "fixture_fixture_001_p9_c3_l1000__text0__seed411.json"
    )
    _write_artifact(artifact_path)

    row_rows, pool_rows, transition_rows, run_row = (
        atlas_mod.extract_rows_for_artifact(artifact_path)
    )

    assert run_row["run_id"] == "run_abc"
    assert run_row["run_label"] == "stage35_live_win"
    assert [row["row_type"] for row in row_rows] == [
        "repair_candidate",
        "unclassified_row",
    ]
    assert [row["pool_type"] for row in pool_rows] == [
        "single_hill_pool",
        "single_hill_pool",
    ]
    assert {
        row["transition_type"] for row in transition_rows
    } == {"parent_to_candidate", "candidate_to_continued_best"}
    assert "phasec_pool_not_row_complete" in pool_rows[0]["data_gap_flags"]


def test_main_writes_atlas_tables(tmp_path: Path, monkeypatch) -> None:
    artifact_path = (
        tmp_path
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "run_a"
        / "final_instances"
        / "fixture_fixture_001_p9_c3_l1000__text0__seed411.json"
    )
    _write_artifact(artifact_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(atlas_mod, "MAX_ARTIFACTS", 100)

    atlas_mod.main()

    [output_dir] = sorted(atlas_mod.OUTPUT_BASE_DIR.glob("*__space_map_v1_atlas"))
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["artifacts_scanned"] == 1
    assert summary["row_atlas_rows"] == 2
    assert summary["pool_atlas_rows"] == 2
    assert summary["run_type_counts"] == {"stage35_live_win": 1}
    with (output_dir / "row_atlas.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["row_type"] == "repair_candidate"


def test_detect_data_gap_flags_treats_stage35_archive_baseline_as_root() -> None:
    artifact = {
        "stage3_diagnostics": {
            "stage35_requested_cfg": 1,
            "stage35_ran": 1,
            "stage35_baseline_candidate_hash": "baseline_hash",
            "stage35_progress_jsonl_name": "stage35_progress.jsonl",
            "stage35_partial_state_name": "stage35_partial_state.json",
            "space_map_v1": {
                "run_id": "run_stage35",
                "partial_state_rows": [
                    {
                        "stage_boundary": "stage35_archive",
                        "candidate_hash": "baseline_hash",
                        "parent_candidate_hash": "",
                        "family_id": "f0",
                        "distance_to_anchor": 0.0,
                        "admitted_by_next_stage": 0,
                    }
                ],
                "pool_summaries": [
                    {
                        "stage_boundary": "stage35_archive",
                        "pool_id": "stage35_archive",
                        "pool_status": "empty",
                        "row_count": 1,
                    }
                ],
            },
        }
    }

    flags = atlas_mod.detect_data_gap_flags(
        artifact=artifact,
        partial_row=dict(
            artifact["stage3_diagnostics"]["space_map_v1"]["partial_state_rows"][0]
        ),
    )

    assert "missing_parent_candidate_hash" not in flags


def test_detect_data_gap_flags_does_not_require_stage35_progress_paths_when_stage35_absent() -> None:
    artifact = {
        "stage3_diagnostics": {
            "stage35_requested_cfg": 0,
            "stage35_ran": 0,
            "stage35_baseline_candidate_hash": "",
            "stage35_progress_jsonl_name": "",
            "stage35_partial_state_name": "",
            "space_map_v1": {
                "run_id": "run_no_stage35",
                "partial_state_rows": [
                    {
                        "stage_boundary": "stage2_promoted",
                        "candidate_hash": "stage2_hash",
                        "parent_candidate_hash": "",
                        "family_id": "f0",
                        "distance_to_anchor": 0.0,
                        "admitted_by_next_stage": 0,
                    }
                ],
                "pool_summaries": [
                    {
                        "stage_boundary": "stage2_promoted",
                        "pool_id": "stage2_promoted",
                        "pool_status": "available",
                        "row_count": 1,
                    }
                ],
            },
        }
    }

    flags = atlas_mod.detect_data_gap_flags(
        artifact=artifact,
        partial_row=dict(
            artifact["stage3_diagnostics"]["space_map_v1"]["partial_state_rows"][0]
        ),
    )

    assert "missing_stage35_progress_paths" not in flags
