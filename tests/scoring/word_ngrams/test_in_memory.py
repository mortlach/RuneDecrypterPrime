from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.scoring.word_ngrams import (
    RuneTokenWordNgramMemoryModel,
    RuneTokenWordNgramScorer,
    summarize_prefix_total_confidence,
    summarize_word_ngram_report_trust,
    wli_pairs_from_flat_array,
    word_ngram_report_is_active,
    word_tokens_from_idx_and_wli,
)


pytestmark = pytest.mark.tier_a


def test_word_tokens_from_idx_and_wli_splits_words() -> None:
    text = [1, 2, 3, 4, 5]
    wli = [(0, 2), (1, 2), (0, 3), (1, 3), (2, 3)]
    tokens = word_tokens_from_idx_and_wli(text, wli)
    assert tokens == (bytes([1, 2]), bytes([3, 4, 5]))


def test_wli_pairs_from_flat_array_reshapes_pairs() -> None:
    flat = np.asarray([0, 2, 1, 2, 0, 1], dtype=np.uint8)
    pairs = wli_pairs_from_flat_array(flat)
    assert pairs == ((0, 2), (1, 2), (0, 1))


def test_memory_model_and_scorer_count_trigrams() -> None:
    model = RuneTokenWordNgramMemoryModel.from_token_sequences(
        [
            (b"a", b"b", b"c", b"d"),
            (b"a", b"b", b"c", b"e"),
        ],
        orders=(3,),
    )
    scorer = RuneTokenWordNgramScorer(model, alpha=0.4, miss_logp=-20.0)
    scored = scorer.score_segments([(b"a", b"b", b"c", b"d")])
    assert scored.n_positions == 2
    assert scored.used3_rate == pytest.approx(1.0)
    assert scored.miss_rate == pytest.approx(0.0)
    assert scored.xent_3 > 0.0


def test_memory_model_from_tokenized_npz_paths(tmp_path) -> None:
    fp = tmp_path / "toy_fwd.npz"
    np.savez(
        fp,
        pt_nose_data=np.asarray([1, 2, 3, 4, 5], dtype=np.uint8),
        wli_nose_data=np.asarray([0, 2, 1, 2, 0, 3, 1, 3, 2, 3], dtype=np.uint8),
    )
    model = RuneTokenWordNgramMemoryModel.from_tokenized_npz_paths([fp], orders=(3,))
    scorer = RuneTokenWordNgramScorer(model)
    scored = scorer.score_segments([(bytes([1, 2]), bytes([3, 4, 5]), bytes([1, 2]))])
    assert scored.n_positions == 1
    assert np.isfinite(scored.xent_3)


def test_backoff_short_context_does_not_over_penalize() -> None:
    model = RuneTokenWordNgramMemoryModel.from_token_sequences(
        [
            (b"a", b"b", b"c"),
            (b"a", b"b", b"c"),
            (b"b", b"c", b"d"),
        ],
        orders=(3,),
    )
    scorer = RuneTokenWordNgramScorer(model, alpha=0.4, miss_logp=-20.0)
    diag = scorer.score_segments_with_diagnostics([(b"a", b"b", b"c")])
    assert diag.score.n_positions == 1
    assert diag.score.used3_rate == pytest.approx(1.0)
    assert diag.score.used4_rate == pytest.approx(0.0)
    assert diag.score.used5_rate == pytest.approx(0.0)
    assert diag.score.xent_backoff_5_4_3 == pytest.approx(diag.score.xent_3)


def test_backoff_applies_only_available_fallback_penalty() -> None:
    model = RuneTokenWordNgramMemoryModel.from_token_sequences(
        [
            (b"a", b"b", b"c"),
            (b"a", b"b", b"c"),
            (b"b", b"c", b"d"),
        ],
        orders=(3,),
    )
    scorer = RuneTokenWordNgramScorer(model, alpha=0.4, miss_logp=-20.0)
    diag = scorer.score_segments_with_diagnostics([(b"x", b"a", b"b", b"c")])
    assert diag.score.n_positions == 2
    assert diag.score.used3_rate == pytest.approx(0.5)
    assert diag.score.used4_rate == pytest.approx(0.0)
    assert diag.score.used5_rate == pytest.approx(0.0)
    assert diag.score.miss_rate == pytest.approx(0.5)
    expected = float((-(-20.0 + np.log(0.4))) / 2.0)
    assert diag.score.xent_backoff_5_4_3 == pytest.approx(expected)


def test_prefix_total_confidence_summary_and_report_gate() -> None:
    summary = summarize_prefix_total_confidence((0, 10, 100), thresholds=(1, 10, 100))
    assert summary["prefix_total_mean"] == pytest.approx((0.0 + 10.0 + 100.0) / 3.0)
    assert summary["prefix_total_min"] == pytest.approx(0.0)
    assert summary["prefix_total_ge_1_rate"] == pytest.approx(2.0 / 3.0)
    assert summary["prefix_total_ge_10_rate"] == pytest.approx(2.0 / 3.0)
    assert summary["prefix_total_ge_100_rate"] == pytest.approx(1.0 / 3.0)
    assert word_ngram_report_is_active(n_positions=11, min_positions=12) is False
    assert word_ngram_report_is_active(n_positions=12, min_positions=12) is True


def test_no_position_segments_return_zeroed_score_and_empty_confidence() -> None:
    model = RuneTokenWordNgramMemoryModel.from_token_sequences([(b"a", b"b", b"c")], orders=(3,))
    scorer = RuneTokenWordNgramScorer(model)
    diag = scorer.score_segments_with_diagnostics([(b"a",), (b"b", b"c")])
    assert diag.score.n_positions == 0
    assert diag.score.xent_3 == pytest.approx(0.0)
    assert diag.score.xent_backoff_5_4_3 == pytest.approx(0.0)
    assert diag.prefix_totals_3 == ()


def test_report_trust_summary_is_inactive_without_coverage() -> None:
    trust = summarize_word_ngram_report_trust(
        n_positions=5,
        min_positions=12,
        prefix_total_ge_10_rate=1.0,
        prefix_total_ge_100_rate=1.0,
    )
    assert trust.active is False
    assert trust.trust_score == pytest.approx(0.0)
    assert trust.trust_tier == "inactive"


def test_report_trust_summary_scales_with_prefix_support() -> None:
    weak = summarize_word_ngram_report_trust(
        n_positions=12,
        min_positions=12,
        prefix_total_ge_10_rate=0.2,
        prefix_total_ge_100_rate=0.0,
    )
    medium = summarize_word_ngram_report_trust(
        n_positions=12,
        min_positions=12,
        prefix_total_ge_10_rate=0.5,
        prefix_total_ge_100_rate=0.0,
    )
    strong = summarize_word_ngram_report_trust(
        n_positions=12,
        min_positions=12,
        prefix_total_ge_10_rate=0.8,
        prefix_total_ge_100_rate=0.4,
    )
    assert weak.active is True
    assert weak.trust_tier == "weak"
    assert medium.trust_tier == "medium"
    assert strong.trust_tier == "strong"
    assert weak.trust_score < medium.trust_score < strong.trust_score


def test_multi_order_backoff_uses_higher_order_context_when_available() -> None:
    model = RuneTokenWordNgramMemoryModel.from_token_sequences(
        [
            (b"a", b"b", b"c", b"d", b"e"),
            (b"a", b"b", b"c", b"d", b"f"),
            (b"x", b"b", b"c", b"d", b"g"),
        ],
        orders=(3, 4, 5),
    )
    scorer = RuneTokenWordNgramScorer(model, alpha=0.4, miss_logp=-20.0)
    diag = scorer.score_segments_with_diagnostics([(b"a", b"b", b"c", b"d", b"e")])
    assert diag.score.n_positions == 3
    assert diag.score.used5_rate == pytest.approx(1.0 / 3.0)
    assert diag.score.used4_rate == pytest.approx(1.0 / 3.0)
    assert diag.score.used3_rate == pytest.approx(1.0 / 3.0)
    assert diag.score.miss_rate == pytest.approx(0.0)
    assert np.isfinite(diag.score.xent_backoff_5_4_3)
