from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    analyse_current_scorer_failure_v1 as failure_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.analyse_current_scorer_failure_v1 import (
    ALLOWED_FAILURE_TYPES,
    CANDIDATE_FEATURE_FIELDS,
    build_failure_row,
    build_failure_rows,
    summarize_failure_rows,
    write_failure_outputs,
)


pytestmark = pytest.mark.tier_a


def _truth_gap_row(**overrides):
    row = {
        "run_dir": "output/tools/benchmarks/periodic_sub_trans/no_wli/demo_run",
        "key_seed": 1111,
        "search_seed": 7005,
        "best_stage": "stage3_search",
        "winner_candidate_hash": "winner-hash",
        "challenger_candidate_hash": "challenger-hash",
        "winner_truth_match": 0.400,
        "challenger_truth_match": 0.500,
        "winner_score": 0.250,
        "challenger_score": 0.200,
        "winner_source": "stage3_best_phaseB",
        "challenger_source": "phaseA_selected",
    }
    row.update(overrides)
    return row


def test_pairwise_truth_ranking_metric_and_gaps_are_correct() -> None:
    row = build_failure_row(_truth_gap_row())

    assert row["truth_gap_challenger_minus_winner"] == pytest.approx(0.100)
    assert row["score_gap_challenger_minus_winner"] == pytest.approx(-0.050)
    assert row["truth_better_candidate_hash"] == "challenger-hash"
    assert int(row["current_scorer_chose_truth_better"]) == 0
    assert row["failure_type"] == "truth_positive_present_but_under_scored"


def test_current_scorer_chose_truth_better_is_computed_correctly() -> None:
    row = build_failure_row(
        _truth_gap_row(
            winner_truth_match=0.500,
            challenger_truth_match=0.400,
            winner_score=0.250,
            challenger_score=0.200,
        )
    )

    assert row["truth_better_candidate_hash"] == "winner-hash"
    assert int(row["current_scorer_chose_truth_better"]) == 1


def test_missing_truth_labels_make_row_invalid_and_excluded_from_accuracy() -> None:
    rows = build_failure_rows(
        [
            _truth_gap_row(winner_truth_match=None, challenger_truth_match=None),
            _truth_gap_row(),
        ]
    )
    summary = summarize_failure_rows(rows)

    assert int(summary["pair_count"]) == 2
    assert int(summary["valid_accuracy_pair_count"]) == 1
    assert int(summary["current_scorer_wrong_count"]) == 1


def test_missing_component_scores_are_blank_and_marked_missing_not_zero() -> None:
    row = build_failure_row(_truth_gap_row())

    assert int(row["component_scores_available"]) == 0
    assert row["missing_component_score_reason"]
    assert row["winner_char_lm_score"] == ""
    assert row["challenger_word_ngram_score"] == ""


def test_failure_type_must_be_from_allowed_labels() -> None:
    row = build_failure_row(_truth_gap_row())

    assert str(row["failure_type"]) in ALLOWED_FAILURE_TYPES


def test_summary_counts_match_row_counts() -> None:
    rows = build_failure_rows(
        [
            _truth_gap_row(),
            _truth_gap_row(
                winner_candidate_hash="truth-winner",
                challenger_candidate_hash="worse-challenger",
                winner_truth_match=0.600,
                challenger_truth_match=0.500,
                winner_score=0.300,
                challenger_score=0.100,
            ),
        ]
    )
    summary = summarize_failure_rows(rows)

    assert int(summary["pair_count"]) == len(rows)
    assert int(summary["current_scorer_correct_count"]) == 1
    assert int(summary["current_scorer_wrong_count"]) == 1
    assert float(summary["current_scorer_pairwise_accuracy"]) == pytest.approx(0.5)


def test_summary_reports_unique_candidate_pairs_and_dominant_pair() -> None:
    rows = build_failure_rows(
        [
            _truth_gap_row(),
            _truth_gap_row(),
            _truth_gap_row(winner_candidate_hash="winner-2", challenger_candidate_hash="challenger-2"),
        ]
    )
    summary = summarize_failure_rows(rows)

    assert int(summary["row_occurrence_count"]) == 3
    assert int(summary["unique_candidate_pair_count"]) == 2
    assert int(summary["dominant_pair_count"]) == 2
    assert float(summary["dominant_pair_fraction"]) == pytest.approx(2 / 3)
    assert summary["candidate_pair_counts"]["winner-hash|challenger-hash"] == 2


def test_truth_or_oracle_fields_are_not_candidate_features() -> None:
    forbidden_tokens = ("truth", "oracle")

    assert CANDIDATE_FEATURE_FIELDS
    for field in CANDIDATE_FEATURE_FIELDS:
        assert not any(token in field for token in forbidden_tokens)


def test_write_failure_outputs_uses_expected_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(failure_mod, "REPO_ROOT", tmp_path)
    rows = build_failure_rows([_truth_gap_row()])
    out_dir = tmp_path / "current_scorer_failure_v1"

    summary = write_failure_outputs(rows=rows, output_dir=out_dir)

    assert int(summary["pair_count"]) == 1
    assert (out_dir / "current_scorer_failure_rows.csv").exists()
    assert (out_dir / "current_scorer_failure_rows.jsonl").exists()
    assert (out_dir / "current_scorer_failure_summary.json").exists()
    assert (out_dir / "current_scorer_failure_readout.md").exists()
