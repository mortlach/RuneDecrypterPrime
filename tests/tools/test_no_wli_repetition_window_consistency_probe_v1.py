from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    probe_repetition_window_consistency_v1 as probe_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.probe_repetition_window_consistency_v1 import (
    repeated_ngram_rate,
    summarize_probe_rows,
    window_repeated_ngram_metrics,
    write_probe_outputs,
)


pytestmark = pytest.mark.tier_a


def _probe_row(**overrides):
    row = {
        "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/demo/final_instances/case.json",
        "bundle_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/demo",
        "fixture_seed": 411,
        "search_seed": 0,
        "candidate_a_hash": "winner",
        "candidate_b_hash": "challenger",
        "truth_better_side": "b",
        "score_better_side": "a",
        "current_score_chose_truth_better": 0,
        "truth_gap_abs": 0.2,
        "score_gap_abs": 0.05,
        "candidate_a_truth_match": 0.2,
        "candidate_b_truth_match": 0.4,
        "candidate_a_current_score": 0.3,
        "candidate_b_current_score": 0.25,
        "candidate_a_source": "stage3_best_phaseB",
        "candidate_b_source": "phaseA_selected",
        "candidate_a_source_rank": 1,
        "candidate_b_source_rank": 2,
        "candidate_a_text_length": 1000,
        "candidate_b_text_length": 1000,
        "candidate_a_repeated_4gram_rate": 0.08,
        "candidate_b_repeated_4gram_rate": 0.04,
        "repeated_4gram_prefers_truth_better": 1,
        "candidate_a_window_repeated_4gram_mean": 0.09,
        "candidate_b_window_repeated_4gram_mean": 0.05,
        "candidate_a_window_repeated_4gram_worst": 0.2,
        "candidate_b_window_repeated_4gram_worst": 0.1,
        "candidate_a_window_repeated_4gram_variance": 0.01,
        "candidate_b_window_repeated_4gram_variance": 0.02,
        "window_worst_repeated_4gram_prefers_truth_better": 1,
        "window_mean_repeated_4gram_prefers_truth_better": 1,
    }
    row.update(overrides)
    return row


def test_repeated_ngram_rate_detects_repeated_positions() -> None:
    assert repeated_ngram_rate([1, 2, 3]) == ""
    assert float(repeated_ngram_rate([1, 2, 3, 4, 1, 2, 3, 4])) > 0.0


def test_window_repeated_ngram_metrics_report_mean_worst_variance() -> None:
    tokens = ([1, 2, 3, 4] * 50) + ([5, 6, 7, 8] * 50)

    metrics = window_repeated_ngram_metrics(tokens, window_size=40, window_step=20, n=4)

    assert int(metrics["window_count"]) > 0
    assert float(metrics["worst"]) >= float(metrics["mean"])
    assert float(metrics["variance"]) >= 0.0


def test_summary_separates_row_occurrences_unique_pairs_and_controls() -> None:
    rows = [
        _probe_row(),
        _probe_row(),
        _probe_row(
            candidate_a_hash="control-a",
            candidate_b_hash="control-b",
            truth_better_side="b",
            score_better_side="b",
            current_score_chose_truth_better=1,
            repeated_4gram_prefers_truth_better=0,
            window_worst_repeated_4gram_prefers_truth_better=0,
            window_mean_repeated_4gram_prefers_truth_better=0,
        ),
    ]

    summary = summarize_probe_rows(rows)

    assert int(summary["row_occurrence_count"]) == 3
    assert int(summary["unique_candidate_pair_count"]) == 2
    assert int(summary["score_misranked_row_count"]) == 2
    assert int(summary["score_misranked_unique_pair_count"]) == 1
    assert int(summary["score_correct_row_count"]) == 1
    assert int(summary["score_correct_unique_pair_count"]) == 1
    assert summary["repeated_4gram_misranked_rows"]["truth_better_count"] == 2
    assert summary["repeated_4gram_misranked_rows"]["not_truth_better_count"] == 0
    assert summary["repeated_4gram_misranked_unique_pairs"]["truth_better_count"] == 1
    assert summary["repeated_4gram_correct_rows"]["not_truth_better_count"] == 1


def test_write_probe_outputs_uses_expected_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe_mod, "REPO_ROOT", tmp_path)
    out_dir = tmp_path / "repetition_window_consistency_probe_v1"

    summary = write_probe_outputs(rows=[_probe_row()], output_dir=out_dir)

    assert int(summary["row_occurrence_count"]) == 1
    assert (out_dir / "repetition_window_consistency_probe_rows.csv").exists()
    assert (out_dir / "repetition_window_consistency_probe_rows.jsonl").exists()
    assert (out_dir / "repetition_window_consistency_probe_summary.json").exists()
    assert (out_dir / "repetition_window_consistency_probe_readout.md").exists()
