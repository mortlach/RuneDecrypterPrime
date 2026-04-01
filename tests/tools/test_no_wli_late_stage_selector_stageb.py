from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_selector_stageb import (
    build_stageb_fixture_comparison,
    build_stageb_selected_trial_material_rows,
    write_stageb_replay_report,
)


pytestmark = pytest.mark.tier_a


def _fixture(*, fixture_id: str, policy: str) -> dict:
    return {
        "fixture_id": fixture_id,
        "run_id": f"{fixture_id}_run",
        "phasec_start_policy": policy,
        "phasec_frontier_row_source": "checkpoint",
        "phasec_checkpoint_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/phasec_start_checkpoints.jsonl",
        "score_selected_winner_hash": "winner-hash",
        "oracle_best_explored_hash": "truth-hash",
        "frontier_key_material_complete": 1,
        "candidate_count": 3,
        "candidates": [
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
                "init_score": 0.1776,
                "final_score": 0.1910,
                "score_gain": 0.0134,
                "final_match": 0.039,
                "final_key_idx": [1, 2, 3],
                "final_plaintext_idx": [4, 5, 6],
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
                "init_score": 0.1529,
                "final_score": 0.1728,
                "score_gain": 0.0199,
                "final_match": 0.418,
                "final_key_idx": [7, 8, 9],
                "final_plaintext_idx": [10, 11, 12],
            },
            {
                "start_idx": 3,
                "lane": "challenger",
                "source": "phaseB_topk",
                "source_rank": 3,
                "candidate_hash": "mild-hash",
                "selection_bucket": "legacy_fill",
                "selected_by_novel_policy": 0,
                "eligible_novel_challenger": 0,
                "novelty_distance_to_anchor": None,
                "init_score": 0.1500,
                "final_score": 0.1668,
                "score_gain": 0.0168,
                "final_match": 0.058,
                "final_key_idx": [13, 14, 15],
                "final_plaintext_idx": [16, 17, 18],
            },
        ],
    }


def test_build_stageb_fixture_comparison_keeps_replay_ready_selected_rows() -> None:
    fixture = _fixture(
        fixture_id="demo_control",
        policy="source_order",
    )

    out = build_stageb_fixture_comparison(fixture)

    assert str(out["legacy"]["candidate_hash"]) == "winner-hash"
    assert str(out["score_plus_novelty"]["candidate_hash"]) == "truth-hash"
    assert int(out["legacy"]["replay_material_complete"]) == 1
    assert int(out["score_plus_novelty"]["replay_material_complete"]) == 1
    assert int(out["replay_ready_selected_candidates"]) == 1


def test_write_stageb_replay_report_writes_selected_trial_material(
    tmp_path: Path,
) -> None:
    control_fixture = _fixture(
        fixture_id="demo_control",
        policy="source_order",
    )
    candidate_fixture = _fixture(
        fixture_id="demo_candidate",
        policy="novel_challenger_v1",
    )

    summary = write_stageb_replay_report(
        control_fixture=control_fixture,
        candidate_fixture=candidate_fixture,
        output_dir=tmp_path,
    )

    assert int(summary["control"]["replay_ready_selected_candidates"]) == 1
    assert int(summary["candidate"]["replay_ready_selected_candidates"]) == 1

    saved = json.loads((tmp_path / "selected_trial_material_rows.json").read_text(encoding="utf-8"))
    assert len(saved) == 8
    assert any(
        str(row["selector"]) == "score_plus_novelty"
        and str(row["candidate_hash"]) == "truth-hash"
        for row in saved
    )
    assert all(str(row["source_artifact_path"]) == "" for row in saved)
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "control_feature_rows.json").exists()
    assert (tmp_path / "candidate_feature_rows.json").exists()
    assert (tmp_path / "control_trial_material_rows.json").exists()
    assert (tmp_path / "candidate_trial_material_rows.json").exists()


def test_build_stageb_selected_trial_material_rows_keeps_final_material_lists() -> None:
    rows = build_stageb_selected_trial_material_rows(
        fixture_label="control",
        fixture=_fixture(fixture_id="demo_control", policy="source_order"),
    )

    assert len(rows) == 4
    assert all(isinstance(row["final_key_idx"], list) for row in rows)
    assert all(isinstance(row["final_plaintext_idx"], list) for row in rows)
    assert all("source_artifact_path" in row for row in rows)
