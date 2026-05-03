from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    audit_scorer_component_features_v1 as audit,
)


def _pair_row(**overrides):
    row = {
        "pair_id": "pair-1",
        "artifact_path": "artifact.json",
        "fixture_id": "fixture",
        "fixture_seed": "411",
        "search_seed": "0",
        "token_length": "6",
        "winner_candidate_hash": "cw",
        "challenger_candidate_hash": "cc",
        "winner_token_hash": "tw",
        "challenger_token_hash": "tc",
        "winner_truth_match": "0.90",
        "challenger_truth_match": "0.80",
        "truth_gap": "0.10",
        "winner_current_score": "0.10",
        "challenger_current_score": "0.20",
        "current_score_margin": "-0.10",
        "current_score_correct": "0",
    }
    row.update(overrides)
    return row


class _FakeSpanBackend:
    def score(self, tokens):
        _ = tokens
        intervals = (
            SimpleNamespace(length=3, weight=2.0),
            SimpleNamespace(length=4, weight=3.0),
        )
        return SimpleNamespace(
            span_raw=0.5,
            coverage=0.7,
            quality=0.8,
            n_intervals_selected=2,
            selected_intervals=intervals,
        )


class _FakeWordRuntime:
    def score_candidate(self, *, text_idx, selected_intervals, direction):
        _ = text_idx, selected_intervals, direction
        return SimpleNamespace(
            available=True,
            active=True,
            inactive_reason=None,
            trust_tier="medium",
            trust_score=0.6,
            xent_3=2.0,
            xent_backoff_5_4_3=1.5,
            exact_word_count=5,
            n_positions=12,
            miss_rate=0.1,
            used5_rate=0.2,
            used4_rate=0.3,
            used3_rate=0.4,
        )


def test_numeric_token_validation_rejects_outside_base29() -> None:
    assert audit.parse_numeric_tokens("0 1 28") == [0, 1, 28]

    for bad in ("", "0 29", "-1 0", "1 x"):
        with pytest.raises(ValueError):
            audit.parse_numeric_tokens(bad)


def test_candidate_feature_rows_are_built_once_per_unique_token_hash() -> None:
    pair_rows = [
        _pair_row(),
        _pair_row(pair_id="pair-2", winner_current_score="0.30"),
    ]
    token_rows = {
        "tw": {"token_sequence_text": "1 2 3 1 2 3"},
        "tc": {"token_sequence_text": "4 5 6 7 8 9"},
    }

    rows = audit.build_candidate_feature_rows(
        token_rows=token_rows,
        pair_rows=pair_rows,
        span_backend=None,
        span_missing_reason="span disabled",
        word_runtime=None,
        word_missing_reason="word disabled",
    )

    assert [row["token_hash"] for row in rows] == ["tc", "tw"]
    assert len(rows) == 2
    tw = {row["token_hash"]: row for row in rows}["tw"]
    assert int(tw["numeric_valid"]) == 1
    assert int(tw["current_score_value_count"]) == 2
    assert float(tw["repeated_3gram_rate"]) > 0.0
    assert tw["span_hamming_missing_reason"] == "span disabled"
    assert tw["word_ngram_missing_reason"] == "word disabled"


def test_span_and_word_features_are_reported_when_available() -> None:
    pair_rows = [_pair_row()]
    token_rows = {
        "tw": {"token_sequence_text": "1 2 3 1 2 3"},
        "tc": {"token_sequence_text": "4 5 6 7 8 9"},
    }

    rows = audit.build_candidate_feature_rows(
        token_rows=token_rows,
        pair_rows=pair_rows,
        span_backend=_FakeSpanBackend(),
        word_runtime=_FakeWordRuntime(),
    )

    first = rows[0]
    assert int(first["span_hamming_available"]) == 1
    assert float(first["span_raw_score"]) == pytest.approx(0.5)
    assert int(first["selected_interval_count"]) == 2
    assert int(first["word_ngram_available"]) == 1
    assert int(first["word_ngram_active"]) == 1
    assert str(first["word_ngram_trust_tier"]) == "medium"


def test_pair_feature_rows_join_candidate_features_and_keep_winner_truth_better() -> None:
    pair_rows = [_pair_row()]
    candidate_rows = [
        {"token_hash": "tw", "repeated_3gram_rate": 0.1},
        {"token_hash": "tc", "repeated_3gram_rate": 0.8},
    ]

    rows = audit.build_pair_feature_rows(pair_rows=pair_rows, candidate_feature_rows=candidate_rows)
    repeated = [
        row for row in rows
        if row["feature_name"] == "repeated_3gram_rate"
    ][0]
    current = [
        row for row in rows
        if row["feature_name"] == "current_score"
    ][0]

    assert repeated["winner_token_hash"] == "tw"
    assert int(repeated["feature_prefers_truth_better"]) == 1
    assert int(repeated["feature_prefers_truth_worse"]) == 0
    assert repeated["pair_group"] == "current_score_misranked"
    assert int(current["feature_prefers_truth_better"]) == 0
    assert int(current["feature_prefers_truth_worse"]) == 1


def test_missing_feature_values_are_not_coerced_to_zero() -> None:
    rows = audit.build_pair_feature_rows(
        pair_rows=[_pair_row()],
        candidate_feature_rows=[
            {"token_hash": "tw", "word_ngram_xent": ""},
            {"token_hash": "tc", "word_ngram_xent": ""},
        ],
    )

    word = [row for row in rows if row["feature_name"] == "word_ngram_xent"][0]
    assert int(word["feature_missing"]) == 1
    assert word["winner_feature_value"] == ""
    assert word["challenger_feature_value"] == ""
    assert word["feature_margin"] == ""


def test_feature_summary_reports_splits_unique_counts_and_net() -> None:
    pair_rows = [
        _pair_row(pair_id="mis", current_score_correct="0"),
        _pair_row(
            pair_id="ok",
            winner_token_hash="tw2",
            challenger_token_hash="tc2",
            winner_candidate_hash="cw2",
            challenger_candidate_hash="cc2",
            current_score_correct="1",
            winner_current_score="0.30",
            challenger_current_score="0.20",
        ),
    ]
    candidate_rows = [
        {"token_hash": "tw", "repeated_3gram_rate": 0.1},
        {"token_hash": "tc", "repeated_3gram_rate": 0.8},
        {"token_hash": "tw2", "repeated_3gram_rate": 0.9},
        {"token_hash": "tc2", "repeated_3gram_rate": 0.2},
    ]
    pair_feature_rows = audit.build_pair_feature_rows(
        pair_rows=pair_rows,
        candidate_feature_rows=candidate_rows,
    )

    summary_rows = audit.build_feature_summary_rows(pair_feature_rows)
    row = [item for item in summary_rows if item["feature_name"] == "repeated_3gram_rate"][0]

    assert int(row["available_pair_count"]) == 2
    assert int(row["current_misranked_prefers_truth_better"]) == 1
    assert int(row["current_correct_controls_prefers_truth_worse"]) == 1
    assert int(row["rescues"]) == 1
    assert int(row["breaks"]) == 1
    assert int(row["net"]) == 0
    assert int(row["unique_text_pair_count"]) == 2


def test_summary_declares_report_only_and_truth_is_evaluation_only() -> None:
    pair_rows = [_pair_row()]
    candidate_rows = [
        {"token_hash": "tw", "span_hamming_available": 0, "word_ngram_available": 0, "word_ngram_active": 0},
        {"token_hash": "tc", "span_hamming_available": 0, "word_ngram_available": 0, "word_ngram_active": 0},
    ]
    pair_feature_rows = audit.build_pair_feature_rows(
        pair_rows=pair_rows,
        candidate_feature_rows=candidate_rows,
    )
    feature_summary_rows = audit.build_feature_summary_rows(pair_feature_rows)

    summary = audit.build_summary(
        pair_rows=pair_rows,
        candidate_feature_rows=candidate_rows,
        pair_feature_rows=pair_feature_rows,
        feature_summary_rows=feature_summary_rows,
        elapsed_seconds=1.0,
    )

    assert summary["runtime_behavior_changed"] is False
    assert summary["truth_is_evaluation_only"] is True
    assert "0..28" in summary["representation_rule"]
