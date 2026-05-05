from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    audit_word_ngram_support_thresholds_v1 as mod,
)


def test_word_ngram_support_score_formulas() -> None:
    row = {
        "prefix_total_ge_1_rate": 1.0,
        "prefix_total_ge_10_rate": 0.5,
        "prefix_total_ge_100_rate": 0.25,
        "word_ngram_n_positions": 12,
    }

    assert mod.word_ngram_support_score(row, "ge10_ge100") == pytest.approx(0.375)
    assert mod.word_ngram_support_score(row, "ge1_ge10_ge100") == pytest.approx(0.5)
    assert mod.word_ngram_support_score(row, "ge10_only") == pytest.approx(0.5)
    assert mod.word_ngram_support_score(row, "ge100_only") == pytest.approx(0.25)
    assert 0.0 < mod.word_ngram_support_score(row, "positions_log_ge10_ge100") < 0.375


def test_evaluate_feature_counts_rescues_and_breaks() -> None:
    candidate_by_hash = {
        "w1": {"word_ngram_n_positions": 12, "prefix_total_ge_10_rate": 1, "prefix_total_ge_100_rate": 1},
        "c1": {"word_ngram_n_positions": 12, "prefix_total_ge_10_rate": 0, "prefix_total_ge_100_rate": 0},
        "w2": {"word_ngram_n_positions": 12, "prefix_total_ge_10_rate": 0, "prefix_total_ge_100_rate": 0},
        "c2": {"word_ngram_n_positions": 12, "prefix_total_ge_10_rate": 1, "prefix_total_ge_100_rate": 1},
    }
    pair_rows = [
        {
            "winner_token_hash": "w1",
            "challenger_token_hash": "c1",
            "current_score_correct": "0",
        },
        {
            "winner_token_hash": "w2",
            "challenger_token_hash": "c2",
            "current_score_correct": "1",
        },
    ]

    row = mod.evaluate_feature(
        pair_rows=pair_rows,
        candidate_by_hash=candidate_by_hash,
        feature_name="support_ge10_ge100",
        direction="higher",
        threshold=12,
        formula=lambda item, threshold: (
            mod.word_ngram_support_score(item, "ge10_ge100")
            if int(item["word_ngram_n_positions"]) >= threshold
            else 0.0
        ),
    )

    assert row["rescues"] == 1
    assert row["breaks"] == 1
    assert row["net"] == 0
    assert row["truth_better"] == 1
    assert row["truth_worse"] == 1


def test_active_counts_use_position_thresholds() -> None:
    rows = [
        {"word_ngram_n_positions": 0},
        {"word_ngram_n_positions": 6},
        {"word_ngram_n_positions": 12},
    ]

    active = {row["min_positions"]: row["active_candidates"] for row in mod._active_counts(rows)}

    assert active[1] == 2
    assert active[6] == 2
    assert active[12] == 1


def test_candidate_features_pass_span_interval_objects_to_word_runtime() -> None:
    interval = SimpleNamespace(start=0, end=3, length=3, distance=0, quality=1.0, weight=3.0)

    class FakeBackend:
        def score(self, tokens):
            assert tokens == [1, 2, 3, 4]
            return SimpleNamespace(selected_intervals=(interval,))

    class FakeRuntime:
        def score_candidate(self, *, text_idx, selected_intervals, direction):
            assert text_idx == [1, 2, 3, 4]
            assert direction == "ltr"
            assert selected_intervals == (interval,)
            assert hasattr(selected_intervals[0], "distance")
            return SimpleNamespace(
                available=True,
                active=True,
                inactive_reason=None,
                used5_rate=0.2,
                used4_rate=0.3,
                used3_rate=0.4,
                exact_word_count=1,
                segment_count=1,
                n_positions=2,
                xent_3=3.0,
                xent_backoff_5_4_3=2.5,
                miss_rate=0.0,
                prefix_total_mean=100.0,
                prefix_total_min=100.0,
                prefix_total_ge_1_rate=1.0,
                prefix_total_ge_10_rate=1.0,
                prefix_total_ge_100_rate=1.0,
            )

    row = mod._candidate_features(
        token_hash="hash",
        token_row={"token_sequence_text": "1 2 3 4"},
        backend=FakeBackend(),
        runtime=FakeRuntime(),
    )

    assert row["numeric_valid"] == 1
    assert row["span_selected_interval_count"] == 1
    assert row["word_ngram_n_positions"] == 2
