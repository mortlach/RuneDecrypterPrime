from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_frontier_fixture import (
    build_late_stage_frontier_fixture,
    write_late_stage_frontier_fixture,
)


pytestmark = pytest.mark.tier_a


def test_build_late_stage_frontier_fixture_tracks_material_completeness() -> None:
    artifact = {
        "tier": "fixture_fixture_001_p9_c3_l1000",
        "text_id": 0,
        "key_seed": 411,
        "period": 9,
        "columns": 3,
        "length": 1000,
        "best_stage": "stage2_search",
        "best_match_ratio": 0.041,
        "stage3_match_ratio": 0.039,
        "ciphertext_idx": [1, 2, 3],
        "target_plaintext_idx": [4, 5, 6],
        "stage3_diagnostics": {
            "phaseC_start_policy": "novel_challenger_v1",
            "phaseB_top_n_used": 32,
            "phaseC_final_winner_lane": "anchor",
            "phaseC_final_winner_source": "stage3_best_phaseB",
            "phaseC_start_summaries": [
                {
                    "start_idx": 1,
                    "lane": "anchor",
                    "source": "stage3_best_phaseB",
                    "source_rank": 1,
                    "candidate_hash": "winner-hash",
                    "selection_bucket": "anchor",
                    "selected_by_novel_policy": 0,
                    "eligible_novel_challenger": 0,
                    "novelty_distance_to_anchor": None,
                    "novelty_min_distance_to_selected_challenger": None,
                    "init_match": 0.039,
                    "final_match": 0.039,
                    "init_score": 0.1776,
                    "final_score": 0.1910,
                    "became_global_best": 1,
                    "init_key_idx": [1, 2],
                    "init_plaintext_idx": [3, 4],
                    "final_key_idx": [5, 6],
                    "final_plaintext_idx": [7, 8],
                },
                {
                    "start_idx": 2,
                    "lane": "challenger",
                    "source": "phaseA_selected",
                    "source_rank": 2,
                    "candidate_hash": "truth-hash",
                    "selection_bucket": "novel_reserved",
                    "selected_by_novel_policy": 1,
                    "eligible_novel_challenger": 1,
                    "novelty_distance_to_anchor": 164,
                    "novelty_min_distance_to_selected_challenger": None,
                    "init_match": 0.402,
                    "final_match": 0.418,
                    "init_score": 0.1529,
                    "final_score": 0.1728,
                    "became_global_best": 0,
                    "init_key_idx": [9, 10],
                    "init_plaintext_idx": [11, 12],
                    "final_key_idx": [13, 14],
                    "final_plaintext_idx": [15, 16],
                },
            ],
        },
    }

    fixture = build_late_stage_frontier_fixture(
        artifact_path=Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/example/final_instances/case.json"
        ),
        artifact=artifact,
        fixture_id="demo_frontier",
    )

    assert str(fixture["fixture_id"]) == "demo_frontier"
    assert str(fixture["source_artifact_path"]) == (
        "output/tools/benchmarks/periodic_sub_trans/no_wli/example/final_instances/case.json"
    )
    assert int(fixture["candidate_count"]) == 2
    assert str(fixture["score_selected_winner_hash"]) == "winner-hash"
    assert str(fixture["oracle_best_explored_hash"]) == "truth-hash"
    assert int(fixture["candidates_with_final_key_idx"]) == 2
    assert int(fixture["candidates_with_final_plaintext_idx"]) == 2
    assert int(fixture["frontier_key_material_complete"]) == 1
    assert list(fixture["candidates"][1]["final_key_idx"]) == [13, 14]
    assert list(fixture["candidates"][1]["final_plaintext_idx"]) == [15, 16]


def test_write_late_stage_frontier_fixture_keeps_incomplete_rows_visible(
    tmp_path: Path,
) -> None:
    fixture = {
        "fixture_id": "demo_frontier",
        "candidate_count": 2,
        "candidates_with_final_key_idx": 1,
        "candidates_with_final_plaintext_idx": 1,
        "frontier_key_material_complete": 0,
        "candidates": [
            {"candidate_hash": "winner-hash", "final_key_idx": [1, 2], "final_plaintext_idx": [3, 4]},
            {"candidate_hash": "missing-hash", "final_key_idx": [], "final_plaintext_idx": []},
        ],
    }

    output_path = tmp_path / "fixture.json"
    write_late_stage_frontier_fixture(
        fixture=fixture,
        output_path=output_path,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert int(saved["frontier_key_material_complete"]) == 0
    assert str(saved["candidates"][1]["candidate_hash"]) == "missing-hash"
    assert list(saved["candidates"][1]["final_key_idx"]) == []


def test_build_late_stage_frontier_fixture_falls_back_to_checkpoint_rows(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli" / "run_demo"
    final_dir = run_dir / "final_instances"
    final_dir.mkdir(parents=True)
    artifact_path = final_dir / "fixture_fixture_001_p9_c3_l1000__text0__seed411.json"
    checkpoint_path = run_dir / "phasec_start_checkpoints.jsonl"
    artifact = {
        "tier": "fixture_fixture_001_p9_c3_l1000",
        "text_id": 0,
        "key_seed": 411,
        "period": 9,
        "columns": 3,
        "length": 1000,
        "best_stage": "stage2_search",
        "best_match_ratio": 0.041,
        "ciphertext_idx": [1, 2, 3],
        "target_plaintext_idx": [4, 5, 6],
        "stage3_diagnostics": {
            "phaseC_start_policy": "source_order",
            "phaseC_checkpoint_jsonl_name": "phasec_start_checkpoints.jsonl",
            "phaseC_final_winner_lane": "anchor",
            "phaseC_final_winner_source": "stage3_best_phaseB",
            "phaseC_start_summaries": [],
        },
    }
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    checkpoint_rows = [
        {
            "start_idx": 1,
            "lane": "anchor",
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "candidate_hash": "winner-hash",
            "final_score": 0.1910,
            "final_match": 0.039,
            "became_global_best": 1,
            "init_key_idx": [1, 2],
            "init_plaintext_idx": [3, 4],
            "final_key_idx": [5, 6],
            "final_plaintext_idx": [7, 8],
        },
        {
            "start_idx": 2,
            "lane": "challenger",
            "source": "phaseA_selected",
            "source_rank": 2,
            "candidate_hash": "truth-hash",
            "final_score": 0.1728,
            "final_match": 0.418,
            "eligible_novel_challenger": 1,
            "novelty_distance_to_anchor": 164,
            "init_key_idx": [9, 10],
            "init_plaintext_idx": [11, 12],
            "final_key_idx": [13, 14],
            "final_plaintext_idx": [15, 16],
        },
    ]
    checkpoint_path.write_text(
        "\n".join(json.dumps(row) for row in checkpoint_rows) + "\n",
        encoding="utf-8",
    )

    fixture = build_late_stage_frontier_fixture(
        artifact_path=artifact_path,
        artifact=artifact,
        fixture_id="checkpoint_frontier",
    )

    assert str(fixture["phasec_frontier_row_source"]) == "checkpoint"
    assert str(fixture["phasec_checkpoint_path"]).endswith("phasec_start_checkpoints.jsonl")
    assert int(fixture["candidate_count"]) == 2
    assert int(fixture["frontier_key_material_complete"]) == 1
    assert str(fixture["oracle_best_explored_hash"]) == "truth-hash"
