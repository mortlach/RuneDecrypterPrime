from __future__ import annotations

from rune_decrypter_prime.core.component_contracts import ScorerLaneName
from rune_decrypter_prime.core.config.scoring import ScoringConfig


def _lanes(cfg: ScoringConfig) -> tuple[ScorerLaneName, ...]:
    return tuple(cfg.requested_scorer_lanes())


def test_default_config_requests_no_optional_scorer_lanes() -> None:
    assert _lanes(ScoringConfig()) == tuple()


def test_hamming_enabled_requests_hamming_lane() -> None:
    assert _lanes(ScoringConfig(hamming_enabled=True)) == (
        ScorerLaneName.HAMMING,
    )


def test_nonzero_hamming_weight_requests_hamming_lane() -> None:
    assert _lanes(ScoringConfig(hamming_weight=0.01)) == (
        ScorerLaneName.HAMMING,
    )


def test_zero_hamming_weight_alone_does_not_request_hamming_lane() -> None:
    assert _lanes(ScoringConfig(hamming_weight=0.0)) == tuple()


def test_raw_span_mode_requests_raw_span_lane() -> None:
    assert _lanes(ScoringConfig(span_hamming_mode="raw_bonus")) == (
        ScorerLaneName.SPAN_HAMMING_RAW,
    )


def test_span_enabled_legacy_flag_requests_raw_span_lane() -> None:
    assert _lanes(ScoringConfig(span_hamming_enabled=True)) == (
        ScorerLaneName.SPAN_HAMMING_RAW,
    )


def test_nonzero_span_weight_requests_raw_span_lane() -> None:
    assert _lanes(ScoringConfig(span_hamming_weight=0.5)) == (
        ScorerLaneName.SPAN_HAMMING_RAW,
    )


def test_calibrated_span_mode_requests_calibrated_lane_only() -> None:
    assert _lanes(
        ScoringConfig(
            span_hamming_mode="calibrated",
            span_hamming_enabled=True,
            span_hamming_weight=0.5,
        )
    ) == (
        ScorerLaneName.SPAN_HAMMING_CALIBRATED,
    )


def test_word_ngram_judge_requests_report_only_lane(tmp_path) -> None:
    assert _lanes(
        ScoringConfig(
            word_ngram_judge_enabled=True,
            word_ngram_judge_sqlite_path=tmp_path / "word_ngram.sqlite",
        )
    ) == (
        ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY,
    )


def test_requested_lane_order_is_stable_with_raw_span(tmp_path) -> None:
    assert _lanes(
        ScoringConfig(
            hamming_enabled=True,
            span_hamming_mode="raw_bonus",
            word_ngram_judge_enabled=True,
            word_ngram_judge_sqlite_path=tmp_path / "word_ngram.sqlite",
        )
    ) == (
        ScorerLaneName.HAMMING,
        ScorerLaneName.SPAN_HAMMING_RAW,
        ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY,
    )


def test_requested_lane_order_is_stable_with_calibrated_span(tmp_path) -> None:
    assert _lanes(
        ScoringConfig(
            hamming_enabled=True,
            span_hamming_mode="calibrated",
            word_ngram_judge_enabled=True,
            word_ngram_judge_sqlite_path=tmp_path / "word_ngram.sqlite",
        )
    ) == (
        ScorerLaneName.HAMMING,
        ScorerLaneName.SPAN_HAMMING_CALIBRATED,
        ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY,
    )
