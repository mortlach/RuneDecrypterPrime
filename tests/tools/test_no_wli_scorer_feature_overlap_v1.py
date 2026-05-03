from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    analyse_scorer_feature_overlap_v1 as overlap,
)


def _feature_row(
    *,
    pair_id: str,
    feature_name: str,
    current_score_correct: int,
    prefers_better: int = 0,
    prefers_worse: int = 0,
    tie: int = 0,
    missing: int = 0,
) -> dict[str, object]:
    return {
        "pair_id": pair_id,
        "artifact_path": f"{pair_id}.json",
        "fixture_id": "fixture",
        "fixture_seed": "411",
        "search_seed": "0",
        "token_length": "1000",
        "winner_candidate_hash": f"cw-{pair_id}",
        "challenger_candidate_hash": f"cc-{pair_id}",
        "winner_token_hash": f"tw-{pair_id}",
        "challenger_token_hash": f"tc-{pair_id}",
        "truth_gap": "0.1",
        "current_score_correct": str(current_score_correct),
        "pair_group": "current_score_correct" if current_score_correct else "current_score_misranked",
        "feature_name": feature_name,
        "feature_prefers_truth_better": prefers_better,
        "feature_prefers_truth_worse": prefers_worse,
        "feature_tie": tie,
        "feature_missing": missing,
        "text_pair_key": f"tc-{pair_id}||tw-{pair_id}",
        "candidate_hash_pair_key": f"cc-{pair_id}||cw-{pair_id}",
    }


def test_pair_flag_rows_collect_selected_feature_flags() -> None:
    rows = [
        _feature_row(
            pair_id="p1",
            feature_name="span_raw_score",
            current_score_correct=0,
            prefers_better=1,
        ),
        _feature_row(
            pair_id="p1",
            feature_name="word_ngram_trust_score",
            current_score_correct=0,
            tie=1,
        ),
        _feature_row(
            pair_id="p1",
            feature_name="not_selected",
            current_score_correct=0,
            prefers_worse=1,
        ),
    ]

    flags = overlap.build_pair_flag_rows(rows)

    assert len(flags) == 1
    row = flags[0]
    assert int(row["span_raw_score_prefers_truth_better"]) == 1
    assert int(row["word_ngram_trust_score_tie"]) == 1
    assert "not_selected_prefers_truth_worse" not in row


def test_feature_rollup_reports_rescues_breaks_ties_and_unique_scope() -> None:
    rows = [
        _feature_row(
            pair_id="mis1",
            feature_name="span_raw_score",
            current_score_correct=0,
            prefers_better=1,
        ),
        _feature_row(
            pair_id="ok1",
            feature_name="span_raw_score",
            current_score_correct=1,
            prefers_worse=1,
        ),
        _feature_row(
            pair_id="ok2",
            feature_name="span_raw_score",
            current_score_correct=1,
            tie=1,
        ),
    ]
    flags = overlap.build_pair_flag_rows(rows)

    rollup = overlap.build_feature_rollup_rows(flags)
    span_row = [
        row for row in rollup
        if row["feature_name"] == "span_raw_score" and row["scope"] == "row_occurrence"
    ][0]

    assert int(span_row["pair_count"]) == 3
    assert int(span_row["rescues"]) == 1
    assert int(span_row["breaks"]) == 1
    assert int(span_row["ties_on_controls"]) == 1
    assert int(span_row["net"]) == 0


def test_overlap_matrix_counts_joint_rescues_and_breaks() -> None:
    rows = [
        _feature_row(
            pair_id="mis-both",
            feature_name="span_raw_score",
            current_score_correct=0,
            prefers_better=1,
        ),
        _feature_row(
            pair_id="mis-both",
            feature_name="word_ngram_trust_score",
            current_score_correct=0,
            prefers_better=1,
        ),
        _feature_row(
            pair_id="mis-span-only",
            feature_name="span_raw_score",
            current_score_correct=0,
            prefers_better=1,
        ),
        _feature_row(
            pair_id="mis-span-only",
            feature_name="word_ngram_trust_score",
            current_score_correct=0,
            tie=1,
        ),
        _feature_row(
            pair_id="ok-break",
            feature_name="span_raw_score",
            current_score_correct=1,
            prefers_worse=1,
        ),
        _feature_row(
            pair_id="ok-break",
            feature_name="word_ngram_trust_score",
            current_score_correct=1,
            prefers_worse=1,
        ),
    ]
    flags = overlap.build_pair_flag_rows(rows)

    matrix = overlap.build_overlap_rows(flags)
    row = [
        item for item in matrix
        if item["feature_a"] == "span_raw_score"
        and item["feature_b"] == "word_ngram_trust_score"
        and item["scope"] == "row_occurrence"
    ][0]

    assert int(row["a_rescues"]) == 2
    assert int(row["b_rescues"]) == 1
    assert int(row["both_rescue"]) == 1
    assert int(row["a_only_rescue"]) == 1
    assert int(row["either_rescue"]) == 2
    assert int(row["both_break"]) == 1
    assert float(row["rescue_jaccard"]) == 0.5


def test_summary_is_report_only_and_truth_evaluation_only() -> None:
    rows = [
        _feature_row(
            pair_id="mis1",
            feature_name="span_raw_score",
            current_score_correct=0,
            prefers_better=1,
        )
    ]
    flags = overlap.build_pair_flag_rows(rows)
    rollup = overlap.build_feature_rollup_rows(flags)
    matrix = overlap.build_overlap_rows(flags)

    summary = overlap.build_summary(
        pair_flag_rows=flags,
        feature_rollup_rows=rollup,
        overlap_rows=matrix,
    )

    assert summary["runtime_behavior_changed"] is False
    assert summary["truth_is_evaluation_only"] is True
    assert int(summary["pair_count"]) == 1
    assert "span_raw_vs_word_trust_row_overlap" in summary
