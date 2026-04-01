from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.phasec_truth_gap_dataset import (
    build_phasec_truth_gap_row,
    collect_phasec_truth_gap_rows,
    write_phasec_truth_gap_dataset,
)


pytestmark = pytest.mark.tier_a


def test_build_phasec_truth_gap_row_extracts_winner_challenger_gap() -> None:
    artifact = {
        "tier": "fixture_fixture_001_p9_c3_l1000",
        "text_id": 0,
        "key_seed": 411,
        "best_stage": "stage2_search",
        "best_match_ratio": 0.041,
        "stage3_match_ratio": 0.039,
        "stage3_diagnostics": {
            "phaseC_start_policy": "novel_challenger_v1",
            "phaseB_top_n_used": 32,
            "phaseC_candidate_pool_count": 34,
            "phaseC_start_keys_used": 6,
            "phaseC_final_winner_lane": "anchor",
            "phaseC_final_winner_source": "stage3_best_phaseB",
            "phaseC_start_summaries": [
                {
                    "start_idx": 1,
                    "lane": "anchor",
                    "source": "stage3_best_phaseB",
                    "candidate_hash": "anchor-hash",
                    "selection_bucket": "anchor",
                    "selected_by_novel_policy": 0,
                    "final_match": 0.039,
                    "final_score": 0.1910,
                    "became_global_best": 1,
                },
                {
                    "start_idx": 2,
                    "lane": "challenger",
                    "source": "phaseA_selected",
                    "candidate_hash": "truth-hash",
                    "selection_bucket": "novel_reserved",
                    "selected_by_novel_policy": 1,
                    "final_match": 0.418,
                    "final_score": 0.1728,
                    "became_global_best": 0,
                },
            ],
        },
    }

    row = build_phasec_truth_gap_row(
        artifact_path=Path("output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/case.json"),
        artifact=artifact,
    )

    assert row is not None
    assert str(row["winner_candidate_hash"]) == "anchor-hash"
    assert str(row["challenger_candidate_hash"]) == "truth-hash"
    assert float(row["truth_gap_vs_winner"]) == pytest.approx(0.379)
    assert float(row["score_gap_vs_winner"]) == pytest.approx(-0.0182, abs=1e-4)


def test_collect_and_write_phasec_truth_gap_dataset(tmp_path: Path) -> None:
    run_root = tmp_path / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli"
    final_dir = run_root / "20260331T000000Z__bench_solve_pipeline_no_wli__demo" / "final_instances"
    final_dir.mkdir(parents=True)
    artifact_path = final_dir / "fixture_fixture_001_p9_c3_l1000__text0__seed411.json"
    artifact_payload = {
        "tier": "fixture_fixture_001_p9_c3_l1000",
        "text_id": 0,
        "key_seed": 411,
        "best_stage": "stage2_search",
        "best_match_ratio": 0.041,
        "stage3_match_ratio": 0.039,
        "stage3_diagnostics": {
            "phaseC_start_policy": "source_order",
            "phaseB_top_n_used": 32,
            "phaseC_candidate_pool_count": 34,
            "phaseC_start_keys_used": 6,
            "phaseC_final_winner_lane": "anchor",
            "phaseC_final_winner_source": "stage3_best_phaseB",
            "phaseC_start_summaries": [
                {
                    "start_idx": 1,
                    "lane": "anchor",
                    "source": "stage3_best_phaseB",
                    "candidate_hash": "anchor-hash",
                    "selection_bucket": "anchor",
                    "selected_by_novel_policy": 0,
                    "final_match": 0.039,
                    "final_score": 0.1910,
                    "became_global_best": 1,
                },
                {
                    "start_idx": 2,
                    "lane": "challenger",
                    "source": "phaseA_selected",
                    "candidate_hash": "truth-hash",
                    "selection_bucket": "legacy_fill",
                    "selected_by_novel_policy": 0,
                    "final_match": 0.418,
                    "final_score": 0.1728,
                    "became_global_best": 0,
                },
            ],
        },
    }
    artifact_path.write_text(json.dumps(artifact_payload), encoding="utf-8")

    rows = collect_phasec_truth_gap_rows(run_root)

    assert len(rows) == 1
    assert str(rows[0]["winner_candidate_hash"]) == "anchor-hash"
    assert str(rows[0]["challenger_candidate_hash"]) == "truth-hash"

    out_dir = run_root / "analysis" / "phasec_truth_gap_dataset"
    summary = write_phasec_truth_gap_dataset(rows=rows, output_dir=out_dir, top_n=5)

    assert int(summary["row_count"]) == 1
    assert (out_dir / "summary.json").exists()
    assert (out_dir / "rows.json").exists()
    assert (out_dir / "rows.csv").exists()
    assert (out_dir / "summary.md").exists()


def test_build_phasec_truth_gap_row_falls_back_to_checkpoint_rows(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli" / "run_demo"
    final_dir = run_dir / "final_instances"
    final_dir.mkdir(parents=True)
    artifact_path = final_dir / "fixture_fixture_001_p9_c3_l1000__text0__seed411.json"
    checkpoint_path = run_dir / "phasec_start_checkpoints.jsonl"
    checkpoint_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "start_idx": 1,
                        "lane": "anchor",
                        "source": "stage3_best_phaseB",
                        "candidate_hash": "anchor-hash",
                        "selection_bucket": "anchor",
                        "selected_by_novel_policy": 0,
                        "final_match": 0.039,
                        "final_score": 0.1910,
                        "became_global_best": 1,
                    }
                ),
                json.dumps(
                    {
                        "start_idx": 2,
                        "lane": "challenger",
                        "source": "phaseA_selected",
                        "candidate_hash": "truth-hash",
                        "selection_bucket": "novel_reserved",
                        "selected_by_novel_policy": 1,
                        "final_match": 0.418,
                        "final_score": 0.1728,
                        "became_global_best": 0,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    artifact = {
        "tier": "fixture_fixture_001_p9_c3_l1000",
        "text_id": 0,
        "key_seed": 411,
        "best_stage": "stage2_search",
        "best_match_ratio": 0.041,
        "stage3_diagnostics": {
            "phaseC_start_policy": "novel_challenger_v1",
            "phaseB_top_n_used": 32,
            "phaseC_candidate_pool_count": 34,
            "phaseC_start_keys_used": 6,
            "phaseC_checkpoint_jsonl_name": "phasec_start_checkpoints.jsonl",
            "phaseC_final_winner_lane": "anchor",
            "phaseC_final_winner_source": "stage3_best_phaseB",
            "phaseC_start_summaries": [],
        },
    }
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    row = build_phasec_truth_gap_row(
        artifact_path=artifact_path,
        artifact=artifact,
    )

    assert row is not None
    assert str(row["winner_candidate_hash"]) == "anchor-hash"
    assert str(row["challenger_candidate_hash"]) == "truth-hash"
