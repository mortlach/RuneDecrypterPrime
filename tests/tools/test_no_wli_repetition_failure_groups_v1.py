from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    analyse_repetition_failure_groups_v1 as groups_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.analyse_repetition_failure_groups_v1 import (
    build_readout,
    summarize_failure_group_rows,
    write_failure_group_outputs,
)


pytestmark = pytest.mark.tier_a


def _group_row(**overrides):
    row = {
        "group": "repeated_4gram_helps",
        "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/demo/final_instances/case.json",
        "bundle_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/demo",
        "best_stage": "stage2_search",
        "fixture_seed": 411,
        "search_seed": 0,
        "candidate_pair_key": "a|b",
        "truth_better_hash": "b",
        "truth_worse_hash": "a",
        "truth_better_source": "phaseA_selected",
        "truth_worse_source": "stage3_best_phaseB",
        "truth_better_source_rank": 2,
        "truth_worse_source_rank": 1,
        "truth_gap_abs": 0.2,
        "score_gap_abs": 0.05,
        "truth_better_current_score": 0.1,
        "truth_worse_current_score": 0.15,
        "truth_better_text_length": 1000,
        "truth_worse_text_length": 1000,
        "repeated_3gram_prefers_truth_better": 1,
        "repeated_4gram_prefers_truth_better": 1,
        "repeated_5gram_prefers_truth_better": 1,
        "repeated_6gram_prefers_truth_better": 0,
        "truth_better_repeated_3gram_rate": 0.1,
        "truth_worse_repeated_3gram_rate": 0.2,
        "truth_better_repeated_4gram_rate": 0.1,
        "truth_worse_repeated_4gram_rate": 0.2,
        "truth_better_repeated_5gram_rate": 0.1,
        "truth_worse_repeated_5gram_rate": 0.2,
        "truth_better_repeated_6gram_rate": 0.2,
        "truth_worse_repeated_6gram_rate": 0.1,
        "window_worst_repeated_4gram_prefers_truth_better": 1,
        "window_mean_repeated_4gram_prefers_truth_better": 1,
    }
    row.update(overrides)
    return row


def test_summary_splits_repeated_4gram_help_groups() -> None:
    rows = [
        _group_row(),
        _group_row(
            group="repeated_4gram_not_help",
            candidate_pair_key="c|d",
            best_stage="stage3_full_refine",
            truth_better_source="phaseB_topk",
            truth_worse_source="stage3_best_phaseA",
            repeated_3gram_prefers_truth_better=0,
            repeated_4gram_prefers_truth_better=0,
            repeated_5gram_prefers_truth_better=1,
        ),
    ]

    summary = summarize_failure_group_rows(rows)

    assert int(summary["unique_misranked_pair_count"]) == 2
    assert int(summary["repeated_4gram_helps_count"]) == 1
    assert int(summary["repeated_4gram_not_help_count"]) == 1
    assert summary["groups"]["repeated_4gram_helps"]["best_stage_counts"]["stage2_search"] == 1
    assert summary["groups"]["repeated_4gram_not_help"]["truth_better_source_counts"]["phaseB_topk"] == 1
    assert summary["groups"]["repeated_4gram_not_help"]["repeated_ngram_truth_better_counts"]["n5"] == 1


def test_readout_names_missing_diagnostics_explicitly() -> None:
    summary = summarize_failure_group_rows([_group_row()])

    readout = build_readout(summary)

    assert "Missing Diagnostics" in readout
    assert "word-ngram judge scores are not in the probe rows" in readout
    assert "span/dictionary coverage scores are not in the probe rows" in readout


def test_write_failure_group_outputs_uses_expected_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(groups_mod, "REPO_ROOT", tmp_path)
    out_dir = tmp_path / "repetition_failure_groups_v1"

    summary = write_failure_group_outputs(rows=[_group_row()], output_dir=out_dir)

    assert int(summary["unique_misranked_pair_count"]) == 1
    assert (out_dir / "repetition_failure_group_rows.csv").exists()
    assert (out_dir / "repetition_failure_group_rows.jsonl").exists()
    assert (out_dir / "repetition_failure_group_summary.json").exists()
    assert (out_dir / "repetition_failure_group_readout.md").exists()
